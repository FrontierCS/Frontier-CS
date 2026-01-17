import os
import sys
import re
import inspect
import random
import textwrap


class Solution:
    def solve(self, resources_path: str) -> dict:
        default_keywords = [
            "SELECT", "INSERT", "UPDATE", "DELETE",
            "CREATE", "ALTER", "DROP", "TABLE", "INDEX", "VIEW", "TRIGGER",
            "FROM", "WHERE", "GROUP", "BY", "HAVING", "ORDER", "LIMIT", "OFFSET",
            "JOIN", "INNER", "LEFT", "RIGHT", "FULL", "OUTER", "CROSS", "ON",
            "VALUES", "INTO", "SET", "AS",
            "AND", "OR", "NOT",
            "NULL", "IS", "IN", "EXISTS",
            "DISTINCT", "UNION", "ALL",
            "CASE", "WHEN", "THEN", "ELSE", "END",
            "PRIMARY", "KEY", "FOREIGN", "REFERENCES",
            "DEFAULT", "CHECK", "UNIQUE",
            "IF", "EXISTS",
            "BETWEEN", "LIKE",
            "BEGIN", "TRANSACTION", "COMMIT", "ROLLBACK"
        ]

        kw_set = set()

        # Try to import tokenizer to extract real keyword set
        engine_dir = os.path.join(resources_path, "sql_engine")
        target_tokenizer = None
        if os.path.isdir(engine_dir):
            if resources_path not in sys.path:
                sys.path.insert(0, resources_path)
            try:
                from sql_engine import tokenizer as target_tokenizer  # type: ignore
            except Exception:
                target_tokenizer = None

        if target_tokenizer is not None:
            for attr_name in dir(target_tokenizer):
                if "KEYWORD" in attr_name.upper():
                    try:
                        val = getattr(target_tokenizer, attr_name)
                    except Exception:
                        continue
                    if isinstance(val, dict):
                        for k in val.keys():
                            if isinstance(k, str) and len(k) >= 2 and k.isupper():
                                kw_set.add(k)
                    elif isinstance(val, (list, tuple, set)):
                        for k in val:
                            if isinstance(k, str) and len(k) >= 2 and k.isupper():
                                kw_set.add(k)
            try:
                src = inspect.getsource(target_tokenizer)
            except Exception:
                src = ""
            if src:
                for m in re.findall(r"'([A-Z]{2,})'", src):
                    kw_set.add(m)
                for m in re.findall(r'"([A-Z]{2,})"', src):
                    kw_set.add(m)

        # Also inspect grammar file if present
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        if os.path.exists(grammar_path):
            try:
                with open(grammar_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                for m in re.findall(r"\b[A-Z]{2,}\b", text):
                    kw_set.add(m)
            except Exception:
                pass

        if kw_set:
            kw_list = sorted(kw_set)
            max_keywords = 400
            if len(kw_list) > max_keywords:
                random.seed(0)
                kw_list = sorted(random.sample(kw_list, max_keywords))
            keywords = kw_list
        else:
            keywords = default_keywords

        code_template = textwrap.dedent(
            """\
            import random
            import string
            import time

            KEYWORDS = {keywords_literal}

            SQL_TYPES = ['INT', 'INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT', 'TEXT', 'VARCHAR(10)', 'VARCHAR(255)', 'CHAR(20)', 'REAL', 'DOUBLE', 'FLOAT', 'NUMERIC', 'DECIMAL(10,2)', 'DATE', 'TIME', 'TIMESTAMP', 'BOOLEAN']
            FUNCTION_NAMES = ['ABS', 'LOWER', 'UPPER', 'ROUND', 'LENGTH', 'SUBSTR', 'SUBSTRING', 'COALESCE', 'IFNULL', 'NULLIF', 'MAX', 'MIN', 'SUM', 'AVG', 'COUNT', 'RANDOM', 'RAND']
            ARITH_OPS = ['+', '-', '*', '/', '%']
            COMPARISON_OPS = ['=', '<>', '!=', '<', '>', '<=', '>=']
            LOGICAL_OPS = ['AND', 'OR']
            ORDER_DIR = ['ASC', 'DESC']
            JOIN_TYPES = ['JOIN', 'INNER JOIN', 'LEFT JOIN', 'LEFT OUTER JOIN', 'RIGHT JOIN', 'RIGHT OUTER JOIN', 'FULL JOIN', 'FULL OUTER JOIN', 'CROSS JOIN']

            class FuzzerState:
                def __init__(self):
                    self.iteration = 0
                    self.rand = random.Random(123456789)
                    self.known_tables = ['t', 'users', 'orders', 'products', 'a', 'b']
                    self.known_columns = ['id', 'col1', 'col2', 'col3', 'name', 'value', 'x', 'y', 'z', 'created_at', 'updated_at']
                    self.batch_size = 200
                    self.max_depth = 3
                    self.start_time = time.time()

                def new_table_name(self):
                    name = 't_' + ''.join(self.rand.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(6))
                    self.known_tables.append(name)
                    return name

            STATE = FuzzerState()

            def rand_identifier(state):
                r = state.rand
                length = r.randint(1, 10)
                first = r.choice(string.ascii_letters + '_')
                rest = ''.join(r.choice(string.ascii_letters + string.digits + '_$') for _ in range(max(0, length - 1)))
                ident = first + rest
                if r.random() < 0.1:
                    return '\"' + ident + '\"'
                return ident

            def rand_string_literal(state):
                r = state.rand
                length = r.randint(0, 20)
                chars = string.ascii_letters + string.digits + ' _-!@#$/\\\\'
                s = ''.join(r.choice(chars) for _ in range(length))
                s = s.replace("'", "''")
                return "'" + s + "'"

            def rand_numeric_literal(state):
                r = state.rand
                if r.random() < 0.5:
                    return str(r.randint(-2147483648, 2147483647))
                else:
                    # limit decimal places
                    val = r.uniform(-100000.0, 100000.0)
                    return str(round(val, r.randint(0, 6)))

            def rand_literal(state):
                r = state.rand
                choice = r.random()
                if choice < 0.4:
                    return rand_numeric_literal(state)
                elif choice < 0.8:
                    return rand_string_literal(state)
                elif choice < 0.9:
                    return 'NULL'
                else:
                    return r.choice(['TRUE', 'FALSE'])

            def random_table_name(state):
                r = state.rand
                if state.known_tables and r.random() < 0.8:
                    return r.choice(state.known_tables)
                return state.new_table_name()

            def random_column_name(state):
                r = state.rand
                if state.known_columns and r.random() < 0.8:
                    return r.choice(state.known_columns)
                name = rand_identifier(state)
                state.known_columns.append(name)
                return name

            def gen_expr(state, depth):
                r = state.rand
                if depth <= 0:
                    base_choice = r.random()
                    if base_choice < 0.4:
                        return random_column_name(state)
                    elif base_choice < 0.8:
                        return rand_literal(state)
                    else:
                        return '(' + rand_literal(state) + ')'
                choice = r.random()
                if choice < 0.3:
                    return random_column_name(state)
                elif choice < 0.6:
                    left = gen_expr(state, depth - 1)
                    right = gen_expr(state, depth - 1)
                    op = r.choice(ARITH_OPS)
                    return '(' + left + ' ' + op + ' ' + right + ')'
                elif choice < 0.8:
                    func = r.choice(FUNCTION_NAMES)
                    argc = r.randint(1, 3)
                    args = ', '.join(gen_expr(state, depth - 1) for _ in range(argc))
                    return func + '(' + args + ')'
                else:
                    # CASE expression
                    n_when = r.randint(1, 3)
                    parts = ['CASE']
                    for _ in range(n_when):
                        cond = gen_condition(state, max(0, depth - 1))
                        val = gen_expr(state, depth - 1)
                        parts.append('WHEN ' + cond + ' THEN ' + val)
                    if r.random() < 0.5:
                        parts.append('ELSE ' + gen_expr(state, depth - 1))
                    parts.append('END')
                    return ' '.join(parts)

            def gen_simple_condition(state, depth):
                r = state.rand
                expr_depth = max(0, depth - 1)
                left = gen_expr(state, expr_depth)
                t = r.random()
                if t < 0.4:
                    op = r.choice(COMPARISON_OPS)
                    right = gen_expr(state, expr_depth)
                    return left + ' ' + op + ' ' + right
                elif t < 0.6:
                    neg = ' NOT' if r.random() < 0.5 else ''
                    return left + ' IS' + neg + ' NULL'
                elif t < 0.8:
                    pattern = rand_string_literal(state)
                    return left + ' LIKE ' + pattern
                elif t < 0.9 and depth > 0:
                    count = r.randint(1, 5)
                    items = ', '.join(gen_expr(state, expr_depth) for _ in range(count))
                    return left + ' IN (' + items + ')'
                elif depth > 0:
                    sub = gen_select(state, depth - 1, allow_order=False)
                    return left + ' IN (' + sub + ')'
                else:
                    # Fallback simple comparison
                    op = r.choice(COMPARISON_OPS)
                    right = gen_expr(state, expr_depth)
                    return left + ' ' + op + ' ' + right

            def gen_condition(state, depth):
                r = state.rand
                if depth <= 0:
                    return gen_simple_condition(state, depth)
                if r.random() < 0.6:
                    left = gen_condition(state, depth - 1)
                    right = gen_condition(state, depth - 1)
                    op = r.choice(LOGICAL_OPS)
                    return '(' + left + ' ' + op + ' ' + right + ')'
                else:
                    return gen_simple_condition(state, depth - 1)

            def gen_select_list(state, depth):
                r = state.rand
                cols = []
                if r.random() < 0.2:
                    # wildcard
                    if state.known_tables and r.random() < 0.5:
                        cols.append(r.choice(state.known_tables) + '.*')
                    else:
                        cols.append('*')
                else:
                    count = r.randint(1, 5)
                    for _ in range(count):
                        expr = gen_expr(state, depth)
                        if r.random() < 0.4:
                            alias = rand_identifier(state)
                            if r.random() < 0.5:
                                expr += ' AS ' + alias
                            else:
                                expr += ' ' + alias
                        cols.append(expr)
                return ', '.join(cols)

            def gen_table_factor(state, depth):
                r = state.rand
                if depth <= 0 or r.random() < 0.5:
                    name = random_table_name(state)
                    if r.random() < 0.5:
                        alias = rand_identifier(state)
                        return name + ' AS ' + alias
                    return name
                # subquery in FROM
                sub = gen_select(state, depth - 1, allow_order=False)
                alias = rand_identifier(state)
                return '(' + sub + ') AS ' + alias

            def gen_from_clause(state, depth):
                r = state.rand
                base = gen_table_factor(state, depth)
                # maybe add joins
                join_count = 0
                while depth > 0 and join_count < 3 and r.random() < 0.5:
                    join_type = r.choice(JOIN_TYPES)
                    right = gen_table_factor(state, depth - 1)
                    cond = gen_condition(state, depth - 1)
                    base = base + ' ' + join_type + ' ' + right + ' ON ' + cond
                    join_count += 1
                return base

            def gen_select(state, depth, allow_order=True):
                r = state.rand
                if depth < 0:
                    depth = 0
                distinct_part = ''
                if r.random() < 0.3:
                    distinct_part = ' DISTINCT'
                sql = 'SELECT' + distinct_part + ' ' + gen_select_list(state, depth)
                if r.random() < 0.9:
                    sql += ' FROM ' + gen_from_clause(state, depth)
                if r.random() < 0.6:
                    sql += ' WHERE ' + gen_condition(state, depth)
                if r.random() < 0.4:
                    # GROUP BY
                    count = r.randint(1, 3)
                    group_exprs = ', '.join(gen_expr(state, max(0, depth - 1)) for _ in range(count))
                    sql += ' GROUP BY ' + group_exprs
                    if r.random() < 0.5:
                        sql += ' HAVING ' + gen_condition(state, max(0, depth - 1))
                if allow_order and r.random() < 0.5:
                    count = r.randint(1, 3)
                    items = []
                    for _ in range(count):
                        expr = gen_expr(state, max(0, depth - 1))
                        if r.random() < 0.8:
                            expr += ' ' + r.choice(ORDER_DIR)
                        items.append(expr)
                    sql += ' ORDER BY ' + ', '.join(items)
                if allow_order and r.random() < 0.4:
                    sql += ' LIMIT ' + str(r.randint(0, 1000))
                    if r.random() < 0.5:
                        sql += ' OFFSET ' + str(r.randint(0, 1000))
                # maybe UNION / INTERSECT / EXCEPT
                if allow_order and depth > 0 and r.random() < 0.3:
                    op = r.choice(['UNION', 'UNION ALL', 'INTERSECT', 'EXCEPT'])
                    right = gen_select(state, depth - 1, allow_order=True)
                    sql = sql + ' ' + op + ' ' + right
                return sql

            def gen_create_table(state):
                r = state.rand
                table = state.new_table_name()
                temp = ''
                if r.random() < 0.2:
                    temp = ' TEMPORARY'
                sql = 'CREATE' + temp + ' TABLE '
                if r.random() < 0.2:
                    sql += 'IF NOT EXISTS '
                sql += table + ' ('
                col_defs = []
                ncols = r.randint(1, 6)
                col_names = []
                for _ in range(ncols):
                    col_name = rand_identifier(state)
                    col_names.append(col_name)
                    state.known_columns.append(col_name)
                    col_type = r.choice(SQL_TYPES)
                    parts = [col_name, col_type]
                    if r.random() < 0.3:
                        parts.append('PRIMARY KEY')
                    if r.random() < 0.3:
                        parts.append('NOT NULL')
                    if r.random() < 0.2:
                        parts.append('UNIQUE')
                    if r.random() < 0.2:
                        parts.append('DEFAULT ' + rand_literal(state))
                    col_defs.append(' '.join(parts))
                # optional table-level primary key
                if r.random() < 0.3 and col_names:
                    k = r.randint(1, min(3, len(col_names)))
                    pk_cols = r.sample(col_names, k)
                    col_defs.append('PRIMARY KEY (' + ', '.join(pk_cols) + ')')
                sql += ', '.join(col_defs) + ')'
                return sql

            def gen_insert(state, depth):
                r = state.rand
                table = random_table_name(state)
                sql = 'INSERT INTO ' + table
                use_cols = bool(state.known_columns) and r.random() < 0.7
                if use_cols:
                    ncols = r.randint(1, min(5, len(state.known_columns)))
                    cols = r.sample(state.known_columns, ncols)
                    sql += ' (' + ', '.join(cols) + ')'
                if r.random() < 0.2:
                    sql += ' DEFAULT VALUES'
                    return sql
                if r.random() < 0.3 and depth > 0:
                    # INSERT ... SELECT ...
                    select_depth = max(0, depth - 1)
                    sel = gen_select(state, select_depth, allow_order=False)
                    sql += ' ' + sel
                    return sql
                # VALUES list
                row_count = r.randint(1, 5)
                values_rows = []
                for _ in range(row_count):
                    if use_cols:
                        count = ncols
                    else:
                        count = r.randint(1, 6)
                    vals = ', '.join(rand_literal(state) for _ in range(count))
                    values_rows.append('(' + vals + ')')
                sql += ' VALUES ' + ', '.join(values_rows)
                return sql

            def gen_update(state, depth):
                r = state.rand
                table = random_table_name(state)
                sql = 'UPDATE ' + table + ' SET '
                ncols = r.randint(1, 4)
                assignments = []
                for _ in range(ncols):
                    col = random_column_name(state)
                    expr = gen_expr(state, max(0, depth - 1))
                    assignments.append(col + ' = ' + expr)
                sql += ', '.join(assignments)
                if r.random() < 0.7:
                    sql += ' WHERE ' + gen_condition(state, max(0, depth - 1))
                return sql

            def gen_delete(state, depth):
                r = state.rand
                table = random_table_name(state)
                sql = 'DELETE FROM ' + table
                if r.random() < 0.7:
                    sql += ' WHERE ' + gen_condition(state, max(0, depth - 1))
                return sql

            def gen_misc_statement(state, depth):
                r = state.rand
                choice = r.random()
                if choice < 0.25:
                    table = random_table_name(state)
                    if r.random() < 0.5:
                        sql = 'DROP TABLE '
                    else:
                        sql = 'DROP TABLE IF EXISTS '
                    sql += table
                    return sql
                elif choice < 0.5:
                    # CREATE INDEX
                    table = random_table_name(state)
                    idx_name = rand_identifier(state)
                    ncols = r.randint(1, 3)
                    cols = ', '.join(random_column_name(state) for _ in range(ncols))
                    unique = 'UNIQUE ' if r.random() < 0.3 else ''
                    return 'CREATE ' + unique + 'INDEX ' + idx_name + ' ON ' + table + ' (' + cols + ')'
                elif choice < 0.75:
                    # ALTER TABLE
                    table = random_table_name(state)
                    alter_choice = r.random()
                    if alter_choice < 0.4:
                        col_name = rand_identifier(state)
                        state.known_columns.append(col_name)
                        col_type = r.choice(SQL_TYPES)
                        return 'ALTER TABLE ' + table + ' ADD COLUMN ' + col_name + ' ' + col_type
                    elif alter_choice < 0.7:
                        col_name = random_column_name(state)
                        new_name = rand_identifier(state)
                        return 'ALTER TABLE ' + table + ' RENAME COLUMN ' + col_name + ' TO ' + new_name
                    else:
                        new_name = rand_identifier(state)
                        return 'ALTER TABLE ' + table + ' RENAME TO ' + new_name
                else:
                    # CREATE VIEW
                    view_name = rand_identifier(state)
                    sel = gen_select(state, max(0, depth - 1), allow_order=True)
                    temp = 'TEMPORARY ' if r.random() < 0.2 else ''
                    or_replace = 'OR REPLACE ' if r.random() < 0.2 else ''
                    return 'CREATE ' + or_replace + temp + 'VIEW ' + view_name + ' AS ' + sel

            def maybe_mutate_statement(state, sql):
                r = state.rand
                # With low probability, introduce small syntax anomalies or comments.
                if r.random() < 0.2:
                    # append comment
                    comment_type = r.random()
                    if comment_type < 0.5:
                        sql += ' -- ' + ''.join(r.choice(string.ascii_letters) for _ in range(r.randint(0, 20)))
                    else:
                        sql += ' /* ' + ''.join(r.choice(string.ascii_letters) for _ in range(r.randint(0, 20))) + ' */'
                if r.random() < 0.05 and KEYWORDS:
                    # insert random keyword in the middle
                    pos = r.randint(0, len(sql))
                    kw = r.choice(KEYWORDS)
                    sql = sql[:pos] + ' ' + kw + ' ' + sql[pos:]
                if r.random() < 0.03:
                    # truncate tail to produce incomplete statements
                    if len(sql) > 1:
                        cut = r.randint(0, len(sql) - 1)
                        sql = sql[:cut]
                sql = sql.strip()
                if not sql:
                    sql = 'SELECT 1'
                return sql

            def generate_statement(state):
                r = state.rand
                depth = min(state.max_depth + state.iteration // 50, 5)
                choice = r.random()
                if choice < 0.4:
                    sql = gen_select(state, depth, allow_order=True)
                elif choice < 0.6:
                    sql = gen_insert(state, depth)
                elif choice < 0.75:
                    sql = gen_update(state, depth)
                elif choice < 0.9:
                    sql = gen_delete(state, depth)
                else:
                    sql = gen_create_table(state) if r.random() < 0.5 else gen_misc_statement(state, depth)
                sql = maybe_mutate_statement(state, sql)
                # optional semicolon
                if r.random() < 0.7:
                    sql += ';'
                return sql

            def fuzz(parse_sql):
                state = STATE
                batch = state.batch_size
                statements = [generate_statement(state) for _ in range(batch)]
                t0 = time.time()
                try:
                    parse_sql(statements)
                except Exception:
                    # parse_sql is supposed to catch exceptions, but guard just in case
                    pass
                t1 = time.time()
                duration = t1 - t0
                # Adjust batch size within reasonable bounds
                if duration < 0.02 and batch < 2000:
                    state.batch_size = min(2000, int(batch * 1.3) + 1)
                elif duration > 0.3 and batch > 50:
                    state.batch_size = max(50, int(batch * 0.7))
                state.iteration += 1
                return True
            """
        )

        code = code_template.format(keywords_literal=repr(keywords))
        return {"code": code}