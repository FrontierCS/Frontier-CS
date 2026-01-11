import os
import re
import json
import random
from typing import List, Dict, Any

class Solution:
    def solve(self, resources_path: str) -> dict:
        # Default sets
        default_keywords = {
            "SELECT","INSERT","UPDATE","DELETE","FROM","WHERE","GROUP","BY","HAVING","ORDER","ASC","DESC","LIMIT","OFFSET",
            "DISTINCT","ALL","AS","AND","OR","NOT","IN","IS","NULL","LIKE","GLOB","BETWEEN","EXISTS",
            "JOIN","LEFT","RIGHT","FULL","OUTER","INNER","CROSS","NATURAL","ON","USING",
            "CREATE","TABLE","TEMP","TEMPORARY","IF","NOT","EXISTS","PRIMARY","KEY","UNIQUE","CHECK","DEFAULT","REFERENCES",
            "FOREIGN","CONSTRAINT","AUTOINCREMENT","WITHOUT","ROWID","VIRTUAL",
            "ALTER","ADD","COLUMN","RENAME","TO","DROP",
            "INDEX","UNIQUE","VIEW","TRIGGER","BEGIN","TRANSACTION","COMMIT","ROLLBACK","SAVEPOINT","RELEASE",
            "PRAGMA","ATTACH","DATABASE","DETACH","EXPLAIN","ANALYZE","VACUUM",
            "VALUES","INTO","SET","CASE","WHEN","THEN","ELSE","END","CAST","COLLATE","ESCAPE",
            "UNION","INTERSECT","EXCEPT","ALL",
            "TRUE","FALSE"
        }
        default_functions = {
            "COUNT","SUM","AVG","MIN","MAX","ABS","ROUND","LENGTH","SUBSTR","COALESCE","NULLIF",
            "LOWER","UPPER","REPLACE","TRIM","LTRIM","RTRIM","INSTR","RANDOM","RANDOMBLOB",
            "HEX","DATE","TIME","DATETIME","JULIANDAY","STRFTIME","IFNULL","IIF","PRINTF"
        }
        default_types = {
            "INT","INTEGER","TINYINT","SMALLINT","MEDIUMINT","BIGINT","UNSIGNED","REAL","DOUBLE","DOUBLE PRECISION","FLOAT",
            "NUMERIC","DECIMAL","BOOLEAN","DATE","DATETIME","TIME","TIMESTAMP","CHAR","NCHAR","VARCHAR","NVARCHAR","CLOB","TEXT",
            "BLOB","JSON"
        }
        default_operators = [
            "||","*","/","%","+","-","<<",">>","&","|","<",">","<=",">=","=","==","!=","<>","~"
        ]
        # Attempt to extract tokens from grammar file for additional hints
        grammar_keywords = set()
        grammar_funcs = set()
        grammar_types = set()
        grammar_ops = set()
        try:
            gpath = os.path.join(resources_path, "sql_grammar.txt")
            if os.path.exists(gpath):
                text = open(gpath, "r", encoding="utf-8", errors="ignore").read()
                # Extract uppercase tokens (likely keywords)
                kw = set(re.findall(r"\b[A-Z][A-Z0-9_]*\b", text))
                # Filter out some generic placeholders often found in grammars
                blacklist = {"EOF","ID","IDENT","IDENTIFIER","STRING","NUMBER","DIGIT","HEX","WS","NEWLINE","COMMENT","TOKEN","TOKENS"}
                grammar_keywords = {k for k in kw if k not in blacklist}
                # Try to find functions by context like NAME '('
                fn = set(re.findall(r"\b([A-Z][A-Z0-9_]*)\s*\(", text))
                grammar_funcs = {f for f in fn if f in grammar_keywords or f in default_functions}
                # Extract types by presence in common type contexts
                type_candidates = set(re.findall(r"\b([A-Z][A-Z0-9_]*(?:\s+[A-Z][A-Z0-9_]*)?)\b", text))
                common_type_markers = {"INT","INTEGER","REAL","FLOAT","DOUBLE","NUMERIC","DECIMAL","DATE","TIME","TIMESTAMP","CHAR","VARCHAR","CLOB","TEXT","BLOB","BOOLEAN","JSON"}
                for t in type_candidates:
                    t0 = t.strip()
                    parts = t0.split()
                    if any(p in common_type_markers for p in parts):
                        grammar_types.add(t0)
                # Ops from common operator tokens presence
                if "||" in text: grammar_ops.add("||")
                if "!=" in text: grammar_ops.add("!=")
                if "<>" in text: grammar_ops.add("<>")
                if "==" in text: grammar_ops.add("==")
                if "<=" in text: grammar_ops.add("<=")
                if ">=" in text: grammar_ops.add(">=")
                for ch in ["+","-","*","/","%","&","|","~","<",">","="]:
                    if ch in text: grammar_ops.add(ch)
        except Exception:
            pass

        KEYWORDS = sorted(set(default_keywords) | grammar_keywords)
        FUNCTIONS = sorted(set(default_functions) | grammar_funcs)
        TYPES = sorted(set(default_types) | {t for t in grammar_types if len(t) <= 20})
        OPERATORS = list(dict.fromkeys(default_operators + list(grammar_ops)))  # preserve order, unique

        # Build the fuzzer code
        code_parts: List[str] = []
        code_parts.append("import random, re, string, math")
        code_parts.append(f"KEYWORDS = {repr(KEYWORDS)}")
        code_parts.append(f"FUNCTIONS = {repr(FUNCTIONS)}")
        code_parts.append(f"TYPES = {repr(TYPES)}")
        code_parts.append(f"OPERATORS = {repr(OPERATORS)}")

        code_parts.append("""
_rng = random.Random(1337)

def _rand_name(prefix='n', min_len=1, max_len=8):
    length = _rng.randint(min_len, max_len)
    s = prefix + ''.join(_rng.choice(string.ascii_lowercase + string.digits + '_') for _ in range(length))
    if s[0].isdigit():
        s = '_' + s
    return s

def _maybe_quote_ident(name):
    # Use different quoting styles to exercise tokenizer
    style = _rng.randint(0, 6)
    if style == 0:
        return name
    elif style == 1:
        return '"' + name.replace('"', '""') + '"'
    elif style == 2:
        return '`' + name.replace('`', '``') + '`'
    elif style == 3:
        return '[' + name.replace(']', ']]') + ']'
    elif style == 4:
        # Quoted reserved word to exercise quoting path
        kw = _rng.choice(KEYWORDS) if KEYWORDS else "SELECT"
        return '"' + kw + '"'
    elif style == 5:
        # Mix case
        return ''.join(ch.upper() if _rng.random()<0.5 else ch.lower() for ch in name)
    else:
        return name

def _rand_identifier():
    base = _rand_name(prefix=_rng.choice(['t','c','x','col','tbl','v','f','g']), min_len=1, max_len=10)
    return _maybe_quote_ident(base)

def _rand_schema_qual(name=None):
    if name is None:
        name = _rand_identifier()
    if _rng.random() < 0.2:
        schema = _maybe_quote_ident(_rand_name(prefix='s'))
        return schema + '.' + name
    return name

def _rand_string():
    # produce single-quoted string with possible escapes and doubled quotes
    choices = ["", "a", "abc", "hello world", "O'Reilly", "line1\\nline2", "tab\\tsep", "unicode \\u263A", "null\\x00byte"]
    if _rng.random() < 0.4:
        # random length
        s = ''.join(_rng.choice(string.ascii_letters + string.digits + " _-/:,.!@#$%^&*()[]{}|<>?") for _ in range(_rng.randint(0, 30)))
    else:
        s = _rng.choice(choices)
    s = s.replace("'", "''")
    if _rng.random() < 0.1:
        # Use double quotes string (some dialects allow)
        s2 = ''.join(ch for ch in s)
        s2 = s2.replace('"', '""')
        return '"' + s2 + '"'
    return "'" + s + "'"

def _rand_number():
    r = _rng.random()
    if r < 0.25:
        return str(_rng.randint(-2**31, 2**31-1))
    elif r < 0.5:
        # float / scientific
        base = _rng.uniform(-1e6, 1e6)
        if _rng.random() < 0.5:
            return f"{base:.6f}"
        else:
            exp = _rng.randint(-10, 10)
            mant = _rng.uniform(-1000, 1000)
            sign = '-' if mant < 0 and _rng.random() < 0.5 else ''
            return f"{sign}{abs(mant):.3f}e{exp:+d}"
    elif r < 0.75:
        # hex
        return "0x" + ''.join(_rng.choice('0123456789ABCDEF') for _ in range(_rng.randint(1, 8)))
    else:
        # weird formatted number
        parts = []
        parts.append(str(_rng.randint(0, 999)))
        if _rng.random() < 0.7:
            parts.append(str(_rng.randint(0, 999)).zfill(3))
        if _rng.random() < 0.5:
            parts.append(str(_rng.randint(0, 999)).zfill(3))
        num = '_'.join(parts)
        if _rng.random() < 0.5:
            num += '.' + str(_rng.randint(0, 999999))
        return num

def _rand_literal():
    r = _rng.random()
    if r < 0.28:
        return _rand_number()
    elif r < 0.56:
        return _rand_string()
    elif r < 0.68:
        return "NULL"
    elif r < 0.82:
        return "TRUE"
    else:
        return "FALSE"

def _rand_op():
    return _rng.choice(OPERATORS) if OPERATORS else _rng.choice(["+","-","*","/"])

def _rand_collation():
    # common collations to hit tokenizer branches
    colls = ["BINARY","RTRIM","NOCASE","LOCALIZED","UNICODE","NONE"]
    return _rng.choice(colls)

def _maybe(self, prob=0.5):
    return _rng.random() < prob

def _random_case(s):
    return ''.join(ch.upper() if _rng.random() < 0.5 else ch.lower() for ch in s)

def _with_comments(s):
    # Insert simple comments at deterministic positions to avoid breaking strings: prefix/suffix and after SELECT/WHERE/AND/OR
    prefix = "/* leading comment */ " if _rng.random() < 0.5 else "-- lead cmt\\n"
    suffix = " -- trailing comment" if _rng.random() < 0.5 else " /* trailing */"
    s2 = s
    s2 = re.sub(r'\\bSELECT\\b', 'SELECT /*c*/', s2, count=1, flags=re.IGNORECASE)
    s2 = re.sub(r'\\bWHERE\\b', 'WHERE /*c*/', s2, count=1, flags=re.IGNORECASE)
    s2 = re.sub(r'\\bAND\\b', '/*c*/ AND', s2, count=1, flags=re.IGNORECASE)
    s2 = re.sub(r'\\bOR\\b', '/*c*/ OR', s2, count=1, flags=re.IGNORECASE)
    return prefix + s2 + suffix

def _parenthesize(expr):
    # Randomly add multiple layers
    layers = _rng.randint(0, 2)
    for _ in range(layers):
        expr = "(" + expr + ")"
    return expr

def _rand_expr(depth=0):
    # Expression generator with limited depth
    if depth > 3:
        base_choices = []
    else:
        base_choices = ["binop","func","case","in","between","like","isnull","exists","subquery"]
    terminals = ["literal","ident","paren"]
    choices = terminals + base_choices
    kind = _rng.choice(choices)
    if kind == "literal":
        return _rand_literal()
    if kind == "ident":
        if _rng.random() < 0.3:
            return _rand_identifier() + "." + _rand_identifier()
        return _rand_identifier()
    if kind == "paren":
        return "(" + _rand_expr(depth+1) + ")"
    if kind == "binop":
        left = _rand_expr(depth+1)
        right = _rand_expr(depth+1)
        op = _rand_op()
        # add unary negation or NOT
        if _rng.random() < 0.2:
            left = "NOT " + _parenthesize(left)
        if _rng.random() < 0.2:
            right = "-" + _parenthesize(right)
        return _parenthesize(left) + " " + op + " " + _parenthesize(right)
    if kind == "func":
        fn = _rng.choice(FUNCTIONS) if FUNCTIONS else "ABS"
        if fn.upper() == "COUNT" and _rng.random() < 0.5:
            args = "*"
        else:
            argc = _rng.randint(0, 3)
            args_list = []
            for i in range(argc):
                if _rng.random() < 0.2:
                    args_list.append("DISTINCT " + _rand_expr(depth+1))
                else:
                    args_list.append(_rand_expr(depth+1))
            args = ", ".join(args_list)
        expr = f"{fn}({args})"
        if _rng.random() < 0.2:
            expr += " FILTER (WHERE " + _rand_expr(depth+1) + ")"
        return expr
    if kind == "case":
        n = _rng.randint(1, 3)
        parts = ["CASE"]
        if _rng.random() < 0.3:
            parts.append(_rand_expr(depth+1))
        for _ in range(n):
            parts.append("WHEN " + _rand_expr(depth+1) + " THEN " + _rand_expr(depth+1))
        if _rng.random() < 0.5:
            parts.append("ELSE " + _rand_expr(depth+1))
        parts.append("END")
        return " ".join(parts)
    if kind == "in":
        if _rng.random() < 0.5:
            vals = ", ".join(_rand_expr(depth+1) for _ in range(_rng.randint(1, 4)))
            return _rand_expr(depth+1) + (" NOT" if _rng.random() < 0.3 else "") + " IN (" + vals + ")"
        else:
            return _rand_expr(depth+1) + (" NOT" if _rng.random() < 0.3 else "") + " IN (" + _select_core(depth+1) + ")"
    if kind == "between":
        return _rand_expr(depth+1) + (" NOT" if _rng.random() < 0.3 else "") + " BETWEEN " + _rand_expr(depth+1) + " AND " + _rand_expr(depth+1)
    if kind == "like":
        pat = _rand_string()
        stmt = _rand_expr(depth+1) + (" NOT" if _rng.random() < 0.3 else "") + " LIKE " + pat
        if _rng.random() < 0.3:
            stmt += " ESCAPE " + _rand_string()
        return stmt
    if kind == "isnull":
        return _rand_expr(depth+1) + (" IS NOT" if _rng.random() < 0.3 else " IS") + " NULL"
    if kind == "exists":
        return "EXISTS (" + _select_core(depth+1) + ")"
    if kind == "subquery":
        return "(" + _select_core(depth+1) + ")"
    # Fallback
    return _rand_literal()

def _order_by_clause(depth=0):
    if _rng.random() < 0.4:
        return ""
    n = _rng.randint(1, 3)
    items = []
    for _ in range(n):
        expr = _rand_expr(depth+1)
        suffix = ""
        if _rng.random() < 0.6:
            suffix += " " + _rng.choice(["ASC","DESC"])
        if _rng.random() < 0.3:
            suffix += " NULLS " + _rng.choice(["FIRST","LAST"])
        items.append(expr + suffix)
    return " ORDER BY " + ", ".join(items)

def _group_by_clause(depth=0):
    if _rng.random() < 0.5:
        return ""
    n = _rng.randint(1, 3)
    items = ", ".join(_rand_expr(depth+1) for _ in range(n))
    having = ""
    if _rng.random() < 0.4:
        having = " HAVING " + _rand_expr(depth+1)
    return " GROUP BY " + items + having

def _limit_clause():
    if _rng.random() < 0.6:
        return ""
    if _rng.random() < 0.5:
        return " LIMIT " + _rand_number()
    else:
        if _rng.random() < 0.5:
            return " LIMIT " + _rand_number() + " OFFSET " + _rand_number()
        else:
            # MySQL style LIMIT offset, count
            return " LIMIT " + _rand_number() + ", " + _rand_number()

def _select_list(depth=0):
    if _rng.random() < 0.15:
        return "*"
    n = _rng.randint(1, 4)
    items = []
    for _ in range(n):
        e = _rand_expr(depth+1)
        if _rng.random() < 0.2:
            e = _parenthesize(e)
        if _rng.random() < 0.4:
            e += " AS " + _rand_identifier()
        items.append(e)
    return ", ".join(items)

def _table_factor(depth=0):
    # Base table or subquery with optional alias
    if _rng.random() < 0.25 and depth < 2:
        src = "(" + _select_core(depth+1) + ")"
    else:
        src = _rand_schema_qual(_rand_identifier())
    if _rng.random() < 0.6:
        src += " AS " + _rand_identifier()
    return src

def _join_clause(depth=0):
    left = _table_factor(depth+1)
    nj = _rng.randint(0, 2)
    parts = [left]
    for _ in range(nj):
        jtype = _rng.choice(["JOIN","INNER JOIN","LEFT JOIN","LEFT OUTER JOIN","CROSS JOIN","NATURAL JOIN"])
        right = _table_factor(depth+1)
        on = ""
        if "NATURAL" not in jtype and _rng.random() < 0.8:
            if _rng.random() < 0.6:
                on = " ON " + _rand_expr(depth+1)
            else:
                on = " USING (" + ", ".join(_rand_identifier() for _ in range(_rng.randint(1, 3))) + ")"
        parts.append(jtype + " " + right + on)
    return " ".join(parts)

def _from_clause(depth=0):
    if _rng.random() < 0.25:
        return ""  # SELECT without FROM (SQLite allows)
    n = _rng.randint(1, 2)
    sources = [_join_clause(depth+1) for _ in range(n)]
    return " FROM " + ", ".join(sources)

def _with_clause(depth=0):
    if _rng.random() < 0.3:
        return ""
    n = _rng.randint(1, 2)
    recursive = " RECURSIVE" if _rng.random() < 0.2 else ""
    ctes = []
    for _ in range(n):
        name = _rand_identifier()
        cols = ""
        if _rng.random() < 0.5:
            cols = "(" + ", ".join(_rand_identifier() for _ in range(_rng.randint(1, 3))) + ")"
        as_sel = _select_core(depth+1)
        ctes.append(f"{name}{cols} AS ({as_sel})")
    return "WITH" + recursive + " " + ", ".join(ctes) + " "

def _select_core(depth=0):
    distinct = ""
    if _rng.random() < 0.4:
        distinct = " DISTINCT" if _rng.random() < 0.5 else " ALL"
    sel = "SELECT" + distinct + " " + _select_list(depth+1)
    sel += _from_clause(depth+1)
    if _rng.random() < 0.7:
        sel += " WHERE " + _rand_expr(depth+1)
    sel += _group_by_clause(depth+1)
    sel += _order_by_clause(depth+1)
    sel += _limit_clause()
    # set operations
    if _rng.random() < 0.4:
        op = _rng.choice(["UNION","UNION ALL","INTERSECT","EXCEPT"])
        right = _select_core(depth+1)
        sel = "(" + sel + ") " + op + " (" + right + ")"
    return sel

def gen_select_stmt():
    s = _with_clause() + _select_core()
    if _rng.random() < 0.25:
        s = _random_case(s)
    if _rng.random() < 0.2:
        s = _with_comments(s)
    return s

def _col_def():
    name = _rand_identifier()
    t = _rng.choice(TYPES) if TYPES and _rng.random() < 0.85 else _rng.choice(["INT","TEXT","BLOB","REAL","NUMERIC"])
    # Occasionally add type length or precision
    if _rng.random() < 0.2 and "(" not in t:
        if _rng.random() < 0.5:
            t += "(" + str(_rng.randint(1, 255)) + ")"
        else:
            t += "(" + str(_rng.randint(1, 20)) + "," + str(_rng.randint(0, 10)) + ")"
    parts = [name, t]
    if _rng.random() < 0.3:
        parts.append("PRIMARY KEY")
        if _rng.random() < 0.3:
            parts.append("AUTOINCREMENT")
    if _rng.random() < 0.3:
        parts.append("UNIQUE")
    if _rng.random() < 0.4:
        parts.append("NOT NULL")
    if _rng.random() < 0.4:
        parts.append("DEFAULT " + _rand_expr())
    if _rng.random() < 0.3:
        parts.append("CHECK (" + _rand_expr() + ")")
    if _rng.random() < 0.2:
        parts.append("COLLATE " + _rand_collation())
    return " ".join(parts)

def gen_create_table():
    temp = " TEMP" if _rng.random() < 0.2 else (" TEMPORARY" if _rng.random() < 0.1 else "")
    ifnot = " IF NOT EXISTS" if _rng.random() < 0.5 else ""
    tname = _rand_schema_qual(_rand_identifier())
    if _rng.random() < 0.2:
        # CREATE TABLE AS SELECT
        s = f"CREATE{temp} TABLE{ifnot} {tname} AS " + _select_core()
    else:
        ncols = _rng.randint(1, 5)
        cols = [_col_def() for _ in range(ncols)]
        tconstraints = []
        if _rng.random() < 0.3:
            tconstraints.append("PRIMARY KEY (" + ", ".join(_rand_identifier() for _ in range(_rng.randint(1, min(3, ncols)))) + ")")
        if _rng.random() < 0.3:
            tconstraints.append("UNIQUE (" + ", ".join(_rand_identifier() for _ in range(_rng.randint(1, min(3, ncols)))) + ")")
        if _rng.random() < 0.2:
            tconstraints.append("CHECK (" + _rand_expr() + ")")
        inner = ", ".join(cols + ["CONSTRAINT " + _rand_identifier() + " " + tc for tc in tconstraints] if tconstraints and _rng.random()<0.5 else cols + tconstraints)
        s = f"CREATE{temp} TABLE{ifnot} {tname} (" + inner + ")"
        if _rng.random() < 0.2:
            s += " WITHOUT ROWID"
    if _rng.random() < 0.25:
        s = _random_case(s)
    if _rng.random() < 0.2:
        s = _with_comments(s)
    return s

def gen_alter_table():
    tname = _rand_schema_qual(_rand_identifier())
    choice = _rng.randint(0, 2)
    if choice == 0:
        s = f"ALTER TABLE {tname} ADD COLUMN " + _col_def()
    elif choice == 1:
        s = f"ALTER TABLE {tname} RENAME TO " + _rand_identifier()
    else:
        s = f"ALTER TABLE {tname} DROP COLUMN " + _rand_identifier()
    if _rng.random() < 0.25:
        s = _random_case(s)
    return s

def gen_drop_table():
    tname = _rand_schema_qual(_rand_identifier())
    s = "DROP TABLE " + ("IF EXISTS " if _rng.random()<0.5 else "") + tname
    if _rng.random() < 0.25:
        s = _random_case(s)
    return s

def gen_create_index():
    unique = " UNIQUE" if _rng.random() < 0.3 else ""
    ifnot = " IF NOT EXISTS" if _rng.random() < 0.4 else ""
    iname = _rand_schema_qual(_rand_identifier())
    tname = _rand_schema_qual(_rand_identifier())
    n = _rng.randint(1, 4)
    cols = []
    for _ in range(n):
        item = _rand_identifier()
        if _rng.random() < 0.2:
            item += " COLLATE " + _rand_collation()
        if _rng.random() < 0.5:
            item += " " + _rng.choice(["ASC","DESC"])
        cols.append(item)
    s = f"CREATE{unique} INDEX{ifnot} {iname} ON {tname} (" + ", ".join(cols) + ")"
    if _rng.random() < 0.25:
        s = _random_case(s)
    return s

def gen_drop_index():
    iname = _rand_schema_qual(_rand_identifier())
    s = "DROP INDEX " + ("IF EXISTS " if _rng.random()<0.5 else "") + iname
    if _rng.random() < 0.25:
        s = _random_case(s)
    return s

def gen_insert():
    or_clause = ""
    if _rng.random() < 0.3:
        or_clause = " OR " + _rng.choice(["REPLACE","IGNORE","ABORT","ROLLBACK","FAIL"])
    tname = _rand_schema_qual(_rand_identifier())
    if _rng.random() < 0.2:
        s = f"INSERT{or_clause} INTO {tname} DEFAULT VALUES"
        return s
    cols = ""
    if _rng.random() < 0.7:
        cols = "(" + ", ".join(_rand_identifier() for _ in range(_rng.randint(1, 5))) + ")"
    if _rng.random() < 0.5:
        # VALUES list
        nvals = _rng.randint(1, 3)
        rows = []
        for _ in range(nvals):
            m = _rng.randint(0, 5)
            vals = []
            for _ in range(m):
                vals.append(_rand_expr())
            rows.append("(" + ", ".join(vals) + ")")
        s = f"INSERT{or_clause} INTO {tname} {cols} VALUES " + ", ".join(rows)
    else:
        s = f"INSERT{or_clause} INTO {tname} {cols} " + _select_core()
    if _rng.random() < 0.25:
        s = _random_case(s)
    if _rng.random() < 0.15:
        s = _with_comments(s)
    return s

def gen_update():
    tname = _rand_schema_qual(_rand_identifier())
    s = "UPDATE " + tname + " SET "
    n = _rng.randint(1, 5)
    assigns = []
    for _ in range(n):
        target = _rand_identifier()
        if _rng.random() < 0.3:
            target = tname + "." + target
        op = "=" if _rng.random() < 0.8 else _rng.choice(["=","+=","-=","*=","/=","%="])
        assigns.append(target + " " + op + " " + _rand_expr())
    s += ", ".join(assigns)
    if _rng.random() < 0.8:
        s += " WHERE " + _rand_expr()
    if _rng.random() < 0.25:
        s = _random_case(s)
    return s

def gen_delete():
    tname = _rand_schema_qual(_rand_identifier())
    s = "DELETE FROM " + tname
    if _rng.random() < 0.8:
        s += " WHERE " + _rand_expr()
    if _rng.random() < 0.25:
        s = _random_case(s)
    return s

def gen_transaction():
    choice = _rng.randint(0, 4)
    if choice == 0:
        return "BEGIN"
    elif choice == 1:
        return "BEGIN TRANSACTION"
    elif choice == 2:
        return "COMMIT"
    elif choice == 3:
        return "ROLLBACK"
    else:
        if _rng.random() < 0.5:
            return "SAVEPOINT " + _rand_identifier()
        else:
            return "RELEASE " + _rand_identifier()

def gen_explain():
    base = gen_select_stmt()
    if _rng.random() < 0.5:
        return "EXPLAIN " + base
    else:
        return "EXPLAIN ANALYZE " + base

def gen_pragma():
    # SQLite-like pragmas
    name = _rng.choice(["journal_mode","synchronous","cache_size","foreign_keys","temp_store","encoding","page_size","mmap_size","wal_autocheckpoint","schema_version"])
    if _rng.random() < 0.5:
        return "PRAGMA " + name
    else:
        value = _rng.choice([_rand_number(), _rand_string(), _rng.choice(["OFF","ON","NORMAL","FULL","DELETE","TRUNCATE","WRITE-AHEAD LOG"])])
        return "PRAGMA " + name + " = " + str(value)

def gen_attach_detach():
    if _rng.random() < 0.5:
        return "ATTACH DATABASE " + _rand_string() + " AS " + _rand_identifier()
    else:
        return "DETACH DATABASE " + _rand_identifier()

def gen_view_trigger():
    if _rng.random() < 0.5:
        # VIEW
        temp = " TEMP" if _rng.random() < 0.3 else ""
        ifnot = " IF NOT EXISTS" if _rng.random() < 0.4 else ""
        vname = _rand_schema_qual(_rand_identifier())
        return f"CREATE{temp} VIEW{ifnot} {vname} AS " + _select_core()
    else:
        # TRIGGER (very simplified)
        ifnot = " IF NOT EXISTS" if _rng.random() < 0.3 else ""
        tname = _rand_schema_qual(_rand_identifier())
        trg = _rand_schema_qual(_rand_identifier())
        timing = _rng.choice(["BEFORE","AFTER"])
        event = _rng.choice(["INSERT","UPDATE","DELETE"])
        body = "BEGIN " + "; ".join([_rng.choice([gen_insert(), gen_update(), gen_delete()]) for _ in range(_rng.randint(1, 2))]) + "; END"
        return f"CREATE TRIGGER{ifnot} {trg} {timing} {event} ON {tname} FOR EACH ROW " + body

def gen_random_tokens():
    # Token stream including keywords, operators, literals, identifiers, parentheses
    tokens = []
    length = _rng.randint(5, 25)
    for _ in range(length):
        k = _rng.random()
        if k < 0.2 and KEYWORDS:
            tokens.append(_rng.choice(KEYWORDS))
        elif k < 0.35:
            tokens.append(_rand_identifier())
        elif k < 0.5:
            tokens.append(_rand_literal())
        elif k < 0.7 and OPERATORS:
            tokens.append(_rng.choice(OPERATORS))
        elif k < 0.85:
            tokens.append(_rng.choice(["(",")",",",".",";"]))
        else:
            tokens.append(_rng.choice(["AND","OR","NOT","IN","IS","NULL","LIKE"]))
    # ensure statement-like shape
    s = " ".join(tokens)
    return s

def gen_comment_statement():
    ctype = _rng.randint(0, 3)
    if ctype == 0:
        return "-- just a comment"
    elif ctype == 1:
        return "/* simple comment */ SELECT 1"
    elif ctype == 2:
        return "SELECT /* mid comment */ 1"
    else:
        # multiline
        return "/* line1\\nline2 */ " + _random_case("select 1")

def mutate_statement(s):
    m = s
    if _rng.random() < 0.5:
        m = _random_case(m)
    if _rng.random() < 0.3:
        m = _with_comments(m)
    # Insert extra parentheses around WHERE expression if possible
    if _rng.random() < 0.2:
        m = re.sub(r'(WHERE\\s+)(.+)', lambda mo: mo.group(1) + '(' + mo.group(2) + ')', m, count=1, flags=re.IGNORECASE)
    # Randomly add semicolon
    if _rng.random() < 0.7:
        if not m.strip().endswith(";"):
            m = m.strip() + ";"
    return m

def build_seed_corpus():
    # Handcrafted seeds to cover common parser branches
    seeds = [
        "SELECT 1",
        "SELECT * FROM t",
        "SELECT a, b FROM t WHERE a = 1",
        "SELECT DISTINCT name FROM users WHERE age BETWEEN 18 AND 30 ORDER BY name DESC",
        "SELECT a + b * c AS x FROM t1 JOIN t2 ON t1.id = t2.id WHERE a <> b",
        "SELECT COUNT(*) FROM logs",
        "SELECT CASE WHEN x > 0 THEN 'pos' ELSE 'neg' END FROM nums",
        "SELECT a, SUM(b) FROM tbl GROUP BY a HAVING SUM(b) > 10",
        "SELECT x FROM t ORDER BY 1 LIMIT 10 OFFSET 5",
        "INSERT INTO t (a, b, c) VALUES (1, 'x', NULL)",
        "INSERT OR REPLACE INTO t VALUES (1), (2), (3)",
        "UPDATE t SET a = a + 1, b = 'x' WHERE c IS NOT NULL",
        "DELETE FROM t WHERE id IN (1,2,3)",
        "CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, name TEXT NOT NULL, val REAL DEFAULT 1.0)",
        "CREATE TEMP TABLE tmp (k TEXT UNIQUE, v BLOB, CHECK (length(k) < 100))",
        "ALTER TABLE t ADD COLUMN z INT DEFAULT 0",
        "ALTER TABLE t RENAME TO t_new",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_t_name ON t (name COLLATE NOCASE ASC)",
        "DROP INDEX IF EXISTS idx_t_name",
        "DROP TABLE IF EXISTS old_table",
        "WITH cte AS (SELECT 1 AS a) SELECT a FROM cte",
        "WITH RECURSIVE c(n) AS (VALUES(1) UNION ALL SELECT n+1 FROM c WHERE n<5) SELECT * FROM c",
        "PRAGMA foreign_keys = ON",
        "BEGIN TRANSACTION",
        "COMMIT",
        "ROLLBACK",
        "EXPLAIN SELECT * FROM t",
        "SELECT EXISTS(SELECT 1 FROM t WHERE t.a = 2)",
        "SELECT (SELECT max(id) FROM t2) AS m",
        "SELECT a IN (1,2,3) FROM t",
        "SELECT x LIKE '%ab%' ESCAPE '_' FROM t",
        "SELECT * FROM t1 LEFT OUTER JOIN t2 USING (id)",
        "SELECT * FROM t1 NATURAL JOIN t2",
        "CREATE VIEW IF NOT EXISTS v AS SELECT * FROM t",
        "CREATE TRIGGER IF NOT EXISTS trig AFTER INSERT ON t FOR EACH ROW BEGIN UPDATE t SET a=a+1; END",
    ]
    return seeds

def generate_big_batch(target=6000):
    stmt_list = []
    seen = set()

    # Seeds
    for s in build_seed_corpus():
        s2 = mutate_statement(s)
        if s2 not in seen:
            seen.add(s2); stmt_list.append(s2)

    # Structured generations
    def add_many(gen, count):
        for _ in range(count):
            try:
                s = gen()
                # small chance to create incomplete statements to trigger error paths
                if _rng.random() < 0.05:
                    s = s[:_rng.randint(1, max(1, len(s)-1))]
                s = mutate_statement(s)
                if s not in seen:
                    seen.add(s); stmt_list.append(s)
            except Exception:
                # Keep fuzzing even if generation fails
                pass

    add_many(gen_select_stmt, 1600)
    add_many(gen_insert, 600)
    add_many(gen_update, 600)
    add_many(gen_delete, 400)
    add_many(gen_create_table, 550)
    add_many(gen_alter_table, 250)
    add_many(gen_drop_table, 300)
    add_many(gen_create_index, 350)
    add_many(gen_drop_index, 250)
    add_many(gen_transaction, 250)
    add_many(gen_explain, 200)
    add_many(gen_pragma, 250)
    add_many(gen_attach_detach, 120)
    add_many(gen_view_trigger, 150)
    add_many(gen_comment_statement, 250)
    add_many(gen_random_tokens, 700)

    # Ensure some extremely short/edge statements
    edges = [
        "''", "\"\"", "0x", "0x12AF", "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP",
        "(", ")", ",", ".", ";", "--", "/* */", "/* unterminated", "\"unterminated", "'unterminated",
        "SELECT *", "SELECT FROM", "SELECT 1 FROM", "SELECT 1 WHERE", "WHERE 1", "ORDER BY"
    ]
    for e in edges:
        ss = mutate_statement(e)
        if ss not in seen:
            seen.add(ss); stmt_list.append(ss)

    # Shuffle for diversity
    _rng.shuffle(stmt_list)
    # Limit to target to control time if over-produced
    if len(stmt_list) > target:
        stmt_list = stmt_list[:target]
    return stmt_list

_once_done = False

def fuzz(parse_sql):
    global _once_done
    if _once_done:
        return False
    try:
        # Generate one large, diverse batch and parse in a single call for efficiency
        stmts = generate_big_batch(target=6500)
        parse_sql(stmts)
    except Exception:
        # Even if parse_sql raises unexpectedly (shouldn't per spec), stop further fuzzing
        pass
    _once_done = True
    return False
""")

        code = "\n".join(code_parts)
        return {"code": code}