import os
import sys
import re
import importlib
from typing import List, Tuple, Set, Dict, Optional


class Solution:
    def solve(self, resources_path: str) -> List[str]:
        resources_path = os.path.abspath(resources_path)
        if resources_path not in sys.path:
            sys.path.insert(0, resources_path)

        parse_sql = self._load_parse_sql()

        parser_src = self._read_text(os.path.join(resources_path, "sql_engine", "parser.py"))
        tokenizer_src = self._read_text(os.path.join(resources_path, "sql_engine", "tokenizer.py"))
        ast_src = self._read_text(os.path.join(resources_path, "sql_engine", "ast_nodes.py"))

        supported_keywords = self._extract_supported_keywords(tokenizer_src, parser_src)
        tok_features = self._detect_tokenizer_features(tokenizer_src)

        candidates = self._build_candidates(supported_keywords, tok_features)
        candidates.extend(self._build_keyword_driven_candidates(supported_keywords, tok_features))
        candidates = self._dedupe_preserve_order(candidates)

        valid: List[Tuple[str, Set[str]]] = []
        for stmt in candidates:
            ok_stmt = self._validate_statement(parse_sql, stmt)
            if ok_stmt is None:
                continue
            feats = self._statement_features(ok_stmt, supported_keywords)
            valid.append((ok_stmt, feats))

        if not valid:
            fallback = ["SELECT 1", "SELECT 1;"]
            out: List[str] = []
            for s in fallback:
                ok_stmt = self._validate_statement(parse_sql, s)
                if ok_stmt is not None:
                    out.append(ok_stmt)
            if not out:
                out = ["SELECT 1"]
            return out

        selected = self._select_statements(valid, max_n=40)
        if not selected:
            selected = [valid[0][0]]
        return selected

    def _load_parse_sql(self):
        try:
            mod = importlib.import_module("sql_engine")
            if hasattr(mod, "parse_sql"):
                return getattr(mod, "parse_sql")
        except Exception:
            pass

        try:
            mod = importlib.import_module("sql_engine.parser")
            if hasattr(mod, "parse_sql"):
                return getattr(mod, "parse_sql")
        except Exception:
            pass

        try:
            pkg = importlib.import_module("sql_engine")
            parser_mod = importlib.import_module("sql_engine.parser")
            tokenizer_mod = importlib.import_module("sql_engine.tokenizer")

            Parser = getattr(parser_mod, "Parser", None)
            tokenize = getattr(tokenizer_mod, "tokenize", None)

            if Parser is not None and tokenize is not None:
                def _parse_sql_fallback(s: str):
                    tokens = tokenize(s)
                    p = Parser(tokens)
                    if hasattr(p, "parse"):
                        return p.parse()
                    if hasattr(p, "parse_statement"):
                        return p.parse_statement()
                    if hasattr(p, "parse_sql"):
                        return p.parse_sql()
                    raise AttributeError("No parse entrypoint found on Parser")
                return _parse_sql_fallback
        except Exception:
            pass

        def _no_parse_sql(_s: str):
            raise ImportError("Could not import parse_sql from sql_engine")
        return _no_parse_sql

    def _read_text(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            try:
                with open(path, "r", encoding="latin-1") as f:
                    return f.read()
            except Exception:
                return ""

    def _extract_supported_keywords(self, tokenizer_src: str, parser_src: str) -> Set[str]:
        kw: Set[str] = set()

        # Try to extract from KEYWORDS dict
        # Patterns like: KEYWORDS = { "SELECT": TokenType.SELECT, ... }
        # Or: keywords = {'select': ...}
        for m in re.finditer(r"(?s)\bKEYWORDS\b\s*=\s*\{(.*?)\}", tokenizer_src):
            body = m.group(1)
            for km in re.finditer(r"['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*:", body):
                k = km.group(1)
                if k.isalpha() or "_" in k:
                    kw.add(k.upper())
        # Also look for an enum or list of keywords
        for m in re.finditer(r"\bkeywords\b\s*=\s*\[(.*?)\]", tokenizer_src, re.IGNORECASE | re.DOTALL):
            body = m.group(1)
            for km in re.finditer(r"['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]", body):
                kw.add(km.group(1).upper())

        # If still empty, scan for known SQL words referenced in parser/tokenizer
        if not kw:
            common = [
                "SELECT", "FROM", "WHERE", "GROUP", "BY", "HAVING", "ORDER", "LIMIT", "OFFSET", "DISTINCT",
                "AS", "AND", "OR", "NOT", "NULL", "TRUE", "FALSE", "IN", "EXISTS", "BETWEEN", "LIKE", "IS",
                "JOIN", "INNER", "LEFT", "RIGHT", "FULL", "OUTER", "CROSS", "NATURAL", "ON", "USING",
                "UNION", "ALL", "INTERSECT", "EXCEPT",
                "WITH", "RECURSIVE",
                "INSERT", "INTO", "VALUES", "DEFAULT",
                "UPDATE", "SET",
                "DELETE",
                "CREATE", "TABLE", "VIEW", "INDEX", "DROP", "ALTER", "ADD", "COLUMN",
                "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "UNIQUE", "CHECK", "CONSTRAINT",
                "CASE", "WHEN", "THEN", "ELSE", "END",
                "CAST", "COLLATE",
                "BEGIN", "COMMIT", "ROLLBACK", "TRANSACTION",
                "ASC", "DESC",
            ]
            hay = (tokenizer_src or "") + "\n" + (parser_src or "")
            hay_u = hay.upper()
            for w in common:
                if w in hay_u:
                    kw.add(w)

        return kw

    def _detect_tokenizer_features(self, tokenizer_src: str) -> Dict[str, bool]:
        s = tokenizer_src or ""
        return {
            "backtick_ident": ("`" in s) or ("BACKTICK" in s.upper()),
            "bracket_ident": ("[" in s and "]" in s) or ("BRACKET" in s.upper()),
            "double_quote_ident": ('"' in s) or ("DOUBLE_QUOTE" in s.upper()),
            "line_comment": ("--" in s) or ("LINE_COMMENT" in s.upper()),
            "block_comment": ("/*" in s and "*/" in s) or ("BLOCK_COMMENT" in s.upper()),
            "hex_number": ("0x" in s.lower()) or ("HEX" in s.upper()),
            "param_qmark": ("?" in s),
            "param_colon": (":" in s),
        }

    def _kw_supported(self, supported: Set[str], *need: str) -> bool:
        if not supported:
            return True
        for n in need:
            if n.upper() not in supported:
                return False
        return True

    def _build_candidates(self, supported_keywords: Set[str], tok_features: Dict[str, bool]) -> List[str]:
        c: List[str] = []

        def add(stmt: str, *need: str):
            if self._kw_supported(supported_keywords, *need):
                c.append(stmt)

        # Baseline SELECTs
        add("SELECT 1", "SELECT")
        add("SELECT 1;", "SELECT")
        add("SELECT\t1", "SELECT")
        add("SELECT 1 AS one", "SELECT", "AS")
        add("SELECT NULL", "SELECT", "NULL")
        add("SELECT TRUE, FALSE", "SELECT")
        add("SELECT 'a''b'", "SELECT")
        add("SELECT 123, 45.67, 1e3, 1.2e-3", "SELECT")
        add("SELECT (1 + 2) * 3 - 4 / 5", "SELECT")
        add("SELECT -1, +2", "SELECT")

        # FROM / WHERE variants
        add("SELECT a FROM t", "SELECT", "FROM")
        add("SELECT DISTINCT a FROM t", "SELECT", "DISTINCT", "FROM")
        add("SELECT a,b,c FROM t WHERE a = 1", "SELECT", "FROM", "WHERE")
        add("SELECT a FROM t WHERE a <> 1", "SELECT", "FROM", "WHERE")
        add("SELECT a FROM t WHERE a != 1", "SELECT", "FROM", "WHERE")
        add("SELECT a FROM t WHERE a < 1 OR a > 10", "SELECT", "FROM", "WHERE", "OR")
        add("SELECT a FROM t WHERE NOT (a = 1 AND b = 2)", "SELECT", "FROM", "WHERE", "NOT")
        add("SELECT a FROM t WHERE a BETWEEN 1 AND 3", "SELECT", "FROM", "WHERE", "BETWEEN", "AND")
        add("SELECT a FROM t WHERE a IN (1,2,3)", "SELECT", "FROM", "WHERE", "IN")
        add("SELECT a FROM t WHERE a IN (SELECT a FROM t2)", "SELECT", "FROM", "WHERE", "IN")
        add("SELECT a FROM t WHERE EXISTS (SELECT 1 FROM t2 WHERE t2.id = t.id)", "SELECT", "FROM", "WHERE", "EXISTS")
        add("SELECT a FROM t WHERE a LIKE '%x%'", "SELECT", "FROM", "WHERE", "LIKE")
        add("SELECT a FROM t WHERE a IS NULL", "SELECT", "FROM", "WHERE", "IS", "NULL")
        add("SELECT a FROM t WHERE a IS NOT NULL", "SELECT", "FROM", "WHERE", "IS", "NOT", "NULL")

        # ORDER / LIMIT / OFFSET
        add("SELECT a FROM t ORDER BY a", "SELECT", "FROM", "ORDER", "BY")
        add("SELECT a FROM t ORDER BY a DESC, b ASC", "SELECT", "FROM", "ORDER", "BY")
        add("SELECT a FROM t LIMIT 10", "SELECT", "FROM", "LIMIT")
        add("SELECT a FROM t LIMIT 10 OFFSET 5", "SELECT", "FROM", "LIMIT", "OFFSET")

        # GROUP BY / HAVING
        add("SELECT a, COUNT(*) FROM t GROUP BY a", "SELECT", "FROM", "GROUP", "BY")
        add("SELECT a, COUNT(*) FROM t GROUP BY a HAVING COUNT(*) > 1", "SELECT", "FROM", "GROUP", "BY", "HAVING")

        # Joins
        add("SELECT t1.a, t2.b FROM t1 JOIN t2 ON t1.id = t2.id", "SELECT", "FROM", "JOIN", "ON")
        add("SELECT t1.a FROM t1 INNER JOIN t2 ON t1.id = t2.id", "SELECT", "FROM", "JOIN", "ON", "INNER")
        add("SELECT t1.a FROM t1 LEFT JOIN t2 ON t1.id = t2.id", "SELECT", "FROM", "JOIN", "ON", "LEFT")
        add("SELECT t1.a FROM t1 LEFT OUTER JOIN t2 ON t1.id = t2.id", "SELECT", "FROM", "JOIN", "ON", "LEFT", "OUTER")
        add("SELECT t1.a FROM t1 RIGHT JOIN t2 ON t1.id = t2.id", "SELECT", "FROM", "JOIN", "ON", "RIGHT")
        add("SELECT t1.a FROM t1 CROSS JOIN t2", "SELECT", "FROM", "CROSS", "JOIN")
        add("SELECT t1.a FROM t1 JOIN t2 USING (id)", "SELECT", "FROM", "JOIN", "USING")

        # Subquery / derived table
        add("SELECT * FROM (SELECT 1 AS a) sub", "SELECT", "FROM", "AS")
        add("SELECT (SELECT 1) AS x", "SELECT", "AS")

        # WITH / CTE
        add("WITH cte AS (SELECT 1 AS a) SELECT a FROM cte", "WITH", "AS", "SELECT", "FROM")

        # CASE / functions / CAST
        add("SELECT CASE WHEN a > 0 THEN 'pos' ELSE 'neg' END FROM t", "SELECT", "CASE", "WHEN", "THEN", "ELSE", "END", "FROM")
        add("SELECT COALESCE(a, 0) FROM t", "SELECT", "FROM")
        add("SELECT CAST(a AS INT) FROM t", "SELECT", "CAST", "AS", "FROM")

        # Set operations
        add("SELECT a FROM t UNION SELECT a FROM t2", "SELECT", "FROM", "UNION")
        add("SELECT a FROM t UNION ALL SELECT a FROM t2", "SELECT", "FROM", "UNION", "ALL")
        add("SELECT a FROM t INTERSECT SELECT a FROM t2", "SELECT", "FROM", "INTERSECT")
        add("SELECT a FROM t EXCEPT SELECT a FROM t2", "SELECT", "FROM", "EXCEPT")

        # INSERT/UPDATE/DELETE
        add("INSERT INTO t(a,b) VALUES (1,'x')", "INSERT", "INTO", "VALUES")
        add("INSERT INTO t(a,b) VALUES (1,'x'), (2,'y')", "INSERT", "INTO", "VALUES")
        add("INSERT INTO t DEFAULT VALUES", "INSERT", "INTO", "DEFAULT", "VALUES")
        add("INSERT INTO t(a) SELECT a FROM t2", "INSERT", "INTO", "SELECT", "FROM")
        add("UPDATE t SET a = 1", "UPDATE", "SET")
        add("UPDATE t SET a = 1, b = 'x' WHERE id = 2", "UPDATE", "SET", "WHERE")
        add("DELETE FROM t", "DELETE", "FROM")
        add("DELETE FROM t WHERE id IN (SELECT id FROM t2)", "DELETE", "FROM", "WHERE", "IN", "SELECT")

        # DDL
        add("CREATE TABLE t(id INT PRIMARY KEY, name TEXT NOT NULL, amount REAL DEFAULT 0.0)", "CREATE", "TABLE")
        add("CREATE TABLE t2(a INT, b INT, CHECK (a > b))", "CREATE", "TABLE", "CHECK")
        add("CREATE TABLE t3(id INT, a INT, b INT, UNIQUE (a, b))", "CREATE", "TABLE", "UNIQUE")
        add("ALTER TABLE t ADD COLUMN c TEXT", "ALTER", "TABLE", "ADD", "COLUMN")
        add("DROP TABLE t", "DROP", "TABLE")
        add("CREATE INDEX idx_t_a ON t(a)", "CREATE", "INDEX", "ON")
        add("DROP INDEX idx_t_a", "DROP", "INDEX")
        add("CREATE VIEW v AS SELECT a FROM t", "CREATE", "VIEW", "AS", "SELECT", "FROM")
        add("DROP VIEW v", "DROP", "VIEW")

        # Transactions
        add("BEGIN", "BEGIN")
        add("BEGIN TRANSACTION", "BEGIN", "TRANSACTION")
        add("COMMIT", "COMMIT")
        add("ROLLBACK", "ROLLBACK")

        # Tokenizer stress: comments and quoting
        if tok_features.get("line_comment", True):
            add("SELECT --comment\n 1", "SELECT")
        if tok_features.get("block_comment", True):
            add("SELECT /*block*/ 1", "SELECT")

        if tok_features.get("double_quote_ident", True):
            add('SELECT "a" FROM "t"', "SELECT", "FROM")
            add('SELECT "weird""name" AS "alias" FROM "t"', "SELECT", "FROM", "AS")

        if tok_features.get("backtick_ident", True):
            add("SELECT `a` FROM `t`", "SELECT", "FROM")

        if tok_features.get("bracket_ident", True):
            add("SELECT [a] FROM [t]", "SELECT", "FROM")

        # Parameter placeholders if supported
        add("SELECT ?", "SELECT")
        add("SELECT :x", "SELECT")

        # Hex literal if supported
        add("SELECT 0x10", "SELECT")

        return c

    def _build_keyword_driven_candidates(self, supported_keywords: Set[str], tok_features: Dict[str, bool]) -> List[str]:
        # Some slightly more complex variations, gated by keyword presence
        c: List[str] = []

        def add(stmt: str, *need: str):
            if self._kw_supported(supported_keywords, *need):
                c.append(stmt)

        add(
            "SELECT t1.a, COUNT(*) AS cnt "
            "FROM t1 LEFT JOIN t2 ON t1.id = t2.id "
            "WHERE (t1.a IS NOT NULL AND t2.b IN (1,2,3)) OR EXISTS (SELECT 1 FROM t3 WHERE t3.id = t1.id) "
            "GROUP BY t1.a "
            "HAVING COUNT(*) >= 1 "
            "ORDER BY cnt DESC, t1.a ASC "
            "LIMIT 10 OFFSET 0",
            "SELECT", "FROM"
        )

        add(
            "WITH cte AS (SELECT a, b FROM t WHERE a BETWEEN 1 AND 10) "
            "SELECT a FROM cte WHERE b LIKE 'x%' ORDER BY a",
            "WITH", "SELECT", "FROM"
        )

        add(
            "INSERT INTO t(a,b) SELECT a, b FROM t2 WHERE a IS NOT NULL",
            "INSERT", "INTO", "SELECT", "FROM", "WHERE"
        )

        add(
            "UPDATE t SET a = a + 1, b = COALESCE(b, 'x') WHERE id = (SELECT MAX(id) FROM t)",
            "UPDATE", "SET", "WHERE", "SELECT", "FROM"
        )

        add(
            "DELETE FROM t WHERE EXISTS (SELECT 1 FROM t2 WHERE t2.id = t.id)",
            "DELETE", "FROM", "WHERE", "EXISTS", "SELECT"
        )

        add(
            "CREATE TABLE t_fk(id INT PRIMARY KEY, parent_id INT, "
            "CONSTRAINT fk_parent FOREIGN KEY (parent_id) REFERENCES t_fk(id))",
            "CREATE", "TABLE"
        )

        add(
            "SELECT CASE WHEN a IS NULL THEN 0 WHEN a < 0 THEN -1 ELSE 1 END FROM t",
            "SELECT", "CASE", "WHEN", "THEN", "ELSE", "END", "FROM"
        )

        add(
            "SELECT a FROM t WHERE a IN (SELECT a FROM t2 UNION SELECT a FROM t3)",
            "SELECT", "FROM", "WHERE", "IN", "UNION"
        )

        add(
            "SELECT * FROM (SELECT a FROM t ORDER BY a LIMIT 5) x ORDER BY a DESC",
            "SELECT", "FROM", "ORDER", "BY", "LIMIT"
        )

        # Some dialect-ish constructs; will be filtered by parsing
        add("SELECT a FROM t ORDER BY a DESC NULLS LAST", "SELECT", "FROM", "ORDER", "BY")
        add("SELECT a FROM t FETCH FIRST 10 ROWS ONLY", "SELECT", "FROM")
        add("SELECT a FROM t FOR UPDATE", "SELECT", "FROM")

        return c

    def _validate_statement(self, parse_sql, stmt: str) -> Optional[str]:
        s = stmt.strip()
        if not s:
            return None
        trials = []
        if s.endswith(";"):
            trials.append(s)
            trials.append(s[:-1].rstrip())
        else:
            trials.append(s)
            trials.append(s + ";")

        for t in trials:
            try:
                parse_sql(t)
                return t
            except Exception:
                continue
        return None

    def _statement_features(self, stmt: str, supported_keywords: Set[str]) -> Set[str]:
        feats: Set[str] = set()

        s = stmt
        su = s.upper()

        # keyword features
        words = set(re.findall(r"\b[A-Z_]+\b", su))
        if supported_keywords:
            words = {w for w in words if w in supported_keywords}
        feats |= {f"KW:{w}" for w in words}

        # statement type
        first_kw = None
        for w in re.findall(r"\b[A-Z_]+\b", su):
            if not supported_keywords or w in supported_keywords:
                first_kw = w
                break
        if first_kw:
            feats.add(f"STMT:{first_kw}")

        # literals / tokens
        if re.search(r"'.*?'", s, re.DOTALL):
            feats.add("LIT:STRING")
        if "''" in s:
            feats.add("LIT:STRING_ESC")
        if re.search(r"\b\d+\b", s):
            feats.add("LIT:INT")
        if re.search(r"\b\d+\.\d+\b", s):
            feats.add("LIT:FLOAT")
        if re.search(r"\b\d+(\.\d+)?[eE][+-]?\d+\b", s):
            feats.add("LIT:EXP")
        if re.search(r"\b0x[0-9a-fA-F]+\b", s):
            feats.add("LIT:HEX")
        if "NULL" in su:
            feats.add("LIT:NULL")
        if "TRUE" in su or "FALSE" in su:
            feats.add("LIT:BOOL")

        # operators / punctuation
        if any(op in s for op in ["+", "-", "*", "/", "%"]):
            feats.add("OP:ARITH")
        if any(op in s for op in ["=", "<>", "!=", "<=", ">=", "<", ">"]):
            feats.add("OP:COMP")
        if "(" in s and ")" in s:
            feats.add("PAREN")
        if "." in s:
            feats.add("DOT")
        if ";" in s:
            feats.add("SEMI")

        # comments / quoting
        if "--" in s:
            feats.add("COMMENT:LINE")
        if "/*" in s and "*/" in s:
            feats.add("COMMENT:BLOCK")
        if '"' in s:
            feats.add("QUOTE:DQ")
        if "`" in s:
            feats.add("QUOTE:BT")
        if "[" in s and "]" in s:
            feats.add("QUOTE:BR")

        # placeholders
        if "?" in s:
            feats.add("PARAM:?")
        if re.search(r":[A-Za-z_]\w*", s):
            feats.add("PARAM::NAME")

        # clause combos
        if "JOIN" in su:
            feats.add("CLAUSE:JOIN")
        if "WHERE" in su:
            feats.add("CLAUSE:WHERE")
        if "GROUP" in su and "BY" in su:
            feats.add("CLAUSE:GROUPBY")
        if "HAVING" in su:
            feats.add("CLAUSE:HAVING")
        if "ORDER" in su and "BY" in su:
            feats.add("CLAUSE:ORDERBY")
        if "LIMIT" in su:
            feats.add("CLAUSE:LIMIT")
        if "OFFSET" in su:
            feats.add("CLAUSE:OFFSET")
        if "WITH" in su:
            feats.add("CLAUSE:WITH")
        if "UNION" in su or "INTERSECT" in su or "EXCEPT" in su:
            feats.add("CLAUSE:SETOP")
        if "CASE" in su:
            feats.add("EXPR:CASE")
        if "CAST" in su:
            feats.add("EXPR:CAST")
        if "EXISTS" in su:
            feats.add("EXPR:EXISTS")
        if "IN" in su:
            feats.add("EXPR:IN")
        if "BETWEEN" in su:
            feats.add("EXPR:BETWEEN")
        if "LIKE" in su:
            feats.add("EXPR:LIKE")
        if "IS" in su:
            feats.add("EXPR:IS")

        return feats

    def _select_statements(self, valid: List[Tuple[str, Set[str]]], max_n: int = 40) -> List[str]:
        # Greedy set cover on features; prefer statements that add new features.
        # Tie-break by longer statement (likely exercises more code) and deterministic order.
        remaining = list(valid)
        selected: List[Tuple[str, Set[str]]] = []
        covered: Set[str] = set()

        # Ensure at least one simple SELECT if available
        remaining_sorted = sorted(
            remaining,
            key=lambda x: (0 if x[0].strip().upper().startswith("SELECT") else 1, len(x[0])),
        )
        seed = None
        for stmt, feats in remaining_sorted:
            if stmt.strip().upper().startswith("SELECT"):
                seed = (stmt, feats)
                break
        if seed is None:
            seed = remaining_sorted[0]
        selected.append(seed)
        covered |= seed[1]
        remaining = [x for x in remaining if x[0] != seed[0]]

        # Greedy selection
        while remaining and len(selected) < max_n:
            best_idx = -1
            best_gain = -1
            best_len = -1
            best_stmt = None
            best_feats = None

            for i, (stmt, feats) in enumerate(remaining):
                gain = len(feats - covered)
                if gain > best_gain:
                    best_gain = gain
                    best_idx = i
                    best_len = len(stmt)
                    best_stmt = stmt
                    best_feats = feats
                elif gain == best_gain and gain > 0:
                    l = len(stmt)
                    if l > best_len:
                        best_idx = i
                        best_len = l
                        best_stmt = stmt
                        best_feats = feats

            if best_gain <= 0:
                break

            chosen = remaining.pop(best_idx)
            selected.append(chosen)
            covered |= chosen[1]

        # Add a few more diverse statement types if they parsed and weren't selected, without bloating too much
        desired_types = ["INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "BEGIN", "COMMIT", "ROLLBACK", "WITH"]
        selected_texts = {s for s, _ in selected}
        for typ in desired_types:
            if len(selected) >= max_n:
                break
            if any(s.strip().upper().startswith(typ) for s, _ in selected):
                continue
            for stmt, feats in valid:
                if stmt in selected_texts:
                    continue
                if stmt.strip().upper().startswith(typ):
                    selected.append((stmt, feats))
                    selected_texts.add(stmt)
                    break

        # Final deterministic order: keep selection order
        out = [s for s, _ in selected]
        out = self._dedupe_preserve_order(out)
        return out

    def _dedupe_preserve_order(self, items: List[str]) -> List[str]:
        seen: Set[str] = set()
        out: List[str] = []
        for x in items:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out