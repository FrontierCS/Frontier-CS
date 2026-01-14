import os
import random

class Solution:
    def solve(self, resources_path: str) -> dict:
        fuzzer_code = '''
import random

# Module-level state
last_batch = []
random.seed(42)

tables = ['users', 'orders', 'products', 'employees', 'customers']
reserved_words = ['select', 'from', 'where', 'insert', 'update', 'delete', 'create', 'table', 'order', 'by', 'group', 'having', 'join', 'on', 'as']
columns = ['id', 'name', 'age', 'price', 'date', 'email', 'phone']
conditions = [
    'id = 1',
    'name = \'test\'',
    'age > 10',
    'price BETWEEN 1 AND 100',
    'date = \'2023-01-01\'',
    'email LIKE \'%example.com\'',
    'phone IS NULL',
    'name = "O\'Reilly"',
    'id IN (1, 2, 3)'
]
set_clauses = [
    'id = 2',
    'name = \'new\'',
    'price = 100.5',
    'age = age + 1',
    'date = CURRENT_DATE'
]
defs = [
    'id INT PRIMARY KEY',
    'name VARCHAR(50)',
    'age INT',
    'price DECIMAL(10,2)',
    'email VARCHAR(100) UNIQUE',
    'date DATE'
]

base_templates = [
    # SELECT statements
    "SELECT {cols} FROM {table}",
    "SELECT {cols} FROM {table} WHERE {cond}",
    "SELECT {col} FROM {table} GROUP BY {col}",
    "SELECT {col} FROM {table} ORDER BY {col}",
    "SELECT {col} FROM {table} LIMIT {limit}",
    "SELECT * FROM {table} JOIN {table2} ON {join_cond}",
    "SELECT {col} FROM {table} WHERE {cond} UNION SELECT {col} FROM {table2}",
    "SELECT CASE WHEN {cond} THEN 1 ELSE 0 END FROM {table}",
    # INSERT
    "INSERT INTO {table} ({cols}) VALUES ({vals})",
    "INSERT INTO {table} VALUES ({vals})",
    # UPDATE
    "UPDATE {table} SET {set} WHERE {cond}",
    "UPDATE {table} SET {set}",
    # DELETE
    "DELETE FROM {table} WHERE {cond}",
    "DELETE FROM {table}",
    # DDL
    "CREATE TABLE {table} ({defs})",
    "DROP TABLE {table}",
    "ALTER TABLE {table} ADD COLUMN {col} INT",
    # More complex
    "SELECT * FROM {table} WHERE EXISTS (SELECT 1 FROM {table2})",
    "SELECT {cols} FROM {table} HAVING COUNT(*) > 1"
]

invalid_templates = [
    # Incomplete statements
    "SELECT * FROM",
    "SELECT * FROM {table} WHERE",
    "INSERT INTO {table} VALUES",
    "UPDATE {table} SET",
    "DELETE FROM {table}",
    # Syntax errors
    "SELECT * FROM {table} WHERE id = (",
    "INSERT INTO {table} ({cols}) VALUES (1, 2",
    "CREATE TABLE {table} (id INT",
    # Unclosed strings/quotes
    "SELECT * FROM {table} WHERE name = 'unclosed",
    "SELECT 'unclosed string",
    # Comments and specials
    "-- single line comment",
    "/* multi-line comment */ SELECT 1",
    "SELECT 1 -- trailing comment",
    "SELECT 1.23e4",
    "SELECT -5",
    "SELECT @@version",
    "SELECT {invalid_token}",
    # Keyword misuse
    "FROM {table}",
    "{table} = 1",
    # Multiple statements or injections
    "SELECT 1; SELECT 2",
    "SELECT 1; DROP TABLE {table}",
    # Invalid identifiers
    "SELECT * FROM 123table",
    "SELECT * FROM {table}.nonexistent"
]

def choose_identifier(base_list, use_reserved=False):
    ident = random.choice(base_list)
    if use_reserved and random.random() < 0.2:
        ident = random.choice(reserved_words)
    if random.random() < 0.1:
        ident += str(random.randint(1, 999))
    return ident

def generate_random_sql():
    template = random.choice(base_templates)
    replacements = {
        '{cols}': ', '.join([choose_identifier(columns) for _ in range(random.randint(1, 4))]),
        '{table}': choose_identifier(tables, True),
        '{table2}': choose_identifier(tables, True),
        '{col}': choose_identifier(columns, True),
        '{cond}': random.choice(conditions),
        '{vals}': ', '.join([
            str(random.randint(1, 100)) if random.random() < 0.7 else f"'{random.choice(['a', 'b', 'test', 'x\'y'])}'"
            for _ in range(random.randint(1, 4))
        ]),
        '{set}': ', '.join(random.choices(set_clauses, k=random.randint(1, 3))),
        '{defs}': ', '.join(random.choices(defs, k=random.randint(2, 6))),
        '{join_cond}': f"{choose_identifier(columns)} = {choose_identifier(columns)}",
        '{limit}': str(random.randint(1, 100))
    }
    for key, value in replacements.items():
        template = template.replace(key, value, 1)  # Replace first occurrence
    # Ensure all placeholders are replaced by adding defaults if needed
    for key in replacements:
        template = template.replace(key, 'id')
    return template

def generate_invalid_sql():
    templ = random.choice(invalid_templates)
    table = choose_identifier(tables, True)
    col = choose_identifier(columns, True)
    templ = templ.replace('{table}', table)
    templ = templ.replace('{cols}', ', '.join(random.choices(columns, k=2)))
    if '{invalid_token}' in templ:
        invalid_stuff = random.choice(['@@invalid', '#hashtag', '/*unclosed', ';--', 'exec xp_cmdshell'])
        templ = templ.replace('{invalid_token}', invalid_stuff)
    # Randomly insert keywords or tokens
    if random.random() < 0.6:
        pos = random.randint(0, len(templ))
        insert = random.choice(['AND ', 'OR ', 'NOT ', 'NULL ', 'TRUE ', str(random.randint(1, 100)) + ' ', "'bad' "])
        templ = templ[:pos] + insert + templ[pos:]
    # Occasionally add unbalanced parens or commas
    if random.random() < 0.3:
        pos = random.randint(0, len(templ))
        insert = random.choice(['(', ')', ',', ';'])
        templ = templ[:pos] + insert + templ[pos:]
    return templ

def fuzz(parse_sql):
    batch_size = 800  # Large batch to consume time efficiently
    statements = []
    
    # Generate valid SQL
    num_valid = random.randint(500, 600)
    for _ in range(num_valid):
        statements.append(generate_random_sql())
    
    # Generate invalid SQL for error paths
    num_invalid = batch_size - num_valid
    for _ in range(num_invalid):
        statements.append(generate_invalid_sql())
    
    # Mutations from previous batch if available
    if last_batch:
        for _ in range(100):
            base = random.choice(last_batch)
            # Various mutations
            mutations = [
                lambda s: s + f" AND {random.choice(conditions)}",
                lambda s: s.replace('= ', '!= '),
                lambda s: s + f" LIMIT {random.randint(0, 1000)}",
                lambda s: f"'{base}'",  # Wrap in string
                lambda s: s.replace('SELECT', 'SELCT'),  # Typo
                lambda s: s + random.choice(['/* comment */', '-- comment']),
                lambda s: s[:random.randint(0, len(s))] + random.choice([')', ']', '}' ) + s[random.randint(0, len(s)):],
                lambda s: random.choice(['COUNT(', 'SUM(', 'AVG(') + s + ')'
            ]
            mutated = random.choice(mutations)(base)
            statements.append(mutated)
    
    parse_sql(statements)
    
    # Update last_batch for next iteration
    last_batch[:] = random.sample(statements, min(200, len(statements)))
    
    return True
'''
        return {"code": fuzzer_code}