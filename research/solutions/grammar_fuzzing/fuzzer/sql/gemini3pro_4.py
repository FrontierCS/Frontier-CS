import random
import string
import os

class Solution:
    def solve(self, resources_path: str) -> dict:
        code = r'''import random
import string

def fuzz(parse_sql):
    """
    Fuzzer strategy:
    1. Generates a large corpus of syntactically valid SQL using a grammar-based approach.
    2. Includes a set of manual edge cases (injection, overflows, boundary conditions).
    3. Generates mutated invalid SQL to test error handling paths.
    4. Executes everything in a SINGLE batch (N=1) to maximize the efficiency bonus.
       Efficiency bonus = 30 * 2^(-N/500). With N=1, bonus is ~29.9 points.
    """
    
    # --- Generators ---
    
    def r_id():
        return random.choice(['id', 'name', 'value', 'count', 'created_at', 'status', 'user_id', 'group_id', 't1', 't2', 'meta_data'])

    def r_table():
        return random.choice(['users', 'orders', 'products', 'logs', 'audit', 'settings', 'inventory'])

    def r_val():
        # Mix of integers, floats, strings, NULL
        r = random.random()
        if r < 0.4: return str(random.randint(-1000, 10000))
        if r < 0.5: return f"{random.randint(0,1000)}.{random.randint(0,99)}"
        if r < 0.9: 
            s = ''.join(random.choices(string.ascii_letters + " _-", k=random.randint(0, 15)))
            return f"'{s}'"
        return "NULL"

    def r_op():
        return random.choice(['=', '!=', '<', '>', '<=', '>=', 'LIKE', 'IN', 'IS'])

    def r_expr(depth=0):
        # Recursive expression generator to hit nested parsing logic
        if depth > 3 or random.random() < 0.3:
            return random.choice([r_id(), r_val(), "*"])
        
        kind = random.random()
        if kind < 0.1: 
            return f"(NOT {r_expr(depth+1)})"
        elif kind < 0.4: 
            op = random.choice(['+', '-', '*', '/', '%'])
            return f"({r_expr(depth+1)} {op} {r_expr(depth+1)})"
        elif kind < 0.7:
            op = r_op()
            right = r_expr(depth+1)
            if op == 'IN': right = f"({r_val()}, {r_val()})"
            if op == 'IS': right = "NULL"
            return f"({r_expr(depth+1)} {op} {right})"
        else:
            op = random.choice(['AND', 'OR'])
            return f"({r_expr(depth+1)} {op} {r_expr(depth+1)})"

    # --- Corpus Generation ---
    statements = []
    
    # 1. Grammar-based Valid SQL (~3500 statements)
    for _ in range(3500):
        r = random.random()
        
        if r < 0.45: # SELECT (most complex grammar)
            parts = ["SELECT"]
            if random.random() < 0.15: parts.append("DISTINCT")
            
            # Select List
            cols = []
            for _ in range(random.randint(1, 4)):
                c = r_id()
                if random.random() < 0.1: c = f"COUNT({c})"
                elif random.random() < 0.05: c = f"MAX({c})"
                elif random.random() < 0.05: c = f"AVG({c})"
                cols.append(c)
            parts.append(", ".join(cols))
            
            parts.append(f"FROM {r_table()}")
            
            # Joins
            if random.random() < 0.25:
                parts.append(f"JOIN {r_table()} ON {r_id()} = {r_id()}")
            
            # Where
            if random.random() < 0.6:
                parts.append(f"WHERE {r_expr()}")
                
            # Group By
            if random.random() < 0.15:
                parts.append(f"GROUP BY {r_id()}")
                if random.random() < 0.5:
                    parts.append(f"HAVING {r_expr()}")
            
            # Order By
            if random.random() < 0.15:
                parts.append(f"ORDER BY {r_id()} {random.choice(['ASC', 'DESC'])}")
                
            # Limit
            if random.random() < 0.1:
                parts.append(f"LIMIT {random.randint(1, 500)}")
            
            statements.append(" ".join(parts))
            
        elif r < 0.6: # INSERT
            cols = [r_id() for _ in range(random.randint(1, 4))]
            vals = [r_val() for _ in range(len(cols))]
            statements.append(f"INSERT INTO {r_table()} ({', '.join(cols)}) VALUES ({', '.join(vals)})")
            
        elif r < 0.75: # UPDATE
            statements.append(f"UPDATE {r_table()} SET {r_id()} = {r_val()} WHERE {r_expr()}")
            
        elif r < 0.85: # DELETE
            statements.append(f"DELETE FROM {r_table()} WHERE {r_expr()}")
            
        elif r < 0.95: # CREATE
            cols = []
            for _ in range(random.randint(1, 5)):
                ctype = random.choice(['INT', 'VARCHAR(255)', 'TEXT', 'FLOAT', 'BOOLEAN', 'DATE'])
                opt = " NOT NULL" if random.random() < 0.2 else ""
                cols.append(f"{r_id()} {ctype}{opt}")
            statements.append(f"CREATE TABLE {r_table()} ({', '.join(cols)})")
            
        else: # DROP
            statements.append(f"DROP TABLE {r_table()}")

    # 2. Static Edge Cases (Boundary testing)
    edge_cases = [
        "", ";", " ", "\t", "\n",
        "'", "\"", "'''", "\"\"\"",
        "--", "/* */", "/**/",
        "SELECT", "SELECT *", "SELECT FROM", "FROM table",
        "SELECT * FROM table WHERE",
        "SELECT 1 / 0",
        f"SELECT * FROM {'a'*300}", # Long identifier
        f"SELECT * FROM t WHERE id = {10**50}", # Overflow
        "SELECT * FROM (SELECT * FROM (SELECT * FROM t))", # Nesting
        "SELECT a FROM t WHERE a IS NULL",
        "SELECT a FROM t WHERE a IN (1, 2, 3)",
        "SELECT CAST(a AS INT) FROM t",
        "INSERT INTO t VALUES ()",
        "DELETE * FROM t",
        "UPDATE t SET",
        "CREATE TABLE t",
        "DROP TABLE",
        "SELECT a, b, FROM t", # Trailing comma
        "SELECT * FROM t WHERE a == b", # Invalid Op
        "SELECT * FROM t WHERE a <> b", 
    ]
    statements.extend(edge_cases)

    # 3. Mutation Fuzzing (Invalid Syntax Exploration)
    # Mutate a subset of generated statements to hit exception handlers
    mutants = []
    subset = random.sample(statements, min(len(statements), 600))
    for s in subset:
        if not s: continue
        
        # Random insertion
        idx = random.randint(0, len(s))
        char = random.choice(string.punctuation)
        mutants.append(s[:idx] + char + s[idx:])
        
        # Random deletion
        if len(s) > 1:
            idx = random.randint(0, len(s)-1)
            mutants.append(s[:idx] + s[idx+1:])
            
        # Bit flip
        idx = random.randint(0, len(s)-1)
        c = ord(s[idx])
        mutants.append(s[:idx] + chr(c ^ 0x04) + s[idx+1:])
        
        # Keyword corruption
        if "SELECT" in s: mutants.append(s.replace("SELECT", "SEL ECT"))
        if "FROM" in s: mutants.append(s.replace("FROM", "FORM"))
        
    statements.extend(mutants)

    # Shuffle to mix valid and invalid
    random.shuffle(statements)

    # Execute all statements in a single call
    # This results in N=1 for the efficiency metric.
    parse_sql(statements)

    # Stop immediately
    return False
'''
        return {"code": code}