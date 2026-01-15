import random
import sys

class Solution:
    def solve(self, resources_path: str) -> dict:
        code = r"""
import random
import sys

class SQLGenerator:
    def __init__(self):
        self.max_depth = 10
        self.grammar = {
            '<start>': ['<stmt>'],
            '<stmt>': ['<select_stmt>', '<insert_stmt>', '<update_stmt>', '<delete_stmt>', '<create_stmt>', '<drop_stmt>'],
            
            # SELECT
            '<select_stmt>': ['SELECT <distinct> <columns> FROM <tables> <where> <group> <having> <order> <limit>'],
            '<distinct>': ['', 'DISTINCT'],
            '<columns>': ['*', '<expr>', '<expr>, <columns>', '<func>'],
            '<tables>': ['<table_name>', '<table_name> AS <ident>', '<table_name> <ident>', '(<select_stmt>) AS <ident>', '<tables> JOIN <tables> ON <expr>', '<tables> LEFT JOIN <tables> ON <expr>'],
            '<where>': ['', 'WHERE <expr>'],
            '<group>': ['', 'GROUP BY <expr_list>'],
            '<having>': ['', 'HAVING <expr>'],
            '<order>': ['', 'ORDER BY <expr_list> <asc_desc>'],
            '<limit>': ['', 'LIMIT <int_val>'],
            '<asc_desc>': ['', 'ASC', 'DESC'],

            # INSERT
            '<insert_stmt>': ['INSERT INTO <table_name> VALUES <val_list>', 'INSERT INTO <table_name> (<ident_list>) VALUES <val_list>', 'INSERT INTO <table_name> <select_stmt>'],
            '<val_list>': ['(<expr_list>)', '(<expr_list>), <val_list>'],
            
            # UPDATE
            '<update_stmt>': ['UPDATE <table_name> SET <assignments> <where>'],
            '<assignments>': ['<ident> = <expr>', '<ident> = <expr>, <assignments>'],
            
            # DELETE
            '<delete_stmt>': ['DELETE FROM <table_name> <where>'],
            
            # DDL
            '<create_stmt>': ['CREATE TABLE <table_name> (<col_defs>)', 'CREATE INDEX <ident> ON <table_name> (<ident_list>)', 'CREATE VIEW <ident> AS <select_stmt>'],
            '<drop_stmt>': ['DROP TABLE <table_name>', 'DROP INDEX <ident>', 'DROP VIEW <ident>'],
            '<col_defs>': ['<ident> <type_name> <constraints>', '<ident> <type_name> <constraints>, <col_defs>'],
            '<constraints>': ['', 'NOT NULL', 'PRIMARY KEY', 'UNIQUE', 'DEFAULT <literal>'],
            
            # EXPR
            '<expr>': ['<term>', '<unary> <expr>', '<expr> <binary> <expr>', '(<expr>)', '<case_expr>'],
            '<term>': ['<ident>', '<literal>', '<table_name>.<ident>'],
            '<case_expr>': ['CASE WHEN <expr> THEN <expr> ELSE <expr> END'],
            '<unary>': ['NOT', '-', '+', '~'],
            '<binary>': ['+', '-', '*', '/', '%', '=', '<>', '!=', '<', '>', '<=', '>=', 'AND', 'OR', 'IS', 'LIKE', 'IN'],
            '<func>': ['COUNT(*)', 'SUM(<expr>)', 'AVG(<expr>)', 'MIN(<expr>)', 'MAX(<expr>)', 'ABS(<expr>)', 'COALESCE(<expr>, <expr>)'],
            
            # LISTS
            '<expr_list>': ['<expr>', '<expr>, <expr_list>'],
            '<ident_list>': ['<ident>', '<ident>, <ident_list>'],
            
            # TERMINALS
            '<table_name>': ['t1', 't2', 'users', 'orders', 'products', 'log', 'data'],
            '<ident>': ['id', 'name', 'price', 'qty', 'status', 'ts', 'c1', 'c2', 'val', 'key'],
            '<type_name>': ['INT', 'INTEGER', 'VARCHAR(100)', 'TEXT', 'FLOAT', 'DOUBLE', 'BOOLEAN', 'DATE', 'TIMESTAMP'],
            '<literal>': ['<int_val>', '<float_val>', '<str_val>', '<bool_val>', 'NULL'],
            '<int_val>': ['0', '1', '10', '-1', '100', '9999'],
            '<float_val>': ['0.0', '1.5', '3.14159', '-0.01', '1e5'],
            '<str_val>': ["'a'", "'abc'", "''", "'O''Reilly'", "'test string'", "'\n'", "'\t'"],
            '<bool_val>': ['TRUE', 'FALSE', 'true', 'false'],
        }

    def generate(self, symbol, depth=0):
        if symbol not in self.grammar:
            return symbol
            
        if depth > self.max_depth:
            # Fallback for depth limit
            if symbol == '<expr>': return '1'
            if symbol == '<columns>': return '*'
            if symbol == '<tables>': return 't1'
            if symbol.endswith('_list>'): return 'id'
            if symbol.endswith('_stmt>'): return 'SELECT 1'
            opts = self.grammar[symbol]
            shortest = min(opts, key=len)
            # If shortest is recursive, bail out
            if '<' in shortest and shortest != symbol: 
                return '' 
            if '<' in shortest: return '' 
            return self.expand(shortest, depth)

        template = random.choice(self.grammar[symbol])
        return self.expand(template, depth)

    def expand(self, template, depth):
        result = template
        steps = 0
        # Expand tags iteratively
        while '<' in result and steps < 200:
            steps += 1
            start = result.find('<')
            end = result.find('>', start)
            if end == -1: break
            tag = result[start:end+1]
            replacement = self.generate(tag, depth + 1)
            result = result[:start] + replacement + result[end+1:]
        return result

def fuzz(parse_sql):
    gen = SQLGenerator()
    statements = []
    
    # 1. Grammar Fuzzing (Bulk)
    # Generate a large batch to maximize coverage in one go (N=1 strategy)
    for _ in range(2500):
        try:
            s = gen.generate('<start>')
            s = " ".join(s.split()) # normalize spaces
            if s: statements.append(s)
        except:
            pass
            
    # 2. Heuristic Edge Cases
    edge_cases = [
        # Tokenizer boundaries
        "SELECT 'unclosed string", "SELECT \"unclosed ident", 
        "SELECT 1 /* unclosed comment", "SELECT 1 --", 
        "SELECT 0x", "SELECT 1.2.3", "SELECT 1e",
        # Parser syntax errors
        "SELECT", "SELECT FROM", "INSERT INTO", 
        "SELECT * FROM t WHERE", 
        # Logical edge cases
        "SELECT * FROM t WHERE 1=1 OR 1=1",
        "SELECT 1/0", 
        "SELECT CASE WHEN TRUE THEN 1 END",
        "SELECT * FROM (SELECT 1) AS a JOIN (SELECT 2) AS b ON 1=1",
        # Keywords as identifiers
        "SELECT select FROM table",
        "SELECT * FROM where",
        # Weird whitespace
        "SELECT\n*\r\tFROM\n\tt",
        # Injection styles
        "SELECT * FROM t WHERE id = '1' OR '1'='1'",
        "SELECT * FROM t; DROP TABLE t",
        # Schema ops
        "CREATE TABLE t (id INT PRIMARY KEY)",
        "INSERT INTO t VALUES (1)",
        "SELECT * FROM t WHERE id IN (1, 2, 3)",
        "SELECT COUNT(*) FROM t GROUP BY id HAVING COUNT(*) > 1",
        "SELECT * FROM t ORDER BY id DESC LIMIT 5"
    ]
    statements.extend(edge_cases)
    
    # 3. Random Byte Noise
    # Good for hitting assertion errors or unexpected paths
    for _ in range(100):
        length = random.randint(1, 100)
        s = ''.join(chr(random.randint(32, 126)) for _ in range(length))
        statements.append(s)

    # Execute all in one single batch to maximize efficiency bonus
    parse_sql(statements)
    
    # Return False to stop, we have delivered our payload
    return False
"""
        return {"code": code}