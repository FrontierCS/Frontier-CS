import os
import re
import random
import itertools
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Set, Tuple, Optional
import ast
import inspect

class Grammar:
    def __init__(self, grammar_text: str):
        self.rules = {}
        self.start_symbol = None
        self._parse_grammar(grammar_text)
        
    def _parse_grammar(self, grammar_text: str):
        """Parse BNF-style grammar text into rules."""
        lines = grammar_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if '::=' in line:
                lhs, rhs = line.split('::=', 1)
                lhs = lhs.strip()
                if not self.start_symbol:
                    self.start_symbol = lhs
                
                alternatives = []
                for alt in rhs.split('|'):
                    alt = alt.strip()
                    if alt:
                        symbols = []
                        for token in re.findall(r'<[^>]+>|[^<\s]+|ε', alt):
                            if token == 'ε':
                                symbols.append('')
                            elif token.startswith('<'):
                                symbols.append(token)
                            else:
                                symbols.append(token.strip("'"))
                        alternatives.append(symbols)
                
                if lhs not in self.rules:
                    self.rules[lhs] = []
                self.rules[lhs].extend(alternatives)

class SQLGenerator:
    def __init__(self, grammar_path: str):
        with open(grammar_path, 'r') as f:
            grammar_text = f.read()
        self.grammar = Grammar(grammar_text)
        self.max_depth = 5
        self.generated = set()
        
        # Track coverage targets from parser analysis
        self.coverage_targets = self._identify_coverage_targets()
        
    def _identify_coverage_targets(self) -> Dict[str, List[str]]:
        """Identify parser constructs to target for coverage."""
        return {
            'statements': ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP'],
            'clauses': ['WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT', 'JOIN'],
            'expressions': ['arithmetic', 'comparison', 'logical', 'function', 'case', 'subquery'],
            'data_types': ['INTEGER', 'VARCHAR', 'DECIMAL', 'DATE', 'BOOLEAN'],
            'constraints': ['PRIMARY KEY', 'FOREIGN KEY', 'NOT NULL', 'UNIQUE'],
            'functions': ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'COALESCE', 'CAST'],
            'joins': ['INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN', 'CROSS JOIN'],
        }
    
    def generate_from_symbol(self, symbol: str, depth: int = 0) -> str:
        """Generate SQL from a grammar symbol."""
        if depth > self.max_depth:
            return self._generate_terminal(symbol)
            
        if symbol not in self.grammar.rules:
            return self._generate_terminal(symbol)
            
        alternatives = self.grammar.rules[symbol]
        
        # Weight alternatives based on coverage importance
        weights = self._weight_alternatives(symbol, alternatives)
        chosen = random.choices(alternatives, weights=weights, k=1)[0]
        
        parts = []
        for sym in chosen:
            if not sym:
                continue
            if sym.startswith('<'):
                parts.append(self.generate_from_symbol(sym, depth + 1))
            else:
                parts.append(sym)
                
        return ' '.join(parts).strip()
    
    def _weight_alternatives(self, symbol: str, alternatives: List[List[str]]) -> List[float]:
        """Weight grammar alternatives based on coverage targets."""
        weights = [1.0] * len(alternatives)
        
        # Boost alternatives that contain coverage targets
        for i, alt in enumerate(alternatives):
            alt_str = ' '.join(alt)
            for target_type, targets in self.coverage_targets.items():
                for target in targets:
                    if target.lower() in alt_str.lower():
                        weights[i] *= 1.5
                        
        # Normalize weights
        total = sum(weights)
        return [w/total for w in weights] if total > 0 else weights
    
    def _generate_terminal(self, symbol: str) -> str:
        """Generate terminal value for a symbol."""
        symbol_lower = symbol.lower()
        
        terminals = {
            '<identifier>': lambda: random.choice(['id', 'name', 'value', 'price', 'quantity', 'customer_id', 'order_id']),
            '<table_name>': lambda: random.choice(['customers', 'orders', 'products', 'employees', 'departments']),
            '<column_name>': lambda: random.choice(['id', 'name', 'age', 'salary', 'price', 'quantity', 'date']),
            '<string_literal>': lambda: f"'{random.choice(['John', 'Alice', 'Bob', 'Test', 'Sample'])}'",
            '<number>': lambda: str(random.randint(1, 1000)),
            '<int_literal>': lambda: str(random.randint(1, 100)),
            '<float_literal>': lambda: f"{random.random() * 100:.2f}",
            '<bool_literal>': lambda: random.choice(['TRUE', 'FALSE']),
            '<data_type>': lambda: random.choice(['INTEGER', 'VARCHAR(50)', 'DECIMAL(10,2)', 'DATE', 'BOOLEAN']),
            '<comparison_op>': lambda: random.choice(['=', '<>', '!=', '<', '>', '<=', '>=']),
            '<arithmetic_op>': lambda: random.choice(['+', '-', '*', '/']),
            '<logical_op>': lambda: random.choice(['AND', 'OR']),
        }
        
        for pattern, generator in terminals.items():
            if pattern.lower() in symbol_lower:
                return generator()
                
        return symbol
    
    def generate_statement(self) -> str:
        """Generate a complete SQL statement."""
        statement = self.generate_from_symbol(self.grammar.start_symbol)
        
        # Ensure statement ends with semicolon if not present
        if not statement.strip().endswith(';'):
            statement += ';'
            
        # Clean up whitespace
        statement = re.sub(r'\s+', ' ', statement).strip()
        
        return statement
    
    def generate_diverse_statements(self, count: int) -> List[str]:
        """Generate diverse SQL statements targeting coverage."""
        statements = []
        
        # Generate statements targeting specific coverage areas
        coverage_patterns = [
            # Basic SELECT statements
            "SELECT * FROM <table_name>;",
            "SELECT <column_name> FROM <table_name> WHERE <condition>;",
            "SELECT <column_name>, <column_name> FROM <table_name> ORDER BY <column_name>;",
            
            # SELECT with clauses
            "SELECT <column_name>, COUNT(*) FROM <table_name> GROUP BY <column_name> HAVING <condition>;",
            "SELECT <column_name> FROM <table_name> LIMIT <number> OFFSET <number>;",
            
            # JOINs
            "SELECT t1.<column_name>, t2.<column_name> FROM <table_name> t1 INNER JOIN <table_name> t2 ON t1.id = t2.id;",
            "SELECT * FROM <table_name> t1 LEFT JOIN <table_name> t2 ON t1.id = t2.id WHERE t1.<column_name> IS NOT NULL;",
            "SELECT * FROM <table_name> t1 RIGHT JOIN <table_name> t2 ON t1.id = t2.id;",
            
            # Subqueries
            "SELECT * FROM <table_name> WHERE <column_name> IN (SELECT <column_name> FROM <table_name>);",
            "SELECT * FROM (SELECT <column_name> FROM <table_name>) AS subquery;",
            
            # Functions and expressions
            "SELECT COUNT(*), AVG(<column_name>), SUM(<column_name>) FROM <table_name>;",
            "SELECT <column_name>, CASE WHEN <condition> THEN <value> ELSE <value> END FROM <table_name>;",
            "SELECT COALESCE(<column_name>, <value>) FROM <table_name>;",
            "SELECT CAST(<column_name> AS <data_type>) FROM <table_name>;",
            
            # INSERT statements
            "INSERT INTO <table_name> (<column_name>, <column_name>) VALUES (<value>, <value>);",
            "INSERT INTO <table_name> SELECT * FROM <table_name> WHERE <condition>;",
            
            # UPDATE statements
            "UPDATE <table_name> SET <column_name> = <value> WHERE <condition>;",
            "UPDATE <table_name> SET <column_name> = <value>, <column_name> = <value> WHERE <condition>;",
            
            # DELETE statements
            "DELETE FROM <table_name> WHERE <condition>;",
            "DELETE FROM <table_name>;",
            
            # CREATE statements
            "CREATE TABLE <table_name> (<column_name> <data_type> PRIMARY KEY, <column_name> <data_type> NOT NULL);",
            "CREATE TABLE <table_name> (<column_name> <data_type>, <column_name> <data_type>, FOREIGN KEY (<column_name>) REFERENCES <table_name>(<column_name>));",
            
            # DROP statements
            "DROP TABLE IF EXISTS <table_name>;",
            "DROP TABLE <table_name>;",
            
            # Complex expressions
            "SELECT (<column_name> + <number>) * <number> FROM <table_name> WHERE <column_name> BETWEEN <number> AND <number>;",
            "SELECT * FROM <table_name> WHERE <column_name> LIKE '%pattern%' AND <column_name> IS NOT NULL;",
            
            # Multiple joins
            "SELECT t1.*, t2.*, t3.* FROM <table_name> t1 JOIN <table_name> t2 ON t1.id = t2.id JOIN <table_name> t3 ON t2.id = t3.id;",
            
            # Nested subqueries
            "SELECT * FROM <table_name> WHERE <column_name> = (SELECT MAX(<column_name>) FROM <table_name> WHERE <condition>);",
            
            # Window functions (if supported)
            "SELECT <column_name>, ROW_NUMBER() OVER (ORDER BY <column_name>) FROM <table_name>;",
        ]
        
        # Fill templates with actual values
        for pattern in coverage_patterns:
            if len(statements) >= count:
                break
                
            statement = pattern
            for _ in range(10):  # Try multiple times to generate valid statement
                # Replace placeholders
                while '<' in statement:
                    for match in re.findall(r'<[^>]+>', statement):
                        replacement = self._generate_terminal(match)
                        statement = statement.replace(match, replacement, 1)
                
                # Ensure uniqueness
                if statement not in self.generated and statement not in statements:
                    statements.append(statement)
                    self.generated.add(statement)
                    break
        
        # Generate additional random statements if needed
        while len(statements) < count:
            statement = self.generate_statement()
            if statement and statement not in self.generated:
                statements.append(statement)
                self.generated.add(statement)
                
        return statements

class ParserAnalyzer:
    """Analyze parser source code to identify coverage targets."""
    
    def __init__(self, parser_path: str):
        self.parser_path = parser_path
        self.functions = set()
        self.conditions = set()
        
    def analyze(self):
        """Analyze parser source files."""
        for file in ['parser.py', 'tokenizer.py', 'ast_nodes.py']:
            path = os.path.join(self.parser_path, file)
            if os.path.exists(path):
                self._analyze_file(path)
    
    def _analyze_file(self, filepath: str):
        """Analyze a single Python file."""
        with open(filepath, 'r') as f:
            try:
                tree = ast.parse(f.read())
            except:
                return
                
        # Collect function/method definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.functions.add(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                self.functions.add(node.name)
            elif isinstance(node, ast.ClassDef):
                for subnode in node.body:
                    if isinstance(subnode, ast.FunctionDef):
                        self.functions.add(f"{node.name}.{subnode.name}")
            
            # Collect conditional statements
            if isinstance(node, (ast.If, ast.While, ast.Assert)):
                self.conditions.add(self._get_condition_code(node))

    def _get_condition_code(self, node) -> str:
        """Extract condition code from AST node."""
        try:
            if isinstance(node, ast.If):
                return ast.unparse(node.test)
            elif isinstance(node, ast.While):
                return ast.unparse(node.test)
            elif isinstance(node, ast.Assert):
                return ast.unparse(node.test)
        except:
            return str(type(node))
        return str(type(node))

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        # Initialize components
        grammar_path = os.path.join(resources_path, 'sql_grammar.txt')
        parser_path = os.path.join(resources_path, 'sql_engine')
        
        # Analyze parser for coverage guidance
        analyzer = ParserAnalyzer(parser_path)
        analyzer.analyze()
        
        # Generate SQL statements
        generator = SQLGenerator(grammar_path)
        
        # Target ~40 statements for good efficiency bonus
        target_count = 40
        
        # Generate diverse statements
        statements = generator.generate_diverse_statements(target_count)
        
        # Ensure we have some variety in statement types
        if len(statements) < target_count:
            # Generate more random ones
            while len(statements) < target_count:
                stmt = generator.generate_statement()
                if stmt and stmt not in statements:
                    statements.append(stmt)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_statements = []
        for stmt in statements:
            if stmt not in seen:
                seen.add(stmt)
                unique_statements.append(stmt)
        
        return unique_statements[:target_count]