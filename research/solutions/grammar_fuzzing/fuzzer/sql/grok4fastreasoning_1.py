class Solution:
    def solve(self, resources_path: str) -> dict:
        fuzzer_code = """
import random

class SQLGenerator:
    def __init__(self):
        self.tables = ['users', 'orders', 'products', 'employees', 'customers', 'items', 'categories', 'suppliers']
        self.columns = ['id', 'name', 'age', 'price', 'quantity', 'date', 'email', 'description', 'status', 'category_id']
        self.types = ['INT', 'VARCHAR(255)', 'DECIMAL(10,2)', 'DATE', 'BOOLEAN', 'TEXT', 'TIMESTAMP']
        self.keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP', 'BY', 'ORDER', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE', 'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'DROP', 'ALTER', 'ADD', 'COLUMN', 'NOT', 'NULL', 'DEFAULT', 'AND', 'OR', 'LIKE', 'IN', 'BETWEEN', 'IS', 'JOIN', 'ON', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'UNION', 'ALL', 'HAVING', 'LIMIT', 'OFFSET', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'ASC', 'DESC']
        self.operators = ['=', '!=', '<', '>', '<=', '>=', 'LIKE', 'NOT LIKE', 'IN', 'NOT IN', 'BETWEEN', 'IS NULL', 'IS NOT NULL']

    def generate_identifier(self):
        if random.random() < 0.05:
            return f'"{random.choice(self.columns + self.keywords + ["weird_name", "123invalid"])}"'
        elif random.random() < 0.1:
            return f'{random.choice(["_", "tbl", "col"])}{random.randint(1, 1000)}'
        else:
            return random.choice(self.columns)

    def generate_literal(self):
        lit_types = ['int', 'float', 'string_single', 'string_double', 'null', 'bool', 'date']
        t = random.choice(lit_types)
        if t == 'int':
            return str(random.randint(-100000, 100000))
        elif t == 'float':
            return f"{random.uniform(-1000.0, 1000.0):.6f}"
        elif t == 'string_single':
            s = random.choice(['hello', 'world', "it's", "don''t", '\\"escaped\\"'])
            return f"'{s}'"
        elif t == 'string_double':
            s = random.choice(['hello', 'world', "'single'", 'double'])
            return f'"{s}"'
        elif t == 'null':
            return 'NULL'
        elif t == 'bool':
            return random.choice(['TRUE', 'FALSE'])
        elif t == 'date':
            return f"'{random.randint(2000, 2023):04d}-{random.randint(1,12):02d}-{random.randint(1,28):02d}'"

    def generate_expression(self, depth=0):
        if depth > 3:
            return self.generate_literal()
        choices = [
            self.generate_identifier(),
            self.generate_literal(),
            f"{self.generate_identifier()} + {self.generate_expression(depth + 1)}",
            f"{self.generate_identifier()} * {self.generate_expression(depth + 1)}",
            f"COUNT({self.generate_identifier()})",
            f"SUM({self.generate_identifier()})",
            f"CASE WHEN {self.generate_condition(depth + 1)} THEN {self.generate_literal()} ELSE {self.generate_literal()} END"
        ]
        return random.choice(choices)

    def generate_condition(self, depth=0):
        if depth > 4:
            return f"{self.generate_identifier()} = {self.generate_literal()}"
        op = random.choice(self.operators)
        left = self.generate_expression(depth)
        if op in ['IN', 'NOT IN']:
            if random.random() < 0.4 and depth < 3:
                subquery = f"(SELECT {random.choice(self.columns)} FROM {random.choice(self.tables)} WHERE {self.generate_condition(depth + 1)})"
                right = subquery
            else:
                num_vals = random.randint(1, 5)
                vals = [self.generate_literal() for _ in range(num_vals)]
                right = f"({', '.join(vals)})"
        elif op == 'BETWEEN':
            right = f"{self.generate_literal()} AND {self.generate_literal()}"
        elif op in ['IS NULL', 'IS NOT NULL']:
            right = ''
        else:
            right = self.generate_expression(depth + 1)
            if random.random() < 0.3 and depth < 3 and op == '=':
                right = f"(SELECT {random.choice(self.columns)} FROM {random.choice(self.tables)})"
        cond = f"{left} {op} {right}" if right else f"{left} {op}"
        if random.random() < 0.5:
            op2 = random.choice(['AND', 'OR'])
            cond2 = self.generate_condition(depth)
            cond = f"({cond}) {op2} ({cond2})"
        return cond

    def generate_column_list(self, min_cols=1, max_cols=5):
        num = random.randint(min_cols, max_cols)
        cols = []
        for _ in range(num):
            if random.random() < 0.4:
                cols.append(self.generate_expression())
            else:
                cols.append(self.generate_identifier())
        if random.random() < 0.2:
            cols.insert(0, '*')
        return ', '.join(cols)

    def generate_table_ref(self):
        table = random.choice(self.tables)
        if random.random() < 0.3:
            alias = random.choice(['t1', 't2', 'a', 'b'])
            table = f"{table} {alias}"
        return table

    def generate_from_clause(self):
        tables = [self.generate_table_ref() for _ in range(random.randint(1, 3))]
        if len(tables) > 1 and random.random() < 0.6:
            join_type = random.choice(['INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL OUTER JOIN'])
            on_cond = self.generate_condition()
            tables[1] = f"{join_type} {tables[1]} ON {on_cond}"
        return f"FROM {', '.join(tables) if len(tables) == 1 else ' '.join(tables)}"

    def generate_select(self):
        distinct = "DISTINCT " if random.random() < 0.3 else ""
        select_list = self.generate_column_list(1, 6)
        from_clause = self.generate_from_clause()
        where_clause = f"WHERE {self.generate_condition()}" if random.random() > 0.3 else ""
        group_clause = f"GROUP BY {', '.join([self.generate_identifier() for _ in range(random.randint(1, 2))])}" if random.random() > 0.4 else ""
        having_clause = f"HAVING {self.generate_condition()}" if group_clause and random.random() > 0.4 else ""
        order_clause = f"ORDER BY {', '.join([f'{self.generate_identifier()} {random.choice(["ASC", "DESC"])}' for _ in range(random.randint(1, 2))])}" if random.random() > 0.3 else ""
        limit_offset = ""
        if random.random() > 0.4:
            limit = random.randint(1, 100)
            offset = f" OFFSET {random.randint(0, 50)}" if random.random() > 0.5 else ""
            limit_offset = f"LIMIT {limit}{offset}"
        union = f" UNION {self.generate_select()}" if random.random() < 0.1 else ""
        sql = f"SELECT {distinct}{select_list} {from_clause} {where_clause} {group_clause} {having_clause} {order_clause} {limit_offset}{union}"
        return sql

    def generate_insert(self):
        table = self.generate_table_ref()
        cols = self.generate_column_list(0, 4)
        cols_str = f"({cols})" if cols else ""
        num_rows = random.randint(1, 3)
        values_lists = []
        for _ in range(num_rows):
            if cols:
                num_vals = len([c.strip() for c in cols.split(',')])
                vals = [self.generate_literal() for _ in range(num_vals)]
            else:
                num_vals = random.randint(1, 4)
                vals = [self.generate_literal() for _ in range(num_vals)]
            values_lists.append(f"({', '.join(vals)})")
        values_str = ', '.join(values_lists)
        if random.random() < 0.2:
            return f"INSERT INTO {table}{cols_str} {values_str}"
        else:
            subselect = self.generate_select()
            return f"INSERT INTO {table}{cols_str} {subselect}"

    def generate_update(self):
        table = self.generate_table_ref()
        num_sets = random.randint(1, 3)
        set_clauses = [f"{self.generate_identifier()} = {self.generate_expression()}" for _ in range(num_sets)]
        set_str = ', '.join(set_clauses)
        where_clause = f"WHERE {self.generate_condition()}" if random.random() > 0.4 else ""
        return f"UPDATE {table} SET {set_str} {where_clause}"

    def generate_delete(self):
        table = self.generate_table_ref()
        where_clause = f"WHERE {self.generate_condition()}" if random.random() > 0.4 else ""
        return f"DELETE FROM {table} {where_clause}"

    def generate_create_table(self):
        table = f"{random.choice(['new_', 'temp_', 'test_'])}{random.choice(self.tables)}"
        num_cols = random.randint(2, 6)
        col_defs = []
        for _ in range(num_cols):
            col = self.generate_identifier()
            typ = random.choice(self.types)
            constraints = []
            if random.random() < 0.3:
                constraints.append("NOT NULL")
            if random.random() < 0.2:
                constraints.append("DEFAULT " + self.generate_literal())
            col_def = f"{col} {typ}"
            if constraints:
                col_def += " " + " ".join(constraints)
            col_defs.append(col_def)
        pk_cols = [random.choice(self.columns) for _ in range(random.randint(1, 2))]
        pk = f", PRIMARY KEY ({', '.join(pk_cols)})" if random.random() < 0.4 else ""
        fk = f", FOREIGN KEY ({random.choice(self.columns)}) REFERENCES {random.choice(self.tables)}({random.choice(self.columns)})" if random.random() < 0.2 else ""
        sql = f"CREATE TABLE {table} ({', '.join(col_defs)}{pk}{fk})"
        return sql

    def generate_drop_table(self):
        table = random.choice(self.tables)
        if_exists = "IF EXISTS " if random.random() < 0.5 else ""
        return f"DROP TABLE {if_exists}{table}"

    def generate_alter_table(self):
        table = random.choice(self.tables)
        actions = [
            f"ADD {self.generate_column_list(1,1)}",
            f"ADD CONSTRAINT pk PRIMARY KEY ({random.choice(self.columns)})",
            f"DROP COLUMN {random.choice(self.columns)}",
            f"ALTER COLUMN {random.choice(self.columns)} SET NOT NULL",
            f"RENAME TO new_{table}"
        ]
        action = random.choice(actions)
        return f"ALTER TABLE {table} {action}"

    def generate_invalid(self):
        invalid_types = [
            "SELECT * FROM nonexistent_table WHERE invalid = 'syntax'",
            "INSERT INTO table VALUES (1,,3)",
            "UPDATE table SET col = WHERE id=1",
            "DELETE table",
            "CREATE TABLE (col INT)",
            f"SELECT * FROM {random.choice(self.tables)} ; DROP TABLE {random.choice(self.tables)}",  # multiple
            "-- comment only",
            "/* block comment */ SELECT 1",
            f"SELECT {random.choice(self.keywords)} FROM table",  # keyword as column
            "BEGIN TRANSACTION; COMMIT;",  # transaction
            f"{random.choice(self.keywords)} {random.choice(self.keywords)} {random.choice(self.literals if hasattr(self, 'literals') else ['1'])}"
        ]
        parts = random.choices(self.keywords + self.columns + self.tables + ['1', '2', '*', '(', ')', ',', ';', '--', '/*', '*/'], k=random.randint(5, 25))
        invalid_sql = ' '.join(parts)
        if random.random() < 0.3:
            return random.choice(invalid_types)
        else:
            return invalid_sql

    def generate_sql(self):
        sql_types = [
            (self.generate_select, 0.40),
            (self.generate_insert, 0.15),
            (self.generate_update, 0.10),
            (self.generate_delete, 0.10),
            (self.generate_create_table, 0.08),
            (self.generate_drop_table, 0.05),
            (self.generate_alter_table, 0.07),
            (self.generate_invalid, 0.05)
        ]
        total_weight = sum(weight for _, weight in sql_types)
        r = random.uniform(0, total_weight)
        cum = 0
        for gen_func, weight in sql_types:
            cum += weight
            if r <= cum:
                sql = gen_func()
                if random.random() < 0.2:  # add comment sometimes
                    comment = random.choice(['-- test', '/* fuzz */'])
                    sql += f" {comment}"
                return sql
        return self.generate_select()

generator = SQLGenerator()

def mutate(sql):
    if random.random() < 0.5:
        return sql
    lines = sql.split()
    mutations = []
    if len(lines) > 1 and random.random() < 0.4:
        del_idx = random.randint(0, len(lines) - 1)
        del_word = lines.pop(del_idx)
        mutations.append(f"deleted {del_word}")
    if random.random() < 0.4:
        ins_idx = random.randint(0, len(lines))
        ins_word = random.choice(generator.keywords + ['invalid', 'syntax', 'error', '123'])
        lines.insert(ins_idx, ins_word)
        mutations.append(f"inserted {ins_word}")
    if random.random() < 0.3:
        rep_idx = random.randint(0, len(lines) - 1)
        old = lines[rep_idx]
        new = random.choice(generator.literals if hasattr(generator, 'literals') else [str(random.randint(1,100)), "'mutated'", generator.keywords[0]])
        lines[rep_idx] = new
        mutations.append(f"replaced {old} with {new}")
    if random.random() < 0.2:
        lines.append(random.choice([';', ',', 'AND 1=1']))
    return ' '.join(lines)

def fuzz(parse_sql):
    batch_size = 2000
    statements = []
    for _ in range(batch_size):
        base_sql = generator.generate_sql()
        if random.random() < 0.3:
            sql = mutate(base_sql)
        else:
            sql = base_sql
        statements.append(sql)
    parse_sql(statements)
    return True
"""
        return {"code": fuzzer_code}