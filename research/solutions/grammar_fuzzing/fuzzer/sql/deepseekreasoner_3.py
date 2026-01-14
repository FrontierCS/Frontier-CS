import os
import random
import time
import re
from collections import defaultdict, deque
from typing import List, Dict, Set, Optional, Tuple
import sys
import math
import itertools
import string

class Solution:
    def solve(self, resources_path: str) -> dict:
        fuzzer_code = self._generate_fuzzer_code(resources_path)
        return {"code": fuzzer_code}
    
    def _generate_fuzzer_code(self, resources_path: str) -> str:
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        
        fuzzer_template = '''
import os
import sys
import random
import time
import re
import heapq
from collections import defaultdict, deque, Counter
from typing import List, Dict, Set, Optional, Tuple
import math
import itertools
import string
import copy

# Constants
MAX_DEPTH = 10
MAX_WIDTH = 8
BATCH_SIZE = 50
INITIAL_POPULATION = 1000
MUTATION_RATE = 0.4
CROSSOVER_RATE = 0.2
GRAMMAR_RATE = 0.3
EDGE_RATE = 0.1

# Global state for fuzzer
class FuzzerState:
    def __init__(self):
        self.start_time = None
        self.coverage_history = []
        self.statement_pool = []
        self.grammar = None
        self.statement_counter = 0
        self.unique_statements = set()
        self.best_statements = []
        self.nonterminals = set()
        self.terminals = set()
        self.edge_patterns = []
        self.max_length = 200
        self.min_length = 5
        
    def add_statement(self, stmt: str):
        if stmt not in self.unique_statements and len(stmt) < self.max_length:
            self.statement_pool.append(stmt)
            self.unique_statements.add(stmt)
            self.statement_counter += 1
            
    def get_random_statement(self):
        if self.statement_pool:
            return random.choice(self.statement_pool)
        return None

state = FuzzerState()

def parse_grammar(grammar_path):
    """Parse BNF grammar file into production rules"""
    grammar = defaultdict(list)
    with open(grammar_path, 'r') as f:
        lines = f.readlines()
    
    current_nt = None
    pattern = re.compile(r'<([^>]+)>|"([^"]+)"|\'([^\']+)\'|([^\\s<>"\']+)')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        if '::=' in line:
            parts = line.split('::=', 1)
            current_nt = parts[0].strip()
            if current_nt.startswith('<') and current_nt.endswith('>'):
                current_nt = current_nt[1:-1]
            state.nonterminals.add(current_nt)
            line = parts[1].strip()
        
        if current_nt is None:
            continue
            
        # Parse alternatives
        alternatives = line.split('|')
        for alt in alternatives:
            alt = alt.strip()
            if not alt:
                continue
                
            symbols = []
            tokens = pattern.findall(alt)
            for token_match in tokens:
                # token_match is tuple: (nonterm, dbl_quote, single_quote, other)
                if token_match[0]:  # Nonterminal
                    sym = token_match[0]
                    state.nonterminals.add(sym)
                    symbols.append(('NT', sym))
                elif token_match[1]:  # Double quoted terminal
                    symbols.append(('T', token_match[1]))
                    state.terminals.add(token_match[1])
                elif token_match[2]:  # Single quoted terminal
                    symbols.append(('T', token_match[2]))
                    state.terminals.add(token_match[2])
                elif token_match[3]:  # Other terminal
                    symbols.append(('T', token_match[3]))
                    state.terminals.add(token_match[3])
            
            if symbols:
                grammar[current_nt].append(symbols)
    
    return grammar

def generate_from_grammar(grammar, start_symbol, depth=0):
    """Generate SQL statement from grammar"""
    if depth > MAX_DEPTH:
        return ""
    
    if start_symbol not in grammar:
        return start_symbol if start_symbol in state.terminals else ""
    
    productions = grammar[start_symbol]
    if not productions:
        return ""
    
    # Select random production
    chosen_production = random.choice(productions)
    result_parts = []
    
    for sym_type, sym in chosen_production:
        if sym_type == 'T':
            result_parts.append(sym)
        else:  # NT
            generated = generate_from_grammar(grammar, sym, depth + 1)
            result_parts.append(generated)
    
    result = ' '.join(result_parts)
    # Clean up whitespace
    result = re.sub(r'\\s+', ' ', result).strip()
    return result

def mutate_statement(stmt: str) -> str:
    """Apply random mutation to SQL statement"""
    if not stmt or len(stmt) < 2:
        return stmt
    
    mutations = [
        _mutate_insert_token,
        _mutate_delete_token,
        _mutate_replace_token,
        _mutate_swap_tokens,
        _mutate_change_case,
        _mutate_add_nulls,
        _mutate_change_numbers,
        _mutate_change_strings,
    ]
    
    # Apply 1-3 mutations
    num_mutations = random.randint(1, 3)
    mutated = stmt
    
    for _ in range(num_mutations):
        if random.random() < 0.7:  # 70% chance to use a mutation
            mutator = random.choice(mutations)
            mutated = mutator(mutated)
    
    return mutated.strip()

def _mutate_insert_token(stmt: str) -> str:
    tokens = stmt.split()
    if not tokens:
        return stmt
    
    insert_pos = random.randint(0, len(tokens))
    new_token = random.choice([
        'NULL', 'NULL', 'NULL',  # Higher probability for NULL
        'TRUE', 'FALSE',
        '0', '1', '-1', '999',
        "'text'", "'x'", "''",
        ',', ';', '(', ')',
        'AND', 'OR', 'NOT',
        '=', '!=', '<>', '<', '>', '<=', '>=',
        '+', '-', '*', '/', '%',
        'DISTINCT', 'ALL', 'UNIQUE'
    ])
    
    tokens.insert(insert_pos, new_token)
    return ' '.join(tokens)

def _mutate_delete_token(stmt: str) -> str:
    tokens = stmt.split()
    if len(tokens) <= 3:
        return stmt
    
    del_pos = random.randint(0, len(tokens) - 1)
    del tokens[del_pos]
    return ' '.join(tokens)

def _mutate_replace_token(stmt: str) -> str:
    tokens = stmt.split()
    if not tokens:
        return stmt
    
    replace_pos = random.randint(0, len(tokens) - 1)
    replacements = [
        'NULL', 'NULL', 'NULL',
        '0', '1', '999',
        "'abc'", "'xyz'",
        'TRUE', 'FALSE',
        '*', '?',
        '=', '!=', '<>',
        'AND', 'OR'
    ]
    
    tokens[replace_pos] = random.choice(replacements)
    return ' '.join(tokens)

def _mutate_swap_tokens(stmt: str) -> str:
    tokens = stmt.split()
    if len(tokens) < 3:
        return stmt
    
    i = random.randint(0, len(tokens) - 2)
    j = random.randint(i + 1, len(tokens) - 1)
    tokens[i], tokens[j] = tokens[j], tokens[i]
    return ' '.join(tokens)

def _mutate_change_case(stmt: str) -> str:
    if random.random() < 0.3:
        # Randomly change case of some letters
        chars = list(stmt)
        num_changes = min(5, len(chars) // 3)
        for _ in range(num_changes):
            idx = random.randint(0, len(chars) - 1)
            if chars[idx].isalpha():
                if random.random() < 0.5:
                    chars[idx] = chars[idx].upper()
                else:
                    chars[idx] = chars[idx].lower()
        return ''.join(chars)
    return stmt

def _mutate_add_nulls(stmt: str) -> str:
    patterns = [
        (r'(\bWHERE\b)', r'\\1 NULL AND'),
        (r'(\bAND\b)', r'NULL \\1'),
        (r'(\bOR\b)', r'NULL \\1'),
        (r'(\bVALUES\s*\()', r'\\1NULL,'),
        (r'(\))', r', NULL\\1'),
    ]
    
    mutated = stmt
    if random.random() < 0.3:
        for pattern, replacement in patterns:
            if random.random() < 0.5:
                mutated = re.sub(pattern, replacement, mutated, flags=re.IGNORECASE)
    return mutated

def _mutate_change_numbers(stmt: str) -> str:
    def replace_number(match):
        num = match.group()
        replacements = ['0', '1', '-1', '999', 'NULL', "'0'", '1.0', '-999.99']
        return random.choice(replacements)
    
    return re.sub(r'\\b\\d+\\.?\\d*\\b', replace_number, stmt)

def _mutate_change_strings(stmt: str) -> str:
    def replace_string(match):
        replacements = ["''", "'a'", "'xyz'", "'NULL'", "'1'", "''''", "'\\'"]
        return random.choice(replacements)
    
    return re.sub(r"'[^']*'", replace_string, stmt)

def crossover(stmt1: str, stmt2: str) -> str:
    """Combine two SQL statements"""
    if not stmt1 or not stmt2:
        return stmt1 or stmt2
    
    tokens1 = stmt1.split()
    tokens2 = stmt2.split()
    
    if len(tokens1) < 3 or len(tokens2) < 3:
        return stmt1
    
    # Single-point crossover
    point1 = random.randint(1, len(tokens1) - 1)
    point2 = random.randint(1, len(tokens2) - 1)
    
    # Combine parts
    if random.random() < 0.5:
        new_tokens = tokens1[:point1] + tokens2[point2:]
    else:
        new_tokens = tokens2[:point2] + tokens1[point1:]
    
    result = ' '.join(new_tokens)
    # Ensure reasonable length
    if len(result) > state.max_length:
        result = result[:state.max_length]
    
    return result.strip()

def generate_edge_cases():
    """Generate edge case SQL statements"""
    edge_cases = [
        # Empty/whitespace
        "",
        " ",
        "  ",
        "\\t",
        "\\n",
        ";",
        
        # Minimal statements
        ";",
        ";;",
        "SELECT",
        "FROM",
        "WHERE",
        
        # Special values
        "NULL",
        "NULL NULL",
        "SELECT NULL",
        "SELECT NULL FROM NULL",
        "NULL = NULL",
        "NULL IS NULL",
        "NULL IS NOT NULL",
        
        # Numeric extremes
        "SELECT 0",
        "SELECT 1",
        "SELECT -1",
        "SELECT 999999999999999",
        "SELECT -999999999999999",
        "SELECT 0.0",
        "SELECT 1.0",
        "SELECT 1e100",
        "SELECT -1e100",
        
        # String extremes
        "SELECT ''",
        "SELECT ' '",
        "SELECT 'x'",
        "SELECT '''",
        "SELECT '\\''",
        "SELECT '\\\"'",
        "SELECT 'NULL'",
        "SELECT 'SELECT'",
        
        # Boolean
        "SELECT TRUE",
        "SELECT FALSE",
        "SELECT TRUE AND FALSE",
        "SELECT TRUE OR FALSE",
        "SELECT NOT TRUE",
        
        # Operators
        "SELECT 1 = 1",
        "SELECT 1 != 1",
        "SELECT 1 <> 1",
        "SELECT 1 < 1",
        "SELECT 1 > 1",
        "SELECT 1 <= 1",
        "SELECT 1 >= 1",
        "SELECT 1 + 1",
        "SELECT 1 - 1",
        "SELECT 1 * 1",
        "SELECT 1 / 1",
        "SELECT 1 % 1",
        
        # Parentheses
        "()",
        "(())",
        "((()))",
        "SELECT ()",
        "SELECT (())",
        "SELECT (((1)))",
        
        # Commas
        ",",
        ",,",
        ",,,",
        "SELECT ,",
        "SELECT ,,",
        "SELECT 1,",
        "SELECT ,1",
        "SELECT 1,2",
        "SELECT 1,2,3",
        
        # Mixed
        "SELECT *",
        "SELECT * FROM",
        "SELECT * FROM t",
        "INSERT INTO",
        "INSERT INTO t",
        "INSERT INTO t VALUES",
        "UPDATE t SET",
        "UPDATE t SET c =",
        "DELETE FROM",
        "DELETE FROM t",
        "DELETE FROM t WHERE",
        
        # Keywords as identifiers
        "SELECT SELECT",
        "SELECT FROM",
        "SELECT WHERE",
        "SELECT NULL",
        "SELECT TRUE",
        "SELECT FALSE",
        "SELECT AND",
        "SELECT OR",
        "SELECT NOT",
        
        # Case variations
        "select",
        "SELECT",
        "Select",
        "sElEcT",
        "SeLeCt",
        
        # Unusual whitespace
        "SELECT\\t*",
        "SELECT\\n*",
        "SELECT\\r*",
        "SELECT\\f*",
        "SELECT\\v*",
        "SELECT\\t\\n\\r*",
        
        # Special characters
        "SELECT @",
        "SELECT #",
        "SELECT $",
        "SELECT %",
        "SELECT ^",
        "SELECT &",
        "SELECT *",
        "SELECT (",
        "SELECT )",
        "SELECT -",
        "SELECT +",
        "SELECT =",
        "SELECT [",
        "SELECT ]",
        "SELECT {",
        "SELECT }",
        "SELECT |",
        "SELECT \\",
        "SELECT /",
        "SELECT :",
        "SELECT ;",
        "SELECT \"",
        "SELECT '",
        "SELECT <",
        "SELECT >",
        "SELECT ?",
        "SELECT .",
        "SELECT ,",
        
        # Very long (but within limits)
        "SELECT " + "A" * 50,
        "SELECT " + "A," * 25 + "A",
        "SELECT * FROM t WHERE " + "c = 1 AND " * 10 + "c = 1",
        
        # Nested
        "SELECT (SELECT 1)",
        "SELECT (SELECT (SELECT 1))",
        "SELECT * FROM (SELECT 1)",
        "SELECT * FROM (SELECT * FROM (SELECT 1))",
        
        # JOIN variations
        "SELECT * FROM a JOIN b",
        "SELECT * FROM a LEFT JOIN b",
        "SELECT * FROM a RIGHT JOIN b",
        "SELECT * FROM a FULL JOIN b",
        "SELECT * FROM a CROSS JOIN b",
        "SELECT * FROM a NATURAL JOIN b",
        "SELECT * FROM a JOIN b ON",
        "SELECT * FROM a JOIN b ON 1=1",
        
        # Aggregates
        "SELECT COUNT(*)",
        "SELECT COUNT(1)",
        "SELECT COUNT(NULL)",
        "SELECT SUM(1)",
        "SELECT AVG(1)",
        "SELECT MIN(1)",
        "SELECT MAX(1)",
        
        # GROUP BY/ORDER BY
        "SELECT 1 GROUP BY",
        "SELECT 1 ORDER BY",
        "SELECT 1 GROUP BY 1",
        "SELECT 1 ORDER BY 1",
        "SELECT 1 GROUP BY 1, 2, 3",
        "SELECT 1 ORDER BY 1, 2, 3",
        
        # LIMIT/OFFSET
        "SELECT 1 LIMIT",
        "SELECT 1 OFFSET",
        "SELECT 1 LIMIT 0",
        "SELECT 1 LIMIT 1",
        "SELECT 1 LIMIT 100",
        "SELECT 1 LIMIT 0 OFFSET 0",
        "SELECT 1 LIMIT 1 OFFSET 1",
        
        # Subqueries
        "SELECT * FROM (SELECT 1) AS t",
        "SELECT * FROM (SELECT * FROM (SELECT 1))",
        "SELECT (SELECT 1 FROM (SELECT 1))",
        
        # CTEs
        "WITH t AS (SELECT 1) SELECT * FROM t",
        "WITH t AS (SELECT 1), u AS (SELECT 2) SELECT * FROM t, u",
        
        # Set operations
        "SELECT 1 UNION",
        "SELECT 1 UNION ALL",
        "SELECT 1 INTERSECT",
        "SELECT 1 EXCEPT",
        "SELECT 1 UNION SELECT 2",
        "SELECT 1 UNION ALL SELECT 2",
        
        # Comments
        "SELECT 1 -- comment",
        "SELECT /* comment */ 1",
        "SELECT /* multi\\nline */ 1",
        "-- comment\\nSELECT 1",
        "/* comment */ SELECT 1",
        
        # Aliases
        "SELECT 1 AS a",
        "SELECT 1 a",
        "SELECT * FROM t AS a",
        "SELECT * FROM t a",
        
        # Functions
        "SELECT ABS(1)",
        "SELECT COALESCE(NULL, 1)",
        "SELECT NULLIF(1, 1)",
        "SELECT CAST(1 AS INTEGER)",
        "SELECT EXTRACT(YEAR FROM CURRENT_DATE)",
        
        # Dates and times
        "SELECT CURRENT_DATE",
        "SELECT CURRENT_TIME",
        "SELECT CURRENT_TIMESTAMP",
        "SELECT DATE '2023-01-01'",
        "SELECT TIME '12:00:00'",
        "SELECT TIMESTAMP '2023-01-01 12:00:00'",
    ]
    
    return random.choice(edge_cases)

def generate_template_based():
    """Generate SQL from predefined templates"""
    templates = [
        # SELECT templates
        "SELECT * FROM {table}",
        "SELECT {col} FROM {table}",
        "SELECT {col1}, {col2} FROM {table}",
        "SELECT DISTINCT {col} FROM {table}",
        "SELECT * FROM {table} WHERE {condition}",
        "SELECT * FROM {table} ORDER BY {col}",
        "SELECT * FROM {table} LIMIT {num}",
        "SELECT * FROM {table} WHERE {col} = {value}",
        "SELECT * FROM {table} WHERE {col} IN ({values})",
        "SELECT * FROM {table} WHERE {col} BETWEEN {val1} AND {val2}",
        "SELECT * FROM {table} WHERE {col} LIKE '{pattern}'",
        "SELECT * FROM {table} WHERE {col} IS NULL",
        "SELECT * FROM {table} WHERE {col} IS NOT NULL",
        "SELECT * FROM {table} GROUP BY {col}",
        "SELECT {col}, COUNT(*) FROM {table} GROUP BY {col}",
        "SELECT * FROM {table1} JOIN {table2} ON {condition}",
        "SELECT * FROM {table1} LEFT JOIN {table2} ON {condition}",
        
        # INSERT templates
        "INSERT INTO {table} VALUES ({values})",
        "INSERT INTO {table} ({cols}) VALUES ({values})",
        "INSERT INTO {table} SELECT * FROM {table2}",
        
        # UPDATE templates
        "UPDATE {table} SET {col} = {value}",
        "UPDATE {table} SET {col1} = {val1}, {col2} = {val2}",
        "UPDATE {table} SET {col} = {value} WHERE {condition}",
        
        # DELETE templates
        "DELETE FROM {table}",
        "DELETE FROM {table} WHERE {condition}",
        
        # CREATE templates
        "CREATE TABLE {table} ({cols})",
        "CREATE TABLE {table} AS SELECT * FROM {table2}",
        
        # DROP templates
        "DROP TABLE {table}",
        "DROP TABLE IF EXISTS {table}",
        
        # ALTER templates
        "ALTER TABLE {table} ADD COLUMN {col} {type}",
        "ALTER TABLE {table} DROP COLUMN {col}",
        
        # Complex templates
        "SELECT * FROM (SELECT * FROM {table}) AS t",
        "WITH cte AS (SELECT * FROM {table}) SELECT * FROM cte",
        "SELECT * FROM {table1} UNION SELECT * FROM {table2}",
        "SELECT * FROM {table1} INTERSECT SELECT * FROM {table2}",
        "SELECT * FROM {table1} EXCEPT SELECT * FROM {table2}",
    ]
    
    template = random.choice(templates)
    
    # Fill placeholders
    placeholders = {
        'table': random.choice(['t', 'table1', 'table2', 'users', 'orders', 'products']),
        'table1': random.choice(['t1', 'a', 'users']),
        'table2': random.choice(['t2', 'b', 'orders']),
        'col': random.choice(['id', 'name', 'value', 'price', 'quantity']),
        'col1': random.choice(['id', 'name']),
        'col2': random.choice(['value', 'price']),
        'condition': random.choice(['1=1', 'id > 0', 'name IS NOT NULL', 'value BETWEEN 1 AND 10']),
        'value': random.choice(['1', "'text'", 'NULL', 'TRUE']),
        'values': random.choice(['1', '1,2,3', "'a','b','c'", 'NULL']),
        'num': random.choice(['1', '10', '100']),
        'pattern': random.choice(["'%test%'", "'a_'", "''"]),
        'val1': random.choice(['0', '1']),
        'val2': random.choice(['10', '100']),
        'cols': random.choice(['id INT', 'name TEXT', 'value REAL', 'id INTEGER PRIMARY KEY']),
        'type': random.choice(['INTEGER', 'TEXT', 'REAL', 'BOOLEAN']),
    }
    
    for key, val in placeholders.items():
        template = template.replace('{' + key + '}', val)
    
    return template

def generate_random_sql():
    """Generate SQL statement using mixed strategies"""
    strategies = [
        (GRAMMAR_RATE, lambda: generate_from_grammar(state.grammar, 'sql')),
        (MUTATION_RATE, lambda: mutate_statement(state.get_random_statement() or "SELECT 1")),
        (CROSSOVER_RATE, lambda: crossover(
            state.get_random_statement() or "SELECT 1",
            state.get_random_statement() or "SELECT 2"
        )),
        (EDGE_RATE, generate_edge_cases),
        (0.1, generate_template_based),
    ]
    
    # Weighted random choice
    r = random.random()
    cumulative = 0
    
    for weight, generator in strategies:
        cumulative += weight
        if r <= cumulative:
            result = generator()
            if result and len(result) < state.max_length:
                return result
    
    # Fallback
    return "SELECT 1"

def initialize_state():
    """Initialize fuzzer state with grammar and seed statements"""
    if state.start_time is None:
        state.start_time = time.time()
    
    # Parse grammar
    grammar_file = os.path.join(os.path.dirname(__file__), "sql_grammar.txt")
    if os.path.exists(grammar_file):
        state.grammar = parse_grammar(grammar_file)
    
    # Generate initial population
    seeds = [
        # Basic statements
        "SELECT 1",
        "SELECT * FROM t",
        "SELECT a FROM t WHERE b = 1",
        "INSERT INTO t VALUES (1)",
        "UPDATE t SET a = 1",
        "DELETE FROM t",
        "CREATE TABLE t (a INT)",
        "DROP TABLE t",
        
        # More complex
        "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id",
        "SELECT a, COUNT(*) FROM t GROUP BY a",
        "SELECT * FROM t ORDER BY a",
        "SELECT * FROM t LIMIT 10",
        "WITH cte AS (SELECT 1 AS a) SELECT * FROM cte",
        "SELECT * FROM t UNION SELECT * FROM u",
        
        # Edge cases
        "SELECT NULL",
        "SELECT ''",
        "SELECT 1 = 1",
        "SELECT * FROM (SELECT 1) AS t",
        "SELECT * FROM t WHERE a IS NULL",
        "SELECT * FROM t WHERE a LIKE '%test%'",
    ]
    
    for seed in seeds:
        state.add_statement(seed)
    
    # Generate additional seeds
    for _ in range(INITIAL_POPULATION - len(seeds)):
        stmt = generate_random_sql()
        if stmt:
            state.add_statement(stmt)
    
    # Shuffle pool
    random.shuffle(state.statement_pool)

def fuzz(parse_sql):
    """
    Generate SQL statements and execute them through the parser.
    
    Args:
        parse_sql: Function that accepts a list[str] of SQL statements.
    
    Returns:
        bool: True to continue fuzzing, False to stop.
    """
    # Initialize on first call
    if state.start_time is None:
        initialize_state()
    
    # Generate batch of statements
    batch = []
    
    # Mix of strategies
    for i in range(BATCH_SIZE):
        strategy = random.random()
        
        if strategy < 0.4 and state.statement_pool:
            # Mutation
            parent = state.get_random_statement()
            if parent:
                mutated = mutate_statement(parent)
                if mutated and mutated not in state.unique_statements:
                    batch.append(mutated)
                    state.add_statement(mutated)
        elif strategy < 0.7:
            # Grammar-based
            if state.grammar:
                generated = generate_from_grammar(state.grammar, 'sql')
                if generated and generated not in state.unique_statements:
                    batch.append(generated)
                    state.add_statement(generated)
        elif strategy < 0.85 and len(state.statement_pool) >= 2:
            # Crossover
            idx1 = random.randint(0, len(state.statement_pool) - 1)
            idx2 = random.randint(0, len(state.statement_pool) - 1)
            if idx1 != idx2:
                child = crossover(state.statement_pool[idx1], state.statement_pool[idx2])
                if child and child not in state.unique_statements:
                    batch.append(child)
                    state.add_statement(child)
        else:
            # Edge cases and templates
            if random.random() < 0.5:
                edge = generate_edge_cases()
                if edge not in state.unique_statements:
                    batch.append(edge)
                    state.add_statement(edge)
            else:
                templated = generate_template_based()
                if templated and templated not in state.unique_statements:
                    batch.append(templated)
                    state.add_statement(templated)
    
    # Ensure we have some statements
    if not batch:
        for _ in range(min(10, len(state.statement_pool))):
            batch.append(state.get_random_statement())
    
    # Remove duplicates and None values
    batch = [stmt for stmt in batch if stmt is not None]
    batch = list(dict.fromkeys(batch))  # Preserve order while deduping
    
    # Execute through parser
    if batch:
        parse_sql(batch)
    
    # Always continue - let evaluator handle time limit
    return True
'''
        return fuzzer_template