import os
import sys
import re
import random
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Set, Any


@dataclass(frozen=True)
class _Lit:
    v: str


@dataclass(frozen=True)
class _Sym:
    n: str


@dataclass(frozen=True)
class _Seq:
    items: Tuple[Any, ...]


@dataclass(frozen=True)
class _Alt:
    alts: Tuple[Any, ...]


@dataclass(frozen=True)
class _Opt:
    item: Any


@dataclass(frozen=True)
class _Rep:
    item: Any
    min_n: int
    max_n: int


@dataclass(frozen=True)
class _Eps:
    pass


class _EBNFParser:
    def __init__(self, tokens: List[str]):
        self.toks = tokens
        self.i = 0

    def _peek(self) -> Optional[str]:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def _next(self) -> Optional[str]:
        if self.i >= len(self.toks):
            return None
        t = self.toks[self.i]
        self.i += 1
        return t

    def _expect(self, t: str) -> None:
        got = self._next()
        if got != t:
            raise ValueError(f"Expected {t}, got {got}")

    def parse(self) -> Any:
        if not self.toks:
            return _Eps()
        node = self._parse_expr()
        return node

    def _parse_expr(self) -> Any:
        terms = [self._parse_term()]
        while self._peek() == "|":
            self._next()
            terms.append(self._parse_term())
        if len(terms) == 1:
            return terms[0]
        return _Alt(tuple(terms))

    def _parse_term(self) -> Any:
        items = []
        while True:
            p = self._peek()
            if p is None or p in ("]", "}", ")", "|"):
                break
            items.append(self._parse_factor())
        if not items:
            return _Eps()
        if len(items) == 1:
            return items[0]
        return _Seq(tuple(items))

    def _parse_factor(self) -> Any:
        base = self._parse_base()
        q = self._peek()
        if q in ("?", "*", "+"):
            self._next()
            if q == "?":
                return _Opt(base)
            if q == "*":
                return _Rep(base, 0, 2)
            return _Rep(base, 1, 2)
        return base

    def _parse_base(self) -> Any:
        t = self._next()
        if t is None:
            return _Eps()
        if t == "(":
            n = self._parse_expr()
            self._expect(")")
            return n
        if t == "[":
            n = self._parse_expr()
            self._expect("]")
            return _Opt(n)
        if t == "{":
            n = self._parse_expr()
            self._expect("}")
            return _Rep(n, 0, 2)
        if t.startswith("<") and t.endswith(">") and len(t) > 2:
            return _Sym(t[1:-1])
        return _Lit(t)


class _Grammar:
    def __init__(self, grammar_text: str):
        self.rules: Dict[str, List[Any]] = {}
        self.start_symbol: Optional[str] = None
        self._parse_grammar(grammar_text)

    @staticmethod
    def _strip_comments(line: str) -> str:
        line = re.split(r"(?://|#)", line, maxsplit=1)[0]
        return line.strip()

    @staticmethod
    def _tokenize_rhs(rhs: str) -> List[str]:
        meta = set("|[]{}()?*+")
        tokens: List[str] = []
        i = 0
        n = len(rhs)
        while i < n:
            c = rhs[i]
            if c.isspace():
                i += 1
                continue
            if c in meta:
                tokens.append(c)
                i += 1
                continue
            if c in ("'", '"'):
                q = c
                i += 1
                buf = []
                while i < n:
                    if rhs[i] == q:
                        if i + 1 < n and rhs[i + 1] == q:
                            buf.append(q)
                            i += 2
                            continue
                        i += 1
                        break
                    buf.append(rhs[i])
                    i += 1
                tokens.append("".join(buf))
                continue
            j = i
            while j < n and (not rhs[j].isspace()) and rhs[j] not in meta and rhs[j] not in ("'", '"'):
                j += 1
            tokens.append(rhs[i:j])
            i = j
        return [t for t in tokens if t != ""]

    def _parse_grammar(self, text: str) -> None:
        lines = text.splitlines()
        chunks: List[str] = []
        cur = ""
        for raw in lines:
            line = self._strip_comments(raw)
            if not line:
                continue
            if "::=" in line:
                if cur:
                    chunks.append(cur)
                cur = line
            else:
                if cur:
                    cur += " " + line
        if cur:
            chunks.append(cur)

        for chunk in chunks:
            if "::=" not in chunk:
                continue
            lhs, rhs = chunk.split("::=", 1)
            lhs = lhs.strip()
            rhs = rhs.strip()
            if not lhs:
                continue
            if self.start_symbol is None:
                self.start_symbol = lhs[1:-1] if lhs.startswith("<") and lhs.endswith(">") else lhs
            lhs_sym = lhs[1:-1] if lhs.startswith("<") and lhs.endswith(">") else lhs
            toks = self._tokenize_rhs(rhs)
            if not toks:
                node = _Eps()
            else:
                try:
                    node = _EBNFParser(toks).parse()
                except Exception:
                    node = _Eps()
            self.rules.setdefault(lhs_sym, []).append(node)

    def generate_samples(self, n: int, seed: int = 0, max_depth: int = 10) -> List[str]:
        rng = random.Random(seed)
        samples: List[str] = []
        if not self.start_symbol:
            return samples
        for _ in range(n):
            toks = self._gen_sym(self.start_symbol, rng, max_depth, stack=[])
            s = _format_tokens(toks)
            s = s.strip()
            if s:
                samples.append(s)
        return samples

    @staticmethod
    def _terminal_for_name(name: str, rng: random.Random) -> Optional[List[str]]:
        n = name.lower()
        if "identifier" in n or n == "ident" or n.endswith("ident") or n.endswith("identifier"):
            return [_rand_ident(rng)]
        if n.endswith("name") or "name" in n:
            return [_rand_ident(rng)]
        if "table" in n:
            return [rng.choice(["t", "t1", "u", "u1"])]
        if "column" in n or "field" in n:
            return [rng.choice(["a", "b", "c", "id", "x", "y", "z"])]
        if "string" in n or "text" in n or "varchar" in n or "char" in n:
            return [_rand_string(rng)]
        if "number" in n or "numeric" in n or "integer" in n or n.endswith("int") or "int" in n:
            return [rng.choice(["0", "1", "2", "10", "-1"])]
        if "float" in n or "real" in n or "double" in n or "decimal" in n:
            return [rng.choice(["0.0", "1.5", "3.14159", "-0.25", "1e2"])]
        if "bool" in n:
            return [rng.choice(["TRUE", "FALSE"])]
        if "null" in n:
            return ["NULL"]
        if "param" in n or "placeholder" in n:
            return [rng.choice(["?", ":p", "@p", "$p"])]
        return None

    @staticmethod
    def _terminal_for_token(tok: str, rng: random.Random) -> Optional[str]:
        t = tok.upper()
        if t in ("IDENT", "IDENTIFIER", "ID", "NAME"):
            return _rand_ident(rng)
        if "STRING" in t or "TEXT" in t:
            return _rand_string(rng)
        if t in ("INT", "INTEGER", "INTEGER_LITERAL", "NUMBER", "NUM", "NUMERIC_LITERAL", "DECIMAL_INTEGER"):
            return rng.choice(["0", "1", "2", "10", "-1"])
        if t in ("FLOAT", "REAL", "DOUBLE", "DECIMAL", "FLOAT_LITERAL", "DECIMAL_LITERAL", "SCIENTIFIC_NUMBER"):
            return rng.choice(["0.0", "1.5", "3.14159", "-0.25", "1e2"])
        if t in ("BOOL", "BOOLEAN"):
            return rng.choice(["TRUE", "FALSE"])
        if t in ("NULL",):
            return "NULL"
        if "PARAM" in t or t in ("QMARK", "PLACEHOLDER"):
            return rng.choice(["?", ":p", "@p", "$p"])
        if "BLOB" in t or "HEX" in t:
            return "X'00'"
        return None

    def _gen_node(self, node: Any, rng: random.Random, depth: int, stack: List[str]) -> List[str]:
        if depth <= 0:
            if isinstance(node, _Lit):
                mapped = self._terminal_for_token(node.v, rng)
                return [mapped] if mapped is not None else [node.v]
            if isinstance(node, _Sym):
                mapped = self._terminal_for_name(node.n, rng)
                if mapped is not None:
                    return mapped
                return [_rand_ident(rng)]
            return []
        if isinstance(node, _Eps):
            return []
        if isinstance(node, _Lit):
            mapped = self._terminal_for_token(node.v, rng)
            return [mapped] if mapped is not None else [node.v]
        if isinstance(node, _Sym):
            return self._gen_sym(node.n, rng, depth - 1, stack)
        if isinstance(node, _Seq):
            out: List[str] = []
            for it in node.items:
                out.extend(self._gen_node(it, rng, depth, stack))
            return out
        if isinstance(node, _Alt):
            # prefer shorter expansions at low depth
            if depth < 3 and len(node.alts) > 1:
                alts = list(node.alts)
                rng.shuffle(alts)
                alts.sort(key=lambda x: _node_size_hint(x))
                chosen = alts[0]
            else:
                chosen = rng.choice(node.alts)
            return self._gen_node(chosen, rng, depth, stack)
        if isinstance(node, _Opt):
            if depth < 3:
                take = rng.random() < 0.25
            else:
                take = rng.random() < 0.55
            return self._gen_node(node.item, rng, depth, stack) if take else []
        if isinstance(node, _Rep):
            if depth < 3:
                k = node.min_n
            else:
                k = rng.randint(node.min_n, node.max_n)
            out: List[str] = []
            for _ in range(k):
                out.extend(self._gen_node(node.item, rng, depth, stack))
            return out
        return []

    def _gen_sym(self, sym: str, rng: random.Random, depth: int, stack: List[str]) -> List[str]:
        mapped = self._terminal_for_name(sym, rng)
        if mapped is not None:
            return mapped
        if sym in stack:
            return [_rand_ident(rng)]
        rules = self.rules.get(sym)
        if not rules:
            return [_rand_ident(rng)]
        stack.append(sym)
        try:
            if depth < 4:
                candidates = list(rules)
                rng.shuffle(candidates)
                candidates.sort(key=_node_size_hint)
                node = candidates[0]
            else:
                node = rng.choice(rules)
            return self._gen_node(node, rng, depth, stack)
        finally:
            stack.pop()


def _node_size_hint(node: Any) -> int:
    if isinstance(node, _Eps):
        return 0
    if isinstance(node, _Lit):
        return 1
    if isinstance(node, _Sym):
        return 2
    if isinstance(node, _Opt):
        return 1 + _node_size_hint(node.item)
    if isinstance(node, _Rep):
        return 2 + _node_size_hint(node.item)
    if isinstance(node, _Seq):
        return sum(_node_size_hint(x) for x in node.items)
    if isinstance(node, _Alt):
        return min(_node_size_hint(x) for x in node.alts) if node.alts else 0
    return 5


def _rand_ident(rng: random.Random) -> str:
    base = rng.choice(["t", "u", "v", "w", "col", "c", "x", "y", "z", "id"])
    suf = rng.randint(0, 3)
    if suf == 0:
        return base
    return f"{base}{suf}"


def _rand_string(rng: random.Random) -> str:
    choices = ["a", "b", "x", "y", "hello", "a'b", "line\nbreak"]
    s = rng.choice(choices)
    s = s.replace("'", "''")
    s = s.replace("\n", "\\n")
    return "'" + s + "'"


def _format_tokens(tokens: List[str]) -> str:
    if not tokens:
        return ""
    no_space_before = {",", ")", ";", ".", "]", "}", ":"}
    no_space_after = {"(", ".", "[", "{", ":"}
    out = ""
    prev = ""
    for t in tokens:
        if t is None:
            continue
        t = str(t)
        if not t:
            continue
        if not out:
            out = t
            prev = t
            continue
        if t in no_space_before or prev in no_space_after or prev.endswith(".") or t == ".":
            out += t
        else:
            out += " " + t
        prev = t
    out = re.sub(r"\s+", " ", out).strip()
    return out


def _safe_import_sql_engine(resources_path: str):
    resources_path = os.path.abspath(resources_path)
    if resources_path not in sys.path:
        sys.path.insert(0, resources_path)
    import importlib

    pkg = importlib.import_module("sql_engine")
    parse_sql = getattr(pkg, "parse_sql", None)
    if parse_sql is None:
        mod = importlib.import_module("sql_engine.parser")
        parse_sql = getattr(mod, "parse_sql", None)
    if parse_sql is None:
        raise ImportError("sql_engine.parse_sql not found")
    engine_dir = os.path.join(resources_path, "sql_engine")
    return parse_sql, engine_dir


def _templates() -> List[str]:
    t = []

    # Minimal / tokenizer exercise
    t += [
        "SELECT 1",
        "SELECT 1;",
        "SELECT -1, +2, 3.14, 1e2",
        "SELECT NULL, TRUE, FALSE",
        "SELECT 'a''b', 'x', 'hello'",
        "SELECT /* block comment */ 1",
        "SELECT 1 -- line comment\n",
        "SELECT (1+2)*3, 4/2, 5%2",
        "SELECT 1=1, 1<>2, 1!=2, 1<2, 1<=2, 2>1, 2>=1",
    ]

    # Basic FROM/WHERE
    t += [
        "SELECT * FROM t",
        "SELECT a, b FROM t",
        "SELECT t.a, t.b FROM t AS t",
        "SELECT a FROM t WHERE a = 1",
        "SELECT a FROM t WHERE NOT (a = 1)",
        "SELECT a FROM t WHERE a IS NULL",
        "SELECT a FROM t WHERE a IS NOT NULL",
        "SELECT a FROM t WHERE a BETWEEN 1 AND 2",
        "SELECT a FROM t WHERE a IN (1, 2, 3)",
        "SELECT a FROM t WHERE a LIKE '%x%'",
        "SELECT a FROM t WHERE a LIKE '%!_%' ESCAPE '!'",
    ]

    # Joins
    t += [
        "SELECT t.a, u.b FROM t JOIN u ON t.id = u.id",
        "SELECT t.a FROM t INNER JOIN u ON t.id = u.id",
        "SELECT t.a FROM t LEFT JOIN u ON t.id = u.id",
        "SELECT t.a FROM t CROSS JOIN u",
        "SELECT t.a FROM t, u WHERE t.id = u.id",
    ]

    # Aggregation / group / having
    t += [
        "SELECT COUNT(*) FROM t",
        "SELECT a, COUNT(*) FROM t GROUP BY a",
        "SELECT a, COUNT(*) FROM t GROUP BY a HAVING COUNT(*) > 1",
        "SELECT COUNT(DISTINCT a) FROM t",
    ]

    # Order / limit
    t += [
        "SELECT a FROM t ORDER BY a",
        "SELECT a FROM t ORDER BY a DESC, b ASC",
        "SELECT a FROM t ORDER BY 1",
        "SELECT a FROM t LIMIT 10",
        "SELECT a FROM t LIMIT 10 OFFSET 5",
    ]

    # Subqueries
    t += [
        "SELECT a FROM (SELECT 1 AS a) sub",
        "SELECT * FROM (SELECT a, b FROM t) s WHERE b > 0",
        "SELECT EXISTS (SELECT 1 FROM t WHERE a=1)",
        "SELECT a FROM t WHERE a IN (SELECT a FROM u)",
        "SELECT a FROM t WHERE EXISTS (SELECT 1 FROM u WHERE u.id = t.id)",
    ]

    # Set ops
    t += [
        "SELECT a FROM t UNION SELECT a FROM u",
        "SELECT a FROM t UNION ALL SELECT a FROM u",
        "SELECT a FROM t EXCEPT SELECT a FROM u",
        "SELECT a FROM t INTERSECT SELECT a FROM u",
    ]

    # CASE / CAST / functions
    t += [
        "SELECT CASE WHEN a=1 THEN 'one' ELSE 'other' END FROM t",
        "SELECT CASE a WHEN 1 THEN 'one' WHEN 2 THEN 'two' ELSE 'other' END FROM t",
        "SELECT CAST(1 AS TEXT)",
        "SELECT COALESCE(NULL, 1, 2)",
        "SELECT ABS(-1), LOWER('A'), UPPER('a')",
        "SELECT SUBSTR('abcd', 1, 2)",
    ]

    # CTE / WITH
    t += [
        "WITH cte AS (SELECT 1 AS x) SELECT x FROM cte",
        "WITH cte(x) AS (SELECT 1) SELECT x FROM cte",
        "WITH cte AS (SELECT a FROM t) SELECT a FROM cte WHERE a > 0",
    ]

    # DML
    t += [
        "INSERT INTO t(a, b) VALUES (1, 2)",
        "INSERT INTO t(a, b) VALUES (1, 2), (3, 4)",
        "INSERT INTO t(a) SELECT a FROM u",
        "UPDATE t SET a = 1",
        "UPDATE t SET a = a + 1, b = NULL WHERE id = 1",
        "DELETE FROM t",
        "DELETE FROM t WHERE id = 1",
    ]

    # DDL (various dialects; filter later by parsing)
    t += [
        "CREATE TABLE t (id INT, a TEXT)",
        "CREATE TABLE IF NOT EXISTS t2 (id INTEGER PRIMARY KEY, a TEXT NOT NULL, b INT DEFAULT 0)",
        "DROP TABLE t2",
        "DROP TABLE IF EXISTS t2",
        "ALTER TABLE t ADD COLUMN z INT",
        "CREATE INDEX idx_t_a ON t(a)",
        "CREATE UNIQUE INDEX idx_t_ab ON t(a, b)",
        "DROP INDEX idx_t_a",
        "CREATE VIEW v AS SELECT a, b FROM t",
    ]

    # Transaction-ish
    t += [
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
    ]

    # Identifier quoting variants (filter by parsing)
    t += [
        'SELECT "a" FROM "t"',
        "SELECT `a` FROM `t`",
        "SELECT [a] FROM [t]",
    ]

    # Ensure semicolon variants for many
    out: List[str] = []
    for s in t:
        s = s.strip()
        if not s:
            continue
        out.append(s)
        if not s.endswith(";"):
            out.append(s + ";")
    # Add a few whitespace/newline variants
    out += [
        "SELECT\t1;\n",
        "SELECT 1  \nFROM t;\n",
        "WITH cte AS (\n  SELECT 1 AS x\n) SELECT x FROM cte;\n",
    ]
    return out


class Solution:
    def solve(self, resources_path: str) -> list[str]:
        parse_sql, engine_dir = _safe_import_sql_engine(resources_path)

        candidates: List[str] = []
        candidates.extend(_templates())

        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        if os.path.exists(grammar_path):
            try:
                with open(grammar_path, "r", encoding="utf-8", errors="ignore") as f:
                    gtxt = f.read()
                g = _Grammar(gtxt)
                gram_samples = g.generate_samples(n=350, seed=0, max_depth=12)
                # add variants with/without trailing semicolon
                for s in gram_samples:
                    s = s.strip()
                    if not s:
                        continue
                    candidates.append(s)
                    if s.endswith(";"):
                        candidates.append(s[:-1].rstrip())
                    else:
                        candidates.append(s + ";")
            except Exception:
                pass

        # Deduplicate and sanity filter
        uniq = []
        seen = set()
        for s in candidates:
            if not s:
                continue
            s2 = s.strip()
            if not s2:
                continue
            if len(s2) > 2000:
                continue
            if s2 in seen:
                continue
            seen.add(s2)
            uniq.append(s2)

        # Validate by parsing first (cheap)
        valid: List[str] = []
        for s in uniq:
            try:
                parse_sql(s)
                valid.append(s)
            except Exception:
                continue

        if not valid:
            # Try a few robust fallbacks
            for s in ["SELECT 1", "SELECT 1;", "SELECT * FROM t", "CREATE TABLE t (id INT)"]:
                try:
                    parse_sql(s)
                    return [s]
                except Exception:
                    continue
            return ["SELECT 1"]

        # If coverage is available, do greedy coverage-guided selection
        try:
            import coverage  # type: ignore
        except Exception:
            # No coverage module: return a small diverse subset
            return valid[:25]

        engine_dir = os.path.abspath(engine_dir)
        target_files = [
            os.path.abspath(os.path.join(engine_dir, "parser.py")),
            os.path.abspath(os.path.join(engine_dir, "tokenizer.py")),
            os.path.abspath(os.path.join(engine_dir, "ast_nodes.py")),
        ]

        include_globs = [os.path.join(engine_dir, "*.py")]

        def canonicalize_data(data) -> Tuple[Dict[str, Set[int]], Dict[str, Set[Tuple[int, int]]]]:
            lines_map: Dict[str, Set[int]] = {f: set() for f in target_files}
            arcs_map: Dict[str, Set[Tuple[int, int]]] = {f: set() for f in target_files}

            measured = list(getattr(data, "measured_files", lambda: [])())
            measured_set = set(measured)

            def _find_measured(path: str) -> Optional[str]:
                if path in measured_set:
                    return path
                base = os.path.basename(path)
                for mf in measured:
                    if os.path.basename(mf) == base:
                        return mf
                return None

            for tf in target_files:
                mf = _find_measured(tf)
                if not mf:
                    continue
                ls = data.lines(mf) or []
                lines_map[tf] = set(int(x) for x in ls if isinstance(x, int))
                arcs = data.arcs(mf) or []
                aout = set()
                for a in arcs:
                    if not a or len(a) != 2:
                        continue
                    a0, a1 = a
                    if isinstance(a0, int) and isinstance(a1, int):
                        aout.add((a0, a1))
                arcs_map[tf] = aout
            return lines_map, arcs_map

        cov = coverage.Coverage(
            data_file=None,
            branch=True,
            include=include_globs,
            config_file=False,
        )

        cand_exec: List[Tuple[str, Dict[str, Set[int]], Dict[str, Set[Tuple[int, int]]], int]] = []

        for s in valid:
            try:
                cov.erase()
                cov.start()
                parse_sql(s)
                cov.stop()
                data = cov.get_data()
                lines_map, arcs_map = canonicalize_data(data)
                total_lines = sum(len(v) for v in lines_map.values())
                total_arcs = sum(len(v) for v in arcs_map.values())
                if total_lines == 0 and total_arcs == 0:
                    continue
                # keep a lightweight size metric for tie-breaking
                size_metric = len(s)
                # also store total to quickly filter low-signal cases
                cand_exec.append((s, lines_map, arcs_map, size_metric))
            except Exception:
                try:
                    cov.stop()
                except Exception:
                    pass
                continue

        if not cand_exec:
            return valid[:25]

        # Greedy set cover: primary lines, secondary arcs
        cur_lines: Dict[str, Set[int]] = {f: set() for f in target_files}
        cur_arcs: Dict[str, Set[Tuple[int, int]]] = {f: set() for f in target_files}

        remaining = cand_exec[:]
        selected: List[Tuple[str, Dict[str, Set[int]], Dict[str, Set[Tuple[int, int]]], int]] = []

        max_selected = 35
        while remaining and len(selected) < max_selected:
            best_idx = -1
            best_score = 0.0
            best_gain_lines = 0
            best_gain_arcs = 0
            best_size = 10**9

            for i, (s, lm, am, sz) in enumerate(remaining):
                gain_lines = 0
                gain_arcs = 0
                for f in target_files:
                    if lm.get(f):
                        gain_lines += len(lm[f] - cur_lines[f])
                    if am.get(f):
                        gain_arcs += len(am[f] - cur_arcs[f])

                if gain_lines == 0 and gain_arcs == 0:
                    continue
                score = gain_lines * 10.0 + gain_arcs * 1.0
                if (score > best_score) or (score == best_score and (gain_lines > best_gain_lines)) or (
                    score == best_score and gain_lines == best_gain_lines and (gain_arcs > best_gain_arcs)
                ) or (score == best_score and gain_lines == best_gain_lines and gain_arcs == best_gain_arcs and sz < best_size):
                    best_score = score
                    best_idx = i
                    best_gain_lines = gain_lines
                    best_gain_arcs = gain_arcs
                    best_size = sz

            if best_idx < 0:
                break

            s, lm, am, sz = remaining.pop(best_idx)
            selected.append((s, lm, am, sz))
            for f in target_files:
                cur_lines[f].update(lm.get(f, set()))
                cur_arcs[f].update(am.get(f, set()))

        if not selected:
            return valid[:25]

        # Redundancy elimination using coverage counters
        def build_counts(sel) -> Tuple[Dict[str, Dict[int, int]], Dict[str, Dict[Tuple[int, int], int]]]:
            line_counts: Dict[str, Dict[int, int]] = {f: {} for f in target_files}
            arc_counts: Dict[str, Dict[Tuple[int, int], int]] = {f: {} for f in target_files}
            for _, lm, am, _ in sel:
                for f in target_files:
                    for ln in lm.get(f, set()):
                        line_counts[f][ln] = line_counts[f].get(ln, 0) + 1
                    for a in am.get(f, set()):
                        arc_counts[f][a] = arc_counts[f].get(a, 0) + 1
            return line_counts, arc_counts

        changed = True
        while changed and len(selected) > 1:
            changed = False
            line_counts, arc_counts = build_counts(selected)

            removable_idxs = []
            for idx, (s, lm, am, sz) in enumerate(selected):
                unique = False
                for f in target_files:
                    for ln in lm.get(f, set()):
                        if line_counts[f].get(ln, 0) == 1:
                            unique = True
                            break
                    if unique:
                        break
                    for a in am.get(f, set()):
                        if arc_counts[f].get(a, 0) == 1:
                            unique = True
                            break
                    if unique:
                        break
                if not unique:
                    removable_idxs.append(idx)

            if removable_idxs:
                # remove shortest first to keep longer only if needed
                removable_idxs.sort(key=lambda i: selected[i][3])
                for ridx in reversed(removable_idxs):
                    selected.pop(ridx)
                    changed = True

        result = [s for (s, _, _, _) in selected]
        # Final sanity: keep deterministic order, ensure still parses
        final: List[str] = []
        for s in result:
            try:
                parse_sql(s)
                final.append(s)
            except Exception:
                continue

        if not final:
            return valid[:25]
        return final[:50]