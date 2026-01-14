import os
import re
import itertools
from typing import Dict, List, Set, Tuple, Optional
import random
import ast
import inspect
from collections import defaultdict

class GrammarRule:
    def __init__(self, name: str, productions: List[List[str]]):
        self.name = name
        self.productions = productions
        self.is_terminal = False
        self.terminal_value = None

class Solution:
    def __init__(self):
        self.grammar: Dict[str, GrammarRule] = {}
        self.start_symbol = "sql_stmt"
        self.max_depth = 8
        self.max_statements = 100
        self.statements_generated = []
        
    def solve(self, resources_path: str) -> List[str]:
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        self.load_grammar(grammar_path)
        
        # Analyze parser code to identify coverage targets
        parser_path = os.path.join(resources_path, "sql_engine", "parser.py")
        tokenizer_path = os.path.join(resources_path, "sql_engine", "tokenizer.py")
        ast_path = os.path.join(resources_path, "sql_engine", "ast_nodes.py")
        
        self.analyze_parser(parser_path, tokenizer_path, ast_path)
        
        # Generate comprehensive test cases
        self.generate_test_cases()
        
        return self.statements_generated[:self.max_statements]
    
    def load_grammar(self, grammar_path: str):
        with open(grammar_path, 'r') as f:
            lines = f.readlines()
        
        current_rule = None
        current_productions = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if '::=' in line:
                if current_rule:
                    self.grammar[current_rule] = GrammarRule(current_rule, current_productions)
                
                parts = line.split('::=', 1)
                current_rule = parts[0].strip()
                current_productions = []
                
                prod_str = parts[1].strip()
                if prod_str:
                    productions = self._parse_production(prod_str)
                    current_productions.extend(productions)
            elif line.startswith('|'):
                prod_str = line[1:].strip()
                if prod_str:
                    productions = self._parse_production(prod_str)
                    current_productions.extend(productions)
        
        if current_rule and current_productions:
            self.grammar[current_rule] = GrammarRule(current_rule, current_productions)
    
    def _parse_production(self, prod_str: str) -> List[List[str]]:
        productions = []
        # Split by '|' but not inside quotes or brackets
        parts = []
        current = []
        depth = 0
        in_quote = False
        
        for char in prod_str:
            if char == "'" and (not current or current[-1] != '\\'):
                in_quote = not in_quote
            elif char == '[' and not in_quote:
                depth += 1
            elif char == ']' and not in_quote:
                depth -= 1
            elif char == '|' and depth == 0 and not in_quote:
                parts.append(''.join(current).strip())
                current = []
                continue
            current.append(char)
        
        if current:
            parts.append(''.join(current).strip())
        
        for part in parts:
            if part:
                symbols = []
                current_symbol = []
                depth = 0
                in_quote = False
                
                for char in part:
                    if char == "'" and (not current_symbol or current_symbol[-1] != '\\'):
                        in_quote = not in_quote
                        current_symbol.append(char)
                    elif char == '[' and not in_quote:
                        if depth == 0 and current_symbol:
                            symbols.append(''.join(current_symbol).strip())
                            current_symbol = [char]
                        else:
                            current_symbol.append(char)
                        depth += 1
                    elif char == ']' and not in_quote:
                        depth -= 1
                        current_symbol.append(char)
                        if depth == 0:
                            symbols.append(''.join(current_symbol).strip())
                            current_symbol = []
                    elif char == ' ' and depth == 0 and not in_quote:
                        if current_symbol:
                            symbols.append(''.join(current_symbol).strip())
                            current_symbol = []
                    else:
                        current_symbol.append(char)
                
                if current_symbol:
                    symbols.append(''.join(current_symbol).strip())
                
                if symbols:
                    productions.append(symbols)
        
        return productions
    
    def analyze_parser(self, parser_path: str, tokenizer_path: str, ast_path: str):
        # Read parser code to understand what constructs exist
        with open(parser_path, 'r') as f:
            self.parser_code = f.read()
        
        # Extract function names and conditional branches
        self.parser_functions = []
        self.conditional_patterns = []
        
        # Parse AST to find function definitions
        try:
            tree = ast.parse(self.parser_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self.parser_functions.append(node.name)
                
                # Find conditional statements
                if isinstance(node, ast.If):
                    self.conditional_patterns.append(
                        (node.lineno, self._get_condition_string(node))
                    )
        except:
            pass
        
        # Common SQL constructs to cover
        self.target_constructs = [
            "SELECT", "INSERT", "UPDATE", "DELETE",
            "WHERE", "GROUP BY", "HAVING", "ORDER BY", "LIMIT",
            "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN",
            "SUBQUERY", "UNION", "INTERSECT", "EXCEPT",
            "FUNCTIONS", "AGGREGATES", "WINDOW_FUNCTIONS",
            "CASE", "CAST", "COALESCE",
            "CREATE TABLE", "CREATE INDEX", "DROP TABLE",
            "ALTER TABLE", "TRANSACTIONS"
        ]
    
    def _get_condition_string(self, node: ast.If) -> str:
        try:
            source = self.parser_code.split('\n')[node.lineno - 1]
            return source.strip()
        except:
            return ""
    
    def generate_test_cases(self):
        # Generate statements for different SQL constructs
        test_cases = []
        
        # 1. Basic SELECT statements
        test_cases.extend(self._generate_select_statements())
        
        # 2. Complex SELECT with various clauses
        test_cases.extend(self._generate_complex_select())
        
        # 3. JOIN statements
        test_cases.extend(self._generate_join_statements())
        
        # 4. Subqueries
        test_cases.extend(self._generate_subqueries())
        
        # 5. Set operations
        test_cases.extend(self._generate_set_operations())
        
        # 6. DML statements
        test_cases.extend(self._generate_dml_statements())
        
        # 7. DDL statements
        test_cases.extend(self._generate_ddl_statements())
        
        # 8. Functions and expressions
        test_cases.extend(self._generate_function_calls())
        
        # 9. Edge cases and special syntax
        test_cases.extend(self._generate_edge_cases())
        
        # 10. Transaction statements
        test_cases.extend(self._generate_transaction_statements())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_cases = []
        for case in test_cases:
            if case not in seen:
                seen.add(case)
                unique_cases.append(case)
        
        self.statements_generated = unique_cases
    
    def _generate_select_statements(self) -> List[str]:
        cases = [
            # Basic selects
            "SELECT 1",
            "SELECT * FROM t1",
            "SELECT a, b, c FROM t1",
            "SELECT a AS alias1, b AS alias2 FROM t1",
            
            # With WHERE
            "SELECT * FROM t1 WHERE a = 1",
            "SELECT * FROM t1 WHERE a > 5 AND b < 10",
            "SELECT * FROM t1 WHERE a BETWEEN 1 AND 10",
            "SELECT * FROM t1 WHERE a IN (1, 2, 3)",
            "SELECT * FROM t1 WHERE a LIKE '%test%'",
            "SELECT * FROM t1 WHERE a IS NULL",
            "SELECT * FROM t1 WHERE a IS NOT NULL",
            
            # With DISTINCT
            "SELECT DISTINCT a FROM t1",
            "SELECT DISTINCT a, b FROM t1 WHERE c > 5",
        ]
        
        # Add more variations
        for col in ["a", "b", "c"]:
            for op in ["=", ">", "<", ">=", "<=", "!="]:
                cases.append(f"SELECT * FROM t1 WHERE {col} {op} 10")
        
        return cases
    
    def _generate_complex_select(self) -> List[str]:
        cases = [
            # GROUP BY and aggregates
            "SELECT a, COUNT(*) FROM t1 GROUP BY a",
            "SELECT a, SUM(b) FROM t1 GROUP BY a",
            "SELECT a, AVG(b), MAX(c), MIN(d) FROM t1 GROUP BY a",
            "SELECT a, COUNT(*) FROM t1 GROUP BY a HAVING COUNT(*) > 5",
            
            # ORDER BY
            "SELECT * FROM t1 ORDER BY a",
            "SELECT * FROM t1 ORDER BY a DESC",
            "SELECT * FROM t1 ORDER BY a, b DESC",
            
            # LIMIT and OFFSET
            "SELECT * FROM t1 LIMIT 10",
            "SELECT * FROM t1 LIMIT 10 OFFSET 5",
            
            # All clauses combined
            "SELECT a, COUNT(*) as cnt FROM t1 WHERE b > 10 GROUP BY a HAVING cnt > 5 ORDER BY cnt DESC LIMIT 10",
        ]
        
        # Add variations with different aggregate functions
        aggregates = ["COUNT", "SUM", "AVG", "MAX", "MIN"]
        for agg in aggregates:
            cases.append(f"SELECT a, {agg}(b) FROM t1 GROUP BY a")
        
        return cases
    
    def _generate_join_statements(self) -> List[str]:
        cases = [
            # INNER JOIN
            "SELECT * FROM t1 INNER JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id",
            
            # LEFT JOIN
            "SELECT * FROM t1 LEFT JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t1 LEFT OUTER JOIN t2 ON t1.id = t2.id",
            
            # RIGHT JOIN
            "SELECT * FROM t1 RIGHT JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t1 RIGHT OUTER JOIN t2 ON t1.id = t2.id",
            
            # FULL JOIN
            "SELECT * FROM t1 FULL JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t1 FULL OUTER JOIN t2 ON t1.id = t2.id",
            
            # CROSS JOIN
            "SELECT * FROM t1 CROSS JOIN t2",
            
            # Multiple joins
            "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id JOIN t3 ON t2.id = t3.id",
            
            # Complex join conditions
            "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id AND t1.name = t2.name",
            "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id WHERE t1.a > 10",
            
            # NATURAL JOIN
            "SELECT * FROM t1 NATURAL JOIN t2",
        ]
        
        # Add variations with USING clause
        cases.append("SELECT * FROM t1 JOIN t2 USING (id)")
        cases.append("SELECT * FROM t1 JOIN t2 USING (id, name)")
        
        return cases
    
    def _generate_subqueries(self) -> List[str]:
        cases = [
            # Scalar subquery
            "SELECT (SELECT MAX(b) FROM t2) FROM t1",
            
            # IN subquery
            "SELECT * FROM t1 WHERE a IN (SELECT a FROM t2)",
            "SELECT * FROM t1 WHERE a NOT IN (SELECT a FROM t2)",
            
            # EXISTS subquery
            "SELECT * FROM t1 WHERE EXISTS (SELECT 1 FROM t2 WHERE t1.id = t2.id)",
            "SELECT * FROM t1 WHERE NOT EXISTS (SELECT 1 FROM t2 WHERE t1.id = t2.id)",
            
            # Subquery in FROM
            "SELECT * FROM (SELECT a, b FROM t1) AS sub",
            "SELECT sub.a FROM (SELECT a FROM t1 WHERE b > 10) AS sub",
            
            # Correlated subquery
            "SELECT a, (SELECT MAX(b) FROM t2 WHERE t2.id = t1.id) FROM t1",
            
            # Subquery with comparison
            "SELECT * FROM t1 WHERE a > (SELECT AVG(a) FROM t2)",
            "SELECT * FROM t1 WHERE a = ANY (SELECT a FROM t2)",
            "SELECT * FROM t1 WHERE a > ALL (SELECT a FROM t2)",
        ]
        
        # Multi-level subqueries
        cases.append("SELECT * FROM (SELECT * FROM (SELECT * FROM t1) AS sub1) AS sub2")
        
        return cases
    
    def _generate_set_operations(self) -> List[str]:
        cases = [
            # UNION
            "SELECT a FROM t1 UNION SELECT a FROM t2",
            "SELECT a FROM t1 UNION ALL SELECT a FROM t2",
            
            # INTERSECT
            "SELECT a FROM t1 INTERSECT SELECT a FROM t2",
            "SELECT a FROM t1 INTERSECT ALL SELECT a FROM t2",
            
            # EXCEPT
            "SELECT a FROM t1 EXCEPT SELECT a FROM t2",
            "SELECT a FROM t1 EXCEPT ALL SELECT a FROM t2",
            
            # Multiple set operations
            "SELECT a FROM t1 UNION SELECT a FROM t2 INTERSECT SELECT a FROM t3",
            
            # With ORDER BY and LIMIT
            "(SELECT a FROM t1) UNION (SELECT a FROM t2) ORDER BY a LIMIT 10",
        ]
        
        # Complex set operations with WHERE
        cases.append("SELECT a FROM t1 WHERE b > 10 UNION SELECT a FROM t2 WHERE c < 5")
        
        return cases
    
    def _generate_dml_statements(self) -> List[str]:
        cases = [
            # INSERT
            "INSERT INTO t1 VALUES (1, 'a', 3.14)",
            "INSERT INTO t1 (a, b, c) VALUES (1, 'a', 3.14)",
            "INSERT INTO t1 VALUES (1, 'a'), (2, 'b'), (3, 'c')",
            "INSERT INTO t1 SELECT * FROM t2",
            
            # UPDATE
            "UPDATE t1 SET a = 1",
            "UPDATE t1 SET a = 1, b = 'test' WHERE c > 10",
            "UPDATE t1 SET a = (SELECT MAX(a) FROM t2)",
            
            # DELETE
            "DELETE FROM t1",
            "DELETE FROM t1 WHERE a > 10",
            "DELETE FROM t1 WHERE a IN (SELECT a FROM t2)",
            
            # MERGE/UPSERT (if supported)
            "INSERT INTO t1 (id, name) VALUES (1, 'a') ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
        ]
        
        return cases
    
    def _generate_ddl_statements(self) -> List[str]:
        cases = [
            # CREATE TABLE
            "CREATE TABLE t1 (id INT, name VARCHAR(50))",
            "CREATE TABLE t1 (id INT PRIMARY KEY, name VARCHAR(50) NOT NULL)",
            "CREATE TABLE t1 (id INT, name VARCHAR(50), PRIMARY KEY (id))",
            "CREATE TABLE t1 (id INT, name VARCHAR(50), FOREIGN KEY (id) REFERENCES t2(id))",
            "CREATE TABLE t1 AS SELECT * FROM t2",
            "CREATE TEMPORARY TABLE temp1 (id INT)",
            "CREATE TABLE IF NOT EXISTS t1 (id INT)",
            
            # ALTER TABLE
            "ALTER TABLE t1 ADD COLUMN new_col INT",
            "ALTER TABLE t1 DROP COLUMN old_col",
            "ALTER TABLE t1 RENAME TO t2",
            "ALTER TABLE t1 RENAME COLUMN old_name TO new_name",
            "ALTER TABLE t1 ADD CONSTRAINT pk PRIMARY KEY (id)",
            
            # DROP TABLE
            "DROP TABLE t1",
            "DROP TABLE IF EXISTS t1",
            "DROP TABLE t1 CASCADE",
            
            # CREATE INDEX
            "CREATE INDEX idx1 ON t1 (id)",
            "CREATE UNIQUE INDEX idx1 ON t1 (id, name)",
            "CREATE INDEX IF NOT EXISTS idx1 ON t1 (id)",
            "DROP INDEX idx1",
            
            # CREATE VIEW
            "CREATE VIEW v1 AS SELECT * FROM t1",
            "CREATE OR REPLACE VIEW v1 AS SELECT id, name FROM t1",
            "DROP VIEW v1",
        ]
        
        # Add more complex constraints
        cases.append("CREATE TABLE t1 (id INT CHECK (id > 0), age INT CHECK (age BETWEEN 0 AND 120))")
        cases.append("CREATE TABLE t1 (id INT UNIQUE, name VARCHAR(50) DEFAULT 'unknown')")
        
        return cases
    
    def _generate_function_calls(self) -> List[str]:
        cases = [
            # Scalar functions
            "SELECT ABS(-1)",
            "SELECT LOWER('HELLO')",
            "SELECT UPPER('hello')",
            "SELECT SUBSTR('hello', 1, 3)",
            "SELECT COALESCE(NULL, 'default')",
            "SELECT NULLIF(1, 1)",
            "SELECT CAST(1 AS VARCHAR)",
            "SELECT CONCAT('a', 'b', 'c')",
            
            # Math functions
            "SELECT ROUND(3.14159, 2)",
            "SELECT CEIL(3.14)",
            "SELECT FLOOR(3.14)",
            "SELECT MOD(10, 3)",
            "SELECT POWER(2, 3)",
            "SELECT SQRT(16)",
            
            # Date functions
            "SELECT CURRENT_DATE",
            "SELECT CURRENT_TIMESTAMP",
            "SELECT DATE('2023-01-01')",
            "SELECT EXTRACT(YEAR FROM CURRENT_DATE)",
            
            # String functions
            "SELECT LENGTH('hello')",
            "SELECT TRIM('  hello  ')",
            "SELECT REPLACE('hello', 'l', 'x')",
            "SELECT INSTR('hello', 'e')",
            
            # Aggregate functions in different contexts
            "SELECT COUNT(*) FROM t1",
            "SELECT COUNT(DISTINCT a) FROM t1",
            "SELECT GROUP_CONCAT(a) FROM t1",
            
            # Window functions
            "SELECT a, ROW_NUMBER() OVER (ORDER BY a) FROM t1",
            "SELECT a, RANK() OVER (ORDER BY a) FROM t1",
            "SELECT a, DENSE_RANK() OVER (ORDER BY a) FROM t1",
            "SELECT a, SUM(b) OVER (PARTITION BY c ORDER BY d) FROM t1",
            
            # CASE expressions
            "SELECT CASE WHEN a > 10 THEN 'high' WHEN a > 5 THEN 'medium' ELSE 'low' END FROM t1",
            "SELECT CASE a WHEN 1 THEN 'one' WHEN 2 THEN 'two' ELSE 'other' END FROM t1",
        ]
        
        # Nested function calls
        cases.append("SELECT UPPER(LOWER('Mixed'))")
        cases.append("SELECT ABS(ROUND(-3.14159, 2))")
        
        return cases
    
    def _generate_edge_cases(self) -> List[str]:
        cases = [
            # Empty values
            "SELECT NULL",
            "SELECT ''",
            "SELECT 0",
            
            # Boolean expressions
            "SELECT 1 = 1",
            "SELECT 1 <> 2",
            "SELECT 1 < 2",
            "SELECT 1 <= 1",
            "SELECT NOT (1 = 2)",
            "SELECT 1 = 1 AND 2 = 2",
            "SELECT 1 = 1 OR 2 = 3",
            
            # Type mixing
            "SELECT 1 + '2'",
            "SELECT 'a' || 'b'",
            
            # Parentheses
            "SELECT (1 + 2) * 3",
            "SELECT * FROM (t1)",
            
            # Star with qualifier
            "SELECT t1.* FROM t1",
            
            # Aliases without AS
            "SELECT a alias1 FROM t1",
            "SELECT a alias1, b alias2 FROM t1",
            
            # Complex expressions
            "SELECT (a + b) * c / d FROM t1",
            "SELECT -a FROM t1",
            "SELECT +a FROM t1",
            
            # Special values
            "SELECT TRUE, FALSE",
            "SELECT -3.14e-10",
            
            # Empty table list
            "SELECT 1, 2, 3",
            
            # With comments
            "SELECT /* comment */ a FROM t1",
            "SELECT a -- inline comment\nFROM t1",
            "SELECT a FROM t1 WHERE b = 1 /* multi-line\ncomment */",
        ]
        
        # Multiple statements (if supported)
        cases.append("SELECT 1; SELECT 2")
        
        return cases
    
    def _generate_transaction_statements(self) -> List[str]:
        cases = [
            "BEGIN TRANSACTION",
            "BEGIN",
            "COMMIT",
            "ROLLBACK",
            "SAVEPOINT sp1",
            "ROLLBACK TO SAVEPOINT sp1",
            "RELEASE SAVEPOINT sp1",
            "START TRANSACTION",
            "COMMIT TRANSACTION",
            "ROLLBACK TRANSACTION",
        ]
        
        return cases