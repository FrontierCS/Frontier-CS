import random
import time
import os
import sys


class Solution:
    def solve(self, resources_path: str) -> dict:
        code = r'''
import random
import time
import string

# Global state to keep efficiency bonus high by minimizing parse_sql calls
_fuzzer_state = {"done": False}

def _rand_bool(p=0.5):
    return random.random() < p

def _rand_int(a=0, b=1000):
    return random.randint(a, b)

def _rand_float():
    # Generate simple or exponential floats
    if _rand_bool(0.3):
        base = random.uniform(-1e6, 1e6)
        return "{:.6f}".format(base)
    else:
        mant = random.uniform(-10, 10)
        exp = random.randint(-10, 10)
        return "{:.3f}e{:+d}".format(mant, exp)

def _rand_string_literal(max_len=20):
    # Generate SQL single-quoted string with escaped quotes by doubling
    length = random.randint(0, max_len)
    chars = []
    # Include some edge characters
    alphabet = string.ascii_letters + string.digits + " _-+=/*%$#@!?,.:;|[](){}"
    for _ in range(length):
        ch = random.choice(alphabet)
        chars.append(ch)
    s = "".join(chars)
    # Occasionally include single quotes to test escaping
    if _rand_bool(0.3):
        s = s[:len(s)//2] + "'" + s[len(s)//2:]
    s = s.replace("'", "''")
    prefix = ""  # could use E or N for extensions, but keep dialect-agnostic
    return f"{prefix}'{s}'"

def _rand_identifier(base=None, quoted_prob=0.25):
    # Simple identifier generator with optional quoting styles
    if base is None:
        first = random.choice(string.ascii_letters + "_")
        rest_len = random.randint(0, 10)
        rest = "".join(random.choice(string.ascii_letters + string.digits + "_$") for _ in range(rest_len))
        ident = first + rest
    else:
        ident = base
    if _rand_bool(quoted_prob):
        style = random.choice(['"', '`', 'bracket', 'none'])
        if style == '"':
            return f"\"{ident}\""
        elif style == '`':
            return f"`{ident}`"
        elif style == 'bracket':
            return f"[{ident}]"
        else:
            return ident
    return ident

def _random_keyword_case(word):
    # Random case for keyword to test tokenizer case-insensitivity
    res = []
    for ch in word:
        if ch.isalpha() and _rand_bool(0.5):
            res.append(ch.upper())
        else:
            res.append(ch.lower())
    return "".join(res)

def _maybe_insert_comment(sql):
    # Insert a block or line comment at a whitespace boundary if possible
    positions = [i for i, ch in enumerate(sql) if ch == ' ']
    if not positions:
        return sql + " /*" + "c" * random.randint(0, 10) + "*/"
    pos = random.choice(positions)
    if _rand_bool(0.5):
        comment = " /* " + "x" * random.randint(0, 10) + " */ "
    else:
        comment = " -- " + "y" * random.randint(0, 10) + "\n"
    return sql[:pos] + comment + sql[pos:]

def _maybe_toggle_case(sql, p=0.3):
    # Randomly toggle case of characters outside quotes for variation
    # Simple approach: toggle with probability but do not try to parse quotes
    out = []
    for ch in sql:
        if ch.isalpha() and _rand_bool(p):
            if ch.islower():
                out.append(ch.upper())
            else:
                out.append(ch.lower())
        else:
            out.append(ch)
    return "".join(out)

class SQLFuzzer:
    def __init__(self):
        random.seed(int(time.time() * 1000003) & 0xFFFFFFFF)
        # Build a pseudo schema with common names
        base_tables = [
            "users", "orders", "products", "customers", "employees",
            "departments", "categories", "suppliers", "shippers", "invoices",
            "payments", "reviews", "sessions", "logs", "roles", "permissions"
        ]
        # Add additional generic tables
        base_tables += [f"t{i}" for i in range(1, 31)]
        base_cols_common = [
            "id", "name", "title", "price", "amount", "quantity",
            "created_at", "updated_at", "status", "description",
            "count", "value", "index", "username", "email", "phone",
            "address", "age", "salary", "level", "category_id", "product_id",
            "order_id", "user_id", "role_id", "dept_id"
        ]
        # Include tricky/reserved-like names to exercise identifier quoting
        base_cols_common += ["select", "from", "where", "table", "group", "order", "limit", "offset"]

        # Build schema map
        self.tables = []
        self.table_columns = {}
        for t in base_tables:
            self.tables.append(t)
            num_cols = random.randint(5, 12)
            cols = set()
            # Ensure id exists
            cols.add("id")
            while len(cols) < num_cols:
                base = random.choice(base_cols_common)
                # add numeric suffix sometimes
                if _rand_bool(0.3):
                    base = f"{base}{random.randint(1, 5)}"
                cols.add(base)
            self.table_columns[t] = list(cols)

        # Data types and functions likely supported by a typical SQL parser
        self.data_types = [
            "INT", "INTEGER", "SMALLINT", "BIGINT",
            "REAL", "FLOAT", "DOUBLE", "DECIMAL(10,2)", "NUMERIC(12,4)",
            "VARCHAR(50)", "VARCHAR(255)", "CHAR(10)", "TEXT",
            "DATE", "TIME", "TIMESTAMP", "BOOLEAN"
        ]
        self.funcs_scalars = [
            "ABS", "ROUND", "FLOOR", "CEIL", "POWER", "SQRT",
            "UPPER", "LOWER", "LENGTH", "SUBSTR", "SUBSTRING",
            "COALESCE", "NULLIF", "GREATEST", "LEAST", "TRIM"
        ]
        self.funcs_aggr = ["COUNT", "SUM", "AVG", "MIN", "MAX"]
        self.boolean_keywords = ["TRUE", "FALSE"]
        self.null_keywords = ["NULL"]
        self.join_types = ["JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "LEFT OUTER JOIN", "RIGHT OUTER JOIN"]
        self.comparators = ["=", "!=", "<>", "<", ">", "<=", ">=", "LIKE", "ILIKE"]
        self.arith_ops = ["+", "-", "*", "/", "%"]
        self.logic_ops = ["AND", "OR"]
        self.bit_ops = ["|", "&", "^"]
        self.other_ops = ["||"]
        self.unary_ops = ["-", "NOT"]
        self.order_keywords = ["ASC", "DESC"]
        self.set_ops = ["UNION", "UNION ALL", "INTERSECT", "EXCEPT"]

        # Pre-generate some index names
        self.index_names = [f"ix_{t}_{random.choice(self.table_columns[t])}_{i}" for i, t in enumerate(self.tables)]

    def _qualify_col(self, table, col, alias=None):
        if alias:
            return f"{alias}.{_rand_identifier(col, quoted_prob=0.15)}"
        else:
            if _rand_bool(0.3):
                return f"{_rand_identifier(table, quoted_prob=0.1)}.{_rand_identifier(col, quoted_prob=0.15)}"
            return _rand_identifier(col, quoted_prob=0.15)

    def literal(self):
        choice = random.random()
        if choice < 0.28:
            return str(_rand_int(-10**9, 10**9))
        elif choice < 0.56:
            return _rand_float()
        elif choice < 0.75:
            return random.choice(self.boolean_keywords)
        elif choice < 0.92:
            return random.choice(self.null_keywords)
        else:
            return _rand_string_literal(40)

    def column_ref(self, available_tables):
        if not available_tables:
            t = random.choice(self.tables)
            col = random.choice(self.table_columns[t])
            return self._qualify_col(t, col)
        else:
            t, alias = random.choice(available_tables)
            col = random.choice(self.table_columns[t])
            return self._qualify_col(t, col, alias=alias)

    def function_call(self, available_tables, depth):
        if _rand_bool(0.5):
            f = random.choice(self.funcs_scalars)
            arity = random.randint(1, 3)
            args = []
            for _ in range(arity):
                args.append(self.expr(available_tables, depth + 1))
            return f"{_random_keyword_case(f)}(" + ", ".join(args) + ")"
        else:
            f = random.choice(self.funcs_aggr)
            if _rand_bool(0.2):
                return f"{_random_keyword_case(f)}(*)"
            else:
                # DISTINCT sometimes
                distinct = _random_keyword_case("DISTINCT") + " " if _rand_bool(0.25) else ""
                return f"{_random_keyword_case(f)}({distinct}{self.expr(available_tables, depth + 1)})"

    def case_when(self, available_tables, depth):
        parts = ["CASE"]
        n = random.randint(1, 3)
        for _ in range(n):
            parts.append("WHEN")
            parts.append(self.expr(available_tables, depth + 1))
            parts.append("THEN")
            parts.append(self.expr(available_tables, depth + 1))
        if _rand_bool(0.5):
            parts.append("ELSE")
            parts.append(self.expr(available_tables, depth + 1))
        parts.append("END")
        return " ".join(_random_keyword_case(p) if p in ("CASE", "WHEN", "THEN", "ELSE", "END") else p for p in parts)

    def cast_expr(self, available_tables, depth):
        typ = random.choice(self.data_types)
        return f"{_random_keyword_case('CAST')}({self.expr(available_tables, depth + 1)} {_random_keyword_case('AS')} {typ})"

    def subquery_expr(self, depth):
        # Wrap a simple SELECT as subquery
        sel = self.select_stmt(depth + 1, force_simple=True)
        return f"({sel})"

    def expr(self, available_tables, depth=0):
        if depth > 3:
            # Limit recursion
            return random.choice([self.literal(), self.column_ref(available_tables)])
        r = random.random()
        if r < 0.20:
            return self.literal()
        elif r < 0.40:
            return self.column_ref(available_tables)
        elif r < 0.55:
            return self.function_call(available_tables, depth)
        elif r < 0.62:
            return self.case_when(available_tables, depth)
        elif r < 0.68:
            return f"({_random_keyword_case('SELECT')} 1)"
        elif r < 0.75:
            # Unary operator
            op = random.choice(self.unary_ops)
            return f"{_random_keyword_case(op)} {self.expr(available_tables, depth + 1)}"
        elif r < 0.90:
            # Binary operation
            left = self.expr(available_tables, depth + 1)
            if _rand_bool(0.5):
                op = random.choice(self.comparators + self.arith_ops + self.bit_ops + self.other_ops)
            else:
                op = random.choice(self.logic_ops)
            right = self.expr(available_tables, depth + 1)
            return f"({left} {op} {right})"
        elif r < 0.96:
            return self.cast_expr(available_tables, depth)
        else:
            # EXISTS subquery
            return f"{_random_keyword_case('EXISTS')} {self.subquery_expr(depth)}"

    def select_list(self, available_tables, depth):
        items = []
        n_items = random.randint(1, 6)
        for _ in range(n_items):
            choice = random.random()
            if choice < 0.15 and available_tables:
                # t.*
                t, alias = random.choice(available_tables)
                qual = alias if alias else t
                items.append(f"{_rand_identifier(qual, quoted_prob=0.1)}.*")
            elif choice < 0.25:
                items.append("*")
            else:
                e = self.expr(available_tables, depth + 1)
                if _rand_bool(0.4):
                    items.append(f"{e} {_random_keyword_case('AS')} {_rand_identifier()}")
                else:
                    items.append(e)
        return ", ".join(items)

    def table_source(self):
        t = random.choice(self.tables)
        alias = None
        if _rand_bool(0.6):
            alias = _rand_identifier("t" + str(random.randint(1, 9)), quoted_prob=0.0)
        return (t, alias)

    def join_clause(self, left_tables):
        # Return join clause string and update available tables
        t, alias = self.table_source()
        join_type = random.choice(self.join_types)
        left_col = self.column_ref(left_tables)
        right_col = self._qualify_col(t, random.choice(self.table_columns[t]), alias=alias)
        cond = f"{left_col} = {right_col}"
        clause = f" {join_type} {_rand_identifier(t, quoted_prob=0.1)}"
        if alias:
            clause += f" {_rand_identifier(alias, quoted_prob=0.0)}"
        clause += f" {_random_keyword_case('ON')} {cond}"
        return clause, (t, alias)

    def group_by_clause(self, available_tables, depth):
        if _rand_bool(0.5):
            return ""
        n = random.randint(1, 3)
        items = []
        for _ in range(n):
            if _rand_bool(0.5):
                items.append(self.column_ref(available_tables))
            else:
                items.append(self.expr(available_tables, depth + 1))
        clause = f" {_random_keyword_case('GROUP BY')} " + ", ".join(items)
        if _rand_bool(0.5):
            clause += f" {_random_keyword_case('HAVING')} {self.expr(available_tables, depth + 1)}"
        return clause

    def order_by_clause(self, available_tables, depth):
        if _rand_bool(0.5):
            return ""
        n = random.randint(1, 3)
        items = []
        for _ in range(n):
            direction = random.choice(self.order_keywords) if _rand_bool(0.6) else ""
            # Use ordinal in ORDER BY sometimes
            if _rand_bool(0.2):
                ord_idx = str(random.randint(1, 5))
                items.append(f"{ord_idx} {direction}".strip())
            else:
                items.append(f"{self.expr(available_tables, depth + 1)} {direction}".strip())
        return f" {_random_keyword_case('ORDER BY')} " + ", ".join(items)

    def limit_offset_clause(self):
        clause = ""
        if _rand_bool(0.6):
            limit = abs(_rand_int(0, 500))
            clause += f" {_random_keyword_case('LIMIT')} {limit}"
        if _rand_bool(0.4):
            offset = abs(_rand_int(0, 500))
            clause += f" {_random_keyword_case('OFFSET')} {offset}"
        return clause

    def cte_clause(self, depth):
        if not _rand_bool(0.25):
            return "", []
        n = random.randint(1, 2)
        names = []
        parts = []
        for i in range(n):
            name = _rand_identifier(f"cte{i+1}", quoted_prob=0.0)
            names.append(name)
            sub = self.select_stmt(depth + 1, force_simple=True)
            parts.append(f"{_rand_identifier(name)} {_random_keyword_case('AS')} ({sub})")
        clause = f"{_random_keyword_case('WITH')} " + ", ".join(parts) + " "
        return clause, names

    def select_stmt(self, depth=0, force_simple=False):
        available_tables = []
        parts = []
        if not force_simple:
            cte, cte_names = self.cte_clause(depth)
            if cte:
                parts.append(cte)
        distinct = f" {_random_keyword_case('DISTINCT')}" if _rand_bool(0.2) else ""
        parts.append(f"{_random_keyword_case('SELECT')}{distinct} ")

        # SELECT list
        # We defer evaluation until FROM is built to provide available tables for expr generation
        # Build FROM
        from_clause = f"{_random_keyword_case('FROM')} "
        t0, alias0 = self.table_source()
        available_tables.append((t0, alias0))
        from_clause += _rand_identifier(t0, quoted_prob=0.1)
        if alias0:
            from_clause += f" {_rand_identifier(alias0, quoted_prob=0.0)}"
        # Joints
        if not force_simple:
            njoins = random.randint(0, 2)
        else:
            njoins = random.randint(0, 1)
        for _ in range(njoins):
            join_str, (t, alias) = self.join_clause(available_tables)
            from_clause += join_str
            available_tables.append((t, alias))

        # SELECT list now that available_tables are defined
        parts.append(self.select_list(available_tables, depth))

        # FROM
        parts.append(" " + from_clause)

        # WHERE
        if _rand_bool(0.7):
            parts.append(f" {_random_keyword_case('WHERE')} {self.expr(available_tables, depth + 1)}")

        # GROUP BY / HAVING
        parts.append(self.group_by_clause(available_tables, depth))

        # ORDER BY
        parts.append(self.order_by_clause(available_tables, depth))

        # LIMIT/OFFSET
        parts.append(self.limit_offset_clause())

        base = "".join(parts).strip()

        # Optional set operations
        if not force_simple and _rand_bool(0.2):
            other = self.select_stmt(depth + 1, force_simple=True)
            op = random.choice(self.set_ops)
            base = f"({base}) {op} ({other})"

        return base

    def create_table_stmt(self):
        t = random.choice(self.tables)
        cols = random.sample(self.table_columns[t], k=min(len(self.table_columns[t]), random.randint(3, 8)))
        parts = []
        for c in cols:
            c_ident = _rand_identifier(c, quoted_prob=0.15)
            typ = random.choice(self.data_types)
            col_def = f"{c_ident} {typ}"
            # Constraints
            if _rand_bool(0.3):
                col_def += " " + _random_keyword_case("NOT NULL")
            if _rand_bool(0.2):
                col_def += " " + _random_keyword_case("UNIQUE")
            if _rand_bool(0.25):
                default_val = self.literal()
                col_def += f" {_random_keyword_case('DEFAULT')} {default_val}"
            parts.append(col_def)
        # Table-level constraints occasionally
        if _rand_bool(0.3):
            pk = random.choice(cols)
            parts.append(f"{_random_keyword_case('PRIMARY KEY')}({_rand_identifier(pk, quoted_prob=0.15)})")
        stmt = f"{_random_keyword_case('CREATE TABLE')} {_rand_identifier(t, quoted_prob=0.1)} (" + ", ".join(parts) + ")"
        return stmt

    def create_index_stmt(self):
        t = random.choice(self.tables)
        cols = random.sample(self.table_columns[t], k=random.randint(1, min(3, len(self.table_columns[t]))))
        idx = random.choice(self.index_names) + "_" + str(random.randint(1, 999))
        unique = _random_keyword_case("UNIQUE") + " " if _rand_bool(0.25) else ""
        cols_sql = ", ".join(_rand_identifier(c, quoted_prob=0.15) for c in cols)
        stmt = f"{_random_keyword_case('CREATE')} {unique}{_random_keyword_case('INDEX')} {_rand_identifier(idx, quoted_prob=0.1)} {_random_keyword_case('ON')} {_rand_identifier(t, quoted_prob=0.1)} ({cols_sql})"
        # Partial index predicate sometimes
        if _rand_bool(0.2):
            stmt += f" {_random_keyword_case('WHERE')} {self.expr([(t, None)], 0)}"
        return stmt

    def insert_stmt(self):
        t = random.choice(self.tables)
        cols = random.sample(self.table_columns[t], k=random.randint(1, min(6, len(self.table_columns[t]))))
        if _rand_bool(0.3):
            # INSERT with SELECT
            sel = self.select_stmt(depth=0, force_simple=True)
            cols_sql = "(" + ", ".join(_rand_identifier(c, quoted_prob=0.15) for c in cols) + ")"
            return f"{_random_keyword_case('INSERT INTO')} {_rand_identifier(t, quoted_prob=0.1)} {cols_sql} {sel}"
        else:
            # INSERT with VALUES
            rows = random.randint(1, 3)
            values = []
            for _ in range(rows):
                vals = []
                for _c in cols:
                    vals.append(self.expr([(t, None)], 0))
                values.append("(" + ", ".join(vals) + ")")
            cols_sql = "(" + ", ".join(_rand_identifier(c, quoted_prob=0.15) for c in cols) + ")"
            return f"{_random_keyword_case('INSERT INTO')} {_rand_identifier(t, quoted_prob=0.1)} {cols_sql} {_random_keyword_case('VALUES')} " + ", ".join(values)

    def update_stmt(self):
        t = random.choice(self.tables)
        cols = random.sample(self.table_columns[t], k=random.randint(1, min(5, len(self.table_columns[t]))))
        assigns = []
        for c in cols:
            assigns.append(f"{_rand_identifier(c, quoted_prob=0.15)} = {self.expr([(t, None)], 0)}")
        stmt = f"{_random_keyword_case('UPDATE')} {_rand_identifier(t, quoted_prob=0.1)} {_random_keyword_case('SET')} " + ", ".join(assigns)
        if _rand_bool(0.7):
            stmt += f" {_random_keyword_case('WHERE')} {self.expr([(t, None)], 0)}"
        return stmt

    def delete_stmt(self):
        t = random.choice(self.tables)
        stmt = f"{_random_keyword_case('DELETE FROM')} {_rand_identifier(t, quoted_prob=0.1)}"
        if _rand_bool(0.7):
            stmt += f" {_random_keyword_case('WHERE')} {self.expr([(t, None)], 0)}"
        return stmt

    def alter_stmt(self):
        t = random.choice(self.tables)
        choice = random.random()
        if choice < 0.4:
            # ADD COLUMN
            new_col = _rand_identifier("col" + str(random.randint(1, 999)), quoted_prob=0.15)
            typ = random.choice(self.data_types)
            return f"{_random_keyword_case('ALTER TABLE')} {_rand_identifier(t, quoted_prob=0.1)} {_random_keyword_case('ADD COLUMN')} {new_col} {typ}"
        elif choice < 0.7:
            # DROP COLUMN
            col = random.choice(self.table_columns[t])
            return f"{_random_keyword_case('ALTER TABLE')} {_rand_identifier(t, quoted_prob=0.1)} {_random_keyword_case('DROP COLUMN')} {_rand_identifier(col, quoted_prob=0.15)}"
        else:
            # RENAME COLUMN
            col = random.choice(self.table_columns[t])
            new_col = _rand_identifier(col + "_renamed", quoted_prob=0.15)
            return f"{_random_keyword_case('ALTER TABLE')} {_rand_identifier(t, quoted_prob=0.1)} {_random_keyword_case('RENAME COLUMN')} {_rand_identifier(col, quoted_prob=0.15)} {_random_keyword_case('TO')} {new_col}"

    def drop_stmt(self):
        if _rand_bool(0.7):
            t = random.choice(self.tables)
            ifexists = _random_keyword_case("IF EXISTS") + " " if _rand_bool(0.5) else ""
            return f"{_random_keyword_case('DROP TABLE')} {ifexists}{_rand_identifier(t, quoted_prob=0.1)}"
        else:
            idx = random.choice(self.index_names) + "_" + str(random.randint(1, 999))
            ifexists = _random_keyword_case("IF EXISTS") + " " if _rand_bool(0.5) else ""
            return f"{_random_keyword_case('DROP INDEX')} {ifexists}{_rand_identifier(idx, quoted_prob=0.1)}"

    def misc_stmt(self):
        # Other statements such as CREATE VIEW, EXPLAIN, BEGIN/COMMIT if supported by tokenizer
        choice = random.random()
        if choice < 0.3:
            # CREATE VIEW AS SELECT
            v = _rand_identifier("v" + str(random.randint(1, 99)), quoted_prob=0.1)
            sel = self.select_stmt(0, force_simple=True)
            return f"{_random_keyword_case('CREATE VIEW')} {v} {_random_keyword_case('AS')} {sel}"
        elif choice < 0.6:
            # EXPLAIN SELECT ...
            sel = self.select_stmt(0, force_simple=False)
            return f"{_random_keyword_case('EXPLAIN')} {sel}"
        else:
            return random.choice([
                _random_keyword_case("BEGIN TRANSACTION"),
                _random_keyword_case("COMMIT"),
                _random_keyword_case("ROLLBACK"),
                _random_keyword_case("VACUUM"),
                _random_keyword_case("ANALYZE")
            ])

    def invalid_stmt(self):
        # Generate intentionally malformed statements to exercise error branches
        patterns = []
        # Missing keywords or typos
        patterns.append("SELEC * FRM " + _rand_identifier(random.choice(self.tables), quoted_prob=0.1))
        # Unbalanced parentheses
        patterns.append("SELECT (" + self.expr([], 0) + " FROM " + _rand_identifier(random.choice(self.tables), quoted_prob=0.1))
        # Trailing comma
        patterns.append("CREATE TABLE " + _rand_identifier(random.choice(self.tables), quoted_prob=0.1) + " (id INT, )")
        # Bad INSERT list
        patterns.append("INSERT INTO " + _rand_identifier(random.choice(self.tables), quoted_prob=0.1) + " VALUES ( , , )")
        # Random tokens
        patterns.append(self.random_token_stream())
        # Bad JOIN
        patterns.append("SELECT * FROM " + _rand_identifier(random.choice(self.tables), quoted_prob=0.1) + " JOIN ON")
        # Incomplete WHERE
        patterns.append("DELETE FROM " + _rand_identifier(random.choice(self.tables), quoted_prob=0.1) + " WHERE")
        return random.choice(patterns)

    def random_token_stream(self, length=None):
        # Create a stream of random tokens to fuzz the tokenizer
        if length is None:
            length = random.randint(10, 30)
        tokens = []
        pool = []
        pool += ["(", ")", ",", ";", ".", "+", "-", "*", "/", "%", "^", "|", "||", "&", "!", "<", ">", "<=", ">=", "=", "!=", "<>"]
        pool += [kw for kw in ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "TABLE", "FROM", "WHERE",
                               "GROUP", "BY", "HAVING", "ORDER", "LIMIT", "OFFSET", "JOIN", "ON", "AS", "IN", "IS", "NULL",
                               "NOT", "AND", "OR", "LIKE", "BETWEEN", "EXISTS", "VALUES", "INTO", "SET"]]
        for _ in range(length):
            kind = random.random()
            if kind < 0.25:
                tokens.append(_rand_identifier())
            elif kind < 0.5:
                tokens.append(str(_rand_int(-1000000, 1000000)))
            elif kind < 0.7:
                tokens.append(_rand_string_literal(10))
            else:
                tokens.append(random.choice(pool))
        # Random spacing/no spacing
        sep_choices = [" ", "  ", "\t", "\n", ""]
        sql = ""
        for i, tok in enumerate(tokens):
            sql += tok
            if i != len(tokens) - 1:
                sql += random.choice(sep_choices)
        return sql

    def maybe_decorate(self, sql):
        # Apply random decorations to stress tokenizer and parser
        if _rand_bool(0.15):
            sql = _maybe_insert_comment(sql)
        if _rand_bool(0.25):
            sql = _maybe_toggle_case(sql, p=0.4)
        if _rand_bool(0.2):
            # Add leading/trailing whitespace or semicolon
            if _rand_bool(0.5):
                sql = " \t " + sql
            if _rand_bool(0.5):
                sql = sql + " ;"
        return sql

    def batch_generate(self):
        # Generate a balanced batch of statements to maximize coverage in one parse_sql call
        stmts = []

        # Numbers tuned to be fast yet diverse
        num_create_table = 60
        num_create_index = 220
        num_select = 1300
        num_insert = 550
        num_update = 320
        num_delete = 320
        num_alter = 180
        num_drop = 180
        num_misc = 120
        num_invalid = 280

        # CREATE TABLE
        for _ in range(num_create_table):
            s = self.create_table_stmt()
            stmts.append(self.maybe_decorate(s))

        # CREATE INDEX
        for _ in range(num_create_index):
            s = self.create_index_stmt()
            stmts.append(self.maybe_decorate(s))

        # SELECT
        for _ in range(num_select):
            s = self.select_stmt()
            stmts.append(self.maybe_decorate(s))

        # INSERT
        for _ in range(num_insert):
            s = self.insert_stmt()
            stmts.append(self.maybe_decorate(s))

        # UPDATE
        for _ in range(num_update):
            s = self.update_stmt()
            stmts.append(self.maybe_decorate(s))

        # DELETE
        for _ in range(num_delete):
            s = self.delete_stmt()
            stmts.append(self.maybe_decorate(s))

        # ALTER
        for _ in range(num_alter):
            s = self.alter_stmt()
            stmts.append(self.maybe_decorate(s))

        # DROP
        for _ in range(num_drop):
            s = self.drop_stmt()
            stmts.append(self.maybe_decorate(s))

        # Miscellaneous
        for _ in range(num_misc):
            s = self.misc_stmt()
            stmts.append(self.maybe_decorate(s))

        # Invalid / token fuzz
        for _ in range(num_invalid):
            s = self.invalid_stmt()
            stmts.append(self.maybe_decorate(s))

        # Shuffle to mix valid/invalid and statement types
        random.shuffle(stmts)
        return stmts

_fuzzer_instance = SQLFuzzer()

def fuzz(parse_sql):
    # Single large batch to maximize efficiency bonus while providing broad coverage
    if _fuzzer_state.get("done"):
        return False
    stmts = _fuzzer_instance.batch_generate()
    parse_sql(stmts)
    _fuzzer_state["done"] = True
    return False
'''
        return {"code": code}