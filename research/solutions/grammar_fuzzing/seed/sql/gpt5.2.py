import os
import re
import sys
import types
import importlib
from collections import OrderedDict


class Solution:
    def solve(self, resources_path: str) -> list[str]:
        resources_path = os.path.abspath(resources_path)
        if resources_path not in sys.path:
            sys.path.insert(0, resources_path)

        parse_sql = None
        tokenizer_mod = None
        parser_mod = None
        engine_mod = None
        ast_nodes_mod = None

        try:
            engine_mod = importlib.import_module("sql_engine")
        except Exception:
            engine_mod = None

        if engine_mod is not None:
            parse_sql = getattr(engine_mod, "parse_sql", None)

        try:
            parser_mod = importlib.import_module("sql_engine.parser")
        except Exception:
            parser_mod = None

        if parse_sql is None and parser_mod is not None:
            parse_sql = getattr(parser_mod, "parse_sql", None)

        try:
            tokenizer_mod = importlib.import_module("sql_engine.tokenizer")
        except Exception:
            tokenizer_mod = None

        try:
            ast_nodes_mod = importlib.import_module("sql_engine.ast_nodes")
        except Exception:
            ast_nodes_mod = None

        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        grammar_text = ""
        try:
            with open(grammar_path, "r", encoding="utf-8") as f:
                grammar_text = f.read()
        except Exception:
            grammar_text = ""

        keyword_set = set()
        if tokenizer_mod is not None:
            for attr in ("KEYWORDS", "RESERVED_WORDS", "RESERVED", "KEYWORD_SET"):
                val = getattr(tokenizer_mod, attr, None)
                if isinstance(val, (set, frozenset, list, tuple)):
                    keyword_set.update(str(x).upper() for x in val)
        if not keyword_set and grammar_text:
            keyword_set.update(re.findall(r"\b[A-Z][A-Z_0-9]*\b", grammar_text))
        # Add common SQL keywords to ensure useful discrimination even if grammar/tokenizer doesn't expose them.
        keyword_set.update(
            {
                "SELECT",
                "DISTINCT",
                "ALL",
                "FROM",
                "WHERE",
                "GROUP",
                "BY",
                "HAVING",
                "ORDER",
                "LIMIT",
                "OFFSET",
                "ASC",
                "DESC",
                "AS",
                "AND",
                "OR",
                "NOT",
                "NULL",
                "IS",
                "IN",
                "EXISTS",
                "BETWEEN",
                "LIKE",
                "ESCAPE",
                "JOIN",
                "INNER",
                "LEFT",
                "RIGHT",
                "FULL",
                "OUTER",
                "CROSS",
                "ON",
                "USING",
                "UNION",
                "INTERSECT",
                "EXCEPT",
                "WITH",
                "RECURSIVE",
                "CASE",
                "WHEN",
                "THEN",
                "ELSE",
                "END",
                "CAST",
                "INSERT",
                "INTO",
                "VALUES",
                "DEFAULT",
                "UPDATE",
                "SET",
                "DELETE",
                "CREATE",
                "TABLE",
                "INDEX",
                "VIEW",
                "DROP",
                "ALTER",
                "ADD",
                "COLUMN",
                "RENAME",
                "TO",
                "IF",
                "EXISTS",
                "PRIMARY",
                "KEY",
                "UNIQUE",
                "CHECK",
                "REFERENCES",
                "FOREIGN",
                "BEGIN",
                "COMMIT",
                "ROLLBACK",
                "SAVEPOINT",
                "RELEASE",
            }
        )

        def try_parse(stmt: str):
            if parse_sql is None:
                return None
            try:
                return parse_sql(stmt)
            except Exception:
                return None

        def is_primitive(x):
            return x is None or isinstance(x, (str, bytes, int, float, bool))

        def iter_children(obj):
            if is_primitive(obj):
                return
            if isinstance(obj, (list, tuple, set)):
                for it in obj:
                    yield it
                return
            if isinstance(obj, dict):
                for it in obj.values():
                    yield it
                return
            if hasattr(obj, "__dict__"):
                for v in obj.__dict__.values():
                    yield v
                return
            # Fallback: inspect public attributes but keep it safe.
            for name in dir(obj):
                if name.startswith("_"):
                    continue
                try:
                    v = getattr(obj, name)
                except Exception:
                    continue
                if callable(v):
                    continue
                yield v

        def collect_node_types(ast_obj):
            types_set = set()
            seen = set()

            def rec(o):
                if is_primitive(o):
                    return
                oid = id(o)
                if oid in seen:
                    return
                seen.add(oid)
                try:
                    types_set.add(o.__class__.__name__)
                except Exception:
                    pass
                for ch in iter_children(o):
                    rec(ch)

            rec(ast_obj)
            return types_set

        op_markers = [
            ("<>", "OP:<>"),
            ("!=", "OP:!="),
            (">=", "OP:>="),
            ("<=", "OP:<="),
            ("||", "OP:||"),
            ("->", "OP:->"),
            ("+", "OP:+"),
            ("-", "OP:-"),
            ("*", "OP:*"),
            ("/", "OP:/"),
            ("%", "OP:%"),
            ("&", "OP:&"),
            ("|", "OP:|"),
            ("^", "OP:^"),
            ("<<", "OP:<<"),
            (">>", "OP:>>"),
            ("=", "OP:="),
            ("<", "OP:<"),
            (">", "OP:>"),
        ]

        def collect_text_features(stmt: str):
            feats = set()
            words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", stmt)
            for w in words:
                uw = w.upper()
                if uw in keyword_set:
                    feats.add("KW:" + uw)
            for s, tag in op_markers:
                if s in stmt:
                    feats.add(tag)
            if "--" in stmt:
                feats.add("CM:LINE")
            if "/*" in stmt and "*/" in stmt:
                feats.add("CM:BLOCK")
            if "'" in stmt:
                feats.add("LIT:STR")
            if '"' in stmt:
                feats.add("ID:DBLQUOTE")
            if "`" in stmt:
                feats.add("ID:BTQUOTE")
            if "[" in stmt and "]" in stmt:
                feats.add("ID:BRACKET")
            if "?" in stmt:
                feats.add("PARAM:?")
            if ":" in stmt and re.search(r":[A-Za-z_]", stmt):
                feats.add("PARAM:NAMED")
            if "\n" in stmt:
                feats.add("WS:NL")
            if "\t" in stmt:
                feats.add("WS:TAB")
            if ";" in stmt:
                feats.add("TERM:;")
            return feats

        candidates = OrderedDict()

        def add(stmt: str):
            s = (stmt or "").strip()
            if not s:
                return
            # keep original newlines in some cases to trigger tokenizer branches
            candidates.setdefault(s, None)

        # Core select / expressions
        add("SELECT 1")
        add("select 1")
        add("SELECT 1;")
        add("SELECT 1 -- line comment\n")
        add("SELECT 1 /* block comment */")
        add("SELECT NULL")
        add("SELECT 'a''b' AS s")
        add("SELECT -1 AS n, +2 AS p, 3.14 AS pi, 1e3 AS e")
        add("SELECT 1 + 2 * 3 - 4 / 5 AS expr")
        add("SELECT (1 + 2) * (3 - 4) AS parens")
        add("SELECT 1 = 1 AS eq, 1 <> 2 AS ne1, 1 != 2 AS ne2, 1 < 2 AS lt, 2 <= 2 AS le, 3 > 2 AS gt, 3 >= 3 AS ge")
        add("SELECT 'a' || 'b' AS concat")
        add('SELECT "col" FROM "tbl"')
        add("SELECT `col` FROM `tbl`")
        add("SELECT [col] FROM [tbl]")

        # Functions
        add("SELECT COUNT(*) AS c FROM t")
        add("SELECT SUM(a) AS s, MIN(a) AS mn, MAX(a) AS mx, AVG(a) AS av FROM t")
        add("SELECT COALESCE(a, 0) AS c, NULLIF(a, 0) AS n FROM t")
        add("SELECT ABS(-3) AS a, ROUND(3.14159, 2) AS r")
        add("SELECT LOWER('AbC') AS l, UPPER('AbC') AS u, LENGTH('xyz') AS len")
        add("SELECT SUBSTR('abcdef', 2, 3) AS sub")

        # FROM / aliases
        add("SELECT * FROM t")
        add("SELECT a, b, c FROM t")
        add("SELECT t.a, t.b FROM t AS t WHERE t.a = 1")
        add("SELECT a AS x, b y FROM t")

        # WHERE clause variants
        add("SELECT a FROM t WHERE a = 1")
        add("SELECT a FROM t WHERE NOT (a = 1)")
        add("SELECT a FROM t WHERE a = 1 AND b = 2 OR c = 3")
        add("SELECT a FROM t WHERE (a = 1 AND b = 2) OR (c = 3 AND d = 4)")
        add("SELECT a FROM t WHERE a BETWEEN 1 AND 10")
        add("SELECT a FROM t WHERE a NOT BETWEEN 1 AND 10")
        add("SELECT a FROM t WHERE a IN (1, 2, 3)")
        add("SELECT a FROM t WHERE a NOT IN (1, 2, 3)")
        add("SELECT a FROM t WHERE a IN (SELECT a FROM t2)")
        add("SELECT a FROM t WHERE EXISTS (SELECT 1 FROM t2 WHERE t2.id = t.id)")
        add("SELECT a FROM t WHERE a LIKE 'x%'")
        add("SELECT a FROM t WHERE a NOT LIKE 'x%'")
        add("SELECT a FROM t WHERE a LIKE '100!_%' ESCAPE '!'")
        add("SELECT a FROM t WHERE a IS NULL")
        add("SELECT a FROM t WHERE a IS NOT NULL")

        # CASE, CAST, scalar subquery
        add("SELECT CASE WHEN 1 < 2 THEN 'yes' ELSE 'no' END AS c")
        add("SELECT CAST('123' AS INTEGER) AS i")
        add("SELECT (SELECT 1) AS scalar_subq")

        # GROUP BY / HAVING / ORDER BY / LIMIT
        add("SELECT a, COUNT(*) AS c FROM t GROUP BY a")
        add("SELECT a, SUM(b) AS s FROM t GROUP BY a HAVING SUM(b) > 10")
        add("SELECT a FROM t ORDER BY a")
        add("SELECT a FROM t ORDER BY a DESC, b ASC")
        add("SELECT a FROM t ORDER BY 1 DESC")
        add("SELECT a FROM t LIMIT 10")
        add("SELECT a FROM t LIMIT 10 OFFSET 5")

        # JOINs
        add("SELECT * FROM t1 JOIN t2 ON t1.id = t2.id")
        add("SELECT * FROM t1 INNER JOIN t2 ON t1.id = t2.id")
        add("SELECT * FROM t1 LEFT JOIN t2 ON t1.id = t2.id")
        add("SELECT * FROM t1 LEFT OUTER JOIN t2 ON t1.id = t2.id")
        add("SELECT * FROM t1 RIGHT JOIN t2 ON t1.id = t2.id")
        add("SELECT * FROM t1 FULL JOIN t2 ON t1.id = t2.id")
        add("SELECT * FROM t1 CROSS JOIN t2")
        add("SELECT * FROM t1 JOIN t2 USING (id)")

        # Subquery in FROM
        add("SELECT * FROM (SELECT 1 AS a, 2 AS b) sub")
        add("SELECT sub.a FROM (SELECT 1 AS a) sub WHERE sub.a = 1")

        # Set operations
        add("SELECT 1 UNION SELECT 2")
        add("SELECT 1 UNION ALL SELECT 2")
        add("(SELECT 1) UNION (SELECT 2)")
        add("SELECT 1 INTERSECT SELECT 1")
        add("SELECT 1 EXCEPT SELECT 2")

        # WITH / RECURSIVE
        add("WITH cte(x) AS (SELECT 1) SELECT x FROM cte")
        add("WITH cte AS (SELECT 1 AS x UNION ALL SELECT 2 AS x) SELECT x FROM cte ORDER BY x")
        add(
            "WITH RECURSIVE cte(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM cte WHERE n < 3) SELECT n FROM cte"
        )

        # DML
        add("INSERT INTO t(a, b) VALUES (1, 'x')")
        add("INSERT INTO t(a) VALUES (NULL)")
        add("INSERT INTO t DEFAULT VALUES")
        add("INSERT INTO t(a) SELECT a FROM t2")
        add("UPDATE t SET a = 1, b = b + 1 WHERE id = 42")
        add("DELETE FROM t WHERE a = 1")
        add("DELETE FROM t WHERE a IN (SELECT a FROM t2 WHERE b IS NULL)")

        # DDL
        add("CREATE TABLE t (id INTEGER PRIMARY KEY, a TEXT NOT NULL, b REAL DEFAULT 0, c TEXT UNIQUE)")
        add("CREATE TABLE t2 (id INTEGER, t_id INTEGER REFERENCES t(id), CHECK (id > 0))")
        add("DROP TABLE t")
        add("DROP TABLE IF EXISTS t")
        add("CREATE INDEX idx_t_a ON t(a)")
        add("DROP INDEX idx_t_a")
        add("DROP INDEX IF EXISTS idx_t_a")
        add("CREATE VIEW v AS SELECT a FROM t")
        add("DROP VIEW v")
        add("DROP VIEW IF EXISTS v")
        add("ALTER TABLE t ADD COLUMN d TEXT")
        add("ALTER TABLE t RENAME TO t_new")
        add("ALTER TABLE t RENAME COLUMN a TO a2")

        # Transaction-ish
        add("BEGIN")
        add("COMMIT")
        add("ROLLBACK")
        add("SAVEPOINT sp1")
        add("RELEASE sp1")
        add("ROLLBACK TO sp1")

        # Mega query attempting to hit lots of parser paths in one statement
        add(
            "WITH cte(id, val) AS (SELECT 1, 'a' UNION ALL SELECT 2, 'b') "
            "SELECT DISTINCT t1.id AS i, COALESCE(t2.val, cte.val) AS v, "
            "CASE WHEN t1.id IN (SELECT id FROM cte) THEN 1 ELSE 0 END AS flag "
            "FROM t1 LEFT OUTER JOIN t2 ON t1.id = t2.id JOIN cte USING (id) "
            "WHERE (t1.id BETWEEN 1 AND 10 AND t2.val LIKE 'a%') OR t2.val IS NULL "
            "GROUP BY t1.id, v HAVING COUNT(*) > 0 ORDER BY i DESC LIMIT 5 OFFSET 1"
        )

        # Parameter markers (may or may not be supported)
        add("SELECT ?")
        add("SELECT :x")
        add("SELECT a FROM t WHERE a = ? AND b = :b")

        # Validate candidates and compute feature sets
        valid_items = []
        for stmt in candidates.keys():
            ast = try_parse(stmt)
            if ast is None:
                continue
            node_types = collect_node_types(ast)
            text_feats = collect_text_features(stmt)
            feats = set()
            for nt in node_types:
                feats.add("NODE:" + nt)
            feats |= text_feats
            # Ensure statement with same AST nodes but different tokens can still be selected
            feats.add("LEN:" + str(min(200, len(stmt))))
            valid_items.append((stmt, feats))

        if not valid_items:
            # Best-effort minimal fallback
            return ["SELECT 1"]

        # Greedy selection for coverage-like diversity
        max_n = 38
        selected = []
        covered = set()
        remaining = valid_items[:]

        # Prefer statements that carry many features but keep count small
        while remaining and len(selected) < max_n:
            best_i = -1
            best_gain = 0
            best_score = None
            for i, (stmt, feats) in enumerate(remaining):
                gain_set = feats - covered
                gain = len(gain_set)
                if gain <= 0:
                    continue
                # score: primary gain, secondary shorter statement
                score = (gain, -len(stmt))
                if best_score is None or score > best_score:
                    best_score = score
                    best_gain = gain
                    best_i = i
            if best_i < 0:
                break
            stmt, feats = remaining.pop(best_i)
            selected.append(stmt)
            covered |= feats

        # Include a minimal baseline if not already selected
        if all(s.strip().upper() != "SELECT 1" for s in selected):
            ast = try_parse("SELECT 1")
            if ast is not None:
                selected.insert(0, "SELECT 1")

        # Final de-dup preserving order
        out = []
        seen = set()
        for s in selected:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out