import os
import re
from pathlib import Path


class Solution:
    def solve(self, resources_path: str) -> dict:
        resources = Path(resources_path)

        keywords = set()

        def add_kw(s: str):
            if not s:
                return
            s = s.strip()
            if not s:
                return
            if len(s) > 40:
                return
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", s):
                keywords.add(s)

        # Extract from grammar
        gp = resources / "sql_grammar.txt"
        if gp.is_file():
            try:
                txt = gp.read_text(encoding="utf-8", errors="ignore")
                for m in re.finditer(r"\b[A-Z][A-Z_]{1,30}\b", txt):
                    add_kw(m.group(0))
                for m in re.finditer(r"['\"]([A-Z][A-Z_]{1,30})['\"]", txt):
                    add_kw(m.group(1))
            except Exception:
                pass

        # Extract from parser/tokenizer sources
        engine_dir = resources / "sql_engine"
        for fp in (engine_dir / "parser.py", engine_dir / "tokenizer.py", engine_dir / "ast_nodes.py"):
            if fp.is_file():
                try:
                    src = fp.read_text(encoding="utf-8", errors="ignore")
                    for m in re.finditer(r"['\"]([A-Z][A-Z_]{1,30})['\"]", src):
                        add_kw(m.group(1))
                except Exception:
                    pass

        # Baseline SQL keywords if extraction fails or misses common tokens
        baseline = {
            "SELECT",
            "FROM",
            "WHERE",
            "GROUP",
            "BY",
            "HAVING",
            "ORDER",
            "LIMIT",
            "OFFSET",
            "AS",
            "DISTINCT",
            "ALL",
            "UNION",
            "INTERSECT",
            "EXCEPT",
            "WITH",
            "RECURSIVE",
            "INSERT",
            "INTO",
            "VALUES",
            "UPDATE",
            "SET",
            "DELETE",
            "CREATE",
            "TABLE",
            "VIEW",
            "INDEX",
            "TRIGGER",
            "DROP",
            "ALTER",
            "ADD",
            "COLUMN",
            "RENAME",
            "TO",
            "IF",
            "NOT",
            "EXISTS",
            "PRIMARY",
            "KEY",
            "FOREIGN",
            "REFERENCES",
            "CHECK",
            "DEFAULT",
            "NULL",
            "UNIQUE",
            "ON",
            "JOIN",
            "LEFT",
            "RIGHT",
            "INNER",
            "OUTER",
            "CROSS",
            "NATURAL",
            "USING",
            "CASE",
            "WHEN",
            "THEN",
            "ELSE",
            "END",
            "AND",
            "OR",
            "IN",
            "IS",
            "LIKE",
            "BETWEEN",
            "ESCAPE",
            "CAST",
            "COLLATE",
            "ASC",
            "DESC",
            "TRUE",
            "FALSE",
            "BEGIN",
            "COMMIT",
            "ROLLBACK",
            "SAVEPOINT",
            "RELEASE",
            "PRAGMA",
            "EXPLAIN",
        }
        keywords |= baseline

        # Avoid huge code string; cap keywords to a reasonable number, prefer baseline + extracted frequent
        # (No frequency analysis here; just cap to deterministic sorted subset while keeping baseline.)
        kws_sorted = sorted(keywords)
        # keep baseline first, then remaining
        baseline_sorted = sorted(baseline)
        baseline_set = set(baseline_sorted)
        remainder = [k for k in kws_sorted if k not in baseline_set]
        cap = 350
        if len(baseline_sorted) > cap:
            kws_final = baseline_sorted[:cap]
        else:
            kws_final = baseline_sorted + remainder[: max(0, cap - len(baseline_sorted))]

        code = f"""import random
import re

KEYWORDS = {kws_final!r}

_rng = random.Random(0xC0FFEE)
_call = 0
_corpus = []

_WS_CHOICES = [" ", "  ", "\\t", "\\n", "\\r\\n", "\\f", "\\v", "\\u00a0", "\\u2003"]
_JOINER = re.compile(
    r"(\\s+|--[^\\n]*\\n|/\\*.*?\\*/|<=|>=|<>|!=|==|\\|\\||\\b|[(),;.]|[=<>+\\-*/%])",
    re.S | re.M
)

_COMMON_TYPES = ["INTEGER", "INT", "TEXT", "REAL", "BLOB", "NUMERIC", "BOOLEAN", "VARCHAR(10)", "CHAR(1)"]
_COMMON_FUNCS = ["COUNT", "SUM", "MIN", "MAX", "AVG", "ABS", "LENGTH", "UPPER", "LOWER", "COALESCE", "NULLIF", "IFNULL", "ROUND", "SUBSTR"]
_TABLE_BASE = ["t", "u", "v", "users", "orders", "items", "products", "logs", "kv", "edge", "tmp"]
_COL_BASE = ["id", "name", "val", "price", "qty", "ts", "flag", "data", "x", "y", "z", "a", "b", "c"]

def _ws():
    return _rng.choice(_WS_CHOICES)

def _maybe_semicolon(s: str) -> str:
    if _rng.random() < 0.75:
        if not s.rstrip().endswith(";"):
            s = s.rstrip() + ";"
        if _rng.random() < 0.08:
            s += _rng.choice([";", ";;", " ; ; "])
    return s

def _rand_case(s: str) -> str:
    # Randomize case to exercise keyword matching/tokenizer branches
    out = []
    for ch in s:
        if "a" <= ch <= "z" or "A" <= ch <= "Z":
            out.append(ch.upper() if _rng.random() < 0.55 else ch.lower())
        else:
            out.append(ch)
    return "".join(out)

def _ident_base():
    b = _rng.choice(_TABLE_BASE + _COL_BASE + ["col", "tbl", "idx", "select", "from", "where", "group", "order"])
    if _rng.random() < 0.8:
        b = b + str(_rng.randrange(0, 200))
    return b

def _quote_ident(name: str) -> str:
    r = _rng.random()
    if r < 0.60:
        return name
    if r < 0.75:
        return '"' + name.replace('"', '""') + '"'
    if r < 0.90:
        return "`" + name.replace("`", "``") + "`"
    return "[" + name.replace("]", "]]") + "]"

def _ident():
    return _quote_ident(_ident_base())

def _string():
    # Include edge cases: quotes, doubled quotes, newlines
    base = _rng.choice(["", "a", "A", "test", "NULL", "O'Reilly", "x\\ny", "  spaced  ", "/*not_comment*/", "--not_comment", "\\u2603"])
    if _rng.random() < 0.2:
        base += str(_rng.randrange(0, 1000))
    base = base.replace("'", "''")
    return "'" + base + "'"

def _number():
    r = _rng.random()
    if r < 0.35:
        return str(_rng.randrange(-10, 5000))
    if r < 0.55:
        return str(_rng.randrange(0, 1000)) + "." + str(_rng.randrange(0, 1000))
    if r < 0.70:
        return "." + str(_rng.randrange(0, 1000))
    if r < 0.85:
        return str(_rng.randrange(0, 1000)) + "."
    if r < 0.95:
        return str(_rng.randrange(0, 99)) + "e" + _rng.choice(["+", "-", ""]) + str(_rng.randrange(0, 20))
    return "0x" + format(_rng.randrange(0, 65535), "x")

def _param():
    return _rng.choice(["?", "??", ":x", ":name", "@p", "$1", "$2", "$val", ":1"])

def _literal():
    r = _rng.random()
    if r < 0.30:
        return _number()
    if r < 0.55:
        return _string()
    if r < 0.72:
        return _rng.choice(["NULL", "TRUE", "FALSE"])
    if r < 0.90:
        return _param()
    # blob-like literal commonly in SQL dialects
    return "X" + _string().replace("''", "").replace("'", "'ABCD'")

def _binop():
    return _rng.choice(["+", "-", "*", "/", "%", "||", "AND", "OR", "=", "<", ">", "<=", ">=", "<>", "!=", "=="])

def _unop():
    return _rng.choice(["+", "-", "NOT"])

def _maybe_parens(s: str) -> str:
    if _rng.random() < 0.4:
        return "(" + s + ")"
    return s

def _expr(depth: int = 0) -> str:
    if depth > 3:
        r = _rng.random()
        if r < 0.40:
            return _literal()
        if r < 0.70:
            return _ident()
        return _maybe_parens(_ident() + "." + _ident())
    r = _rng.random()
    if r < 0.20:
        return _literal()
    if r < 0.40:
        return _ident()
    if r < 0.52:
        return _maybe_parens(_ident() + "." + _ident())
    if r < 0.68:
        # function call
        fn = _rng.choice(_COMMON_FUNCS)
        argc = 0
        if fn in ("COUNT", "SUM", "MIN", "MAX", "AVG"):
            argc = _rng.randrange(1, 3)
        else:
            argc = _rng.randrange(1, 4)
        args = []
        if fn == "COUNT" and _rng.random() < 0.2:
            args = ["*"]
        else:
            args = [_expr(depth + 1) for _ in range(argc)]
        if _rng.random() < 0.15:
            args = ["DISTINCT " + args[0]]
        return fn + "(" + ", ".join(args) + ")"
    if r < 0.78:
        # CAST
        return "CAST(" + _expr(depth + 1) + " AS " + _rng.choice(_COMMON_TYPES) + ")"
    if r < 0.88:
        # CASE
        parts = ["CASE"]
        whens = _rng.randrange(1, 4)
        for _ in range(whens):
            parts.append("WHEN " + _cond(depth + 1) + " THEN " + _expr(depth + 1))
        if _rng.random() < 0.8:
            parts.append("ELSE " + _expr(depth + 1))
        parts.append("END")
        return " ".join(parts)
    if r < 0.94:
        return _unop() + " " + _maybe_parens(_expr(depth + 1))
    # binary
    return _maybe_parens(_expr(depth + 1) + " " + _binop() + " " + _expr(depth + 1))

def _cond(depth: int = 0) -> str:
    r = _rng.random()
    if r < 0.25:
        return _expr(depth + 1) + " " + _rng.choice(["=", "<", ">", "<=", ">=", "<>", "!=", "=="]) + " " + _expr(depth + 1)
    if r < 0.40:
        return _expr(depth + 1) + " IS " + (_rng.choice(["NOT ", ""]) if _rng.random() < 0.6 else "") + "NULL"
    if r < 0.55:
        return _expr(depth + 1) + " BETWEEN " + _expr(depth + 1) + " AND " + _expr(depth + 1)
    if r < 0.70:
        # IN list / subquery
        if _rng.random() < 0.7:
            n = _rng.randrange(1, 6)
            lst = ", ".join(_expr(depth + 1) for _ in range(n))
            return _expr(depth + 1) + " IN (" + lst + ")"
        return _expr(depth + 1) + " IN (" + _select(depth + 1, as_subquery=True) + ")"
    if r < 0.82:
        esc = ""
        if _rng.random() < 0.4:
            esc = " ESCAPE " + _string()
        return _expr(depth + 1) + " " + _rng.choice(["LIKE", "GLOB", "REGEXP", "MATCH"]) + " " + _string() + esc
    if r < 0.90:
        # EXISTS
        return "EXISTS (" + _select(depth + 1, as_subquery=True) + ")"
    # boolean combination
    op = _rng.choice(["AND", "OR"])
    return _maybe_parens(_cond(depth + 1) + " " + op + " " + _cond(depth + 1))

def _table_ref(depth: int = 0) -> str:
    if depth < 2 and _rng.random() < 0.25:
        alias = _ident()
        return "(" + _select(depth + 1, as_subquery=True) + ") " + (_rng.choice(["AS ", ""]) if _rng.random() < 0.8 else "") + alias
    t = _ident()
    if _rng.random() < 0.25:
        t = _ident() + "." + t
    if _rng.random() < 0.6:
        t += " " + (_rng.choice(["AS ", ""]) if _rng.random() < 0.8 else "") + _ident()
    return t

def _join_clause(depth: int = 0) -> str:
    jt = _rng.choice(["JOIN", "INNER JOIN", "CROSS JOIN", "LEFT JOIN", "LEFT OUTER JOIN", "RIGHT JOIN", "RIGHT OUTER JOIN", "NATURAL JOIN"])
    t = _table_ref(depth + 1)
    if "CROSS" in jt or "NATURAL" in jt:
        return jt + " " + t
    if _rng.random() < 0.65:
        return jt + " " + t + " ON " + _cond(depth + 1)
    # USING clause
    cols = ", ".join(_ident() for _ in range(_rng.randrange(1, 4)))
    return jt + " " + t + " USING (" + cols + ")"

def _select(depth: int = 0, as_subquery: bool = False) -> str:
    parts = []
    parts.append("SELECT")
    if _rng.random() < 0.18:
        parts.append(_rng.choice(["DISTINCT", "ALL"]))
    # column list
    cols = []
    if _rng.random() < 0.15:
        cols = ["*"]
    else:
        ncol = _rng.randrange(1, 6)
        for _ in range(ncol):
            if _rng.random() < 0.12:
                cols.append(_ident() + ".*")
                continue
            e = _expr(depth + 1)
            if _rng.random() < 0.5:
                e += " " + (_rng.choice(["AS ", ""]) if _rng.random() < 0.8 else "") + _ident()
            cols.append(e)
    parts.append(", ".join(cols))
    if _rng.random() < 0.90 or as_subquery:
        parts.append("FROM")
        frm = _table_ref(depth + 1)
        # joins
        if _rng.random() < 0.55:
            nj = _rng.randrange(1, 4)
            for _ in range(nj):
                frm += " " + _join_clause(depth + 1)
        parts.append(frm)
    if _rng.random() < 0.70:
        parts.append("WHERE " + _cond(depth + 1))
    if _rng.random() < 0.35:
        gcols = ", ".join(_expr(depth + 1) for _ in range(_rng.randrange(1, 4)))
        parts.append("GROUP BY " + gcols)
        if _rng.random() < 0.45:
            parts.append("HAVING " + _cond(depth + 1))
    if _rng.random() < 0.50:
        ocols = []
        for _ in range(_rng.randrange(1, 4)):
            o = _expr(depth + 1)
            if _rng.random() < 0.6:
                o += " " + _rng.choice(["ASC", "DESC"])
            if _rng.random() < 0.15:
                o += " NULLS " + _rng.choice(["FIRST", "LAST"])
            ocols.append(o)
        parts.append("ORDER BY " + ", ".join(ocols))
    if _rng.random() < 0.55:
        parts.append("LIMIT " + _number())
        if _rng.random() < 0.45:
            parts.append("OFFSET " + _number())
    q = " ".join(parts)
    # compound
    if depth < 2 and _rng.random() < 0.20:
        op = _rng.choice(["UNION", "UNION ALL", "INTERSECT", "EXCEPT"])
        q = q + " " + op + " " + _select(depth + 1, as_subquery=True)
    return q

def _insert(depth: int = 0) -> str:
    t = _ident()
    cols = ""
    if _rng.random() < 0.65:
        cols = "(" + ", ".join(_ident() for _ in range(_rng.randrange(1, 6))) + ")"
    if _rng.random() < 0.7:
        # VALUES form
        rows = []
        nrows = _rng.randrange(1, 4)
        nvals = _rng.randrange(1, 6)
        for _ in range(nrows):
            rows.append("(" + ", ".join(_expr(depth + 1) for _ in range(nvals)) + ")")
        return "INSERT INTO " + t + " " + cols + " VALUES " + ", ".join(rows)
    # INSERT SELECT
    return "INSERT INTO " + t + " " + cols + " " + _select(depth + 1, as_subquery=True)

def _update(depth: int = 0) -> str:
    t = _ident()
    assigns = []
    for _ in range(_rng.randrange(1, 6)):
        assigns.append(_ident() + " = " + _expr(depth + 1))
    s = "UPDATE " + t + " SET " + ", ".join(assigns)
    if _rng.random() < 0.75:
        s += " WHERE " + _cond(depth + 1)
    return s

def _delete(depth: int = 0) -> str:
    t = _ident()
    s = "DELETE FROM " + t
    if _rng.random() < 0.8:
        s += " WHERE " + _cond(depth + 1)
    return s

def _create_table(depth: int = 0) -> str:
    t = _ident()
    parts = ["CREATE"]
    if _rng.random() < 0.2:
        parts.append(_rng.choice(["TEMP", "TEMPORARY"]))
    parts.append("TABLE")
    if _rng.random() < 0.45:
        parts.extend(["IF", "NOT", "EXISTS"])
    parts.append(t)
    cols = []
    ncol = _rng.randrange(1, 8)
    pk_added = False
    for i in range(ncol):
        cname = _ident()
        ctype = _rng.choice(_COMMON_TYPES)
        cparts = [cname, ctype]
        if _rng.random() < 0.25 and not pk_added:
            cparts.append("PRIMARY KEY")
            pk_added = True
            if _rng.random() < 0.25:
                cparts.append("AUTOINCREMENT")
        if _rng.random() < 0.25:
            cparts.append("NOT NULL")
        if _rng.random() < 0.18:
            cparts.append("UNIQUE")
        if _rng.random() < 0.25:
            cparts.append("DEFAULT " + _expr(depth + 1))
        if _rng.random() < 0.18:
            cparts.append("CHECK (" + _cond(depth + 1) + ")")
        if _rng.random() < 0.14:
            cparts.append("REFERENCES " + _ident() + "(" + _ident() + ")")
        cols.append(" ".join(cparts))
    # table-level constraints
    if _rng.random() < 0.22:
        cols.append("PRIMARY KEY (" + ", ".join(_ident() for _ in range(_rng.randrange(1, 3))) + ")")
    if _rng.random() < 0.18:
        cols.append("FOREIGN KEY (" + _ident() + ") REFERENCES " + _ident() + "(" + _ident() + ")")
    if _rng.random() < 0.15:
        cols.append("CHECK (" + _cond(depth + 1) + ")")
    parts.append("(" + ", ".join(cols) + ")")
    if _rng.random() < 0.08:
        parts.append("WITHOUT ROWID")
    if _rng.random() < 0.06:
        parts.append("STRICT")
    return " ".join(parts)

def _create_index(depth: int = 0) -> str:
    idx = _ident()
    t = _ident()
    parts = ["CREATE"]
    if _rng.random() < 0.25:
        parts.append("UNIQUE")
    parts.append("INDEX")
    if _rng.random() < 0.35:
        parts.extend(["IF", "NOT", "EXISTS"])
    parts.append(idx)
    parts.append("ON")
    parts.append(t)
    cols = []
    for _ in range(_rng.randrange(1, 5)):
        c = _ident()
        if _rng.random() < 0.6:
            c += " " + _rng.choice(["ASC", "DESC"])
        cols.append(c)
    parts.append("(" + ", ".join(cols) + ")")
    if _rng.random() < 0.12:
        parts.append("WHERE " + _cond(depth + 1))
    return " ".join(parts)

def _alter_table(depth: int = 0) -> str:
    t = _ident()
    r = _rng.random()
    if r < 0.55:
        # ADD COLUMN
        c = _ident()
        s = "ALTER TABLE " + t + " ADD COLUMN " + c + " " + _rng.choice(_COMMON_TYPES)
        if _rng.random() < 0.3:
            s += " DEFAULT " + _expr(depth + 1)
        return s
    if r < 0.80:
        # RENAME TO
        return "ALTER TABLE " + t + " RENAME TO " + _ident()
    # RENAME COLUMN
    return "ALTER TABLE " + t + " RENAME COLUMN " + _ident() + " TO " + _ident()

def _drop_stmt() -> str:
    kind = _rng.choice(["TABLE", "INDEX", "VIEW", "TRIGGER"])
    s = "DROP " + kind
    if _rng.random() < 0.5:
        s += " IF EXISTS"
    s += " " + _ident()
    return s

def _with_stmt(depth: int = 0) -> str:
    cte = _ident()
    cols = ""
    if _rng.random() < 0.45:
        cols = "(" + ", ".join(_ident() for _ in range(_rng.randrange(1, 4))) + ")"
    rec = "RECURSIVE " if _rng.random() < 0.35 else ""
    cte_def = cte + " " + cols + " AS (" + _select(depth + 1, as_subquery=True) + ")"
    if _rng.random() < 0.15:
        # multiple CTEs
        cte2 = _ident() + " AS (" + _select(depth + 1, as_subquery=True) + ")"
        cte_def = cte_def + ", " + cte2
    main = _select(depth + 1, as_subquery=False)
    return "WITH " + rec + cte_def + " " + main

def _txn_stmt() -> str:
    return _rng.choice([
        "BEGIN",
        "BEGIN TRANSACTION",
        "BEGIN IMMEDIATE",
        "BEGIN EXCLUSIVE",
        "COMMIT",
        "COMMIT TRANSACTION",
        "END",
        "ROLLBACK",
        "ROLLBACK TRANSACTION",
        "SAVEPOINT " + _ident(),
        "RELEASE " + _ident(),
        "ROLLBACK TO " + _ident(),
        "ROLLBACK TO SAVEPOINT " + _ident(),
    ])

def _pragma_stmt() -> str:
    # Not necessarily supported; good for error paths too
    k = _rng.choice(["cache_size", "foreign_keys", "journal_mode", "synchronous", "temp_store", "encoding", "recursive_triggers"])
    v = _rng.choice([_number(), _string(), "ON", "OFF", "FULL", "WAL", "DELETE", "MEMORY"])
    if _rng.random() < 0.4:
        return "PRAGMA " + k
    if _rng.random() < 0.7:
        return "PRAGMA " + k + " = " + v
    return "PRAGMA " + k + "(" + v + ")"

def _explain_stmt(depth: int = 0) -> str:
    prefix = _rng.choice(["EXPLAIN", "EXPLAIN QUERY PLAN"])
    return prefix + " " + _select(depth + 1, as_subquery=False)

def _gen_stmt(depth: int = 0) -> str:
    r = _rng.random()
    if r < 0.28:
        return _select(depth)
    if r < 0.40:
        return _with_stmt(depth)
    if r < 0.52:
        return _insert(depth)
    if r < 0.64:
        return _update(depth)
    if r < 0.74:
        return _delete(depth)
    if r < 0.86:
        return _create_table(depth)
    if r < 0.92:
        return _create_index(depth)
    if r < 0.965:
        return _alter_table(depth)
    if r < 0.99:
        return _drop_stmt()
    if _rng.random() < 0.6:
        return _pragma_stmt()
    return _explain_stmt(depth)

def _tokenize_for_mutation(sql: str):
    # Split into meaningful pieces; keep punctuation/operators
    parts = []
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch.isspace():
            j = i + 1
            while j < n and sql[j].isspace():
                j += 1
            parts.append(sql[i:j])
            i = j
            continue
        if ch == "-" and i + 1 < n and sql[i + 1] == "-":
            j = i + 2
            while j < n and sql[j] != "\\n":
                j += 1
            if j < n:
                j += 1
            parts.append(sql[i:j])
            i = j
            continue
        if ch == "/" and i + 1 < n and sql[i + 1] == "*":
            j = i + 2
            while j + 1 < n and not (sql[j] == "*" and sql[j + 1] == "/"):
                j += 1
            j = min(n, j + 2)
            parts.append(sql[i:j])
            i = j
            continue
        if ch in ("'", '"', "`"):
            q = ch
            j = i + 1
            while j < n:
                if sql[j] == q:
                    if q == "'" and j + 1 < n and sql[j + 1] == "'":
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            parts.append(sql[i:j])
            i = j
            continue
        if ch in "[]":
            if ch == "[":
                j = i + 1
                while j < n and sql[j] != "]":
                    j += 1
                j = min(n, j + 1)
                parts.append(sql[i:j])
                i = j
                continue
        # operators and punctuation
        if i + 1 < n:
            two = sql[i:i+2]
            if two in ("<=", ">=", "<>", "!=", "==", "||"):
                parts.append(two)
                i += 2
                continue
        if ch in "(),;.=<>+-*/%":
            parts.append(ch)
            i += 1
            continue
        # word/number
        j = i + 1
        while j < n and (sql[j].isalnum() or sql[j] in "_$"):
            j += 1
        parts.append(sql[i:j])
        i = j
    return parts

def _sprinkle_comments_and_ws(parts):
    out = []
    for p in parts:
        if p.isspace():
            # replace whitespace with variety + optional comment
            w = _ws()
            if _rng.random() < 0.22:
                if _rng.random() < 0.5:
                    w = w + "/*" + _rng.choice(KEYWORDS) + "*/" + _ws()
                else:
                    w = w + "--" + _rng.choice(KEYWORDS) + "\\n" + _ws()
            out.append(w)
        else:
            out.append(p)
            if _rng.random() < 0.05:
                out.append(_ws())
    s = "".join(out)
    if _rng.random() < 0.08:
        s = "\\ufeff" + s
    return s

def _mutate(sql: str) -> str:
    if not sql:
        return sql
    parts = _tokenize_for_mutation(sql)
    # small structural mutations
    if _rng.random() < 0.10 and len(parts) > 4:
        # delete a token
        del parts[_rng.randrange(0, len(parts))]
    if _rng.random() < 0.10 and len(parts) > 4:
        # duplicate a token
        i = _rng.randrange(0, len(parts))
        parts.insert(i, parts[i])
    if _rng.random() < 0.12:
        # insert random keyword
        i = _rng.randrange(0, len(parts) + 1)
        ins = _rng.choice(KEYWORDS)
        parts.insert(i, ins)
        parts.insert(i + 1, _ws())
    if _rng.random() < 0.10:
        # add random parens around a slice
        a = _rng.randrange(0, len(parts) + 1)
        b = _rng.randrange(a, len(parts) + 1)
        parts.insert(a, "(")
        parts.insert(b + 1, ")")
    s = _sprinkle_comments_and_ws(parts)
    if _rng.random() < 0.65:
        s = _rand_case(s)
    return s

def _handcrafted():
    # Curated to trigger many parser paths; some intentionally invalid/edge.
    return [
        "SELECT 1",
        "SELECT * FROM t",
        "SELECT t.* FROM t AS t",
        "SELECT DISTINCT a, b, c FROM t WHERE a = 1 AND (b <> 2 OR c IS NULL) ORDER BY a DESC, b ASC LIMIT 10 OFFSET 2",
        "SELECT COUNT(*) FROM t GROUP BY a HAVING COUNT(*) > 1",
        "SELECT a, CASE WHEN a > 0 THEN 'pos' ELSE 'neg' END AS s FROM t",
        "SELECT CAST(a AS INTEGER) FROM t",
        "SELECT COALESCE(a, 0), NULLIF(b, 0) FROM t",
        "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c WHERE x < 5) SELECT * FROM c",
        "INSERT INTO t (a,b) VALUES (1,'x'), (2,'y')",
        "INSERT INTO t VALUES (NULL, TRUE, FALSE, 1e3, 0x10)",
        "UPDATE t SET a = a + 1, b = 'z' WHERE id IN (SELECT id FROM t WHERE id BETWEEN 1 AND 10)",
        "DELETE FROM t WHERE a LIKE '%x%' ESCAPE '\\\\'",
        "CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, val REAL DEFAULT 1.0, CHECK (val >= 0))",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_t ON t (name ASC, val DESC) WHERE val > 0",
        "ALTER TABLE t ADD COLUMN extra TEXT DEFAULT 'x'",
        "ALTER TABLE t RENAME TO t2",
        "DROP TABLE IF EXISTS t2",
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT sp1",
        "RELEASE sp1",
        "PRAGMA foreign_keys = ON",
        "EXPLAIN SELECT * FROM t",
        # Tokenizer edges / errors
        "SELECT 'unterminated",
        "SELECT /* unclosed comment ",
        "SELECT 1 FROM",
        "INSERT INTO VALUES (1)",
        "UPDATE SET a = 1",
        "DELETE t WHERE 1=1",
        "CREATE TABLE (a INT)",
        "SELECT 1 + + + 2",
        "SELECT 1e+ 2",
        "SELECT X'ABCD'",
        "SELECT [weird name], `backtick`, \"double\" FROM [t]",
        "-- full line comment\\nSELECT 1",
        "/* block */ SELECT 2",
    ]

def _gen_invalid(n: int):
    out = []
    ops = ["=", "==", "!=", "<>", "<", ">", "<=", ">="]
    for _ in range(n):
        r = _rng.random()
        if r < 0.20:
            out.append(_rng.choice(KEYWORDS) + " " + _rng.choice(KEYWORDS) + " " + _rng.choice(KEYWORDS))
        elif r < 0.40:
            out.append("SELECT " + _ident() + " FROM " + _ident() + " WHERE " + _ident() + " " + _rng.choice(ops))
        elif r < 0.55:
            out.append("SELECT " + _expr(0) + " FROM (" + _select(0, as_subquery=True))  # missing close paren
        elif r < 0.70:
            out.append("CREATE TABLE " + _ident() + " (" + _ident() + " " + _rng.choice(_COMMON_TYPES) + ", )")
        elif r < 0.85:
            out.append("INSERT INTO " + _ident() + " VALUES (" + ", ".join(_expr(0) for _ in range(_rng.randrange(1, 5))) + ",")
        else:
            # nasty tokens
            junk = _rng.choice(["@", "$$", "!!", "???", "\\x00", "\\ud800"])
            out.append("SELECT " + junk + " FROM " + _ident())
    return out

def _keyword_soup(n: int):
    out = []
    for _ in range(n):
        k = [_rng.choice(KEYWORDS) for __ in range(_rng.randrange(3, 14))]
        # make it look like statements sometimes
        if _rng.random() < 0.4:
            k.insert(0, "SELECT")
            k.insert(1, _rng.choice(["*", "1", _ident(), _expr(0)]))
        if _rng.random() < 0.3:
            k.append(";")
        s = " ".join(str(x) for x in k)
        if _rng.random() < 0.65:
            s = _mutate(s)
        out.append(s)
    return out

def _build_batch(mode: int, n: int):
    # mode 0: valid-heavy
    # mode 1: mutate corpus
    # mode 2: invalid-heavy
    # mode 3: keyword soup
    out = []
    if mode == 0:
        for _ in range(n):
            s = _gen_stmt(0)
            if _rng.random() < 0.55:
                s = _mutate(s)
            s = _maybe_semicolon(s)
            out.append(s)
        return out
    if mode == 1:
        if not _corpus:
            return _build_batch(0, n)
        for _ in range(n):
            base = _corpus[_rng.randrange(0, len(_corpus))]
            s = _mutate(base)
            if _rng.random() < 0.35:
                s = _maybe_semicolon(s)
            out.append(s)
        return out
    if mode == 2:
        out.extend(_gen_invalid(n))
        out = [_maybe_semicolon(_mutate(s) if _rng.random() < 0.5 else s) for s in out]
        return out
    out.extend(_keyword_soup(n))
    return out

def fuzz(parse_sql):
    global _call, _corpus
    if _call == 0:
        stmts = []
        hc = _handcrafted()
        stmts.extend([_maybe_semicolon(x) for x in hc])
        stmts.extend(_build_batch(0, 2200))
        _corpus = stmts[:]
        parse_sql(stmts)
        _call += 1
        return True
    if _call == 1:
        stmts = []
        stmts.extend(_build_batch(1, 2400))
        stmts.extend(_build_batch(0, 600))
        parse_sql(stmts)
        _call += 1
        return True
    if _call == 2:
        stmts = []
        stmts.extend(_build_batch(2, 2200))
        stmts.extend(_build_batch(1, 800))
        parse_sql(stmts)
        _call += 1
        return True
    if _call == 3:
        stmts = []
        stmts.extend(_build_batch(3, 2800))
        parse_sql(stmts)
        _call += 1
        return True
    if _call == 4:
        stmts = []
        stmts.extend(_build_batch(0, 1200))
        stmts.extend(_build_batch(2, 600))
        parse_sql(stmts)
        _call += 1
        return False
    return False
"""
        return {"code": code}