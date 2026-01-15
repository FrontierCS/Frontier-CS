import random
import string

class Solution:
    def solve(self, resources_path: str) -> dict:
        fuzzer_code = '''
import random
import string

seeds = [
    "SELECT * FROM users;",
    "SELECT name, age FROM users WHERE age > 18;",
    "INSERT INTO users (name, age) VALUES (\'Bob\', 25);",
    "UPDATE users SET age = 26 WHERE name = \'Bob\';",
    "DELETE FROM users WHERE age < 18;",
    "CREATE TABLE products (id INT PRIMARY KEY, name VARCHAR(100), price DECIMAL(10,2));",
    "DROP TABLE products;",
    "ALTER TABLE users ADD COLUMN email VARCHAR(255);",
    "SELECT COUNT(*) FROM users GROUP BY age;",
    "SELECT * FROM users JOIN orders ON users.id = orders.user_id;",
    "SELECT * FROM (SELECT * FROM users) AS sub WHERE sub.age > 20;",
    "UPDATE users SET name = \'Charlie\' WHERE id = 1;",
    "INSERT INTO products VALUES (1, \'Laptop\', 999.99);",
    "DELETE FROM orders WHERE total > 1000;",
    "CREATE INDEX idx_name ON users(name);",
    "DROP INDEX idx_name;",
    "",
    "SELECT",
    "FROM dual",
    "\'hello",
    "1 + 2 * 3",
    "-- comment SELECT 1",
    "/* multi line */ SELECT 1;",
    "SELECT * FROM users ORDER BY age DESC LIMIT 10;",
    "SELECT AVG(price) FROM products;",
    "SELECT name FROM users WHERE name LIKE \'A%\';",
    "SELECT * FROM users WHERE age BETWEEN 20 AND 30;",
    "SELECT * FROM users WHERE id IN (1,2,3);",
    "\'unclosed quote",
    "1e10",
    "0.123",
    "\'\\\\escaped\'"
]

sql_keywords = [
    'SELECT', 'FROM', 'WHERE', 'GROUP', 'BY', 'HAVING', 'ORDER', 'LIMIT', 'OFFSET',
    'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE', 'PRIMARY', 'KEY',
    'FOREIGN', 'REFERENCES', 'UNIQUE', 'CHECK', 'DEFAULT', 'NOT', 'NULL', 'INDEX',
    'DROP', 'ALTER', 'ADD', 'COLUMN', 'MODIFY', 'RENAME', 'TO', 'JOIN', 'INNER', 'LEFT',
    'RIGHT', 'FULL', 'ON', 'AS', 'DISTINCT', 'ALL', 'UNION', 'INTERSECT', 'EXCEPT',
    'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AND', 'OR', 'IN', 'LIKE', 'BETWEEN', 'IS',
    'EXISTS', 'ANY', 'ALL', 'SOME', 'TRUE', 'FALSE', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN',
    'UPPER', 'LOWER', 'LENGTH', 'SUBSTRING', 'CONCAT', 'CAST', 'CONVERT'
]

symbols = "()[]{},;=+ -*/%<>!&|^~@#$"

all_random_tokens = sql_keywords + list(symbols) + ["1", "2", "10", "'a'", '"b"', "NULL"]

def random_identifier():
    length = random.randint(1, 10)
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def random_column():
    choices = ['*', random_identifier(), f"{random_identifier()} AS {random_identifier()}"]
    if random.random() < 0.3:
        func = random.choice(['COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'UPPER', 'LOWER'])
        choices.append(f"{func}({random_identifier()})")
    return random.choice(choices)

def random_value():
    choices = [
        str(random.randint(1, 100)),
        f"'{''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(1, 20)))}'",
        str(random.uniform(1.0, 100.0)),
        "NULL"
    ]
    return random.choice(choices)

def random_condition():
    op = random.choice(['=', '!=', '<', '>', '<=', '>=', 'LIKE', 'IN'])
    left = random_identifier()
    right = random_value() if op != 'IN' else f"({random_value()}, {random_value()})"
    return f"{left} {op} {right}"

def random_where():
    if random.random() < 0.3:
        return ""
    num_conds = random.randint(1, 3)
    conds = [random_condition() for _ in range(num_conds)]
    return f"WHERE {' AND '.join(conds)}"

def random_order():
    if random.random() < 0.5:
        return ""
    col = random_identifier()
    direction = random.choice(['ASC', 'DESC'])
    return f"ORDER BY {col} {direction}"

def random_cols():
    num_cols = random.randint(1, 4)
    return ', '.join(random_column() for _ in range(num_cols))

def generate_select():
    cols = random_cols()
    table = random_table := random_identifier()
    where = random_where()
    order = random_order()
    if random.random() < 0.2:
        return f"SELECT {cols} FROM ({generate_select()}) AS sub {where} {order}"
    return f"SELECT {cols} FROM {table} {where} {order}"

def random_columns_def():
    num_cols = random.randint(1, 4)
    types = ['INT', 'VARCHAR(255)', 'DECIMAL(10,2)', 'DATE', 'TEXT']
    defs = []
    for _ in range(num_cols):
        col = random_identifier()
        typ = random.choice(types)
        defn = f"{col} {typ}"
        if random.random() < 0.2:
            defn += " PRIMARY KEY"
        defs.append(defn)
    return ', '.join(defs)

def generate_create_table():
    table = random_identifier()
    defs = random_columns_def()
    return f"CREATE TABLE {table} ({defs});"

def generate_insert():
    table = random_identifier()
    num_vals = random.randint(1, 3)
    col_names = ', '.join(random_identifier() for _ in range(num_vals))
    values = ', '.join(random_value() for _ in range(num_vals))
    return f"INSERT INTO {table} ({col_names}) VALUES ({values})"

def generate_update():
    table = random_identifier()
    num_sets = random.randint(1, 2)
    sets = ', '.join(f"{random_identifier()} = {random_value()}" for _ in range(num_sets))
    where = random_where()
    return f"UPDATE {table} SET {sets} {where}"

def generate_delete():
    table = random_identifier()
    where = random_where()
    return f"DELETE FROM {table} {where}"

def generate_drop():
    what = random.choice(['TABLE', 'INDEX'])
    name = random_identifier()
    return f"DROP {what} {name};"

def generate_alter():
    table = random_identifier()
    col = random_identifier()
    typ = random.choice(['VARCHAR(100)', 'INT'])
    return f"ALTER TABLE {table} ADD COLUMN {col} {typ};"

templates = [generate_select, generate_insert, generate_update, generate_delete, generate_create_table, generate_drop, generate_alter]

def generate_template():
    return random.choice(templates)()

def mutate(sql: str) -> str:
    if random.random() < 0.1:
        return sql  # keep original sometimes
    s_list = list(sql)
    strength = random.randint(3, 8)
    # Replacements
    for _ in range(random.randint(1, strength)):
        if len(s_list) == 0:
            break
        pos = random.randint(0, len(s_list) - 1)
        char = s_list[pos]
        if char.isalpha():
            s_list[pos] = random.choice(string.ascii_letters)
        elif char.isdigit():
            s_list[pos] = random.choice(string.digits)
        elif char in string.punctuation:
            s_list[pos] = random.choice(symbols)
    # Insertions
    for _ in range(random.randint(0, 3)):
        pos = random.randint(0, len(s_list))
        insert_token = random.choice(all_random_tokens)
        s_list = s_list[:pos] + list(insert_token) + s_list[pos:]
    # Deletions
    for _ in range(random.randint(0, 2)):
        if len(s_list) > 1:
            start = random.randint(0, len(s_list) - 1)
            length = random.randint(1, min(3, len(s_list) - start))
            del s_list[start:start + length]
    # Sometimes add comment or long string
    if random.random() < 0.2:
        pos = random.randint(0, len(s_list))
        extra = random.choice([" -- comment", " /* comm */ ", f" \'{\'a\' * random.randint(10, 50)}\'"])
        s_list = s_list[:pos] + list(extra) + s_list[pos:]
    return ''.join(s_list)

def generate_random_invalid():
    num_tokens = random.randint(1, 30)
    tokens = random.choices(all_random_tokens, k=num_tokens)
    sql = ' '.join(tokens)
    # Sometimes unclosed
    if random.random() < 0.3:
        sql = sql.replace("'", "", random.randint(1, 2))
    return sql

def generate_sql():
    r = random.random()
    if r < 0.6:
        return generate_template()
    elif r < 0.85:
        seed = random.choice(seeds)
        return mutate(seed)
    else:
        return generate_random_invalid()

batch_size = 100
counter = 0

def fuzz(parse_sql):
    global counter
    statements = [generate_sql() for _ in range(batch_size)]
    # Add some edge cases periodically
    if counter % 5 == 0:
        statements.extend([
            ' ' * random.randint(0, 100),
            '\n'.join(['SELECT 1'] * random.randint(1, 10)),
            generate_sql() + ';' * random.randint(1, 5),
            "'" + 'a' * random.randint(100, 500) + "'"
        ])
    parse_sql(statements)
    counter += 1
    return True
'''
        return {"code": fuzzer_code}