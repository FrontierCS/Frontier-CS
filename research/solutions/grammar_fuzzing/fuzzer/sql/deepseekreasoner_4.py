import os
import re
import random
import time
import heapq
import hashlib
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict, deque
from pathlib import Path
import pickle
import math
from enum import Enum


class Solution:
    def solve(self, resources_path: str) -> dict:
        # Read grammar to understand SQL structure
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        grammar_rules = self._parse_grammar(grammar_path)
        
        # Generate optimized fuzzer code
        fuzzer_code = self._generate_fuzzer_code(grammar_rules, resources_path)
        
        return {"code": fuzzer_code}
    
    def _parse_grammar(self, grammar_path: str) -> Dict[str, List[str]]:
        """Parse BNF-style grammar file into rules dictionary."""
        grammar = {}
        if os.path.exists(grammar_path):
            with open(grammar_path, 'r') as f:
                lines = f.readlines()
            
            current_rule = None
            current_productions = []
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '::=' in line:
                    if current_rule and current_productions:
                        grammar[current_rule] = current_productions
                    
                    parts = line.split('::=', 1)
                    current_rule = parts[0].strip()
                    current_productions = [parts[1].strip()] if parts[1].strip() else []
                elif current_rule is not None and line.startswith('|'):
                    production = line[1:].strip()
                    if production:
                        current_productions.append(production)
            
            if current_rule and current_productions:
                grammar[current_rule] = current_productions
        
        # Fallback grammar if file not found or empty
        if not grammar:
            grammar = {
                'statement': [
                    'SELECT * FROM table_name',
                    'INSERT INTO table_name VALUES (value)',
                    'UPDATE table_name SET column = value',
                    'DELETE FROM table_name WHERE condition',
                    'CREATE TABLE table_name (column type)',
                    'DROP TABLE table_name'
                ]
            }
        
        return grammar
    
    def _generate_fuzzer_code(self, grammar_rules: Dict[str, List[str]], resources_path: str) -> str:
        """Generate the complete fuzzer code as a string."""
        return f'''
import os
import re
import random
import time
import heapq
import hashlib
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, deque
import math
import itertools

# Constants
BATCH_SIZE = 50
MAX_STATEMENT_LENGTH = 1000
MAX_DEPTH = 8
MUTATION_RATE = 0.3
CROSSOVER_RATE = 0.1
INITIAL_GENERATION_SIZE = 200
MAX_CORPUS_SIZE = 1000
EXPLORE_EXPLOIT_RATIO = 0.7

class FuzzingStrategy(Enum):
    GRAMMAR = 1
    MUTATION = 2
    COMBINATION = 3
    EXPLORATION = 4

class SQLFuzzer:
    def __init__(self, grammar_rules):
        self.grammar = grammar_rules
        self.corpus = []
        self.unique_hashes = set()
        self.statement_count = 0
        self.start_time = time.time()
        self.time_budget = 60
        self.phase = 0
        self.coverage_guided = False
        self.last_batch_interesting = True
        
        # Statement patterns for different SQL types
        self.statement_patterns = self._build_statement_patterns()
        
        # Initialize with diverse seeds
        self._initialize_corpus()
        
        # Build token pool for mutation
        self.token_pool = self._build_token_pool()
        
        # For coverage guidance (simulated until real feedback available)
        self.coverage_map = defaultdict(int)
        self.statement_coverage = {{}}
        
    def _build_statement_patterns(self):
        """Build patterns for different SQL statement types."""
        patterns = {{
            'SELECT': [
                "SELECT {columns} FROM {table}",
                "SELECT {columns} FROM {table} WHERE {condition}",
                "SELECT {columns} FROM {table} GROUP BY {group_by}",
                "SELECT {columns} FROM {table} ORDER BY {order_by}",
                "SELECT DISTINCT {columns} FROM {table}",
                "SELECT {columns} FROM {table} JOIN {join_table} ON {join_condition}",
                "SELECT {columns} FROM {table} WHERE {condition} AND {condition2}",
                "SELECT {columns} FROM {table} WHERE {condition} OR {condition2}",
                "SELECT {columns} FROM {table} LIMIT {limit}",
                "SELECT {columns} FROM {table} OFFSET {offset}"
            ],
            'INSERT': [
                "INSERT INTO {table} VALUES ({values})",
                "INSERT INTO {table} ({columns}) VALUES ({values})",
                "INSERT INTO {table} SELECT {columns} FROM {source_table}"
            ],
            'UPDATE': [
                "UPDATE {table} SET {set_clause}",
                "UPDATE {table} SET {set_clause} WHERE {condition}",
                "UPDATE {table} SET {set_clause} = {value} WHERE {condition}"
            ],
            'DELETE': [
                "DELETE FROM {table}",
                "DELETE FROM {table} WHERE {condition}",
                "DELETE FROM {table} WHERE {condition} AND {condition2}"
            ],
            'CREATE': [
                "CREATE TABLE {table} ({columns_with_types})",
                "CREATE TABLE {table} AS SELECT {columns} FROM {source_table}",
                "CREATE INDEX {index_name} ON {table} ({columns})"
            ],
            'DROP': [
                "DROP TABLE {table}",
                "DROP TABLE IF EXISTS {table}",
                "DROP INDEX {index_name}"
            ],
            'ALTER': [
                "ALTER TABLE {table} ADD COLUMN {column} {type}",
                "ALTER TABLE {table} DROP COLUMN {column}",
                "ALTER TABLE {table} RENAME TO {new_name}"
            ],
            'WITH': [
                "WITH {cte_name} AS (SELECT {columns} FROM {table}) SELECT {columns2} FROM {cte_name}"
            ]
        }}
        return patterns
    
    def _build_token_pool(self):
        """Build a pool of tokens for mutation operations."""
        tokens = set()
        
        # Keywords
        keywords = [
            'SELECT', 'FROM', 'WHERE', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET',
            'DELETE', 'CREATE', 'TABLE', 'DROP', 'ALTER', 'ADD', 'COLUMN', 'INDEX',
            'AND', 'OR', 'NOT', 'NULL', 'IS', 'IN', 'LIKE', 'BETWEEN', 'EXISTS',
            'GROUP', 'BY', 'ORDER', 'HAVING', 'LIMIT', 'OFFSET', 'DISTINCT', 'JOIN',
            'LEFT', 'RIGHT', 'INNER', 'OUTER', 'ON', 'AS', 'UNION', 'ALL', 'ANY',
            'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'WITH', 'RECURSIVE'
        ]
        
        # Data types
        types = [
            'INT', 'INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT', 'BIT',
            'FLOAT', 'REAL', 'DOUBLE', 'DECIMAL', 'NUMERIC',
            'CHAR', 'VARCHAR', 'TEXT', 'NCHAR', 'NVARCHAR',
            'DATE', 'TIME', 'DATETIME', 'TIMESTAMP', 'BOOLEAN'
        ]
        
        # Functions
        functions = [
            'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'ABS', 'ROUND', 'CEIL', 'FLOOR',
            'UPPER', 'LOWER', 'SUBSTR', 'TRIM', 'LTRIM', 'RTRIM', 'LENGTH',
            'COALESCE', 'NULLIF', 'CAST', 'EXTRACT', 'CURRENT_DATE', 'CURRENT_TIME'
        ]
        
        # Operators
        operators = ['+', '-', '*', '/', '%', '=', '<>', '!=', '<', '>', '<=', '>=', '||']
        
        # Literals
        literals = [
            '0', '1', '-1', '100', '3.14', '-3.14', 'NULL',
            "'text'", "'a'", "'example'", "'2023-01-01'", "'true'", "'false'",
            'TRUE', 'FALSE'
        ]
        
        # Identifiers
        identifiers = [
            't1', 't2', 'table1', 'table2', 'users', 'orders', 'products',
            'id', 'name', 'price', 'quantity', 'date', 'status',
            'col1', 'col2', 'col3', 'column1', 'column2'
        ]
        
        # Build token pool
        token_pool = {{
            'keywords': keywords,
            'types': types,
            'functions': functions,
            'operators': operators,
            'literals': literals,
            'identifiers': identifiers
        }}
        
        return token_pool
    
    def _initialize_corpus(self):
        """Initialize corpus with diverse SQL statements."""
        seeds = []
        
        # Basic statements
        seeds.extend([
            "SELECT 1",
            "SELECT * FROM t",
            "INSERT INTO t VALUES (1)",
            "UPDATE t SET c = 1",
            "DELETE FROM t",
            "CREATE TABLE t (id INT)",
            "DROP TABLE t",
            "WITH cte AS (SELECT 1) SELECT * FROM cte",
            "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t WHERE x IS NULL",
            "SELECT CASE WHEN x = 1 THEN 'a' ELSE 'b' END FROM t",
            "SELECT * FROM t GROUP BY x HAVING COUNT(*) > 1",
            "SELECT * FROM t ORDER BY x DESC",
            "SELECT DISTINCT x FROM t",
            "SELECT * FROM t LIMIT 10 OFFSET 5",
            "ALTER TABLE t ADD COLUMN c INT",
            "CREATE INDEX idx ON t (c)",
            "SELECT * FROM (SELECT * FROM t) AS sub",
            "SELECT * FROM t WHERE x BETWEEN 1 AND 10",
            "SELECT * FROM t WHERE x IN (1, 2, 3)"
        ])
        
        # Edge cases
        seeds.extend([
            "",  # Empty
            ";",  # Just semicolon
            "SELECT",  # Incomplete
            "SELECT * FROM",  # Incomplete
            "SELECT * FROM t WHERE",  # Incomplete WHERE
            "INSERT INTO",  # Incomplete INSERT
            "1+1",  # Expression only
            "(SELECT 1)",  # Subquery
            "SELECT * FROM t WHERE x = '); DROP TABLE users; --'",  # SQL injection attempt
            "SELECT * FROM t WHERE x = \"quoted\"",  # Double quotes
            "SELECT `column` FROM `table`",  # Backticks
            "SELECT * FROM [table]",  # Brackets
            "/* comment */ SELECT 1",  # Comment
            "SELECT -- comment\\n1",  # Line comment
            "SELECT 1; SELECT 2",  # Multiple statements
            "SELECT * FROM t WHERE x = 1 AND y = 2 OR z = 3",  # Complex condition
            "SELECT * FROM t1, t2, t3",  # Multiple tables
            "SELECT FUNC(1, 2, 3) FROM t",  # Function call
            "SELECT * FROM t WHERE x LIKE '%test%'",  # LIKE pattern
            "SELECT * FROM t WHERE x NOT IN (1, 2, 3)"  # NOT IN
        ])
        
        # Add grammar-based statements if grammar exists
        if self.grammar:
            grammar_seeds = self._generate_from_grammar('statement', 20)
            seeds.extend(grammar_seeds)
        
        # Add to corpus with deduplication
        for seed in seeds:
            if seed and self._add_to_corpus(seed):
                self.corpus.append(seed)
    
    def _generate_from_grammar(self, symbol: str, count: int) -> List[str]:
        """Generate statements from grammar rules."""
        results = []
        if symbol not in self.grammar:
            return results
        
        for _ in range(min(count, 50)):
            try:
                result = self._expand_symbol(symbol)
                if result and len(result) < MAX_STATEMENT_LENGTH:
                    results.append(result)
            except:
                continue
        
        return results
    
    def _expand_symbol(self, symbol: str, depth: int = 0) -> str:
        """Recursively expand a grammar symbol."""
        if depth > MAX_DEPTH:
            return ""
        
        if symbol not in self.grammar:
            return symbol
        
        productions = self.grammar[symbol]
        if not productions:
            return ""
        
        # Choose random production
        production = random.choice(productions)
        
        # Expand each token in production
        tokens = re.split(r'(\\s+|::=|[|]|<[^>]+>|[^<\\s]+)', production)
        expanded_tokens = []
        
        for token in tokens:
            if not token or token.isspace():
                if token:
                    expanded_tokens.append(token)
                continue
            
            if token.startswith('<') and token.endswith('>'):
                # Non-terminal
                inner_symbol = token[1:-1]
                expanded = self._expand_symbol(inner_symbol, depth + 1)
                if expanded:
                    expanded_tokens.append(expanded)
            else:
                # Terminal
                expanded_tokens.append(token)
        
        return ''.join(expanded_tokens)
    
    def _add_to_corpus(self, statement: str) -> bool:
        """Add statement to corpus if unique."""
        if not statement:
            return False
        
        # Simple hash for deduplication
        stmt_hash = hashlib.md5(statement.encode()).hexdigest()
        
        if stmt_hash in self.unique_hashes:
            return False
        
        self.unique_hashes.add(stmt_hash)
        return True
    
    def generate_batch(self, strategy_distribution=None) -> List[str]:
        """Generate a batch of statements using multiple strategies."""
        if not strategy_distribution:
            # Dynamic strategy selection based on phase
            elapsed = time.time() - self.start_time
            phase_ratio = elapsed / self.time_budget
            
            if phase_ratio < 0.3:
                # Initial phase: exploration
                strategy_distribution = {{
                    FuzzingStrategy.GRAMMAR: 0.4,
                    FuzzingStrategy.EXPLORATION: 0.5,
                    FuzzingStrategy.MUTATION: 0.1,
                    FuzzingStrategy.COMBINATION: 0.0
                }}
            elif phase_ratio < 0.7:
                # Middle phase: balanced
                strategy_distribution = {{
                    FuzzingStrategy.GRAMMAR: 0.2,
                    FuzzingStrategy.EXPLORATION: 0.3,
                    FuzzingStrategy.MUTATION: 0.4,
                    FuzzingStrategy.COMBINATION: 0.1
                }}
            else:
                # Final phase: exploitation
                strategy_distribution = {{
                    FuzzingStrategy.GRAMMAR: 0.1,
                    FuzzingStrategy.EXPLORATION: 0.1,
                    FuzzingStrategy.MUTATION: 0.6,
                    FuzzingStrategy.COMBINATION: 0.2
                }}
        
        batch = []
        target_size = BATCH_SIZE
        
        while len(batch) < target_size:
            # Select strategy
            rand_val = random.random()
            cumulative = 0
            selected_strategy = FuzzingStrategy.MUTATION  # Default
            
            for strategy, prob in strategy_distribution.items():
                cumulative += prob
                if rand_val <= cumulative:
                    selected_strategy = strategy
                    break
            
            # Generate using selected strategy
            new_statements = []
            
            if selected_strategy == FuzzingStrategy.GRAMMAR:
                new_statements = self._generate_grammar_based()
            elif selected_strategy == FuzzingStrategy.MUTATION:
                new_statements = self._generate_mutation_based()
            elif selected_strategy == FuzzingStrategy.COMBINATION:
                new_statements = self._generate_combination_based()
            else:  # EXPLORATION
                new_statements = self._generate_exploration_based()
            
            # Add to batch
            for stmt in new_statements:
                if stmt and self._add_to_corpus(stmt):
                    batch.append(stmt)
                    self.corpus.append(stmt)
                    
                    # Limit corpus size
                    if len(self.corpus) > MAX_CORPUS_SIZE:
                        # Remove oldest (but keep some diversity)
                        if random.random() < 0.7:
                            self.corpus.pop(0)
                        else:
                            idx = random.randint(0, len(self.corpus) - 1)
                            self.corpus.pop(idx)
                
                if len(batch) >= target_size:
                    break
        
        return batch
    
    def _generate_grammar_based(self) -> List[str]:
        """Generate statements using grammar rules."""
        statements = []
        
        # Try to generate from grammar
        if self.grammar:
            for _ in range(5):
                try:
                    stmt = self._expand_symbol('statement')
                    if stmt and 10 < len(stmt) < 500:
                        statements.append(stmt)
                except:
                    continue
        
        # If grammar fails, use patterns
        if not statements:
            statements = self._generate_from_patterns(3)
        
        return statements
    
    def _generate_from_patterns(self, count: int) -> List[str]:
        """Generate statements using predefined patterns."""
        statements = []
        pattern_types = list(self.statement_patterns.keys())
        
        for _ in range(count):
            # Randomly select statement type
            stmt_type = random.choice(pattern_types)
            pattern = random.choice(self.statement_patterns[stmt_type])
            
            try:
                # Fill pattern with random values
                filled = self._fill_pattern(pattern)
                if filled:
                    statements.append(filled)
            except:
                continue
        
        return statements
    
    def _fill_pattern(self, pattern: str) -> str:
        """Fill a pattern template with random values."""
        replacements = {{
            'table': random.choice(['t', 'table1', 'users', 'orders', 'products', 't1', 't2']),
            'columns': self._generate_column_list(),
            'columns_with_types': self._generate_column_defs(),
            'condition': self._generate_condition(),
            'condition2': self._generate_condition(),
            'values': self._generate_value_list(),
            'set_clause': self._generate_set_clause(),
            'group_by': self._generate_column_list(),
            'order_by': self._generate_column_list(),
            'limit': str(random.randint(1, 100)),
            'offset': str(random.randint(0, 50)),
            'join_table': random.choice(['t2', 'orders', 'products']),
            'join_condition': 't1.id = t2.id',
            'source_table': random.choice(['t2', 'source']),
            'column': random.choice(['col1', 'col2', 'name', 'value']),
            'type': random.choice(['INT', 'VARCHAR(50)', 'DATE', 'DECIMAL(10,2)']),
            'index_name': 'idx_' + random.choice(['id', 'name', 'date']),
            'new_name': 'new_' + random.choice(['t', 'table']),
            'cte_name': 'cte' + str(random.randint(1, 5)),
            'columns2': self._generate_column_list()
        }}
        
        # Replace placeholders
        result = pattern
        for key, value in replacements.items():
            placeholder = '{{{}}}'.format(key)
            result = result.replace(placeholder, value)
        
        return result
    
    def _generate_column_list(self) -> str:
        """Generate a column list."""
        columns = ['*']
        for i in range(1, random.randint(2, 5)):
            columns.append(f'col{{i}}')
        
        # Sometimes add expressions
        if random.random() < 0.3:
            columns.append('COUNT(*)')
        
        if random.random() < 0.2:
            columns.append(f'col{{random.randint(1, 5)}} + 1')
        
        return ', '.join(random.sample(columns, random.randint(1, len(columns))))
    
    def _generate_column_defs(self) -> str:
        """Generate column definitions for CREATE TABLE."""
        defs = []
        for i in range(1, random.randint(2, 6)):
            col_name = f'col{{i}}'
            col_type = random.choice(['INT', 'VARCHAR(50)', 'DATE', 'DECIMAL(10,2)', 'BOOLEAN'])
            
            # Sometimes add constraints
            constraint = ''
            if random.random() < 0.3:
                constraint = ' PRIMARY KEY'
            elif random.random() < 0.3:
                constraint = ' NOT NULL'
            
            defs.append(f'{{col_name}} {{col_type}}{{constraint}}')
        
        return ', '.join(defs)
    
    def _generate_condition(self) -> str:
        """Generate a WHERE condition."""
        conditions = [
            '1 = 1',
            'id = 1',
            'name = \\'test\\'',
            'value > 0',
            'date IS NOT NULL',
            'status IN (\\'active\\', \\'pending\\')',
            'amount BETWEEN 0 AND 100',
            'text LIKE \\'%search%\\'',
            'x = y',
            '(SELECT COUNT(*) FROM t2) > 0'
        ]
        
        # Combine conditions
        if random.random() < 0.5:
            cond1 = random.choice(conditions)
            cond2 = random.choice(conditions)
            connector = random.choice(['AND', 'OR'])
            return f'({{cond1}} {{connector}} {{cond2}})'
        else:
            return random.choice(conditions)
    
    def _generate_value_list(self) -> str:
        """Generate a VALUES list."""
        values = []
        for _ in range(random.randint(1, 5)):
            if random.random() < 0.7:
                values.append(str(random.randint(1, 100)))
            elif random.random() < 0.5:
                values.append(f"\\'{{random.choice(['a', 'b', 'test', 'name'])}}\\'")
            else:
                values.append('NULL')
        
        return ', '.join(values)
    
    def _generate_set_clause(self) -> str:
        """Generate SET clause for UPDATE."""
        clauses = []
        for i in range(1, random.randint(1, 3)):
            col = f'col{{i}}'
            if random.random() < 0.7:
                value = str(random.randint(1, 100))
            else:
                value = f"\\'new_value\\'"
            clauses.append(f'{{col}} = {{value}}')
        
        return ', '.join(clauses)
    
    def _generate_mutation_based(self) -> List[str]:
        """Generate statements by mutating existing ones."""
        if not self.corpus:
            return self._generate_from_patterns(3)
        
        statements = []
        
        for _ in range(5):
            # Select parent statement
            parent = random.choice(self.corpus)
            if not parent or len(parent) < 2:
                continue
            
            # Apply mutation
            mutated = self._mutate_statement(parent)
            if mutated and mutated != parent:
                statements.append(mutated)
        
        return statements
    
    def _mutate_statement(self, statement: str) -> str:
        """Apply random mutations to a statement."""
        if not statement:
            return statement
        
        tokens = self._tokenize_statement(statement)
        if not tokens:
            return statement
        
        mutation_type = random.random()
        
        if mutation_type < 0.3 and len(tokens) > 1:
            # Delete random token
            idx = random.randint(0, len(tokens) - 1)
            del tokens[idx]
        
        elif mutation_type < 0.6:
            # Insert random token
            idx = random.randint(0, len(tokens))
            new_token = self._get_random_token()
            tokens.insert(idx, new_token)
        
        elif mutation_type < 0.8 and len(tokens) > 0:
            # Replace random token
            idx = random.randint(0, len(tokens) - 1)
            new_token = self._get_random_token()
            tokens[idx] = new_token
        
        else:
            # Swap two tokens
            if len(tokens) >= 2:
                idx1, idx2 = random.sample(range(len(tokens)), 2)
                tokens[idx1], tokens[idx2] = tokens[idx2], tokens[idx1]
        
        return ' '.join(tokens)
    
    def _tokenize_statement(self, statement: str) -> List[str]:
        """Simple tokenization for mutation."""
        # Split by whitespace and common delimiters
        tokens = re.split(r'(\\s+|[,;()=<>!+\\-*/%])', statement)
        return [t for t in tokens if t and not t.isspace()]
    
    def _get_random_token(self) -> str:
        """Get a random token from token pool."""
        category = random.choice(list(self.token_pool.keys()))
        return random.choice(self.token_pool[category])
    
    def _generate_combination_based(self) -> List[str]:
        """Generate statements by combining parts of existing ones."""
        if len(self.corpus) < 2:
            return self._generate_from_patterns(2)
        
        statements = []
        
        for _ in range(3):
            # Select two parents
            parent1 = random.choice(self.corpus)
            parent2 = random.choice(self.corpus)
            
            if not parent1 or not parent2:
                continue
            
            # Simple crossover: take first part of parent1, second part of parent2
            split1 = max(1, len(parent1) // 2)
            split2 = max(1, len(parent2) // 2)
            
            if random.random() < 0.5:
                # Prefix-suffix combination
                new_stmt = parent1[:split1] + parent2[split2:]
            else:
                # Mix at word level
                words1 = parent1.split()
                words2 = parent2.split()
                
                if len(words1) > 1 and len(words2) > 1:
                    split_w = min(len(words1) // 2, len(words2) // 2)
                    new_words = words1[:split_w] + words2[split_w:]
                    new_stmt = ' '.join(new_words)
                else:
                    continue
            
            if new_stmt and new_stmt != parent1 and new_stmt != parent2:
                statements.append(new_stmt)
        
        return statements
    
    def _generate_exploration_based(self) -> List[str]:
        """Generate exploratory statements to find new paths."""
        statements = []
        
        # Try different SQL constructs
        constructs = [
            # Subqueries
            "SELECT * FROM (SELECT * FROM t) AS sub",
            "SELECT * FROM t WHERE x IN (SELECT y FROM t2)",
            "SELECT * FROM t WHERE EXISTS (SELECT 1 FROM t2 WHERE t2.id = t.id)",
            
            # Complex joins
            "SELECT * FROM t1 LEFT JOIN t2 ON t1.id = t2.id RIGHT JOIN t3 ON t2.id = t3.id",
            "SELECT * FROM t1 CROSS JOIN t2",
            "SELECT * FROM t1 NATURAL JOIN t2",
            
            # Set operations
            "SELECT * FROM t1 UNION SELECT * FROM t2",
            "SELECT * FROM t1 INTERSECT SELECT * FROM t2",
            "SELECT * FROM t1 EXCEPT SELECT * FROM t2",
            
            # Window functions
            "SELECT *, ROW_NUMBER() OVER (ORDER BY id) FROM t",
            "SELECT *, SUM(value) OVER (PARTITION BY category) FROM t",
            
            # CTEs
            "WITH recursive cte AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM cte WHERE n < 10) SELECT * FROM cte",
            
            # Case expressions
            "SELECT CASE x WHEN 1 THEN 'one' WHEN 2 THEN 'two' ELSE 'other' END FROM t",
            
            # Cast expressions
            "SELECT CAST(id AS VARCHAR), CAST(value AS DECIMAL(10,2)) FROM t",
            
            # Aggregations with filters
            "SELECT SUM(CASE WHEN status = 'active' THEN value ELSE 0 END) FROM t",
            
            # Complex conditions
            "SELECT * FROM t WHERE (x = 1 OR y = 2) AND NOT (z = 3)",
            
            # Nested function calls
            "SELECT UPPER(SUBSTR(name, 1, 5)) FROM t",
            
            # Special values
            "SELECT NULLIF(x, 0), COALESCE(y, 'default') FROM t",
            
            # Date operations
            "SELECT CURRENT_DATE, CURRENT_TIMESTAMP, EXTRACT(YEAR FROM date_col) FROM t",
            
            # String operations
            "SELECT CONCAT(name, '_', id), REPLACE(description, 'old', 'new') FROM t",
            
            # Mathematical operations
            "SELECT POWER(x, 2), SQRT(y), ABS(z) FROM t",
            
            # Type-specific operations
            "SELECT * FROM t WHERE json_col->>'key' = 'value'",
            "SELECT * FROM t WHERE array_col[1] = 1"
        ]
        
        # Select random constructs
        selected = random.sample(constructs, min(5, len(constructs)))
        statements.extend(selected)
        
        # Also try some intentionally malformed SQL
        if random.random() < 0.3:
            malformed = [
                "SELECT * FROM WHERE",  # Missing table
                "SELECT * FROM t WHERE = 1",  # Missing column
                "INSERT INTO VALUES (1)",  # Missing table
                "UPDATE SET x = 1",  # Missing table
                "DELETE WHERE x = 1",  # Missing FROM
                "SELECT * FROM t GROUP BY",  # Missing columns
                "SELECT * FROM t ORDER BY",  # Missing columns
                "SELECT * FROM t LIMIT",  # Missing number
                "SELECT * FROM t OFFSET",  # Missing number
                "SELECT * FROM (SELECT)",  # Incomplete subquery
                "SELECT 1 1",  # Duplicate
                "SELECT FROM",  # Missing columns
                "INSERT t VALUES",  # Missing INTO
                "SELECT * FROM t WHERE x BETWEEN AND 10",  # Missing start
                "SELECT * FROM t WHERE x IN ()",  # Empty list
                "CREATE TABLE (id INT)",  # Missing table name
                "DROP TABLE",  # Missing table name
                "ALTER TABLE ADD COLUMN c INT",  # Missing table name
                "SELECT * FROM t WHERE x LIKE",  # Missing pattern
                "SELECT * FROM t WHERE x IS",  # Missing NULL/NOT NULL
                "SELECT * FROM t WHERE x NOT",  # Missing IN/BETWEEN/etc
                "WITH AS (SELECT 1) SELECT 2",  # Missing CTE name
                "SELECT * FROM t JOIN ON x = y",  # Missing table
                "SELECT * FROM t UNION",  # Missing second SELECT
                "SELECT * FROM t INTERSECT",  # Missing second SELECT
                "SELECT * FROM t EXCEPT",  # Missing second SELECT
                "SELECT CASE WHEN THEN 'a' END",  # Missing condition
                "SELECT CAST(id AS) FROM t",  # Missing type
                "SELECT FUNC()",  # Unknown function
                "SELECT 1; ; SELECT 2",  # Empty statement
                "/* Unclosed comment SELECT 1",
                "-- Another comment without newline SELECT 1",
                "SELECT `column",  # Unclosed backtick
                "SELECT 'string",  # Unclosed string
                "SELECT \"string",  # Unclosed double quote
                "SELECT [column",  # Unclosed bracket
                "SELECT (1 + 2",  # Unclosed parenthesis
                "SELECT * FROM t WHERE x = 1))",  # Extra parenthesis
                "SELECT 1 FROM DUAL WHERE 1 = 1 AND 2 = 2 OR",  # Trailing OR
                "SELECT * FROM t WHERE x = 1 GROUP BY y HAVING",  # Missing condition
                "SELECT DISTINCT",  # Missing columns
                "SELECT ALL",  # Missing columns
                "SELECT TOP 10",  # Missing columns (SQL Server style)
                "SELECT * FROM t FOR UPDATE",  # Locking clause
                "SELECT * FROM t WITH (NOLOCK)",  # Hint (SQL Server)
                "SELECT * FROM t /*+ INDEX(t idx) */",  # Hint (Oracle)
                "EXPLAIN SELECT 1",  # Explain plan
                "DESCRIBE t",  # Describe table
                "SHOW TABLES",  # Show tables
                "BEGIN TRANSACTION",  # Transaction
                "COMMIT",  # Commit
                "ROLLBACK",  # Rollback
                "SAVEPOINT s1",  # Savepoint
                "RELEASE SAVEPOINT s1",  # Release savepoint
                "SET TRANSACTION ISOLATION LEVEL READ COMMITTED",  # Isolation level
                "SET NAMES 'utf8'",  # Character set
                "SET @var = 1",  # Variable assignment
                "SELECT @var",  # Variable reference
                "PREPARE stmt FROM 'SELECT 1'",  # Prepared statement
                "EXECUTE stmt",  # Execute prepared
                "DEALLOCATE PREPARE stmt"  # Deallocate prepared
            ]
            
            selected_malformed = random.sample(malformed, min(3, len(malformed)))
            statements.extend(selected_malformed)
        
        return statements
    
    def should_continue(self) -> bool:
        """Determine if fuzzing should continue."""
        elapsed = time.time() - self.start_time
        
        # Always continue if we have time
        if elapsed < self.time_budget * 0.95:  # Leave 5% buffer
            return True
        
        # If we're close to time budget, stop
        return False

# Global fuzzer instance
_fuzzer_instance = None

def fuzz(parse_sql):
    """
    Main fuzzing function called by evaluator.
    Generates SQL statements and passes them to parser.
    """
    global _fuzzer_instance
    
    # Initialize fuzzer on first call
    if _fuzzer_instance is None:
        # Try to load grammar from resources
        grammar_rules = {{}}
        try:
            # Look for grammar file in expected locations
            possible_paths = [
                'resources/sql_grammar.txt',
                'sql_grammar.txt',
                '/tmp/sql_grammar.txt'
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        content = f.read()
                    # Simple grammar parsing
                    lines = content.split('\\n')
                    for line in lines:
                        line = line.strip()
                        if '::=' in line:
                            parts = line.split('::=', 1)
                            non_terminal = parts[0].strip()
                            productions = [p.strip() for p in parts[1].split('|')]
                            grammar_rules[non_terminal] = productions
                    break
        except:
            pass  # Use default grammar
        
        _fuzzer_instance = SQLFuzzer(grammar_rules)
    
    # Check if we should continue
    if not _fuzzer_instance.should_continue():
        return False
    
    # Generate batch of statements
    statements = _fuzzer_instance.generate_batch()
    
    if statements:
        # Execute through parser
        parse_sql(statements)
        
        # Update statement count
        _fuzzer_instance.statement_count += len(statements)
    
    return True
'''