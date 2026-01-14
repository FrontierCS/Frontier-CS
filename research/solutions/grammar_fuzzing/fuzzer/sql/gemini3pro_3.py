import random
import os
import sys

class Solution:
    def solve(self, resources_path: str) -> dict:
        # We provide a comprehensive self-contained fuzzer.
        # This approach maximizes the efficiency bonus by generating a single massive batch
        # of diverse SQL statements and invoking the parser only once (N=1).
        
        fuzzer_code = r'''
import random
import string
import sys

def fuzz(parse_sql):
    """
    Generates a massive corpus of SQL statements including:
    1. Valid SQL (SELECT, INSERT, UPDATE, DELETE, CREATE, DROP)
    2. Complex recursive expressions and nested queries
    3. Boundary values and edge cases
    4. Randomly mutated SQL strings
    5. Token soups (random sequences of keywords/operators)
    
    Executes all in a single batch to maximize efficiency score.
    """
    
    # --- Configuration ---
    BATCH_SIZE = 8000  # Large enough to saturate coverage, small enough for 60s
    MAX_DEPTH = 5
    
    # --- Data Pools ---
    KEYWORDS = [
        "SELECT", "FROM", "WHERE", "AS", "GROUP BY", "HAVING", "ORDER BY", "ASC", "DESC",
        "LIMIT", "OFFSET", "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE",
        "CREATE", "TABLE", "DROP", "INDEX", "ALTER", "ADD", "COLUMN", "view",
        "INNER", "LEFT", "RIGHT", "OUTER", "JOIN", "ON", "CROSS", "NATURAL",
        "UNION", "ALL", "INTERSECT", "EXCEPT", "DISTINCT",
        "TRUE", "FALSE", "NULL", "NOT", "AND", "OR", "LIKE", "IN", "BETWEEN", "IS",
        "EXISTS", "ANY", "ALL", "CASE", "WHEN", "THEN", "ELSE", "END",
        "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "DEFAULT", "UNIQUE", "CHECK", "CONSTRAINT"
    ]
    
    TYPES = ["INTEGER", "INT", "SMALLINT", "BIGINT", "VARCHAR(255)", "TEXT", "BOOLEAN", "FLOAT", "DOUBLE", "DATE", "TIMESTAMP"]
    
    OPERATORS = [
        "=", "<>", "<", ">", "<=", ">=", 
        "+", "-", "*", "/", "%", 
        "||", "&", "|", "^", "<<", ">>"
    ]
    
    FUNCTIONS = ["COUNT", "SUM", "AVG", "MIN", "MAX", "ABS", "LENGTH", "LOWER", "UPPER", "COALESCE", "ROUND"]
    
    TABLES = ["users", "products", "orders", "items", "logs", "t1", "t2", "a", "b"]
    COLUMNS = ["id", "name", "email", "price", "status", "created_at", "qty", "val", "x", "y", "z"]
    
    # --- Generators ---
    
    class SQLGenerator:
        def __init__(self):
            self.depth = 0
            
        def atom(self):
            r = random.random()
            if r < 0.3: return str(random.randint(-100, 100))
            if r < 0.4: return str(random.random() * 1000)
            if r < 0.5: return "'test_string'"
            if r < 0.6: return "NULL"
            if r < 0.7: return "TRUE" if random.random() < 0.5 else "FALSE"
            if r < 0.9: return random.choice(COLUMNS)
            return "?" # Parameter placeholder if supported

        def expression(self, depth=0):
            if depth > MAX_DEPTH or random.random() < 0.4:
                return self.atom()
            
            r = random.random()
            if r < 0.1: # Function
                func = random.choice(FUNCTIONS)
                arg = self.expression(depth + 1)
                return f"{func}({arg})"
            elif r < 0.2: # Parentheses
                return f"({self.expression(depth + 1)})"
            elif r < 0.3: # Unary
                return f"NOT {self.expression(depth + 1)}"
            else: # Binary Op
                op = random.choice(OPERATORS)
                left = self.expression(depth + 1)
                right = self.expression(depth + 1)
                return f"{left} {op} {right}"

        def condition(self, depth=0):
            if depth > MAX_DEPTH or random.random() < 0.3:
                return f"{random.choice(COLUMNS)} {random.choice(['=', '<>', 'IS'])} {self.atom()}"
            
            op = random.choice(["AND", "OR"])
            return f"({self.condition(depth+1)} {op} {self.condition(depth+1)})"

        def select_stmt(self):
            cols = "*"
            if random.random() > 0.3:
                n = random.randint(1, 4)
                cols = ", ".join([f"{random.choice(COLUMNS)}" for _ in range(n)])
            
            t = random.choice(TABLES)
            stmt = f"SELECT {cols} FROM {t}"
            
            # Joins
            if random.random() > 0.7:
                jt = random.choice(TABLES)
                jtype = random.choice(["INNER", "LEFT", "RIGHT"])
                stmt += f" {jtype} JOIN {jt} ON {t}.id = {jt}.{random.choice(COLUMNS)}"
                
            # Where
            if random.random() > 0.4:
                stmt += f" WHERE {self.condition()}"
                
            # Group By / Having
            if random.random() > 0.8:
                gcol = random.choice(COLUMNS)
                stmt += f" GROUP BY {gcol}"
                if random.random() > 0.5:
                    stmt += f" HAVING COUNT({gcol}) > 1"
                    
            # Order By
            if random.random() > 0.8:
                stmt += f" ORDER BY {random.choice(COLUMNS)} {random.choice(['ASC', 'DESC'])}"
                
            # Limit
            if random.random() > 0.9:
                stmt += f" LIMIT {random.randint(1, 100)}"
                
            return stmt

        def insert_stmt(self):
            t = random.choice(TABLES)
            if random.random() < 0.5:
                # VALUES format
                vals = ", ".join([self.atom() for _ in range(3)])
                return f"INSERT INTO {t} VALUES ({vals})"
            else:
                # SELECT format
                return f"INSERT INTO {t} {self.select_stmt()}"

        def update_stmt(self):
            t = random.choice(TABLES)
            assigns = ", ".join([f"{c} = {self.atom()}" for c in random.sample(COLUMNS, k=random.randint(1, 3))])
            stmt = f"UPDATE {t} SET {assigns}"
            if random.random() > 0.3:
                stmt += f" WHERE {self.condition()}"
            return stmt

        def delete_stmt(self):
            t = random.choice(TABLES)
            stmt = f"DELETE FROM {t}"
            if random.random() > 0.3:
                stmt += f" WHERE {self.condition()}"
            return stmt

        def create_stmt(self):
            t = "".join(random.choices(string.ascii_lowercase, k=6))
            cols = []
            for _ in range(random.randint(1, 5)):
                cname = "".join(random.choices(string.ascii_lowercase, k=4))
                ctype = random.choice(TYPES)
                cstr = f"{cname} {ctype}"
                if random.random() > 0.8: cstr += " NOT NULL"
                if random.random() > 0.9: cstr += " PRIMARY KEY"
                cols.append(cstr)
            return f"CREATE TABLE {t} ({', '.join(cols)})"

        def drop_stmt(self):
            return f"DROP TABLE {random.choice(TABLES)}"

        def generate_valid(self):
            r = random.random()
            if r < 0.4: return self.select_stmt()
            if r < 0.55: return self.insert_stmt()
            if r < 0.7: return self.update_stmt()
            if r < 0.8: return self.delete_stmt()
            if r < 0.9: return self.create_stmt()
            return self.drop_stmt()

    # --- Corpus Construction ---
    
    statements = []
    gen = SQLGenerator()
    
    # 1. Structural Valid SQL
    for _ in range(int(BATCH_SIZE * 0.6)):
        try:
            statements.append(gen.generate_valid())
        except:
            pass
            
    # 2. Hardcoded Edge Cases & Syntax Variations
    edge_cases = [
        ";", "", " ", "\n", "\t",
        "SELECT", "SELECT *", "SELECT FROM", "FROM WHERE",
        "SELECT * FROM t WHERE",
        "SELECT 'unterminated string",
        "SELECT \"unterminated identifier",
        "SELECT 1/0",
        "SELECT * FROM t WHERE 1=1 -- comment",
        "SELECT * FROM t /* block comment */ WHERE 1=1",
        "SELECT * FROM t WHERE col LIKE '%pattern%'",
        "SELECT * FROM t WHERE col IN (1, 2, 3)",
        "SELECT CASE WHEN 1 THEN 2 ELSE 3 END",
        "CREATE INDEX idx ON t(c)",
        "DROP INDEX idx",
        "ALTER TABLE t ADD COLUMN c INT",
        "ALTER TABLE t DROP COLUMN c",
        "SELECT * FROM (SELECT * FROM t) as sub",
        "SELECT * FROM t WHERE id IN (SELECT id FROM t2)",
        "UNION SELECT 1",
        "VALUES (1), (2), (3)",
        "SELECT DISTINCT a, b FROM t",
        "SELECT * FROM t WHERE a IS NULL",
        "SELECT * FROM t WHERE a IS NOT NULL",
        # Big numbers
        f"SELECT {sys.maxsize}",
        f"SELECT {-sys.maxsize}",
        "SELECT 1.23e50",
    ]
    statements.extend(edge_cases)
    
    # 3. Mutations (Bit flips, Deletions, Insertions)
    mutated = []
    source_corpus = statements[:1000] # Use subset to mutate
    for _ in range(int(BATCH_SIZE * 0.2)):
        if not source_corpus: break
        s = random.choice(source_corpus)
        if not s: continue
        
        mutation_type = random.randint(0, 3)
        l = len(s)
        if l < 2: 
            mutated.append(s)
            continue
            
        if mutation_type == 0: # Delete char
            idx = random.randint(0, l-1)
            new_s = s[:idx] + s[idx+1:]
        elif mutation_type == 1: # Insert char
            idx = random.randint(0, l)
            char = random.choice(string.printable)
            new_s = s[:idx] + char + s[idx:]
        elif mutation_type == 2: # Replace char
            idx = random.randint(0, l-1)
            char = random.choice(string.printable)
            new_s = s[:idx] + char + s[idx+1:]
        else: # Duplicate slice
            start = random.randint(0, l-2)
            end = random.randint(start+1, l)
            chunk = s[start:end]
            new_s = s[:end] + chunk + s[end:]
            
        mutated.append(new_s)
    statements.extend(mutated)
    
    # 4. Token Soup (Random keywords/ops to trigger parser error states)
    soup = []
    pool = KEYWORDS + OPERATORS + ["(", ")", ",", "*", ";"] + COLUMNS
    for _ in range(int(BATCH_SIZE * 0.1)):
        length = random.randint(1, 15)
        soup.append(" ".join(random.choices(pool, k=length)))
    statements.extend(soup)
    
    # Shuffle
    random.shuffle(statements)
    
    # Execute
    parse_sql(statements)
    
    # Return False to stop the fuzzer (Efficiency Bonus logic: minimize calls)
    return False
'''
        return {"code": fuzzer_code}