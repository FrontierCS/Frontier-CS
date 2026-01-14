import os
import sys
import re
import random
import time
import importlib
from typing import List, Tuple, Optional, Dict, Set, Iterable


class Solution:
    def solve(self, resources_path: str) -> list[str]:
        engine_dir = os.path.join(resources_path, "sql_engine")
        if resources_path not in sys.path:
            sys.path.insert(0, resources_path)

        parse_sql = None
        try:
            eng = importlib.import_module("sql_engine")
            parse_sql = getattr(eng, "parse_sql", None)
            if parse_sql is None:
                parse_sql = importlib.import_module("sql_engine.parser").parse_sql
        except Exception:
            # As a last resort, return a few common SQL statements
            return [
                "SELECT 1",
                "SELECT * FROM t",
                "CREATE TABLE t(a INTEGER, b TEXT)",
                "INSERT INTO t(a,b) VALUES(1,'x')",
                "UPDATE t SET a=a+1 WHERE a=1",
                "DELETE FROM t WHERE a=1",
            ]

        grammar_text = self._read_text(os.path.join(resources_path, "sql_grammar.txt"))
        parser_text = self._read_text(os.path.join(engine_dir, "parser.py"))
        tokenizer_text = self._read_text(os.path.join(engine_dir, "tokenizer.py"))
        ast_text = self._read_text(os.path.join(engine_dir, "ast_nodes.py"))

        keywords = self._extract_keywords(grammar_text + "\n" + parser_text + "\n" + tokenizer_text)

        try:
            import coverage  # type: ignore
            cov_available = True
        except Exception:
            coverage = None
            cov_available = False

        def try_parse(stmt: str) -> bool:
            try:
                parse_sql(stmt)
                return True
            except Exception:
                return False

        candidates = self._generate_candidates(keywords, grammar_text, parser_text, tokenizer_text, ast_text)
        valid = []
        seen = set()
        for s in candidates:
            s2 = self._normalize_stmt(s)
            if not s2 or s2 in seen:
                continue
            if try_parse(s2):
                valid.append(s2)
                seen.add(s2)

        if not valid:
            # minimal fallback
            base = ["SELECT 1", "SELECT * FROM t", "SELECT 1+2*3", "SELECT 'a''b'"]
            return [s for s in base if try_parse(s)] or ["SELECT 1"]

        if not cov_available:
            return valid[: min(30, len(valid))]

        target_basenames = {"parser.py", "tokenizer.py", "ast_nodes.py"}

        cov_cache: Dict[str, Tuple[frozenset, frozenset]] = {}

        def stmt_coverage(stmt: str) -> Tuple[frozenset, frozenset]:
            if stmt in cov_cache:
                return cov_cache[stmt]
            lines_cov: Set[Tuple[str, int]] = set()
            arcs_cov: Set[Tuple[str, int, int]] = set()

            cov = coverage.Coverage(branch=True, source=[engine_dir], data_file=None, config_file=False)
            cov.erase()
            cov.start()
            ok = False
            try:
                parse_sql(stmt)
                ok = True
            except Exception:
                ok = False
            finally:
                cov.stop()
                cov.save()
            if not ok:
                cov_cache[stmt] = (frozenset(), frozenset())
                return cov_cache[stmt]
            try:
                data = cov.get_data()
                for f in data.measured_files():
                    bn = os.path.basename(f)
                    if bn not in target_basenames:
                        continue
                    ls = data.lines(f) or []
                    for ln in ls:
                        lines_cov.add((bn, int(ln)))
                    arcs = data.arcs(f) or []
                    for a in arcs:
                        if a is None:
                            continue
                        try:
                            fr, to = a
                        except Exception:
                            continue
                        if fr is None or to is None:
                            continue
                        arcs_cov.add((bn, int(fr), int(to)))
            except Exception:
                pass

            cov_cache[stmt] = (frozenset(lines_cov), frozenset(arcs_cov))
            return cov_cache[stmt]

        # Seed coverage cache for valid statements (limit to avoid excessive time)
        max_valid_for_cov = min(len(valid), 250)
        for i in range(max_valid_for_cov):
            stmt_coverage(valid[i])

        # Coverage-guided fuzzing to discover additional valid statements that add new coverage
        rng = random.Random(0)
        corpus = valid[:]
        corpus_set = set(corpus)
        global_lines: Set[Tuple[str, int]] = set()
        global_arcs: Set[Tuple[str, int, int]] = set()
        for s in corpus[: min(50, len(corpus))]:
            l, a = stmt_coverage(s)
            global_lines |= set(l)
            global_arcs |= set(a)

        start_time = time.perf_counter()
        time_budget = 6.0
        max_iters = 500

        for _ in range(max_iters):
            if time.perf_counter() - start_time > time_budget:
                break
            base_stmt = corpus[rng.randrange(len(corpus))]
            mutated = self._mutate_stmt(base_stmt, rng)
            mutated = self._normalize_stmt(mutated)
            if not mutated or mutated in corpus_set:
                continue
            if not try_parse(mutated):
                continue
            l, a = stmt_coverage(mutated)
            if not l and not a:
                continue
            new_lines = set(l) - global_lines
            new_arcs = set(a) - global_arcs
            if new_lines or new_arcs:
                corpus.append(mutated)
                corpus_set.add(mutated)
                global_lines |= set(l)
                global_arcs |= set(a)

        # Filter to statements for which coverage was computed or can be computed quickly
        pool = corpus[:]
        # Ensure coverage cached
        for s in pool:
            if s not in cov_cache:
                stmt_coverage(s)

        # Remove exact-duplicate coverage statements to reduce pool size
        sig_map: Dict[Tuple[int, int, int], str] = {}
        reduced_pool = []
        for s in pool:
            l, a = cov_cache.get(s, (frozenset(), frozenset()))
            sig = (len(l), len(a), hash(l) ^ (hash(a) << 1))
            prior = sig_map.get(sig)
            if prior is not None:
                # keep both if different text and might hit different branches even with same size; but prune aggressively
                continue
            sig_map[sig] = s
            reduced_pool.append(s)
        if reduced_pool:
            pool = reduced_pool

        # Greedy selection maximizing new coverage
        selected = self._greedy_select(pool, cov_cache, max_cases=30)

        # Backward elimination
        selected = self._minimize_selected(selected, cov_cache)

        # Try to bundle into fewer scripts (multi-statement inputs), verifying coverage is preserved
        scripts = self._bundle_statements(selected, parse_sql, stmt_coverage, cov_cache)

        # Final sanity: ensure all scripts parse
        final_scripts = []
        for sc in scripts:
            sc2 = sc.strip()
            if not sc2:
                continue
            if try_parse(sc2):
                final_scripts.append(sc2)
        if not final_scripts:
            final_scripts = selected[: min(30, len(selected))]

        return final_scripts

    def _read_text(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    def _normalize_stmt(self, s: str) -> str:
        s = s.strip()
        if not s:
            return ""
        # Normalize line endings, but keep internal whitespace (tokenizer coverage)
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        # Strip excessive trailing semicolons
        s = re.sub(r"[;\s]+$", "", s)
        return s

    def _extract_keywords(self, text: str) -> Set[str]:
        kws: Set[str] = set()
        # From string literals in code/grammar
        for m in re.finditer(r"(['\"])([A-Za-z_][A-Za-z0-9_ ]{0,30})\1", text):
            v = m.group(2)
            if v and v.upper() == v and len(v) <= 30:
                for w in v.split():
                    if 2 <= len(w) <= 20 and w.isupper():
                        kws.add(w)
        # Uppercase words
        for w in re.findall(r"\b[A-Z][A-Z0-9_]{1,24}\b", text):
            if 2 <= len(w) <= 20:
                kws.add(w)
        # Remove some that aren't SQL keywords
        for bad in ("PYTHON", "TRUE", "FALSE"):
            pass
        return kws

    def _add_unique(self, lst: List[str], seen: Set[str], stmt: str) -> None:
        stmt2 = stmt.strip()
        if not stmt2:
            return
        if stmt2 in seen:
            return
        seen.add(stmt2)
        lst.append(stmt2)

    def _generate_candidates(
        self,
        keywords: Set[str],
        grammar_text: str,
        parser_text: str,
        tokenizer_text: str,
        ast_text: str,
    ) -> List[str]:
        seen: Set[str] = set()
        out: List[str] = []

        def add(s: str) -> None:
            self._add_unique(out, seen, s)

        # Basic literals / expressions
        add("SELECT 1")
        add("SELECT 1+2*3")
        add("SELECT (1+2)*3")
        add("SELECT -1, +2")
        add("SELECT NULL")
        add("SELECT 'x'")
        add("SELECT 'a''b'")
        add("SELECT \"a\"")
        add("SELECT `a`")
        add("SELECT [a]")
        add("SELECT 1.0")
        add("SELECT 1e3")
        add("SELECT 1.2e-3")
        add("SELECT X'ABCD'")

        # Tokenizer comment handling
        add("-- comment\nSELECT 1")
        add("/* comment */ SELECT 1")
        add("SELECT 1 -- trailing comment")
        add("SELECT /* inline */ 1")

        # Parameters / placeholders
        add("SELECT ?")
        add("SELECT ?1, ?2")
        add("SELECT :x, @y, $z")

        # Basic SELECT forms
        add("SELECT * FROM t")
        add("SELECT t.* FROM t")
        add("SELECT a, b FROM t")
        add("SELECT a AS b FROM t")
        add("SELECT a b FROM t")
        add("SELECT DISTINCT a FROM t")
        add("SELECT ALL a FROM t")

        # WHERE expressions
        add("SELECT a FROM t WHERE a=1")
        add("SELECT a FROM t WHERE a<>1")
        add("SELECT a FROM t WHERE a!=1")
        add("SELECT a FROM t WHERE a<1 OR a>2")
        add("SELECT a FROM t WHERE NOT (a=1 AND b=2)")
        add("SELECT a FROM t WHERE a IS NULL")
        add("SELECT a FROM t WHERE a IS NOT NULL")
        add("SELECT a FROM t WHERE a BETWEEN 1 AND 3")
        add("SELECT a FROM t WHERE a NOT BETWEEN 1 AND 3")
        add("SELECT a FROM t WHERE a IN (1,2,3)")
        add("SELECT a FROM t WHERE a NOT IN (1,2,3)")
        add("SELECT a FROM t WHERE a LIKE 'x%'")
        add(r"SELECT a FROM t WHERE a LIKE 'x\_%' ESCAPE '\'")

        # ORDER/LIMIT
        add("SELECT a FROM t ORDER BY a")
        add("SELECT a FROM t ORDER BY a DESC, b ASC")
        add("SELECT a FROM t ORDER BY 1")
        add("SELECT a FROM t LIMIT 1")
        add("SELECT a FROM t LIMIT 10 OFFSET 5")

        # GROUP BY / HAVING
        add("SELECT a, COUNT(*) FROM t GROUP BY a")
        add("SELECT a, COUNT(*) FROM t GROUP BY a HAVING COUNT(*)>1")

        # Functions / CASE / CAST / COALESCE
        add("SELECT COUNT(*) FROM t")
        add("SELECT COUNT(DISTINCT a) FROM t")
        add("SELECT SUM(a), AVG(a), MIN(a), MAX(a) FROM t")
        add("SELECT COALESCE(a,0) FROM t")
        add("SELECT CAST(a AS TEXT) FROM t")
        add("SELECT CASE WHEN a>1 THEN 'x' ELSE 'y' END FROM t")

        # Subqueries
        add("SELECT a FROM (SELECT 1 AS a) sub")
        add("SELECT a FROM t WHERE a IN (SELECT a FROM t2)")
        add("SELECT a FROM t WHERE EXISTS (SELECT 1 FROM t2 WHERE t2.a=t.a)")
        add("SELECT a FROM t WHERE NOT EXISTS (SELECT 1 FROM t2)")

        # Joins
        add("SELECT * FROM t1 JOIN t2 ON t1.id=t2.id")
        add("SELECT * FROM t1 INNER JOIN t2 ON t1.id=t2.id")
        add("SELECT * FROM t1 LEFT JOIN t2 ON t1.id=t2.id")
        add("SELECT * FROM t1 LEFT OUTER JOIN t2 ON t1.id=t2.id")
        add("SELECT * FROM t1 CROSS JOIN t2")
        add("SELECT * FROM t1 JOIN t2 USING(id)")

        # Set operations
        add("SELECT 1 UNION SELECT 2")
        add("SELECT 1 UNION ALL SELECT 1")
        add("SELECT 1 INTERSECT SELECT 1")
        add("SELECT 1 EXCEPT SELECT 1")

        # WITH / CTE
        add("WITH cte AS (SELECT 1 AS a) SELECT a FROM cte")
        add("WITH RECURSIVE cte(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cte WHERE x<3) SELECT x FROM cte")

        # DML
        add("INSERT INTO t(a,b) VALUES(1,'x')")
        add("INSERT INTO t VALUES(1,'x')")
        add("INSERT INTO t DEFAULT VALUES")
        add("INSERT INTO t(a) SELECT a FROM t2")
        add("UPDATE t SET a=1")
        add("UPDATE t SET a=a+1, b='y' WHERE id=1")
        add("DELETE FROM t")
        add("DELETE FROM t WHERE a IS NULL")

        # UPSERT-ish (if supported)
        add("INSERT OR REPLACE INTO t(a) VALUES(1)")
        add("REPLACE INTO t(a) VALUES(1)")
        add("INSERT OR IGNORE INTO t(a) VALUES(1)")

        # DDL
        add("CREATE TABLE t(a INTEGER)")
        add("CREATE TABLE IF NOT EXISTS t(a INTEGER, b TEXT)")
        add("CREATE TEMP TABLE t(a INTEGER, b TEXT)")
        add("CREATE TABLE t(id INTEGER PRIMARY KEY, name TEXT NOT NULL, price REAL DEFAULT 0.0, CHECK(price>=0))")
        add("CREATE TABLE t(a INTEGER UNIQUE, b TEXT)")
        add("CREATE TABLE t(a INTEGER, b TEXT, PRIMARY KEY(a,b))")
        add("CREATE TABLE t(a INTEGER, b INTEGER, FOREIGN KEY(a) REFERENCES t2(b))")
        add("CREATE INDEX idx_t_a ON t(a)")
        add("CREATE UNIQUE INDEX idx_t_a ON t(a)")
        add("DROP TABLE t")
        add("DROP TABLE IF EXISTS t")
        add("DROP INDEX idx_t_a")
        add("DROP INDEX IF EXISTS idx_t_a")
        add("ALTER TABLE t ADD COLUMN c TEXT")
        add("CREATE VIEW v AS SELECT * FROM t")
        add("DROP VIEW v")
        add("CREATE TRIGGER tr AFTER INSERT ON t BEGIN SELECT 1; END")
        add("CREATE TRIGGER tr2 BEFORE UPDATE ON t BEGIN UPDATE t SET a=a; END")

        # Less common / discoverable via keywords
        if "EXPLAIN" in keywords:
            add("EXPLAIN SELECT 1")
        if "QUERY" in keywords and "PLAN" in keywords:
            add("EXPLAIN QUERY PLAN SELECT 1")
        if "PRAGMA" in keywords:
            add("PRAGMA table_info('t')")
            add("PRAGMA foreign_keys=ON")
        if "VACUUM" in keywords:
            add("VACUUM")
        if "ANALYZE" in keywords:
            add("ANALYZE")
        if "ATTACH" in keywords and "DATABASE" in keywords:
            add("ATTACH DATABASE 'x.db' AS x")
        if "DETACH" in keywords and "DATABASE" in keywords:
            add("DETACH DATABASE x")
        if "BEGIN" in keywords:
            add("BEGIN")
            add("BEGIN TRANSACTION")
        if "COMMIT" in keywords:
            add("COMMIT")
        if "ROLLBACK" in keywords:
            add("ROLLBACK")
        if "SAVEPOINT" in keywords:
            add("SAVEPOINT sp1")
            add("RELEASE SAVEPOINT sp1")
            add("ROLLBACK TO SAVEPOINT sp1")

        # Randomized statements (mostly SELECT-like)
        rng = random.Random(0)
        idents = ["t", "t1", "t2", "users", "orders", "x", "y", "sub"]
        cols = ["a", "b", "c", "id", "name", "price", "qty"]
        literals = ["1", "2", "3", "0", "-1", "NULL", "'x'", "'a''b'", "1.5", "1e2"]
        funcs = ["COUNT(*)", "COUNT(DISTINCT a)", "SUM(a)", "AVG(a)", "MIN(a)", "MAX(a)", "COALESCE(a,0)", "CAST(a AS TEXT)"]
        exprs = [
            "a",
            "b",
            "a+b",
            "(a+b)*c",
            "a||b",
            "-a",
            "+b",
            "CASE WHEN a>1 THEN 'x' ELSE 'y' END",
        ] + funcs + literals

        wheres = [
            "a=1",
            "a<>1",
            "a!=1",
            "a<1",
            "a<=1",
            "a>1",
            "a>=1",
            "a IS NULL",
            "a IS NOT NULL",
            "a BETWEEN 1 AND 3",
            "a NOT BETWEEN 1 AND 3",
            "a IN (1,2,3)",
            "a NOT IN (1,2,3)",
            "a LIKE 'x%'",
            "NOT (a=1 AND b=2)",
            "(a=1 OR b=2) AND c=3",
        ]

        join_forms = [
            "FROM t1 JOIN t2 ON t1.id=t2.id",
            "FROM t1 INNER JOIN t2 ON t1.id=t2.id",
            "FROM t1 LEFT JOIN t2 ON t1.id=t2.id",
            "FROM t1 LEFT OUTER JOIN t2 ON t1.id=t2.id",
            "FROM t1 CROSS JOIN t2",
            "FROM t1 JOIN t2 USING(id)",
        ]

        for _ in range(220):
            proj_n = rng.randint(1, 4)
            proj = ", ".join(rng.choice(exprs) for _ in range(proj_n))
            distinct = "DISTINCT " if rng.random() < 0.2 else ""
            from_choice = rng.random()
            if from_choice < 0.2:
                from_clause = ""
            elif from_choice < 0.5:
                t = rng.choice(idents)
                alias = "" if rng.random() < 0.5 else f" AS {rng.choice(['x','y','z'])}"
                from_clause = f" FROM {t}{alias}"
            elif from_choice < 0.75:
                from_clause = " " + rng.choice(join_forms)
            else:
                from_clause = " FROM (SELECT 1 AS a) sub"
            where_clause = f" WHERE {rng.choice(wheres)}" if rng.random() < 0.6 and from_clause else ""
            group_clause = " GROUP BY a" if rng.random() < 0.25 and from_clause else ""
            having_clause = " HAVING COUNT(*)>1" if group_clause and rng.random() < 0.5 else ""
            order_clause = ""
            if rng.random() < 0.35 and from_clause:
                ob = rng.choice(cols + ["1"])
                order_clause = f" ORDER BY {ob}" + (" DESC" if rng.random() < 0.4 else "")
            limit_clause = ""
            if rng.random() < 0.25:
                limit_clause = f" LIMIT {rng.choice(['1','2','10'])}" + (f" OFFSET {rng.choice(['0','1','5'])}" if rng.random() < 0.5 else "")
            stmt = f"SELECT {distinct}{proj}{from_clause}{where_clause}{group_clause}{having_clause}{order_clause}{limit_clause}"
            if rng.random() < 0.15:
                stmt = stmt + " UNION SELECT 1"
            if rng.random() < 0.2:
                stmt = "/*c*/ " + stmt
            add(stmt)

        # Add some potentially tricky quoting / identifiers
        add('SELECT "a""b"')
        add('SELECT "select" FROM "from"')
        add("SELECT [a b] FROM [t t]")
        add("SELECT `a``b` FROM `t`")

        return out

    def _mutate_stmt(self, stmt: str, rng: random.Random) -> str:
        s = stmt.strip()
        s_no_semis = re.sub(r"[;\s]+$", "", s)
        variants = []

        def strip_trailing_semis(x: str) -> str:
            return re.sub(r"[;\s]+$", "", x.strip())

        def maybe_comment(x: str) -> str:
            if rng.random() < 0.25:
                return "/*m*/ " + x
            if rng.random() < 0.15:
                return "--m\n" + x
            return x

        def add_limit(x: str) -> str:
            if re.search(r"\bLIMIT\b", x, re.IGNORECASE):
                return x
            return x + " LIMIT 1"

        def add_order(x: str) -> str:
            if re.search(r"\bORDER\s+BY\b", x, re.IGNORECASE):
                return x
            return x + " ORDER BY 1"

        def add_where(x: str) -> str:
            if not re.search(r"\bFROM\b", x, re.IGNORECASE):
                return x
            if re.search(r"\bWHERE\b", x, re.IGNORECASE):
                return x
            return x + " WHERE 1=1"

        def add_group(x: str) -> str:
            if not re.search(r"\bFROM\b", x, re.IGNORECASE):
                return x
            if re.search(r"\bGROUP\s+BY\b", x, re.IGNORECASE):
                return x
            return x + " GROUP BY 1"

        def add_having(x: str) -> str:
            if not re.search(r"\bGROUP\s+BY\b", x, re.IGNORECASE):
                return x
            if re.search(r"\bHAVING\b", x, re.IGNORECASE):
                return x
            return x + " HAVING COUNT(*)>0"

        def toggle_distinct(x: str) -> str:
            m = re.match(r"(?is)\s*SELECT\s+(.*)$", x)
            if not m:
                return x
            if re.match(r"(?is)\s*SELECT\s+DISTINCT\b", x):
                return re.sub(r"(?is)^\s*SELECT\s+DISTINCT\b", "SELECT", x, count=1)
            return re.sub(r"(?is)^\s*SELECT\b", "SELECT DISTINCT", x, count=1)

        def wrap_as_subquery(x: str) -> str:
            x2 = strip_trailing_semis(x)
            return f"SELECT * FROM ({x2}) sub"

        def union_with_select1(x: str) -> str:
            if re.search(r"\bUNION\b", x, re.IGNORECASE):
                return x
            return f"{strip_trailing_semis(x)} UNION SELECT 1"

        def add_join(x: str) -> str:
            if not re.search(r"(?is)^\s*SELECT\b", x):
                return x
            if re.search(r"\bFROM\b", x, re.IGNORECASE):
                # replace FROM t with a join form
                return re.sub(
                    r"(?is)\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)(\s+AS\s+[A-Za-z_][A-Za-z0-9_]*)?",
                    r"FROM \1 JOIN t2 ON \1.id=t2.id",
                    x,
                    count=1,
                )
            return x + " FROM t1 JOIN t2 ON t1.id=t2.id"

        def add_cte(x: str) -> str:
            x2 = strip_trailing_semis(x)
            if re.match(r"(?is)^\s*WITH\b", x2):
                return x2
            return f"WITH cte AS (SELECT 1 AS a) {x2}"

        def tweak_literals(x: str) -> str:
            # swap 1 with 2, 'x' with 'y'
            y = x
            y = re.sub(r"\b1\b", "2", y)
            y = y.replace("'x'", "'y'")
            return y

        def add_semicolon(x: str) -> str:
            return strip_trailing_semis(x) + ";"

        base = s_no_semis
        variants.append(maybe_comment(base))
        variants.append(add_semicolon(base))
        variants.append(toggle_distinct(base))
        variants.append(add_where(base))
        variants.append(add_order(base))
        variants.append(add_limit(base))
        variants.append(add_group(base))
        variants.append(add_having(base))
        variants.append(union_with_select1(base))
        variants.append(wrap_as_subquery(base))
        variants.append(add_join(base))
        variants.append(add_cte(base))
        variants.append(tweak_literals(base))

        # Some statement-type mutations
        if re.match(r"(?is)^\s*INSERT\b", base):
            variants.append(re.sub(r"(?is)^\s*INSERT\b", "INSERT OR IGNORE", base, count=1))
            variants.append(re.sub(r"(?is)^\s*INSERT\b", "INSERT OR REPLACE", base, count=1))
        if re.match(r"(?is)^\s*CREATE\s+TABLE\b", base):
            variants.append(re.sub(r"(?is)^\s*CREATE\s+TABLE\b", "CREATE TEMP TABLE", base, count=1))
            variants.append(re.sub(r"(?is)^\s*CREATE\s+TABLE\b", "CREATE TABLE IF NOT EXISTS", base, count=1))

        # Prefer larger variety
        cand = rng.choice(variants)
        if rng.random() < 0.2:
            cand = " " + cand + " "
        return cand

    def _greedy_select(
        self,
        pool: List[str],
        cov_cache: Dict[str, Tuple[frozenset, frozenset]],
        max_cases: int = 30,
    ) -> List[str]:
        covered_lines: Set[Tuple[str, int]] = set()
        covered_arcs: Set[Tuple[str, int, int]] = set()
        remaining = [s for s in pool if s in cov_cache]
        selected: List[str] = []

        # Start with the single best statement
        for _ in range(max_cases):
            best_idx = -1
            best_gain = 0
            best_lgain = 0
            best_again = 0
            for i, s in enumerate(remaining):
                l, a = cov_cache.get(s, (frozenset(), frozenset()))
                if not l and not a:
                    continue
                lg = len(set(l) - covered_lines)
                ag = len(set(a) - covered_arcs)
                gain = lg * 12 + ag * 2
                if gain > best_gain:
                    best_gain = gain
                    best_idx = i
                    best_lgain = lg
                    best_again = ag
                elif gain == best_gain and gain > 0:
                    # tie-break: more lines, then more arcs, then shorter statement
                    if lg > best_lgain or (lg == best_lgain and (ag > best_again or (ag == best_again and len(s) < len(remaining[best_idx])))):
                        best_idx = i
                        best_lgain = lg
                        best_again = ag
            if best_idx < 0 or best_gain <= 0:
                break
            best_stmt = remaining.pop(best_idx)
            selected.append(best_stmt)
            l, a = cov_cache.get(best_stmt, (frozenset(), frozenset()))
            covered_lines |= set(l)
            covered_arcs |= set(a)

        # Ensure at least a few
        if not selected:
            selected = remaining[: min(max_cases, len(remaining))]

        return selected

    def _minimize_selected(
        self,
        selected: List[str],
        cov_cache: Dict[str, Tuple[frozenset, frozenset]],
    ) -> List[str]:
        if len(selected) <= 1:
            return selected

        def union_cov(stmts: List[str]) -> Tuple[Set[Tuple[str, int]], Set[Tuple[str, int, int]]]:
            ul: Set[Tuple[str, int]] = set()
            ua: Set[Tuple[str, int, int]] = set()
            for s in stmts:
                l, a = cov_cache.get(s, (frozenset(), frozenset()))
                ul |= set(l)
                ua |= set(a)
            return ul, ua

        totalL, totalA = union_cov(selected)
        changed = True
        while changed and len(selected) > 1:
            changed = False
            for i in range(len(selected) - 1, -1, -1):
                trial = selected[:i] + selected[i + 1 :]
                uL, uA = union_cov(trial)
                if len(uL) == len(totalL) and len(uA) == len(totalA):
                    selected = trial
                    changed = True
                    break
        return selected

    def _bundle_statements(
        self,
        statements: List[str],
        parse_sql,
        stmt_coverage_func,
        cov_cache: Dict[str, Tuple[frozenset, frozenset]],
    ) -> List[str]:
        if not statements:
            return []

        def strip_semis(s: str) -> str:
            return re.sub(r"[;\s]+$", "", s.strip())

        def can_parse(script: str) -> bool:
            try:
                parse_sql(script)
                return True
            except Exception:
                return False

        # Determine if multi-statement scripts are supported by checking coverage preservation
        if len(statements) >= 2:
            # pick two that likely differ in coverage
            s1 = statements[0]
            s2 = None
            l1, a1 = cov_cache.get(s1, (frozenset(), frozenset()))
            best = -1
            best_stmt = None
            for cand in statements[1:]:
                l2, a2 = cov_cache.get(cand, (frozenset(), frozenset()))
                gain = len(set(l2) - set(l1)) + len(set(a2) - set(a1))
                if gain > best:
                    best = gain
                    best_stmt = cand
            s2 = best_stmt or statements[1]

            test_script = strip_semis(s1) + ";\n" + strip_semis(s2) + ";"
            if can_parse(test_script):
                lsc, asc = stmt_coverage_func(test_script)
                unionL = set(l1) | set(cov_cache.get(s2, (frozenset(), frozenset()))[0])
                unionA = set(a1) | set(cov_cache.get(s2, (frozenset(), frozenset()))[1])
                missing = (len(unionL - set(lsc)), len(unionA - set(asc)))
                multi_supported = (missing[0] <= 2 and missing[1] <= 5)
            else:
                multi_supported = False
        else:
            multi_supported = False

        if not multi_supported:
            return [strip_semis(s) for s in statements]

        # Try bundle all
        all_script = ";\n".join(strip_semis(s) for s in statements if strip_semis(s)) + ";"
        if can_parse(all_script):
            # verify coverage roughly includes union
            unionL: Set[Tuple[str, int]] = set()
            unionA: Set[Tuple[str, int, int]] = set()
            for s in statements:
                l, a = cov_cache.get(s, (frozenset(), frozenset()))
                unionL |= set(l)
                unionA |= set(a)
            lsc, asc = stmt_coverage_func(all_script)
            if len(unionL - set(lsc)) <= 5 and len(unionA - set(asc)) <= 15:
                return [all_script]

        # Otherwise chunk into a few scripts
        scripts: List[str] = []
        cur_parts: List[str] = []
        for s in statements:
            part = strip_semis(s)
            if not part:
                continue
            trial_parts = cur_parts + [part]
            trial_script = ";\n".join(trial_parts) + ";"
            if can_parse(trial_script):
                cur_parts = trial_parts
            else:
                if cur_parts:
                    scripts.append(";\n".join(cur_parts) + ";")
                cur_parts = [part]
        if cur_parts:
            scripts.append(";\n".join(cur_parts) + ";")

        # final sanity: if any script fails, fallback to individual
        for sc in scripts:
            if not can_parse(sc):
                return [strip_semis(s) for s in statements]
        return scripts