import random
import re

class Solution:
    def solve(self, resources_path: str) -> dict:
        grammar = {
            "sql": ["select_stmt", "insert_stmt", "update_stmt", "delete_stmt", "create_table_stmt", "drop_table_stmt"],
            "select_stmt": [
                "SELECT {select_list} FROM {from_clause} {where_clause} {group_by_clause} {having_clause} {order_by_clause} {limit_clause}",
                "SELECT {select_list} FROM {from_clause} {join_clause} {where_clause}",
                "WITH {cte_name} AS ({select_stmt}) SELECT {select_list} FROM {cte_name}"
            ],
            "select_list": ["*", "COUNT(*)", "SUM({col})", "AVG({col})", "{col}", "{col} AS {alias}", "{expr}, {col}"],
            "from_clause": ["{table_name}", "{table_name} {alias}"],
            "table_name": ["users", "products", "orders", "employees", "categories", "sessions"],
            "alias": ["u", "p", "o", "e", "c", "s"],
            "cte_name": ["temp", "sub", "filtered"],
            "join_clause": ["", "INNER JOIN {table_name} ON {cond}", "LEFT JOIN {table_name} ON {cond}"],
            "where_clause": ["", "WHERE {cond}", "WHERE {cond} AND {cond}"],
            "cond": [
                "{col} = {val}", "{col} > {val}", "{col} < {val}", "{col} != {val}",
                "{col} IS NULL", "{col} IS NOT NULL", "{col} LIKE {pattern}",
                "{col} IN {val_list}", "{col} BETWEEN {val} AND {val}",
                "{expr} {op} {expr}"
            ],
            "col": ["{table_name}.{col_name}", "{col_name}"],
            "col_name": ["id", "name", "price", "date", "user_id", "order_id", "category_id", "quantity", "status"],
            "expr": ["{col}", "{num}", "{col} + {num}", "{col} * {num}", "({expr})"],
            "op": ["=", ">", "<", ">=", "<=", "!=", "LIKE", "IN"],
            "val": ["{num}", "{str_val}", "NULL"],
            "str_val": ["'{str}'", "''"],
            "pattern": ["'{str_pattern}'", "'%'"],
            "str": ["Alice", "Bob", "test", "data%", "o'clock", "_under", "x y"],
            "str_pattern": ["a%", "%b", "_c", "d_e"],
            "val_list": ["({val})", "({val}, {val})", "({val}, {val}, {val})"],
            "group_by_clause": ["", "GROUP BY {col}", "GROUP BY {col}, {col}"],
            "having_clause": ["", "HAVING {cond}"],
            "order_by_clause": ["", "ORDER BY {col} {direction}", "ORDER BY {col} {direction}, {col} {direction}"],
            "direction": ["ASC", "DESC"],
            "limit_clause": ["", "LIMIT {num}", "LIMIT {num} OFFSET {num}"],
            "insert_stmt": [
                "INSERT INTO {table_name} ({col_list}) VALUES {value_list}",
                "INSERT INTO {table_name} VALUES {value_list}"
            ],
            "col_list": ["{col_name}", "{col_name}, {col_name}", "{col_name}, {col_name}, {col_name}"],
            "value_list": ["({val})", "({val}), ({val})", "({val}), ({val}), ({val})"],
            "update_stmt": ["UPDATE {table_name} SET {set_clause} {where_clause}"],
            "set_clause": ["{col} = {val}", "{col} = {val}, {col} = {val}", "{col} = {val}, {col} = {val}, {col} = {val}"],
            "delete_stmt": ["DELETE FROM {table_name} {where_clause}"],
            "create_table_stmt": ["CREATE TABLE {table_name} ({col_def_list})"],
            "col_def_list": ["{col_def}", "{col_def}, {col_def}", "{col_def}, {col_def}, {col_def}"],
            "col_def": ["{col_name} INT", "{col_name} VARCHAR({len})", "{col_name} TEXT", "{col_name} DECIMAL({num},2)"],
            "len": ["10", "50", "255"],
            "drop_table_stmt": ["DROP TABLE {table_name}", "DROP TABLE IF EXISTS {table_name}"]
        }

        terminals = {
            "num": ["0", "1", "42", "-5", "3.14", "100.50", "0.0"]
        }

        def generate_code(grammar_str, terminals_str):
            code = f'''import random
import re

grammar = {grammar_str}

terminals = {terminals_str}

def generate(rule, depth=0, max_depth=3):
    if depth > max_depth:
        return ""
    if rule in terminals:
        if rule == "str":
            s = random.choice(["Alice", "Bob", "test", "data", "o'clock", "_under", "x y"])
            s = s.replace("'", "''")
            return f"'{{s}}'"
        elif rule == "str_pattern":
            s = random.choice(["a", "b", "%", "_", "d_e"])
            s = s.replace("'", "''")
            return f"'%s{s}%'"
        elif rule == "len":
            return random.choice(["10", "50", "255"])
        else:
            return random.choice(terminals[rule])
    if rule not in grammar:
        return rule  # fallback
    prods = grammar[rule]
    prod = random.choice(prods)
    i = 0
    while i < len(prod):
        match = re.search(r'\\{([^}]+)\\}', prod[i:])
        if not match:
            break
        start = i + match.start()
        end = i + match.end()
        subrule = match.group(1)
        sub = generate(subrule, depth + 1, max_depth)
        prod = prod[:start] + sub + prod[end:]
        i = start + len(sub)
    return prod

def fuzz(parse_sql):
    statements = []
    num_valid = 2500
    num_mutated = 1000
    # Generate valid statements
    for _ in range(num_valid):
        stmt_type = random.choice(["select_stmt", "insert_stmt", "update_stmt", "delete_stmt", "create_table_stmt", "drop_table_stmt"])
        stmt = generate(stmt_type)
        statements.append(stmt)
    # Generate mutated statements
    mutation_tokens = ["AND", "OR", "NOT", "WHERE", "FROM", "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", ";", ",", "(", ")", "=", ">", "<", "NULL", "TRUE", "FALSE", "'invalid'", "1e3", "-- comment", "/* invalid */", "UNION", "ALL", "DISTINCT"]
    for _ in range(num_mutated):
        base = generate(random.choice(["select_stmt", "insert_stmt"]))
        parts = base.split()
        num_mut = random.randint(0, 4)
        for _ in range(num_mut):
            if random.random() < 0.5 and parts:
                idx = random.randint(0, len(parts) - 1)
                parts[idx] = random.choice(mutation_tokens)
            elif parts:
                idx = random.randint(0, len(parts))
                tok = random.choice(mutation_tokens)
                parts.insert(idx, tok)
            # Sometimes delete
            if random.random() < 0.2 and len(parts) > 1:
                del parts[random.randint(0, len(parts) - 1)]
        stmt = ' '.join(parts).strip()
        if stmt:
            statements.append(stmt)
    # Edge cases
    edges = [
        "", ";", ";;", "SELECT", "FROM users", "SELECT *", "INSERT INTO users", "UPDATE users", "DELETE FROM",
        "SELECT 1 -- comment", "SELECT /* comment */ 1", "SELECT 1 FROM users -- trailing",
        "SELECT 'unclosed", "SELECT ''", "'unclosed", "1.2.3.4", "id..name", "name = 'value",
        "SELECT * FROM users WHERE 1=1 OR 1=1", "SELECT * FROM users LIMIT 999999",
        "CREATE TABLE foo (id INT,,)", "INSERT INTO foo VALUES (1,,)", "UPDATE foo SET id = 1,",
        "'string with \\' escape'", "'multi\\nline'", "0x1", "1E10"
    ]
    statements.extend([e for e in edges for _ in range(10)])
    random.shuffle(statements)
    batch_size = min(5000, len(statements))
    parse_sql(statements[:batch_size])
    return False
'''
            return code

        grammar_str = str(grammar).replace("'", '"').replace('True', 'True').replace('False', 'False')  # rough str
        # Better to use repr
        import pprint
        grammar_str = pprint.pformat(grammar)
        terminals_str = pprint.pformat(terminals)
        code = generate_code(grammar_str, terminals_str)
        return {"code": code}