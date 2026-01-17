import os
import ast
import re
import random
from pathlib import Path
from collections import defaultdict
from itertools import product, combinations
import hashlib
import sys

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        # Read and analyze the grammar
        grammar_path = os.path.join(resources_path, 'sql_grammar.txt')
        with open(grammar_path, 'r') as f:
            grammar_content = f.read()
        
        # Parse the grammar to understand available constructs
        grammar = self._parse_grammar(grammar_content)
        
        # Analyze parser source code to understand coverage targets
        parser_path = os.path.join(resources_path, 'sql_engine', 'parser.py')
        with open(parser_path, 'r') as f:
            parser_code = f.read()
        
        # Generate comprehensive test cases
        test_cases = self._generate_test_cases(grammar, parser_code)
        
        # Optimize test cases for coverage
        optimized_cases = self._optimize_test_cases(test_cases)
        
        return optimized_cases
    
    def _parse_grammar(self, grammar_content: str) -> dict:
        """Parse BNF grammar into structured format"""
        grammar = {}
        lines = grammar_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '::=' in line:
                parts = line.split('::=', 1)
                non_terminal = parts[0].strip()
                productions = parts[1].strip().split('|')
                
                grammar[non_terminal] = []
                for prod in productions:
                    # Clean up the production
                    prod = prod.strip()
                    if prod:
                        # Handle optional groups [ ... ]
                        prod = re.sub(r'\[([^\]]+)\]', r'(?:\1)?', prod)
                        # Handle repetitions { ... }
                        prod = re.sub(r'\{([^}]+)\}', r'(?:\1)*', prod)
                        grammar[non_terminal].append(prod)
        
        return grammar
    
    def _generate_test_cases(self, grammar: dict, parser_code: str) -> list[str]:
        """Generate diverse SQL test cases based on grammar and parser analysis"""
        test_cases = []
        
        # Basic SELECT statements
        test_cases.extend([
            "SELECT 1",
            "SELECT * FROM t1",
            "SELECT a, b FROM t1",
            "SELECT a AS a1, b AS b1 FROM t1",
            "SELECT DISTINCT a FROM t1",
            "SELECT a FROM t1 WHERE b = 1",
            "SELECT a FROM t1 WHERE b > 1 AND c < 10",
            "SELECT a FROM t1 WHERE b = 1 OR c = 2",
            "SELECT a FROM t1 WHERE NOT b = 1",
            "SELECT a FROM t1 WHERE b IN (1, 2, 3)",
            "SELECT a FROM t1 WHERE b BETWEEN 1 AND 10",
            "SELECT a FROM t1 WHERE b LIKE 'test%'",
            "SELECT a FROM t1 WHERE b IS NULL",
            "SELECT a FROM t1 WHERE b IS NOT NULL",
        ])
        
        # JOIN operations
        test_cases.extend([
            "SELECT * FROM t1 INNER JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t1 LEFT JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t1 RIGHT JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t1 FULL OUTER JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t1 CROSS JOIN t2",
            "SELECT * FROM t1, t2 WHERE t1.id = t2.id",
            "SELECT * FROM t1 JOIN t2 USING (id)",
            "SELECT * FROM t1 NATURAL JOIN t2",
            "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id JOIN t3 ON t2.id = t3.id",
        ])
        
        # GROUP BY and aggregates
        test_cases.extend([
            "SELECT a, COUNT(*) FROM t1 GROUP BY a",
            "SELECT a, SUM(b) FROM t1 GROUP BY a",
            "SELECT a, AVG(b) FROM t1 GROUP BY a",
            "SELECT a, MIN(b), MAX(b) FROM t1 GROUP BY a",
            "SELECT a, COUNT(*) FROM t1 GROUP BY a HAVING COUNT(*) > 1",
            "SELECT a, b, COUNT(*) FROM t1 GROUP BY a, b",
            "SELECT a, SUM(b) as total FROM t1 GROUP BY a ORDER BY total DESC",
        ])
        
        # ORDER BY and LIMIT
        test_cases.extend([
            "SELECT * FROM t1 ORDER BY a",
            "SELECT * FROM t1 ORDER BY a ASC",
            "SELECT * FROM t1 ORDER BY a DESC",
            "SELECT * FROM t1 ORDER BY a, b DESC",
            "SELECT * FROM t1 LIMIT 10",
            "SELECT * FROM t1 LIMIT 10 OFFSET 5",
            "SELECT * FROM t1 ORDER BY a LIMIT 10",
            "SELECT * FROM t1 ORDER BY a LIMIT 10 OFFSET 20",
        ])
        
        # Subqueries
        test_cases.extend([
            "SELECT * FROM t1 WHERE a IN (SELECT b FROM t2)",
            "SELECT * FROM t1 WHERE a > (SELECT AVG(b) FROM t2)",
            "SELECT * FROM t1 WHERE EXISTS (SELECT 1 FROM t2 WHERE t2.id = t1.id)",
            "SELECT * FROM (SELECT a, b FROM t1) AS sub",
            "SELECT a, (SELECT MAX(b) FROM t2 WHERE t2.id = t1.id) FROM t1",
            "SELECT * FROM t1 WHERE a = ANY (SELECT b FROM t2)",
            "SELECT * FROM t1 WHERE a = ALL (SELECT b FROM t2)",
        ])
        
        # Set operations
        test_cases.extend([
            "SELECT a FROM t1 UNION SELECT b FROM t2",
            "SELECT a FROM t1 UNION ALL SELECT b FROM t2",
            "SELECT a FROM t1 INTERSECT SELECT b FROM t2",
            "SELECT a FROM t1 EXCEPT SELECT b FROM t2",
            "SELECT a FROM t1 UNION SELECT b FROM t2 ORDER BY a",
            "(SELECT a FROM t1) UNION (SELECT b FROM t2)",
        ])
        
        # Complex expressions
        test_cases.extend([
            "SELECT a + b FROM t1",
            "SELECT a - b FROM t1",
            "SELECT a * b FROM t1",
            "SELECT a / b FROM t1",
            "SELECT a % b FROM t1",
            "SELECT -a FROM t1",
            "SELECT +a FROM t1",
            "SELECT a || b FROM t1",
            "SELECT (a + b) * c FROM t1",
            "SELECT CASE WHEN a > 0 THEN 'positive' WHEN a < 0 THEN 'negative' ELSE 'zero' END FROM t1",
            "SELECT COALESCE(a, b, 0) FROM t1",
            "SELECT NULLIF(a, b) FROM t1",
            "SELECT a COLLATE NOCASE FROM t1",
        ])
        
        # Functions
        test_cases.extend([
            "SELECT COUNT(*) FROM t1",
            "SELECT COUNT(DISTINCT a) FROM t1",
            "SELECT SUM(a) FROM t1",
            "SELECT AVG(a) FROM t1",
            "SELECT MIN(a) FROM t1",
            "SELECT MAX(a) FROM t1",
            "SELECT ABS(a) FROM t1",
            "SELECT ROUND(a, 2) FROM t1",
            "SELECT UPPER(a) FROM t1",
            "SELECT LOWER(a) FROM t1",
            "SELECT LENGTH(a) FROM t1",
            "SELECT SUBSTR(a, 1, 3) FROM t1",
            "SELECT TRIM(a) FROM t1",
            "SELECT DATE('now')",
            "SELECT TIME('now')",
            "SELECT CAST(a AS INTEGER) FROM t1",
            "SELECT TYPEOF(a) FROM t1",
        ])
        
        # Multiple tables and aliases
        test_cases.extend([
            "SELECT t1.a, t2.b FROM t1, t2",
            "SELECT a.a, b.b FROM t1 AS a, t2 AS b",
            "SELECT * FROM t1 AS t, t2 AS u WHERE t.id = u.id",
        ])
        
        # Nested queries with all constructs
        test_cases.extend([
            "SELECT a, COUNT(*) FROM (SELECT * FROM t1 WHERE b > 0) AS sub GROUP BY a HAVING COUNT(*) > 1 ORDER BY a",
            "SELECT * FROM t1 WHERE id IN (SELECT id FROM t2 WHERE value > (SELECT AVG(value) FROM t3))",
            "SELECT a, (SELECT MAX(b) FROM t2) as max_b FROM t1 WHERE c = (SELECT MIN(d) FROM t3) GROUP BY a HAVING COUNT(*) > 0 ORDER BY max_b DESC LIMIT 10",
        ])
        
        # Window functions (if supported by grammar)
        test_cases.extend([
            "SELECT a, ROW_NUMBER() OVER (ORDER BY b) FROM t1",
            "SELECT a, RANK() OVER (PARTITION BY c ORDER BY b) FROM t1",
            "SELECT a, SUM(b) OVER (PARTITION BY c ORDER BY d) FROM t1",
        ])
        
        # Common Table Expressions (if supported)
        test_cases.extend([
            "WITH cte AS (SELECT * FROM t1) SELECT * FROM cte",
            "WITH cte1 AS (SELECT a FROM t1), cte2 AS (SELECT b FROM t2) SELECT * FROM cte1 JOIN cte2 ON cte1.a = cte2.b",
        ])
        
        # INSERT, UPDATE, DELETE statements
        test_cases.extend([
            "INSERT INTO t1 VALUES (1, 2, 3)",
            "INSERT INTO t1 (a, b, c) VALUES (1, 2, 3)",
            "INSERT INTO t1 SELECT * FROM t2",
            "UPDATE t1 SET a = 1 WHERE b = 2",
            "UPDATE t1 SET a = 1, b = 2 WHERE c = 3",
            "DELETE FROM t1 WHERE a = 1",
            "DELETE FROM t1",
        ])
        
        # CREATE statements
        test_cases.extend([
            "CREATE TABLE t1 (a INTEGER, b TEXT, c REAL)",
            "CREATE TABLE t1 (a INTEGER PRIMARY KEY, b TEXT NOT NULL, c REAL UNIQUE)",
            "CREATE TABLE t1 (a INTEGER, b TEXT, FOREIGN KEY (a) REFERENCES t2(id))",
            "CREATE INDEX idx1 ON t1 (a)",
            "CREATE UNIQUE INDEX idx2 ON t1 (a, b)",
            "CREATE VIEW v1 AS SELECT * FROM t1",
        ])
        
        # DROP statements
        test_cases.extend([
            "DROP TABLE t1",
            "DROP INDEX idx1",
            "DROP VIEW v1",
        ])
        
        # Transactions
        test_cases.extend([
            "BEGIN TRANSACTION",
            "COMMIT",
            "ROLLBACK",
            "SAVEPOINT sp1",
            "RELEASE SAVEPOINT sp1",
            "ROLLBACK TO SAVEPOINT sp1",
        ])
        
        # Pragmas and special commands
        test_cases.extend([
            "PRAGMA foreign_keys = ON",
            "PRAGMA table_info(t1)",
            "VACUUM",
            "ANALYZE",
            "EXPLAIN SELECT * FROM t1",
            "EXPLAIN QUERY PLAN SELECT * FROM t1",
        ])
        
        # Edge cases and unusual syntax
        test_cases.extend([
            "SELECT",
            "SELECT 1; SELECT 2",
            "SELECT 'test' || 'string'",
            "SELECT 1.234e+10",
            "SELECT 0x1234",
            "SELECT NULL",
            "SELECT * FROM (VALUES (1, 2), (3, 4))",
            "SELECT * FROM t1 WHERE a IN ()",
            "SELECT * FROM t1 WHERE a = (SELECT 1 UNION SELECT 2 LIMIT 1)",
            "SELECT * FROM t1 WITH (NOLOCK)",
        ])
        
        return test_cases
    
    def _optimize_test_cases(self, test_cases: list[str]) -> list[str]:
        """Optimize test cases to maximize coverage with fewer statements"""
        # Remove duplicates
        unique_cases = []
        seen = set()
        
        for case in test_cases:
            # Normalize whitespace for deduplication
            normalized = re.sub(r'\s+', ' ', case.strip())
            if normalized not in seen:
                seen.add(normalized)
                unique_cases.append(case)
        
        # Prioritize test cases that cover diverse syntax
        prioritized = []
        
        # Group by statement type
        groups = defaultdict(list)
        for case in unique_cases:
            first_word = case.split()[0].upper() if case.strip() else ''
            groups[first_word].append(case)
        
        # Take representative samples from each group
        max_per_group = 15
        for group_name, cases in groups.items():
            if group_name in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP']:
                # For major statement types, take more samples
                sampled = cases[:max_per_group]
            else:
                # For others, take fewer
                sampled = cases[:min(5, len(cases))]
            prioritized.extend(sampled)
        
        # Ensure we have a good mix of complexity levels
        simple_cases = []
        medium_cases = []
        complex_cases = []
        
        for case in prioritized:
            length = len(case)
            if length < 50:
                simple_cases.append(case)
            elif length < 200:
                medium_cases.append(case)
            else:
                complex_cases.append(case)
        
        # Mix cases of different complexity
        optimized = []
        max_total = 150  # Target number of test cases
        
        # Add all complex cases (they likely cover more code)
        optimized.extend(complex_cases)
        
        # Add medium cases
        optimized.extend(medium_cases[:max(0, max_total - len(optimized))])
        
        # Add simple cases to fill up if needed
        remaining = max_total - len(optimized)
        if remaining > 0:
            optimized.extend(simple_cases[:remaining])
        
        # Ensure we don't exceed target
        return optimized[:max_total]