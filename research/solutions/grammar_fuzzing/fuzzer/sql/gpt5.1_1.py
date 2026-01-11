import textwrap


class Solution:
    def solve(self, resources_path: str) -> dict:
        program = textwrap.dedent("""\
            import random
            import string
            import time
            import os
            import re


            class SQLFuzzer:
                def __init__(self):
                    seed = int(time.time() * 1000000.0)
                    try:
                        pid = os.getpid()
                    except Exception:
                        pid = 0
                    seed ^= pid
                    try:
                        seed_bytes = os.urandom(8)
                        seed ^= int.from_bytes(seed_bytes, "little")
                    except Exception:
                        pass
                    self.rnd = random.Random(seed)
                    self.start_time = None
                    self.max_runtime = 50.0
                    self.max_parse_calls = 24
                    self.max_statements_per_call = 500
                    self.max_total_statements = 12000
                    self.parse_calls = 0
                    self.total_generated = 0
                    self.table_names = [
                        "users",
                        "orders",
                        "products",
                        "t",
                        "u",
                        "v",
                        "logs",
                        "tmp",
                        "sessions",
                        "items",
                    ]
                    self.column_names = [
                        "id",
                        "user_id",
                        "order_id",
                        "product_id",
                        "name",
                        "value",
                        "created_at",
                        "updated_at",
                        "status",
                        "price",
                        "qty",
                        "description",
                        "flag",
                        "col1",
                        "col2",
                        "col3",
                    ]
                    self.function_names = [
                        "ABS",
                        "ROUND",
                        "LENGTH",
                        "UPPER",
                        "LOWER",
                        "SUBSTR",
                        "COALESCE",
                        "IFNULL",
                        "RANDOM",
                        "COUNT",
                        "SUM",
                        "MIN",
                        "MAX",
                        "AVG",
                    ]
                    self.type_names = [
                        "INT",
                        "INTEGER",
                        "SMALLINT",
                        "BIGINT",
                        "REAL",
                        "FLOAT",
                        "DOUBLE",
                        "DECIMAL(10,2)",
                        "NUMERIC",
                        "TEXT",
                        "VARCHAR(255)",
                        "CHAR(10)",
                        "BLOB",
                        "BOOLEAN",
                        "DATE",
                        "DATETIME",
                    ]
                    self.predefined_statements = self._build_predefined_statements()
                    self._predefined_index = 0

                def _build_predefined_statements(self):
                    stmts = []
                    # Basic queries
                    stmts.append("SELECT 1")
                    stmts.append("SELECT -1 + 2 * 3")
                    stmts.append("SELECT NULL, TRUE, FALSE, 'text', 1.23, X'ABCD'")
                    stmts.append("SELECT id, name FROM users")
                    stmts.append("SELECT * FROM users")
                    stmts.append("SELECT * FROM orders")
                    stmts.append("SELECT id, name, status FROM users WHERE id = 1")
                    stmts.append("SELECT id FROM users WHERE id IN (1, 2, 3)")
                    stmts.append("SELECT name, COUNT(*) FROM users GROUP BY name HAVING COUNT(*) > 1")
                    stmts.append(
                        "SELECT u.id AS user_id, o.id AS order_id, o.price "
                        "FROM users AS u INNER JOIN orders AS o ON u.id = o.user_id "
                        "WHERE o.price >= 100 ORDER BY o.created_at DESC"
                    )
                    stmts.append(
                        "SELECT id FROM users WHERE id IN (SELECT user_id FROM orders WHERE price > 50)"
                    )
                    stmts.append(
                        "SELECT id FROM users WHERE EXISTS (SELECT 1 FROM orders WHERE orders.user_id = users.id)"
                    )
                    stmts.append("SELECT id FROM users WHERE id BETWEEN 10 AND 20")
                    stmts.append("SELECT id, name FROM users ORDER BY name DESC, id ASC")
                    stmts.append("SELECT DISTINCT status FROM orders")
                    stmts.append("SELECT COALESCE(name, 'unknown') AS nm FROM users")
                    stmts.append(
                        "SELECT CASE WHEN price > 100 THEN 'expensive' ELSE 'cheap' END AS kind FROM products"
                    )
                    # INSERT statements
                    stmts.append(
                        "INSERT INTO users (id, name, status) VALUES (1, 'alice', 'active')"
                    )
                    stmts.append(
                        "INSERT OR REPLACE INTO users (id, name) VALUES (2, 'bob')"
                    )
                    stmts.append(
                        "INSERT INTO orders (id, user_id, price) VALUES (1, 1, 9.99), (2, 1, 19.99)"
                    )
                    # UPDATE / DELETE
                    stmts.append("UPDATE users SET status = 'inactive' WHERE id = 3")
                    stmts.append("UPDATE orders SET price = price * 1.1")
                    stmts.append("DELETE FROM users WHERE id = 4")
                    stmts.append("DELETE FROM orders")
                    # DDL
                    stmts.append(
                        "CREATE TABLE users ("
                        "id INTEGER PRIMARY KEY,"
                        "name TEXT NOT NULL,"
                        "status TEXT DEFAULT 'active'"
                        ")"
                    )
                    stmts.append(
                        "CREATE TABLE orders ("
                        "id INTEGER PRIMARY KEY,"
                        "user_id INTEGER NOT NULL,"
                        "price REAL,"
                        "created_at DATETIME"
                        ")"
                    )
                    stmts.append(
                        "CREATE TABLE products ("
                        "id INTEGER PRIMARY KEY,"
                        "name TEXT,"
                        "price REAL,"
                        "description TEXT"
                        ")"
                    )
                    stmts.append(
                        "CREATE INDEX idx_orders_user_id ON orders (user_id)"
                    )
                    stmts.append(
                        "CREATE UNIQUE INDEX idx_users_name ON users (name)"
                    )
                    stmts.append("ALTER TABLE users ADD COLUMN email TEXT")
                    stmts.append("ALTER TABLE orders RENAME TO orders_archive")
                    stmts.append("DROP TABLE IF EXISTS tmp")
                    stmts.append("DROP INDEX IF EXISTS idx_old")
                    # Views / temp tables
                    stmts.append(
                        "CREATE VIEW active_users AS "
                        "SELECT id, name FROM users WHERE status = 'active'"
                    )
                    stmts.append(
                        "CREATE TEMP TABLE temp_items (id INT, value TEXT)"
                    )
                    stmts.append("SELECT * FROM temp_items")
                    # Pragmas / meta
                    stmts.append("PRAGMA cache_size = 2000")
                    stmts.append("PRAGMA foreign_keys = ON")
                    # Simple transactions
                    stmts.append("BEGIN TRANSACTION")
                    stmts.append("COMMIT")
                    stmts.append("ROLLBACK")
                    return stmts

                # Utility generators

                def random_simple_name(self):
                    length = self.rnd.randint(1, 8)
                    first = self.rnd.choice(string.ascii_letters + "_")
                    rest_chars = string.ascii_letters + string.digits + "_"
                    name = first + "".join(self.rnd.choice(rest_chars) for _ in range(length - 1))
                    return name

                def random_identifier(self):
                    if self.rnd.random() < 0.5:
                        base = self.rnd.choice(
                            self.table_names + self.column_names + ["x", "y", "z"]
                        )
                    else:
                        base = self.random_simple_name()
                    r = self.rnd.random()
                    if r < 0.15:
                        return '"' + base.replace('"', '""') + '"'
                    elif r < 0.25:
                        return "[" + base.replace("]", "]]") + "]"
                    elif r < 0.35:
                        return "`" + base.replace("`", "``") + "`"
                    else:
                        return base

                def random_table_name(self):
                    if self.table_names and self.rnd.random() < 0.8:
                        return self.rnd.choice(self.table_names)
                    name = "t" + self.random_simple_name()
                    self.table_names.append(name)
                    return name

                def random_column_name(self):
                    if self.column_names and self.rnd.random() < 0.8:
                        return self.rnd.choice(self.column_names)
                    name = "c" + self.random_simple_name()
                    self.column_names.append(name)
                    return name

                def random_literal(self):
                    r = self.rnd.random()
                    if r < 0.22:
                        return str(self.rnd.randint(-100000, 100000))
                    elif r < 0.44:
                        int_part = str(self.rnd.randint(0, 100000))
                        frac_part = str(self.rnd.randint(0, 100000))
                        return int_part + "." + frac_part
                    elif r < 0.66:
                        length = self.rnd.randint(0, 10)
                        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-"
                        s = "".join(self.rnd.choice(chars) for _ in range(length))
                        s = s.replace("'", "''")
                        return "'" + s + "'"
                    elif r < 0.76:
                        return "NULL"
                    elif r < 0.86:
                        return "TRUE"
                    elif r < 0.96:
                        return "FALSE"
                    else:
                        hex_len = self.rnd.randint(1, 8)
                        hx = "".join(self.rnd.choice("0123456789ABCDEF") for _ in range(hex_len))
                        return "X'" + hx + "'"

                def random_column_ref(self):
                    col = self.random_column_name()
                    if self.rnd.random() < 0.6:
                        tbl = self.random_table_name()
                        return tbl + "." + col
                    return col

                def random_function_call(self, depth):
                    name = self.rnd.choice(self.function_names)
                    max_args = 3
                    arg_count = self.rnd.randint(0, max_args)
                    args = []
                    for _ in range(arg_count):
                        args.append(self.random_expr(depth + 1))
                    if not args and self.rnd.random() < 0.5:
                        args = [self.random_simple_expr()]
                    if name.upper() in ("COUNT", "SUM", "MIN", "MAX", "AVG") and args and self.rnd.random() < 0.3:
                        arg_str = "DISTINCT " + args[0]
                    else:
                        arg_str = ", ".join(args)
                    return name + "(" + arg_str + ")"

                def random_simple_expr(self):
                    r = self.rnd.random()
                    if r < 0.4:
                        return self.random_column_ref()
                    elif r < 0.75:
                        return self.random_literal()
                    elif r < 0.85:
                        return "?" + str(self.rnd.randint(1, 8))
                    else:
                        return self.random_function_call(0)

                def random_expr(self, depth=0):
                    if depth >= 3:
                        return self.random_simple_expr()
                    r = self.rnd.random()
                    if r < 0.3:
                        return self.random_simple_expr()
                    elif r < 0.55:
                        left = self.random_expr(depth + 1)
                        right = self.random_expr(depth + 1)
                        op = self.rnd.choice(["+", "-", "*", "/", "%", "||"])
                        return "(" + left + " " + op + " " + right + ")"
                    elif r < 0.75:
                        left = self.random_expr(depth + 1)
                        right = self.random_expr(depth + 1)
                        op = self.rnd.choice(["=", "<>", "!=", "<", "<=", ">", ">="])
                        return "(" + left + " " + op + " " + right + ")"
                    elif r < 0.85:
                        inner = self.random_expr(depth + 1)
                        if self.rnd.random() < 0.5:
                            return "(-" + inner + ")"
                        else:
                            return "(NOT " + inner + ")"
                    elif r < 0.93:
                        return self.random_function_call(depth + 1)
                    else:
                        parts = []
                        when_count = self.rnd.randint(1, 3)
                        for _ in range(when_count):
                            cond = self.random_condition(depth + 1)
                            res = self.random_expr(depth + 1)
                            parts.append("WHEN " + cond + " THEN " + res)
                        else_expr = self.random_expr(depth + 1)
                        base_expr = ""
                        if self.rnd.random() < 0.3:
                            base_expr = " " + self.random_expr(depth + 1)
                        return "(CASE" + base_expr + " " + " ".join(parts) + " ELSE " + else_expr + " END)"

                def random_condition(self, depth=0):
                    if depth >= 3:
                        left = self.random_expr(depth + 1)
                        op = self.rnd.choice(["=", "<>", "!=", "<", "<=", ">", ">=", "IS", "IS NOT"])
                        if op in ("IS", "IS NOT"):
                            right = self.rnd.choice(["NULL", "TRUE", "FALSE"])
                        else:
                            right = self.random_expr(depth + 1)
                        return left + " " + op + " " + right
                    r = self.rnd.random()
                    if r < 0.4:
                        left = self.random_expr(depth + 1)
                        op = self.rnd.choice(["=", "<>", "!=", "<", "<=", ">", ">="])
                        right = self.random_expr(depth + 1)
                        return left + " " + op + " " + right
                    elif r < 0.7:
                        expr = self.random_expr(depth + 1)
                        if self.rnd.random() < 0.5:
                            low = self.random_expr(depth + 1)
                            high = self.random_expr(depth + 1)
                            not_str = "NOT " if self.rnd.random() < 0.3 else ""
                            return expr + " " + not_str + "BETWEEN " + low + " AND " + high
                        else:
                            not_str = "NOT " if self.rnd.random() < 0.3 else ""
                            if self.rnd.random() < 0.4 and depth < 2:
                                sub = self.random_select(depth + 1, allow_complex=False)
                                return expr + " " + not_str + "IN (" + sub + ")"
                            else:
                                count = self.rnd.randint(1, 4)
                                items = [self.random_expr(depth + 1) for _ in range(count)]
                                return expr + " " + not_str + "IN (" + ", ".join(items) + ")"
                    else:
                        left = self.random_condition(depth + 1)
                        right = self.random_condition(depth + 1)
                        op = self.rnd.choice(["AND", "OR"])
                        return "(" + left + " " + op + " " + right + ")"

                def random_table_or_subquery(self, depth):
                    if depth < 2 and self.rnd.random() < 0.3:
                        sub = self.random_select(depth + 1, allow_complex=False)
                        alias = self.random_identifier()
                        return "(" + sub + ") AS " + alias
                    else:
                        name = self.random_table_name()
                        alias = ""
                        if self.rnd.random() < 0.5:
                            alias = " AS " + self.random_identifier()
                        return name + alias

                def random_from_clause(self, depth):
                    if depth >= 2 or self.rnd.random() < 0.5:
                        return self.random_table_or_subquery(depth)
                    else:
                        left = self.random_table_or_subquery(depth)
                        right = self.random_table_or_subquery(depth)
                        join_type = self.rnd.choice(
                            ["JOIN", "INNER JOIN", "LEFT JOIN", "LEFT OUTER JOIN", "CROSS JOIN"]
                        )
                        sql = left + " " + join_type + " " + right
                        choice = self.rnd.random()
                        if choice < 0.6:
                            cond = self.random_condition(depth + 1)
                            sql += " ON " + cond
                        elif choice < 0.8:
                            col = self.random_column_name()
                            sql += " USING (" + col + ")"
                        return sql

                def random_select(self, depth=0, allow_complex=True):
                    distinct = ""
                    r = self.rnd.random()
                    if r < 0.3:
                        distinct = "DISTINCT "
                    elif r < 0.4:
                        distinct = "ALL "
                    col_count = self.rnd.randint(1, 4)
                    cols = []
                    for _ in range(col_count):
                        if self.rnd.random() < 0.2:
                            expr = "*"
                        else:
                            expr = self.random_expr(depth + 1)
                        if self.rnd.random() < 0.3:
                            alias = self.random_identifier()
                            expr = expr + " AS " + alias
                        cols.append(expr)
                    sql = "SELECT " + distinct + ", ".join(cols)
                    if self.rnd.random() < 0.85:
                        from_clause = self.random_from_clause(depth)
                        sql += " FROM " + from_clause
                    if self.rnd.random() < 0.7:
                        cond = self.random_condition(depth + 1)
                        sql += " WHERE " + cond
                    if self.rnd.random() < 0.5:
                        group_count = self.rnd.randint(1, 3)
                        groups = [self.random_expr(depth + 1) for _ in range(group_count)]
                        sql += " GROUP BY " + ", ".join(groups)
                        if self.rnd.random() < 0.5:
                            having = self.random_condition(depth + 1)
                            sql += " HAVING " + having
                    if self.rnd.random() < 0.7:
                        order_count = self.rnd.randint(1, 3)
                        orders = []
                        for _ in range(order_count):
                            expr = self.random_expr(depth + 1)
                            direction = self.rnd.choice(["", " ASC", " DESC"])
                            orders.append(expr + direction)
                        sql += " ORDER BY " + ", ".join(orders)
                    if self.rnd.random() < 0.5:
                        limit = str(self.rnd.randint(0, 1000))
                        if self.rnd.random() < 0.5:
                            offset = str(self.rnd.randint(0, 1000))
                            if self.rnd.random() < 0.5:
                                sql += " LIMIT " + limit + " OFFSET " + offset
                            else:
                                sql += " LIMIT " + offset + ", " + limit
                        else:
                            sql += " LIMIT " + limit
                    if allow_complex and depth < 2 and self.rnd.random() < 0.3:
                        op = self.rnd.choice(["UNION", "UNION ALL", "INTERSECT", "EXCEPT"])
                        rhs = self.random_select(depth + 1, allow_complex=False)
                        sql = "(" + sql + ") " + op + " (" + rhs + ")"
                    return sql

                # Statement generators

                def gen_create_table(self):
                    table_name = self.random_table_name()
                    col_count = self.rnd.randint(1, 6)
                    cols_sql = []
                    local_cols = []
                    for _ in range(col_count):
                        col_name = self.random_column_name()
                        local_cols.append(col_name)
                        type_name = self.rnd.choice(self.type_names)
                        col_def = col_name + " " + type_name
                        if self.rnd.random() < 0.3:
                            col_def += " PRIMARY KEY"
                            if self.rnd.random() < 0.3:
                                col_def += " AUTOINCREMENT"
                        if self.rnd.random() < 0.4:
                            col_def += " NOT NULL"
                        if self.rnd.random() < 0.3:
                            col_def += " UNIQUE"
                        if self.rnd.random() < 0.4:
                            col_def += " DEFAULT " + self.random_literal()
                        if self.rnd.random() < 0.2:
                            check = self.random_condition(0)
                            col_def += " CHECK (" + check + ")"
                        cols_sql.append(col_def)
                    if len(local_cols) >= 2 and self.rnd.random() < 0.5:
                        subset = self.rnd.sample(local_cols, 2)
                        cols_sql.append("PRIMARY KEY (" + ", ".join(subset) + ")")
                    if len(local_cols) >= 2 and self.rnd.random() < 0.4:
                        subset = self.rnd.sample(local_cols, 2)
                        cols_sql.append("UNIQUE (" + ", ".join(subset) + ")")
                    if len(local_cols) >= 1 and self.rnd.random() < 0.3:
                        ref_table = self.random_table_name()
                        ref_col = self.random_column_name()
                        fk_col = self.rnd.choice(local_cols)
                        fk = "FOREIGN KEY (" + fk_col + ") REFERENCES " + ref_table + "(" + ref_col + ")"
                        if self.rnd.random() < 0.5:
                            fk += " ON DELETE " + self.rnd.choice(
                                ["CASCADE", "SET NULL", "SET DEFAULT", "RESTRICT", "NO ACTION"]
                            )
                        cols_sql.append(fk)
                    body = ", ".join(cols_sql)
                    prefix = "CREATE "
                    if self.rnd.random() < 0.25:
                        prefix += "TEMP "
                    prefix += "TABLE "
                    if self.rnd.random() < 0.4:
                        prefix += "IF NOT EXISTS "
                    sql = prefix + table_name + " (" + body + ")"
                    if self.rnd.random() < 0.15:
                        sql += " WITHOUT ROWID"
                    return sql

                def gen_create_index(self):
                    table_name = self.random_table_name()
                    index_name = "idx_" + self.random_simple_name()
                    col_count = self.rnd.randint(1, 3)
                    cols = []
                    for _ in range(col_count):
                        col = self.random_column_name()
                        direction = self.rnd.choice(["", " ASC", " DESC"])
                        cols.append(col + direction)
                    col_list = ", ".join(cols)
                    prefix = "CREATE "
                    if self.rnd.random() < 0.3:
                        prefix += "UNIQUE "
                    prefix += "INDEX "
                    if self.rnd.random() < 0.4:
                        prefix += "IF NOT EXISTS "
                    sql = prefix + index_name + " ON " + table_name + " (" + col_list + ")"
                    return sql

                def gen_insert(self):
                    table = self.random_table_name()
                    num_cols = self.rnd.randint(1, min(5, max(1, len(self.column_names))))
                    cols = self.rnd.sample(self.column_names, num_cols)
                    col_part = ""
                    if self.rnd.random() < 0.8:
                        col_part = "(" + ", ".join(cols) + ")"
                    conflict = ""
                    if self.rnd.random() < 0.3:
                        conflict = " OR " + self.rnd.choice(
                            ["ROLLBACK", "ABORT", "REPLACE", "FAIL", "IGNORE"]
                        )
                    if self.rnd.random() < 0.4:
                        sub = self.random_select(0)
                        values_part = sub
                    else:
                        row_count = 1
                        if num_cols > 1 and self.rnd.random() < 0.5:
                            row_count = self.rnd.randint(1, 3)
                        rows = []
                        for _ in range(row_count):
                            vals = [self.random_expr(0) for _ in range(num_cols)]
                            rows.append("(" + ", ".join(vals) + ")")
                        values_part = "VALUES " + ", ".join(rows)
                    sql = "INSERT" + conflict + " INTO " + table + " " + col_part + " " + values_part
                    return sql.strip()

                def gen_update(self):
                    table = self.random_table_name()
                    set_count = self.rnd.randint(1, 4)
                    pairs = []
                    for _ in range(set_count):
                        col = self.random_column_name()
                        expr = self.random_expr(0)
                        pairs.append(col + " = " + expr)
                    sql = "UPDATE " + table + " SET " + ", ".join(pairs)
                    if self.rnd.random() < 0.7:
                        cond = self.random_condition(0)
                        sql += " WHERE " + cond
                    return sql

                def gen_delete(self):
                    table = self.random_table_name()
                    sql = "DELETE FROM " + table
                    if self.rnd.random() < 0.7:
                        cond = self.random_condition(0)
                        sql += " WHERE " + cond
                    return sql

                def gen_drop(self):
                    kind = self.rnd.choice(["TABLE", "INDEX", "VIEW", "TRIGGER"])
                    name = self.random_identifier()
                    prefix = "DROP "
                    if self.rnd.random() < 0.4:
                        prefix += "IF EXISTS "
                    sql = prefix + kind + " " + name
                    return sql

                def gen_alter_table(self):
                    table = self.random_table_name()
                    action = self.rnd.random()
                    if action < 0.33:
                        new_name = table + "_" + self.random_simple_name()
                        if new_name not in self.table_names:
                            self.table_names.append(new_name)
                        return "ALTER TABLE " + table + " RENAME TO " + new_name
                    elif action < 0.66:
                        col_name = self.random_column_name()
                        type_name = self.rnd.choice(self.type_names)
                        return "ALTER TABLE " + table + " ADD COLUMN " + col_name + " " + type_name
                    else:
                        old_col = self.random_column_name()
                        new_col = old_col + "_" + self.random_simple_name()
                        if new_col not in self.column_names:
                            self.column_names.append(new_col)
                        return (
                            "ALTER TABLE " + table + " RENAME COLUMN " + old_col + " TO " + new_col
                        )

                def gen_transaction(self):
                    choice = self.rnd.random()
                    if choice < 0.25:
                        return "BEGIN TRANSACTION"
                    elif choice < 0.5:
                        return "COMMIT"
                    elif choice < 0.75:
                        return "ROLLBACK"
                    else:
                        name = self.random_simple_name()
                        if self.rnd.random() < 0.5:
                            return "SAVEPOINT " + name
                        else:
                            return "RELEASE " + name

                def gen_pragma_or_set(self):
                    if self.rnd.random() < 0.5:
                        name = self.random_simple_name()
                        value = self.random_literal()
                        return "PRAGMA " + name + " = " + value
                    else:
                        name = self.random_simple_name()
                        value = self.random_literal()
                        return "SET " + name + " = " + value

                def gen_noise(self):
                    base_choices = [
                        ";",
                        "(",
                        ")",
                        ",",
                        "SELECT",
                        "INSERT INTO",
                        "CREATE TABLE (",
                        "'\"'",
                        "--",
                        "/* unclosed comment",
                    ]
                    if self.rnd.random() < 0.5:
                        length = self.rnd.randint(1, 40)
                        chars = "".join(ch for ch in string.printable if ch not in "\\n\\r")
                        s = "".join(self.rnd.choice(chars) for _ in range(length))
                        return s
                    else:
                        return self.rnd.choice(base_choices)

                def wrap_with_comments(self, sql):
                    prefix = ""
                    suffix = ""
                    r = self.rnd.random()
                    if r < 0.25:
                        prefix = "-- " + self.random_simple_name() + " comment\\n"
                    elif r < 0.45:
                        prefix = "/* " + self.random_simple_name() + " */ "
                    r2 = self.rnd.random()
                    if r2 < 0.25:
                        suffix = " -- " + self.random_simple_name()
                    elif r2 < 0.45:
                        suffix = " /* end */"
                    if self.rnd.random() < 0.3:
                        suffix += ";"
                    return prefix + sql + suffix

                def random_statement(self):
                    r = self.rnd.random()
                    if r < 0.3:
                        sql = self.random_select(0)
                    elif r < 0.45:
                        sql = self.gen_insert()
                    elif r < 0.6:
                        sql = self.gen_update()
                    elif r < 0.7:
                        sql = self.gen_delete()
                    elif r < 0.8:
                        sql = self.gen_create_table()
                    elif r < 0.86:
                        sql = self.gen_create_index()
                    elif r < 0.9:
                        sql = self.gen_alter_table()
                    elif r < 0.95:
                        sql = self.gen_drop()
                    else:
                        if self.rnd.random() < 0.5:
                            sql = self.gen_pragma_or_set()
                        else:
                            sql = self.gen_transaction()
                    if self.rnd.random() < 0.15:
                        sql = self.gen_noise()
                    return self.wrap_with_comments(sql)

                def generate_batch(self, target_size):
                    result = []
                    while len(result) < target_size and self.total_generated < self.max_total_statements:
                        if self._predefined_index < len(self.predefined_statements):
                            sql = self.predefined_statements[self._predefined_index]
                            self._predefined_index += 1
                            if self.rnd.random() < 0.7:
                                sql = self.wrap_with_comments(sql)
                        else:
                            sql = self.random_statement()
                        result.append(sql)
                        self.total_generated += 1
                    return result


            _state = None


            def _get_state():
                global _state
                if _state is None:
                    _state = SQLFuzzer()
                return _state


            def fuzz(parse_sql):
                state = _get_state()
                if state.start_time is None:
                    state.start_time = time.time()
                if state.parse_calls >= state.max_parse_calls:
                    return False
                if time.time() - state.start_time > state.max_runtime:
                    return False
                while state.parse_calls < state.max_parse_calls:
                    now = time.time()
                    if now - state.start_time > state.max_runtime:
                        break
                    batch = state.generate_batch(state.max_statements_per_call)
                    if not batch:
                        break
                    parse_sql(batch)
                    state.parse_calls += 1
                return False
        """)
        return {"code": program}