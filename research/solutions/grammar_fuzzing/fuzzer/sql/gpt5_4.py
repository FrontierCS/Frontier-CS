import random
import time
import os
import sys
import textwrap


class Solution:
    def solve(self, resources_path: str) -> dict:
        fuzzer_code = r'''
import random
import time
import string

# High-performance SQL fuzzer emphasizing parser/tokenizer coverage diversity.
# Strategy: hybrid grammar-based generation + lightweight mutations.
# Single fuzz() call with large, diverse batch to maximize efficiency bonus.

# Global state to ensure single-call fuzzing (minimize parse_sql invocations).
__FUZZ_DONE = False

def _rand_identifier(rng, base_names):
    name = rng.choice(base_names)
    # Randomly append suffixes, numeric parts, and mix case
    if rng.random() < 0.7:
        name += str(rng.randint(0, 9999))
    if rng.random() < 0.3:
        name = name + "_" + rng.choice(base_names)
    # Randomly apply quoting
    style = rng.random()
    if style < 0.15:
        return '"' + name.replace('"', '""') + '"'
    elif style < 0.3:
        return '`' + name.replace('`', '``') + '`'
    elif style < 0.33:
        # Bracket quoting variant
        return '[' + name.replace(']', ']]') + ']'
    # Randomly change case
    cases = [str.lower, str.upper, str.title]
    if rng.random() < 0.6:
        name = rng.choice(cases)(name)
    return name

def _rand_schema_qualified(rng, base_names):
    if rng.random() < 0.2:
        schema = _rand_identifier(rng, base_names)
        return schema + "." + _rand_identifier(rng, base_names)
    return _rand_identifier(rng, base_names)

def _rand_string_literal(rng):
    # generate SQL single-quoted string with escaped single quotes
    length = rng.randint(0, 40)
    chars = string.ascii_letters + string.digits + " _-!@#$%^&*()+=[]{}|;:,.<>/?\\\n\t"
    s = "".join(rng.choice(chars) for _ in range(length))
    s = s.replace("'", "''")
    # Occasionally include embedded null-like sequences or unicode escapes
    if rng.random() < 0.2:
        s += "\\0\\x1F"
    return "'" + s + "'"

def _rand_number_literal(rng):
    # ints or floats with exponents
    if rng.random() < 0.5:
        val = rng.randint(-10**10, 10**10)
        return str(val)
    else:
        mant = rng.uniform(-1e6, 1e6)
        if rng.random() < 0.5:
            exp = rng.randint(-10, 10)
            return ("%.6fe%d" % (mant, exp)).replace("e-0", "e-").replace("e+0", "e+")
        else:
            return "%.12f" % mant

def _rand_blob_literal(rng):
    # e.g., X'ABCD' or 0xABCD
    hexlen = rng.randint(0, 20) * 2
    hexchars = "0123456789ABCDEF"
    hx = "".join(rng.choice(hexchars) for _ in range(hexlen))
    if rng.random() < 0.5:
        return "X'" + hx + "'"
    else:
        return "0x" + hx

def _rand_bool_literal(rng):
    return rng.choice(["TRUE", "FALSE"])

def _rand_null_like(rng):
    # Use NULL, or NaN/INF variants to stress tokenizer
    return rng.choice(["NULL", "null", "NaN", "INF", "-INF"])

def _rand_date_time_literal(rng):
    dates = [
        "DATE '2020-01-01'",
        "DATE '1999-12-31'",
        "TIME '12:34:56'",
        "TIMESTAMP '2020-01-01 12:34:56'",
        "TIMESTAMP '1970-01-01 00:00:00'",
    ]
    return rng.choice(dates)

def _rand_literal(rng):
    p = rng.random()
    if p < 0.30:
        return _rand_string_literal(rng)
    elif p < 0.55:
        return _rand_number_literal(rng)
    elif p < 0.65:
        return _rand_blob_literal(rng)
    elif p < 0.8:
        return _rand_bool_literal(rng)
    elif p < 0.9:
        return _rand_date_time_literal(rng)
    else:
        return _rand_null_like(rng)

def _rand_type(rng):
    base = rng.choice([
        "INT", "INTEGER", "SMALLINT", "BIGINT", "TINYINT",
        "REAL", "FLOAT", "DOUBLE", "DOUBLE PRECISION", "DECIMAL", "NUMERIC",
        "BOOLEAN", "BOOL",
        "CHAR", "NCHAR", "VARCHAR", "NVARCHAR", "TEXT", "CLOB",
        "BLOB",
        "DATE", "TIME", "TIMESTAMP",
        "VARBINARY", "BINARY"
    ])
    if base in ("VARCHAR", "NVARCHAR", "CHAR", "NCHAR", "VARBINARY", "BINARY"):
        if rng.random() < 0.9:
            size = rng.randint(0, 256)
            return f"{base}({size})"
    if base in ("DECIMAL", "NUMERIC"):
        if rng.random() < 0.9:
            p = rng.randint(1, 18)
            s = rng.randint(0, min(8, p))
            return f"{base}({p},{s})"
    return base

def _rand_op(rng):
    return rng.choice([
        "+", "-", "*", "/", "%", "||",
        "&", "|", "^", "<<", ">>"
    ])

def _rand_cmp_op(rng):
    return rng.choice([
        "=", "!=", "<>", "<", "<=", ">", ">=",
        "LIKE", "NOT LIKE", "GLOB", "REGEXP", "IS", "IS NOT"
    ])

def _rand_unary_op(rng):
    return rng.choice(["-", "+", "~", "NOT"])

def _rand_func_name(rng):
    return rng.choice([
        "ABS", "ROUND", "FLOOR", "CEIL", "POWER", "SQRT", "EXP", "LOG", "LN",
        "LOWER", "UPPER", "SUBSTR", "SUBSTRING", "TRIM", "LTRIM", "RTRIM", "REPLACE", "LENGTH",
        "COALESCE", "NULLIF", "IFNULL",
        "RANDOM", "RANDOMBLOB", "HEX",
        "DATE", "TIME", "DATETIME", "JULIANDAY", "STRFTIME",
        "JSON", "JSON_EXTRACT", "JSON_OBJECT", "JSON_ARRAY",
        "COUNT", "SUM", "AVG", "MIN", "MAX"
    ])

def _rand_comment(rng):
    if rng.random() < 0.5:
        # single-line
        chars = ''.join(rng.choice(string.ascii_letters + string.digits + " _-") for _ in range(rng.randint(0, 20)))
        return "-- " + chars + "\n"
    else:
        chars = ''.join(rng.choice(string.ascii_letters + string.digits + " _-*/") for _ in range(rng.randint(0, 40)))
        return "/*" + chars.replace("/*", "/ *").replace("*/", "* /") + "*/"

def _maybe(rng, p):
    return rng.random() < p

class _SQLGen:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.base_ident_names = [
            "id","name","title","value","data","ts","dt","flag","count","price",
            "col","x","y","z","alpha","beta","gamma","delta","k","v",
            "t","u","w","r","s","m","n","o","p","q","idx","key",
            "select","from","where","order","group","limit","offset","join","left","right",
            "users","orders","products","inventory","logs","metrics","events","sales","purchases","dept",
            "schema","public","test","tmp","archive"
        ]
        self.table_bases = ["users","orders","products","invoices","items","logs","metrics","events","t","u","v"]
        self.column_bases = ["id","user_id","order_id","product_id","name","age","price","qty","count","total","flag","active","created_at","updated_at","data","payload","info","status","state","code","category","rate","score","x","y","z","a","b","c","d","e"]
        self.index_bases = ["idx","ix","pk","uk","uq","i","j","k"]
        self.cte_bases = ["cte","tmp","sub","part","agg","filter"]
        self.schema_bases = ["main","public","temp","archive","s1","s2"]
        self.alias_bases = ["a","b","c","d","e","f","g","h","i","j","k","t1","t2","x","y","z"]
        self.join_types = [
            "JOIN","INNER JOIN","LEFT JOIN","LEFT OUTER JOIN","RIGHT JOIN","RIGHT OUTER JOIN","FULL JOIN","FULL OUTER JOIN","CROSS JOIN","NATURAL JOIN"
        ]

    def identifier(self):
        return _rand_identifier(self.rng, self.base_ident_names)

    def schema_qualified(self):
        if _maybe(self.rng, 0.25):
            schema = _rand_identifier(self.rng, self.schema_bases)
            return schema + "." + _rand_identifier(self.rng, self.table_bases)
        return _rand_identifier(self.rng, self.table_bases)

    def column_name(self):
        return _rand_identifier(self.rng, self.column_bases)

    def index_name(self):
        return _rand_identifier(self.rng, self.index_bases)

    def alias(self):
        return _rand_identifier(self.rng, self.alias_bases)

    def literal(self):
        return _rand_literal(self.rng)

    def type_name(self):
        return _rand_type(self.rng)

    def func_name(self):
        return _rand_func_name(self.rng)

    def comment(self):
        return _rand_comment(self.rng)

    def unary_expr(self, depth):
        op = _rand_unary_op(self.rng)
        return f"{op} {self.expr(depth-1)}"

    def func_call(self, depth):
        fn = self.func_name()
        # sometimes aggregate with DISTINCT
        if fn in ("COUNT","SUM","AVG","MIN","MAX") and _maybe(self.rng, 0.3):
            argcnt = self.rng.randint(1, 3)
            args = ", ".join(self.expr(depth-1) for _ in range(argcnt))
            return f"{fn}(DISTINCT {args})"
        argcnt = self.rng.randint(0, 3)
        if argcnt == 0 and _maybe(self.rng, 0.4):
            return f"{fn}()"
        args = ", ".join(self.expr(depth-1) for _ in range(argcnt))
        return f"{fn}({args})"

    def case_expr(self, depth):
        parts = []
        when_count = self.rng.randint(1, 3)
        for _ in range(when_count):
            cond = self.predicate(depth-1)
            then = self.expr(depth-1)
            parts.append(f"WHEN {cond} THEN {then}")
        if _maybe(self.rng, 0.5):
            els = self.expr(depth-1)
            parts.append(f"ELSE {els}")
        return "CASE " + " ".join(parts) + " END"

    def base_expr(self, depth):
        choice = self.rng.random()
        if choice < 0.25:
            return self.literal()
        elif choice < 0.45:
            # column reference with optional table alias
            if _maybe(self.rng, 0.4):
                return f"{self.alias()}.{self.column_name()}"
            return self.column_name()
        elif choice < 0.65:
            return self.func_call(depth)
        elif choice < 0.8:
            return "(" + self.expr(depth-1) + ")"
        else:
            return self.case_expr(depth)

    def expr(self, depth=3):
        if depth <= 0:
            return self.base_expr(0)
        p = self.rng.random()
        if p < 0.2:
            return self.unary_expr(depth)
        elif p < 0.65:
            # binary operation
            left = self.expr(depth-1)
            if _maybe(self.rng, 0.2):
                op = "||"
            else:
                op = _rand_op(self.rng)
            right = self.expr(depth-1)
            return f"({left} {op} {right})"
        elif p < 0.8:
            # comparison
            left = self.expr(depth-1)
            op = _rand_cmp_op(self.rng)
            if op in ("LIKE","NOT LIKE") and _maybe(self.rng, 0.3):
                # include ESCAPE clause
                return f"({left} {op} {_rand_string_literal(self.rng)} ESCAPE '\\')"
            right = self.expr(depth-1)
            return f"({left} {op} {right})"
        elif p < 0.9:
            # IN list or subquery
            left = self.expr(depth-1)
            if _maybe(self.rng, 0.5):
                # value list
                lst_count = self.rng.randint(0, 5)
                items = ", ".join(self.expr(depth-1) for _ in range(lst_count))
                return f"({left} IN ({items}))"
            else:
                return f"({left} IN ({self.select_stmt(as_subquery=True)}))"
        else:
            # BETWEEN
            target = self.expr(depth-1)
            a = self.expr(depth-1)
            b = self.expr(depth-1)
            not_kw = "NOT " if _maybe(self.rng, 0.3) else ""
            return f"({target} {not_kw}BETWEEN {a} AND {b})"

    def predicate(self, depth=3):
        if depth <= 0:
            return self.expr(0)
        # Combine boolean operations
        parts = [self.expr(depth-1)]
        for _ in range(self.rng.randint(0, 2)):
            op = self.rng.choice(["AND","OR"])
            if _maybe(self.rng, 0.25):
                parts.append(op + " NOT " + self.expr(depth-1))
            else:
                parts.append(op + " " + self.expr(depth-1))
        # Sometimes add IS NULL/NOT NULL tail
        if _maybe(self.rng, 0.2):
            parts.append(self.rng.choice(["IS NULL","IS NOT NULL"]))
        return " ".join(parts)

    def table_source(self, depth=2):
        # produce named table or derived table with alias
        if depth > 0 and _maybe(self.rng, 0.25):
            sub = self.select_stmt(as_subquery=True)
            alias = self.alias()
            return f"({sub}) AS {alias}"
        else:
            tbl = self.schema_qualified()
            if _maybe(self.rng, 0.7):
                return f"{tbl} AS {self.alias()}"
            return tbl

    def join_clause(self, depth=2):
        left = self.table_source(depth)
        joins = []
        join_count = self.rng.randint(0, 2)
        for _ in range(join_count):
            jt = self.rng.choice(self.join_types)
            right = self.table_source(depth-1)
            if "NATURAL" in jt:
                joins.append(f"{jt} {right}")
            elif "CROSS" in jt:
                if _maybe(self.rng, 0.7):
                    joins.append(f"{jt} {right}")
                else:
                    # CROSS APPLY-like
                    joins.append(f"{jt} {right}")
            else:
                cond = self.predicate(depth-1)
                joins.append(f"{jt} {right} ON {cond}")
        return " ".join([left] + joins)

    def select_core(self, depth=2):
        sel = "SELECT "
        if _maybe(self.rng, 0.25):
            sel += self.rng.choice(["DISTINCT ", "ALL "])
        # projection list
        colcount = self.rng.randint(1, 6)
        items = []
        for _ in range(colcount):
            if _maybe(self.rng, 0.2):
                items.append("*")
            else:
                ex = self.expr(depth)
                if _maybe(self.rng, 0.5):
                    items.append(f"{ex} AS {self.alias()}")
                else:
                    items.append(ex)
        sel += ", ".join(items)
        # FROM clause
        if _maybe(self.rng, 0.9):
            frm = " FROM " + self.join_clause(depth)
        else:
            frm = ""
        # WHERE
        if _maybe(self.rng, 0.7):
            where = " WHERE " + self.predicate(depth)
        else:
            where = ""
        # GROUP BY
        if _maybe(self.rng, 0.5):
            gcount = self.rng.randint(1, 3)
            gitems = ", ".join(self.expr(depth) for _ in range(gcount))
            group_by = " GROUP BY " + gitems
            having = " HAVING " + self.predicate(depth) if _maybe(self.rng, 0.4) else ""
        else:
            group_by = ""
            having = ""
        # ORDER BY
        if _maybe(self.rng, 0.5):
            ocount = self.rng.randint(1, 3)
            oitems = []
            for _ in range(ocount):
                order = self.expr(depth)
                if _maybe(self.rng, 0.7):
                    order += " " + self.rng.choice(["ASC","DESC"])
                if _maybe(self.rng, 0.3):
                    order += " " + self.rng.choice(["NULLS FIRST","NULLS LAST"])
                oitems.append(order)
            order_by = " ORDER BY " + ", ".join(oitems)
        else:
            order_by = ""
        # LIMIT OFFSET
        limit_off = ""
        if _maybe(self.rng, 0.6):
            lim = self.rng.randint(0, 1000)
            limit_off = f" LIMIT {lim}"
            if _maybe(self.rng, 0.5):
                off = self.rng.randint(0, 1000)
                if _maybe(self.rng, 0.5):
                    limit_off += f" OFFSET {off}"
                else:
                    limit_off += f" , {off}"
        return sel + frm + where + group_by + having + order_by + limit_off

    def select_stmt(self, depth=2, as_subquery=False):
        # WITH clause optional
        with_clause = ""
        if _maybe(self.rng, 0.2) and depth > 0:
            cte_count = self.rng.randint(1, 2)
            ctes = []
            for _ in range(cte_count):
                name = _rand_identifier(self.rng, self.cte_bases)
                if _maybe(self.rng, 0.5):
                    # column list
                    cols = ", ".join(self.column_name() for _ in range(self.rng.randint(1, 4)))
                    name += f"({cols})"
                ctes.append(f"{name} AS ({self.select_core(max(1, depth-1))})")
            with_clause = "WITH " + ", ".join(ctes) + " "
            if _maybe(self.rng, 0.2):
                with_clause = "WITH RECURSIVE " + ", ".join(ctes) + " "
        core = self.select_core(depth)
        # set operations
        set_stmt = core
        for _ in range(self.rng.randint(0, 2)):
            op = self.rng.choice(["UNION","UNION ALL","INTERSECT","EXCEPT","EXCEPT ALL"])
            rhs = self.select_core(depth)
            if _maybe(self.rng, 0.5):
                rhs = "(" + rhs + ")"
            set_stmt = f"{set_stmt} {op} {rhs}"
        stmt = with_clause + set_stmt
        if not as_subquery and _maybe(self.rng, 0.7):
            # append semicolon
            if _maybe(self.rng, 0.7):
                stmt += ";"
        # Insert comments randomly at start or end
        if _maybe(self.rng, 0.2):
            stmt = self.comment() + stmt
        if _maybe(self.rng, 0.2):
            stmt = stmt + " " + self.comment()
        return stmt

    def insert_stmt(self):
        tbl = self.schema_qualified()
        if _maybe(self.rng, 0.5):
            cols = "(" + ", ".join(self.column_name() for _ in range(self.rng.randint(1, 5))) + ")"
        else:
            cols = ""
        if _maybe(self.rng, 0.4):
            # INSERT SELECT
            sel = self.select_stmt(as_subquery=True)
            stmt = f"INSERT INTO {tbl} {cols} {sel}"
        else:
            # VALUES
            rows = []
            rowc = self.rng.randint(1, 5)
            for _ in range(rowc):
                vc = self.rng.randint(0, 6)
                vals = ", ".join(self.expr(2) for _ in range(vc))
                rows.append("(" + vals + ")")
            stmt = f"INSERT INTO {tbl} {cols} VALUES " + ", ".join(rows)
        if _maybe(self.rng, 0.2):
            stmt += " ON CONFLICT DO NOTHING"
        if _maybe(self.rng, 0.6):
            stmt += ";"
        return stmt

    def update_stmt(self):
        tbl = self.schema_qualified()
        alias = self.alias() if _maybe(self.rng, 0.5) else ""
        alias_str = f" AS {alias}" if alias else ""
        set_count = self.rng.randint(1, 5)
        sets = []
        for _ in range(set_count):
            col = self.column_name()
            val = self.expr(2)
            sets.append(f"{col} = {val}")
        where = " WHERE " + self.predicate(2) if _maybe(self.rng, 0.7) else ""
        stmt = f"UPDATE {tbl}{alias_str} SET " + ", ".join(sets) + where
        if _maybe(self.rng, 0.6):
            stmt += ";"
        return stmt

    def delete_stmt(self):
        tbl = self.schema_qualified()
        where = " WHERE " + self.predicate(2) if _maybe(self.rng, 0.7) else ""
        stmt = f"DELETE FROM {tbl}" + where
        if _maybe(self.rng, 0.6):
            stmt += ";"
        return stmt

    def create_table_stmt(self):
        tbl = self.schema_qualified()
        cols = []
        col_count = self.rng.randint(1, 7)
        pkcols = []
        for _ in range(col_count):
            cname = self.column_name()
            ctype = self.type_name()
            col_parts = [cname, ctype]
            if _maybe(self.rng, 0.4):
                col_parts.append("NOT NULL")
            if _maybe(self.rng, 0.2):
                col_parts.append("UNIQUE")
            if _maybe(self.rng, 0.4):
                col_parts.append("DEFAULT " + self.expr(1))
            if _maybe(self.rng, 0.2):
                col_parts.append("CHECK (" + self.predicate(1) + ")")
            if _maybe(self.rng, 0.2):
                col_parts.append("COLLATE " + self.rng.choice(["BINARY","NOCASE","RTRIM"]))
            if _maybe(self.rng, 0.2):
                pkcols.append(cname)
            cols.append(" ".join(col_parts))
        # table constraints
        if _maybe(self.rng, 0.5) and pkcols:
            # add table-level PK or UNIQUE
            if _maybe(self.rng, 0.5):
                tcons = "PRIMARY KEY (" + ", ".join(pkcols) + ")"
            else:
                tcons = "UNIQUE (" + ", ".join(pkcols) + ")"
            cols.append(tcons)
        if _maybe(self.rng, 0.2):
            # foreign key (syntactic)
            ref_tbl = self.schema_qualified()
            ref_col_count = self.rng.randint(1, min(3, col_count))
            fcols = ", ".join(self.column_name() for _ in range(ref_col_count))
            rcols = ", ".join(self.column_name() for _ in range(ref_col_count))
            cols.append(f"FOREIGN KEY ({fcols}) REFERENCES {ref_tbl} ({rcols})")
        body = ", ".join(cols)
        stmt = f"CREATE TABLE {'IF NOT EXISTS ' if _maybe(self.rng,0.3) else ''}{tbl} ({body})"
        if _maybe(self.rng, 0.6):
            stmt += ";"
        return stmt

    def alter_table_stmt(self):
        tbl = self.schema_qualified()
        choice = self.rng.random()
        if choice < 0.33:
            # ADD COLUMN
            cname = self.column_name()
            ctype = self.type_name()
            tail = ""
            if _maybe(self.rng, 0.4):
                tail += " NOT NULL"
            if _maybe(self.rng, 0.3):
                tail += " DEFAULT " + self.expr(1)
            stmt = f"ALTER TABLE {tbl} ADD COLUMN {cname} {ctype}{tail}"
        elif choice < 0.66:
            # RENAME
            if _maybe(self.rng, 0.5):
                newtbl = self.schema_qualified()
                stmt = f"ALTER TABLE {tbl} RENAME TO {newtbl}"
            else:
                oldc = self.column_name()
                newc = self.column_name()
                stmt = f"ALTER TABLE {tbl} RENAME COLUMN {oldc} TO {newc}"
        else:
            # DROP COLUMN
            cname = self.column_name()
            stmt = f"ALTER TABLE {tbl} DROP COLUMN {cname}"
        if _maybe(self.rng, 0.6):
            stmt += ";"
        return stmt

    def index_stmt(self):
        if self.rng.random() < 0.6:
            # CREATE INDEX
            unique = "UNIQUE " if _maybe(self.rng, 0.3) else ""
            name = self.index_name()
            tbl = self.schema_qualified()
            col_count = self.rng.randint(1, 5)
            cols = []
            for _ in range(col_count):
                col = self.column_name()
                if _maybe(self.rng, 0.6):
                    col += " " + self.rng.choice(["ASC","DESC"])
                cols.append(col)
            stmt = f"CREATE {unique}INDEX {'IF NOT EXISTS ' if _maybe(self.rng, 0.2) else ''}{name} ON {tbl} (" + ", ".join(cols) + ")"
            if _maybe(self.rng, 0.3):
                stmt += " WHERE " + self.predicate(1)
        else:
            # DROP INDEX
            if _maybe(self.rng, 0.4):
                stmt = f"DROP INDEX IF EXISTS {self.index_name()}"
            else:
                stmt = f"DROP INDEX {self.index_name()}"
        if _maybe(self.rng, 0.6):
            stmt += ";"
        return stmt

    def transaction_stmt(self):
        r = self.rng.random()
        if r < 0.33:
            kind = self.rng.choice(["DEFERRED","IMMEDIATE","EXCLUSIVE"])
            return f"BEGIN {kind};"
        elif r < 0.66:
            return self.rng.choice(["COMMIT;","COMMIT","END;","END"])
        else:
            if _maybe(self.rng, 0.5):
                sp = _rand_identifier(self.rng, ["sp","s","sv","save","point"])
                return f"SAVEPOINT {sp};"
            else:
                if _maybe(self.rng, 0.5):
                    sp = _rand_identifier(self.rng, ["sp","s","sv","save","point"])
                    return f"ROLLBACK TO {sp};"
                return self.rng.choice(["ROLLBACK;","ROLLBACK"])

    def drop_stmt(self):
        if _maybe(self.rng, 0.5):
            return f"DROP TABLE {'IF EXISTS ' if _maybe(self.rng,0.5) else ''}{self.schema_qualified()};"
        else:
            return f"DROP VIEW {'IF EXISTS ' if _maybe(self.rng,0.5) else ''}{self.schema_qualified()};"

    def random_statement(self):
        p = self.rng.random()
        if p < 0.35:
            return self.select_stmt()
        elif p < 0.50:
            return self.insert_stmt()
        elif p < 0.62:
            return self.update_stmt()
        elif p < 0.72:
            return self.delete_stmt()
        elif p < 0.82:
            return self.create_table_stmt()
        elif p < 0.90:
            return self.index_stmt()
        elif p < 0.95:
            return self.alter_table_stmt()
        elif p < 0.98:
            return self.transaction_stmt()
        else:
            return self.drop_stmt()

def _mutate_flip_case(rng, s):
    # Randomly change character case
    out = []
    for ch in s:
        if 'a' <= ch <= 'z' or 'A' <= ch <= 'Z':
            if rng.random() < 0.5:
                out.append(ch.swapcase())
            else:
                out.append(ch)
        else:
            out.append(ch)
    return "".join(out)

def _mutate_insert_noise(rng, s):
    # Insert punctuation or keywords at random positions
    tokens = [";", ",", "(", ")", "+", "-", "*", "/", "%", "||", "&", "|", "^", "<<", ">>",
              "AND", "OR", "NOT", "XOR", "UNKNOWN", "SELEC", "FR0M", "WHER", "HAVIN", "GROU BY",
              "/*noise*/", "--x\n"]
    pos = rng.randint(0, max(0, len(s)))
    tok = rng.choice(tokens)
    return s[:pos] + " " + tok + " " + s[pos:]

def _mutate_delete_chunk(rng, s):
    if len(s) < 4:
        return s
    start = rng.randint(0, len(s)-2)
    end = min(len(s), start + rng.randint(1, max(2, len(s)//6)))
    return s[:start] + s[end:]

def _mutate_duplicate_word(rng, s):
    parts = s.split()
    if not parts:
        return s
    idx = rng.randint(0, len(parts)-1)
    parts.insert(idx, parts[idx])
    return " ".join(parts)

def _mutate_whitespace(rng, s):
    # replace spaces with random whitespace sequences
    out = []
    for ch in s:
        if ch == ' ' and rng.random() < 0.5:
            out.append(" " * rng.randint(1, 4) + ("\n" if rng.random() < 0.3 else ""))
        else:
            out.append(ch)
    return "".join(out)

def _mutate_wrap_comment(rng, s):
    # wrap statement with comments
    return _rand_comment(rng) + " " + s + " " + _rand_comment(rng)

def _mutate_splice(rng, s1, s2):
    # combine parts of two statements
    p1 = rng.randint(0, len(s1))
    p2 = rng.randint(0, len(s2))
    return s1[:p1] + " /*splice*/ " + s2[p2:]

def _mutate_stmt_pool(rng, base_stmts, budget):
    mutants = []
    if not base_stmts:
        return mutants
    ops = [
        _mutate_flip_case,
        _mutate_insert_noise,
        _mutate_delete_chunk,
        _mutate_duplicate_word,
        _mutate_whitespace,
        _mutate_wrap_comment,
    ]
    for _ in range(budget):
        s = rng.choice(base_stmts)
        if rng.random() < 0.2 and len(base_stmts) > 1:
            t = rng.choice(base_stmts)
            mutants.append(_mutate_splice(rng, s, t))
        else:
            fn = rng.choice(ops)
            mutants.append(fn(rng, s))
    return mutants

def _edge_case_statements(rng, gen):
    stmts = []
    # Tokenizer edge cases: unusual literals, comments, empty inputs, semicolons
    stmts.extend([
        ";",
        "  ;  ",
        "",
        "-- just a comment\n",
        "/* unterminated comment ...",  # likely error
        "SELECT",  # incomplete keyword
        "SELECT *",  # incomplete
        "SELECT * FROM",  # incomplete
        "'unclosed string",  # unclosed string
        '"unclosed identifier',  # unclosed identifier
        "SELECT 1/0;",  # division by zero not executed but tokenized/parsed
        "SELECT - - - + + 5;",
        "SELECT 'a''b''c' || 'd';",
        "SELECT X'0A0B' = 0x0A0B;",
        "SELECT NULL, TRUE, FALSE, NaN, INF, -INF;",
        "SELECT DATE '2020-01-01', TIME '12:34:56', TIMESTAMP '2000-01-01 00:00:00';",
        "SELECT /* comment */ 1 -- tail\n",
        "/*multi*line*/ SELECT\n1\n,\n2\nFROM\n" + gen.schema_qualified() + ";",
        "SELECT 1 AS \"select\", 2 AS `from`, 3 AS [where];",
        "CREATE TABLE " + gen.schema_qualified() + " (id INT PRIMARY KEY, name TEXT NOT NULL, note TEXT DEFAULT 'x''y');",
        "CREATE INDEX " + gen.index_name() + " ON " + gen.schema_qualified() + "(id, name DESC) WHERE id > 10;",
        "ALTER TABLE " + gen.schema_qualified() + " RENAME TO " + gen.schema_qualified() + ";",
        "DELETE FROM " + gen.schema_qualified() + " WHERE id IN ();",  # empty IN list
        "INSERT INTO " + gen.schema_qualified() + " VALUES ();",  # empty values
        "UPDATE " + gen.schema_qualified() + " SET " + gen.column_name() + " = (SELECT 1);",
        "SELECT CASE WHEN 1 THEN 2 ELSE 3 END;",
        "WITH cte(a,b) AS (SELECT 1,2) SELECT a,b FROM cte;",
        "SELECT 1 UNION SELECT 2 INTERSECT SELECT 2 EXCEPT SELECT 3;",
        "BEGIN IMMEDIATE;",
        "ROLLBACK;",
        "COMMIT;",
    ])
    # Long identifier, long string
    long_ident = ''.join(rng.choice(string.ascii_letters) for _ in range(200))
    stmts.append(f'SELECT 1 AS "{long_ident}";')
    long_str = "'" + ("x" * 1000).replace("'", "''") + "'"
    stmts.append("SELECT " + long_str + ";")
    return stmts

def fuzz(parse_sql):
    global __FUZZ_DONE
    if __FUZZ_DONE:
        return False

    rng = random.Random(int(time.time() * 1000000) & 0xFFFFFFFF)
    gen = _SQLGen(seed=rng.randint(0, 2**32 - 1))

    # Build a diverse base corpus
    base = []

    # Add edge-case statements first
    base.extend(_edge_case_statements(rng, gen))

    # Core categories with balanced counts for breadth
    counts = {
        "select": 450,
        "insert": 180,
        "update": 160,
        "delete": 160,
        "create": 180,
        "index": 150,
        "alter": 120,
        "transaction": 70,
        "drop": 80,
    }

    for _ in range(counts["select"]):
        base.append(gen.select_stmt())
    for _ in range(counts["insert"]):
        base.append(gen.insert_stmt())
    for _ in range(counts["update"]):
        base.append(gen.update_stmt())
    for _ in range(counts["delete"]):
        base.append(gen.delete_stmt())
    for _ in range(counts["create"]):
        base.append(gen.create_table_stmt())
    for _ in range(counts["index"]):
        base.append(gen.index_stmt())
    for _ in range(counts["alter"]):
        base.append(gen.alter_table_stmt())
    for _ in range(counts["transaction"]):
        base.append(gen.transaction_stmt())
    for _ in range(counts["drop"]):
        base.append(gen.drop_stmt())

    # Deduplicate a bit to keep size moderate, but avoid heavy overhead
    # Use a set with sampling for speed
    seen = set()
    uniq = []
    for s in base:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    base = uniq

    # Generate mutants to explore error paths and alternate tokenizations
    mutant_budget = max(300, len(base) // 3)
    mutants = _mutate_stmt_pool(rng, base, mutant_budget)

    # Compose final corpus
    corpus = base + mutants

    # Shuffle for diversity
    rng.shuffle(corpus)

    # Split into a small number of large batches to minimize parse_sql invocations
    # Aim: 2-4 calls total
    total = len(corpus)
    batches = []
    target_calls = 3
    chunk = (total + target_calls - 1) // target_calls
    for i in range(0, total, chunk):
        batches.append(corpus[i:i+chunk])

    # Execute batches
    for batch in batches:
        # Guard extremely long batch sizes (should not be too big for time/memory)
        if not batch:
            continue
        parse_sql(batch)

    __FUZZ_DONE = True
    return False
'''
        return {"code": fuzzer_code}