import os
import re
import ast
from typing import Dict, Any, Set, List


class Solution:
    def __init__(self):
        self._cached = None

    def _extract_strings_from_ast(self, src: str) -> Set[str]:
        out: Set[str] = set()
        try:
            tree = ast.parse(src)
        except Exception:
            return out

        def add_obj(o):
            if o is None:
                return
            if isinstance(o, str):
                out.add(o)
            elif isinstance(o, (list, tuple, set)):
                for x in o:
                    add_obj(x)
            elif isinstance(o, dict):
                for k, v in o.items():
                    add_obj(k)
                    add_obj(v)
            elif isinstance(o, ast.Constant) and isinstance(o.value, str):
                out.add(o.value)

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                out.add(node.value)
            elif isinstance(node, ast.Assign):
                try:
                    val = ast.literal_eval(node.value)
                    add_obj(val)
                except Exception:
                    pass
            elif isinstance(node, ast.AnnAssign):
                try:
                    val = ast.literal_eval(node.value)
                    add_obj(val)
                except Exception:
                    pass

        return out

    def _read_text(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    def _extract_from_sources(self, resources_path: str):
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        tokenizer_path = os.path.join(resources_path, "sql_engine", "tokenizer.py")
        parser_path = os.path.join(resources_path, "sql_engine", "parser.py")

        grammar_src = self._read_text(grammar_path)
        tokenizer_src = self._read_text(tokenizer_path)
        parser_src = self._read_text(parser_path)

        all_src = "\n".join([grammar_src, tokenizer_src, parser_src])

        strings: Set[str] = set()
        strings |= self._extract_strings_from_ast(tokenizer_src)
        strings |= self._extract_strings_from_ast(parser_src)

        for m in re.finditer(r"'([^'\n\r]{1,80})'", all_src):
            strings.add(m.group(1))
        for m in re.finditer(r'"([^"\n\r]{1,80})"', all_src):
            strings.add(m.group(1))

        kw: Set[str] = set()
        ops: Set[str] = set()

        for s in strings:
            if not s or len(s) > 80:
                continue
            st = s.strip()
            if not st:
                continue
            if any(ch.isspace() for ch in st):
                continue

            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", st):
                if st.upper() == st and len(st) >= 2:
                    kw.add(st)
                elif st.lower() == st and len(st) >= 2:
                    kw.add(st.upper())
                elif st[0].isalpha() and len(st) >= 2:
                    if st.upper() == st:
                        kw.add(st)
            else:
                if any(c in st for c in "+-*/%<>=!~^|&.,;:()[]{}?@$#`") and len(st) <= 6:
                    ops.add(st)

        for m in re.finditer(r"\b[A-Z][A-Z0-9_]{1,30}\b", grammar_src):
            w = m.group(0)
            if w not in {"BNF", "SQL"}:
                kw.add(w)

        for m in re.finditer(r"::=|<=|>=|<>|!=|==|:=|::|->|=>|\|\||&&|<<|>>", all_src):
            ops.add(m.group(0))

        base_kw = {
            "SELECT", "FROM", "WHERE", "GROUP", "BY", "HAVING", "ORDER", "LIMIT", "OFFSET",
            "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE",
            "CREATE", "TABLE", "DROP", "ALTER", "INDEX", "VIEW",
            "JOIN", "LEFT", "RIGHT", "FULL", "INNER", "OUTER", "CROSS", "ON", "USING",
            "UNION", "ALL", "INTERSECT", "EXCEPT",
            "DISTINCT", "AS", "AND", "OR", "NOT", "NULL", "IS", "IN", "BETWEEN", "LIKE", "EXISTS",
            "CASE", "WHEN", "THEN", "ELSE", "END",
            "CAST", "COLLATE", "ASC", "DESC",
            "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "CHECK", "DEFAULT", "UNIQUE", "NOT", "NULL",
            "IF", "EXISTS", "IFNULL",
            "BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE",
            "WITH", "RECURSIVE",
        }
        kw |= base_kw

        base_ops = {
            "+", "-", "*", "/", "%", "=", "==", "!=", "<>", "<", "<=", ">", ">=",
            "(", ")", ",", ".", ";", "||", "|", "&", "^", "~", "<<", ">>",
        }
        ops |= base_ops

        keywords = sorted(kw)
        operators = sorted({o for o in ops if 0 < len(o) <= 6})

        return keywords, operators

    def solve(self, resources_path: str) -> dict:
        if self._cached is not None:
            return {"code": self._cached}

        keywords, operators = self._extract_from_sources(resources_path)

        code = f"""import random
import string

_DONE = False
_rng = random.Random(1337)

KEYWORDS = {keywords!r}
OPERATORS = {operators!r}

_STMT_KWS = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "WITH", "BEGIN", "COMMIT", "ROLLBACK"]
_FUNCS = ["COUNT", "SUM", "MIN", "MAX", "AVG", "COALESCE", "NULLIF", "LENGTH", "SUBSTR", "LOWER", "UPPER", "ABS", "ROUND", "RANDOM", "IFNULL"]
_TYPES = ["INT", "INTEGER", "SMALLINT", "BIGINT", "REAL", "DOUBLE", "FLOAT", "NUMERIC", "DECIMAL(10,2)", "TEXT", "VARCHAR(20)", "CHAR(1)", "BLOB", "BOOLEAN", "DATE", "DATETIME", "TIMESTAMP"]
_CONSTRAINTS = ["PRIMARY KEY", "NOT NULL", "NULL", "UNIQUE", "DEFAULT 0", "DEFAULT 1", "DEFAULT 'x'", "CHECK(a >= 0)", "CHECK(b <> '')"]
_JOIN_TYPES = ["JOIN", "INNER JOIN", "LEFT JOIN", "LEFT OUTER JOIN", "CROSS JOIN", "RIGHT JOIN", "FULL JOIN"]

def _pick(seq):
    return seq[_rng.randrange(len(seq))] if seq else ""

def _maybe(p=0.5):
    return _rng.random() < p

def _ws():
    r = _rng.random()
    if r < 0.7:
        return " "
    if r < 0.85:
        return "\\n"
    if r < 0.95:
        return "\\t"
    return "  "

def _ident():
    base = _pick(["t", "u", "v", "w", "x", "y", "z", "tbl", "users", "orders", "product", "items", "a", "b", "c", "id", "name", "value", "price", "col"])
    if _maybe(0.4):
        base += str(_rng.randrange(0, 50))
    if _maybe(0.15):
        base = base + "_" + _pick(["x", "y", "z", "tmp", "val", "idx"])
    r = _rng.random()
    if r < 0.10:
        return '"' + base.replace('"', '""') + '"'
    if r < 0.14:
        return "`" + base.replace("`", "``") + "`"
    if r < 0.18:
        return "[" + base.replace("]", "]]") + "]"
    return base

def _num():
    r = _rng.random()
    if r < 0.20:
        return str(_rng.randrange(-10, 100))
    if r < 0.35:
        return str(_rng.randrange(0, 100000))
    if r < 0.50:
        return str(_rng.randrange(-10, 100)) + "." + str(_rng.randrange(0, 100000))
    if r < 0.62:
        return str(_rng.randrange(0, 100)) + "e" + str(_rng.randrange(-10, 10))
    if r < 0.70:
        return "0x" + format(_rng.randrange(0, 2**16), "x")
    if r < 0.78:
        return "0b" + format(_rng.randrange(0, 2**16), "b")
    if r < 0.85:
        return ".{}".format(_rng.randrange(0, 1000))
    return "1e309"

def _str():
    choices = [
        "a", "A", "test", "x", "y", "z", "hello", "world", "NULL", "select",
        "a'b", "a\\nb", "a\\tb", "/*x*/", "--x", "%", "_", "\\\\", "''", "🙂"
    ]
    s = _pick(choices)
    s = s.replace("'", "''")
    return "'" + s + "'"

def _param():
    r = _rng.random()
    if r < 0.4:
        return "?"
    if r < 0.7:
        return "$" + str(_rng.randrange(1, 10))
    if r < 0.85:
        return ":" + _ident().strip('"`[]')
    return "@" + _ident().strip('"`[]')

def _op():
    ops = ["+", "-", "*", "/", "%", "=", "==", "!=", "<>", "<", "<=", ">", ">=", "AND", "OR", "||", "|", "&", "^", "<<", ">>"]
    return _pick(ops)

def _unop():
    return _pick(["NOT", "+", "-", "~"])

def _literal():
    r = _rng.random()
    if r < 0.38:
        return _num()
    if r < 0.72:
        return _str()
    if r < 0.82:
        return "NULL"
    if r < 0.90:
        return _param()
    return _pick(["TRUE", "FALSE", "CURRENT_DATE", "CURRENT_TIME", "CURRENT_TIMESTAMP"])

def _simple_atom():
    r = _rng.random()
    if r < 0.45:
        return _ident()
    if r < 0.62:
        return _literal()
    if r < 0.70:
        return _ident() + "." + _ident()
    if r < 0.78:
        return "*"
    if r < 0.85:
        return _ident() + ".*"
    return "(" + _literal() + ")"

def _expr(depth=0):
    if depth <= 0:
        return _simple_atom()

    r = _rng.random()
    if r < 0.20:
        return "(" + _expr(depth - 1) + _ws() + _op() + _ws() + _expr(depth - 1) + ")"
    if r < 0.32:
        return "(" + _unop() + _ws() + _expr(depth - 1) + ")"
    if r < 0.44:
        fn = _pick(_FUNCS)
        n = 1 + _rng.randrange(0, 3)
        args = []
        for _ in range(n):
            args.append(_expr(depth - 1))
        if _maybe(0.15) and fn in ("COUNT", "SUM", "MIN", "MAX", "AVG"):
            args[0] = "DISTINCT" + _ws() + args[0]
        return fn + "(" + ", ".join(args) + ")"
    if r < 0.55:
        return "CASE WHEN " + _expr(depth - 1) + " THEN " + _expr(depth - 1) + " ELSE " + _expr(depth - 1) + " END"
    if r < 0.64:
        return "CAST(" + _expr(depth - 1) + " AS " + _pick(_TYPES) + ")"
    if r < 0.72:
        return "(" + _expr(depth - 1) + " BETWEEN " + _expr(depth - 1) + " AND " + _expr(depth - 1) + ")"
    if r < 0.80:
        lst = ", ".join(_expr(0) for _ in range(1 + _rng.randrange(0, 4)))
        return "(" + _expr(depth - 1) + " IN (" + lst + "))"
    if r < 0.87:
        esc = " ESCAPE " + _str() if _maybe(0.25) else ""
        return "(" + _expr(depth - 1) + " LIKE " + _str() + esc + ")"
    if r < 0.93:
        return "(" + _expr(depth - 1) + " IS " + ("NOT " if _maybe(0.4) else "") + "NULL)"
    if r < 0.97:
        return "EXISTS (" + _select(depth - 1, allow_with=False, allow_setops=False) + ")"
    return "(" + _expr(depth - 1) + ")"

def _table_ref(depth=0):
    if _maybe(0.18) and depth > 0:
        return "(" + _select(depth - 1, allow_with=False, allow_setops=False) + ")" + _ws() + "AS" + _ws() + _ident()
    return _ident()

def _order_by(depth=0):
    n = 1 + _rng.randrange(0, 3)
    parts = []
    for _ in range(n):
        parts.append(_expr(max(0, depth - 1)) + (_ws() + _pick(["ASC", "DESC"]) if _maybe(0.6) else ""))
    return "ORDER BY " + ", ".join(parts)

def _select(depth=2, allow_with=True, allow_setops=True):
    cols_n = 1 + _rng.randrange(0, 5)
    cols = []
    for _ in range(cols_n):
        e = _expr(max(0, depth - 1))
        if _maybe(0.35) and e not in ("*",):
            if _maybe(0.5):
                e = e + _ws() + "AS" + _ws() + _ident()
            else:
                e = e + _ws() + _ident()
        cols.append(e)

    distinct = "DISTINCT " if _maybe(0.25) else ""
    stmt = "SELECT " + distinct + ", ".join(cols)

    if _maybe(0.85):
        stmt += _ws() + "FROM" + _ws()
        left = _table_ref(depth)
        if _maybe(0.40):
            jt = _pick(_JOIN_TYPES)
            right = _table_ref(depth)
            if _maybe(0.65):
                cond = _expr(max(0, depth - 1))
                stmt += left + _ws() + jt + _ws() + right + _ws() + "ON" + _ws() + cond
            else:
                stmt += left + _ws() + jt + _ws() + right + _ws() + "USING" + _ws() + "(" + _ident() + ")"
        else:
            stmt += left

    if _maybe(0.55):
        stmt += _ws() + "WHERE" + _ws() + _expr(max(0, depth - 1))

    if _maybe(0.25):
        stmt += _ws() + "GROUP BY" + _ws()
        gb = ", ".join(_expr(0) for _ in range(1 + _rng.randrange(0, 3)))
        stmt += gb
        if _maybe(0.45):
            stmt += _ws() + "HAVING" + _ws() + _expr(max(0, depth - 1))

    if _maybe(0.40):
        stmt += _ws() + _order_by(depth)

    if _maybe(0.35):
        lim = _num() if _maybe(0.75) else _param()
        stmt += _ws() + "LIMIT" + _ws() + lim
        if _maybe(0.30):
            off = _num() if _maybe(0.75) else _param()
            stmt += _ws() + "OFFSET" + _ws() + off

    if allow_setops and _maybe(0.18):
        op = _pick(["UNION", "UNION ALL", "INTERSECT", "EXCEPT"])
        stmt = stmt + _ws() + op + _ws() + _select(max(0, depth - 1), allow_with=False, allow_setops=False)

    if allow_with and _maybe(0.12):
        cte_name = _ident().strip('"`[]')
        stmt = "WITH " + cte_name + " AS (" + _select(max(0, depth - 1), allow_with=False, allow_setops=False) + ") " + stmt

    return stmt

def _insert(depth=2):
    tbl = _ident()
    cols = ""
    if _maybe(0.55):
        cols_n = 1 + _rng.randrange(0, 4)
        cols = "(" + ", ".join(_ident() for _ in range(cols_n)) + ")"
    if _maybe(0.70):
        rows = 1 + _rng.randrange(0, 4)
        vals = []
        for _ in range(rows):
            n = 1 + _rng.randrange(0, 4)
            vals.append("(" + ", ".join(_expr(max(0, depth - 1)) for _ in range(n)) + ")")
        return "INSERT INTO " + tbl + (_ws() + cols if cols else "") + _ws() + "VALUES" + _ws() + ", ".join(vals)
    return "INSERT INTO " + tbl + (_ws() + cols if cols else "") + _ws() + _select(max(0, depth - 1), allow_with=True, allow_setops=True)

def _update(depth=2):
    tbl = _ident()
    sets_n = 1 + _rng.randrange(0, 4)
    assigns = []
    for _ in range(sets_n):
        assigns.append(_ident() + "=" + _expr(max(0, depth - 1)))
    stmt = "UPDATE " + tbl + _ws() + "SET " + ", ".join(assigns)
    if _maybe(0.70):
        stmt += _ws() + "WHERE" + _ws() + _expr(max(0, depth - 1))
    return stmt

def _delete(depth=2):
    stmt = "DELETE FROM " + _ident()
    if _maybe(0.75):
        stmt += _ws() + "WHERE" + _ws() + _expr(max(0, depth - 1))
    if _maybe(0.20):
        stmt += _ws() + "AND" + _ws() + _ident() + " IN (" + _select(max(0, depth - 1), allow_with=False, allow_setops=False) + ")"
    return stmt

def _create_table(depth=2):
    tbl = _ident()
    n = 1 + _rng.randrange(0, 6)
    cols = []
    for i in range(n):
        name = _ident()
        typ = _pick(_TYPES)
        extras = []
        if _maybe(0.20):
            extras.append(_pick(_CONSTRAINTS))
        if _maybe(0.12):
            extras.append("REFERENCES " + _ident() + "(" + _ident() + ")")
        cols.append(name + " " + typ + (" " + " ".join(extras) if extras else ""))
    if _maybe(0.18):
        cols.append("PRIMARY KEY(" + _ident() + ("," + _ident() if _maybe(0.3) else "") + ")")
    if _maybe(0.10):
        cols.append("FOREIGN KEY(" + _ident() + ") REFERENCES " + _ident() + "(" + _ident() + ")")
    stmt = "CREATE TABLE " + tbl + " (" + ", ".join(cols) + ")"
    return stmt

def _create_index():
    idx = _ident()
    tbl = _ident()
    cols_n = 1 + _rng.randrange(0, 4)
    cols = ", ".join(_ident() + (_ws() + _pick(["ASC", "DESC"]) if _maybe(0.35) else "") for _ in range(cols_n))
    uniq = "UNIQUE " if _maybe(0.2) else ""
    return "CREATE " + uniq + "INDEX " + idx + " ON " + tbl + " (" + cols + ")"

def _create_view(depth=2):
    v = _ident()
    return "CREATE VIEW " + v + " AS " + _select(max(0, depth - 1), allow_with=True, allow_setops=True)

def _alter_table():
    tbl = _ident()
    r = _rng.random()
    if r < 0.33:
        return "ALTER TABLE " + tbl + " ADD COLUMN " + _ident() + " " + _pick(_TYPES)
    if r < 0.55:
        return "ALTER TABLE " + tbl + " RENAME TO " + _ident()
    if r < 0.75:
        return "ALTER TABLE " + tbl + " RENAME COLUMN " + _ident() + " TO " + _ident()
    return "ALTER TABLE " + tbl + " DROP COLUMN " + _ident()

def _drop():
    what = _pick(["TABLE", "INDEX", "VIEW"])
    name = _ident()
    iff = "IF EXISTS " if _maybe(0.45) else ""
    return "DROP " + what + " " + iff + name

def _txn():
    return _pick([
        "BEGIN",
        "BEGIN TRANSACTION",
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT sp1",
        "RELEASE sp1",
        "ROLLBACK TO sp1",
    ])

def _comment_wrap(sql):
    r = _rng.random()
    if r < 0.33:
        return "/*" + _pick(["x", "comment", "/*nested?*/", ""]) + "*/" + _ws() + sql
    if r < 0.66:
        return "-- " + _pick(["c", "comment", ""]) + "\\n" + sql
    return sql

def _maybe_trailer(sql):
    if _maybe(0.35):
        sql += ";"
    if _maybe(0.08):
        sql += ";;"
    return sql

def _token_soup(max_tokens=30):
    toks = []
    pool = []
    pool.extend(KEYWORDS[:])
    pool.extend(OPERATORS[:])
    pool.extend(["(", ")", ",", ".", ";", "::", ":=", "->", "=>", "||", "&&"])
    for _ in range(1 + _rng.randrange(0, max_tokens)):
        r = _rng.random()
        if r < 0.22:
            toks.append(_ident())
        elif r < 0.44:
            toks.append(_literal())
        elif r < 0.70:
            toks.append(_pick(pool))
        elif r < 0.80:
            toks.append("/*" + _pick(["x", "y", "z", ""]) + "*/")
        else:
            toks.append("--" + _pick(["x", ""]) + "\\n")
    return " ".join(t for t in toks if t)

def _weird_cases():
    w = []
    w.append("SELECT 1 /* unterminated")
    w.append("SELECT 'unterminated")
    w.append("SELECT \"unterminated")
    w.append("SELECT 1e309, -1e309, 0xFF, 0b1010 FROM t")
    w.append("SELECT 1 FROM t WHERE a = 'a''b' AND b LIKE '%\\_%' ESCAPE '\\\\'")
    w.append("SELECT 1 FROM t WHERE a IN (NULL, 1, 2, 3, ?)")
    w.append("SELECT CASE WHEN 1 THEN 2 ELSE 3 END")
    w.append("SELECT (SELECT 1) AS subq")
    w.append("INSERT INTO t VALUES (1,2")
    w.append("CREATE TABLE t (a INT, b TEXT, )")
    w.append("UPDATE t SET a = (SELECT 1) WHERE id = 1")
    w.append("DELETE FROM t WHERE id IN (SELECT id FROM t)")
    w.append("WITH c AS (SELECT 1) SELECT * FROM c")
    w.append("SELECT 1 UNION SELECT 2 UNION ALL SELECT 3")
    w.append("SELECT /*c*/ 1 --x\\n FROM t")
    w.append("SELECT 1 FROM (SELECT 2) AS x")
    w.append("SELECT 1 FROM t ORDER BY 1 DESC LIMIT ? OFFSET ?")
    w.append("ALTER TABLE t ADD COLUMN x INT")
    w.append("DROP TABLE IF EXISTS t")
    w.append("CREATE INDEX idx ON t(a,b)")
    w.append("CREATE VIEW v AS SELECT * FROM t")
    w.append("BEGIN; COMMIT")
    return w

def _seeds():
    s = []
    s.extend(_weird_cases())

    s.append("SELECT 1")
    s.append("SELECT * FROM t")
    s.append("SELECT a, b FROM t WHERE a=1")
    s.append("SELECT DISTINCT a FROM t ORDER BY a DESC LIMIT 10 OFFSET 5")
    s.append("SELECT t.a, u.b FROM t JOIN u ON t.id = u.id")
    s.append("SELECT a, COUNT(*) FROM t GROUP BY a HAVING COUNT(*) > 1")
    s.append("SELECT a BETWEEN 1 AND 2 FROM t")
    s.append("SELECT a IN (1,2,3) FROM t")
    s.append("SELECT a LIKE '%x%' FROM t")
    s.append("SELECT a IS NULL FROM t")
    s.append("SELECT EXISTS (SELECT 1)")
    s.append("SELECT CAST(a AS INT) FROM t")
    s.append("SELECT CASE WHEN a>1 THEN 'x' ELSE 'y' END FROM t")
    s.append("INSERT INTO t VALUES (1,'a')")
    s.append("INSERT INTO t(a,b) VALUES (1,2),(3,4)")
    s.append("UPDATE t SET a=1, b=b+1 WHERE id=1")
    s.append("DELETE FROM t WHERE id=1")
    s.append("CREATE TABLE t (id INT PRIMARY KEY, name TEXT NOT NULL, price REAL DEFAULT 0, CHECK(price>=0))")
    s.append("CREATE TABLE t2 (id INTEGER, t_id INT REFERENCES t(id))")
    s.append("DROP INDEX IF EXISTS idx")
    s.append("WITH c AS (SELECT 1) SELECT * FROM c")
    s.append("-- comment\\nSELECT 1")
    s.append("/*comment*/ SELECT 2")
    s.append("SELECT 'a''b', \"select\" FROM t")

    for op in ["=", "!=", "<>", "<", "<=", ">", ">="]:
        s.append("SELECT 1 FROM t WHERE a " + op + " 1")
    for kw in ["AND", "OR", "NOT", "NULL", "IN", "LIKE", "BETWEEN", "IS", "EXISTS", "CASE", "CAST"]:
        s.append("SELECT 1 FROM t WHERE 1=1 " + kw + " 1=1")
    for t in _TYPES[:8]:
        s.append("CREATE TABLE " + _ident() + " (" + _ident() + " " + t + ")")

    extra = []
    for _ in range(120):
        extra.append(_comment_wrap(_maybe_trailer(_select(2))))
        extra.append(_comment_wrap(_maybe_trailer(_insert(2))))
        extra.append(_comment_wrap(_maybe_trailer(_update(2))))
        extra.append(_comment_wrap(_maybe_trailer(_delete(2))))
    s.extend(extra)

    return s

_SEED_LIST = _seeds()

def _mutate(sql):
    if not sql:
        return sql
    r = _rng.random()
    if r < 0.20:
        i = _rng.randrange(0, len(sql) + 1)
        ins = _pick([" ", "\\n", "\\t", "/*x*/", "--x\\n", "(", ")", ",", ";", "''", "\"\"", "NULL", "?", "0xFF"])
        return sql[:i] + ins + sql[i:]
    if r < 0.38:
        i = _rng.randrange(0, len(sql))
        j = min(len(sql), i + 1 + _rng.randrange(0, 6))
        return sql[:i] + sql[j:]
    if r < 0.56:
        parts = sql.split()
        if not parts:
            return sql
        k = _rng.randrange(0, len(parts))
        parts[k] = _pick([_ident(), _literal(), _pick(KEYWORDS) if KEYWORDS else "SELECT", _pick(OPERATORS) if OPERATORS else "+"])
        return " ".join(parts)
    if r < 0.72:
        parts = sql.split()
        if len(parts) < 2:
            return sql + " " + _token_soup(10)
        i = _rng.randrange(0, len(parts))
        j = _rng.randrange(0, len(parts))
        if i > j:
            i, j = j, i
        return " ".join(parts[:i] + parts[i:j] + parts[i:j] + parts[j:])
    if r < 0.86:
        return sql.swapcase()
    return sql + _ws() + _token_soup(10)

def _stmt():
    r = _rng.random()
    if r < 0.50:
        return _select(3, allow_with=True, allow_setops=True)
    if r < 0.68:
        return _insert(3)
    if r < 0.80:
        return _update(3)
    if r < 0.88:
        return _delete(3)
    if r < 0.93:
        return _create_table(2)
    if r < 0.96:
        return _create_index()
    if r < 0.98:
        return _create_view(2)
    if r < 0.99:
        return _alter_table()
    return _drop()

def fuzz(parse_sql):
    global _DONE
    if _DONE:
        return False

    stmts = []
    stmts.extend(_SEED_LIST)

    for _ in range(1800):
        s = _stmt()
        if _maybe(0.25):
            s = _comment_wrap(s)
        s = _maybe_trailer(s)
        stmts.append(s)

    base_for_mut = _SEED_LIST[:]
    for _ in range(700):
        seed = _pick(base_for_mut) if base_for_mut else _stmt()
        m = _mutate(seed)
        if _maybe(0.2):
            m = "SELECT " + _token_soup(20) + " FROM " + _ident()
        stmts.append(_maybe_trailer(m))

    for _ in range(120):
        stmts.append("SELECT " + _token_soup(25) + " FROM " + _ident() + " WHERE " + _token_soup(15))
        stmts.append("CREATE TABLE " + _ident() + " (" + _token_soup(25) + ")")
        stmts.append("INSERT INTO " + _ident() + " VALUES (" + _token_soup(15) + ")")
        stmts.append("UPDATE " + _ident() + " SET " + _ident() + "=" + _token_soup(15) + " WHERE " + _token_soup(15))

    parse_sql(stmts)
    _DONE = True
    return False
"""
        self._cached = code
        return {"code": code}