import os
import sys
import ast
import inspect
import random
from typing import List, Dict, Set, Tuple, Optional, Any
from pathlib import Path
import itertools
import re

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        """
        Return SQL test cases designed to maximize parser coverage.
        """
        try:
            # Load grammar and analyze parser
            grammar_path = os.path.join(resources_path, "sql_grammar.txt")
            engine_path = os.path.join(resources_path, "sql_engine")
            
            # Add engine to path to import it
            sys.path.insert(0, resources_path)
            sys.path.insert(0, engine_path)
            
            # Import the parser module
            from sql_engine import parser, tokenizer, ast_nodes
            
            # Analyze parser source for coverage hints
            parser_source = self._get_source_files(engine_path)
            coverage_hints = self._analyze_parser_structure(parser_source)
            
            # Generate comprehensive test cases
            test_cases = self._generate_comprehensive_tests(coverage_hints)
            
            # Add edge cases and specific patterns
            edge_cases = self._generate_edge_cases(coverage_hints)
            test_cases.extend(edge_cases)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_cases = []
            for case in test_cases:
                if case not in seen:
                    seen.add(case)
                    unique_cases.append(case)
            
            return unique_cases[:100]  # Limit to reasonable number
            
        except Exception as e:
            # Fallback to basic SQL coverage if analysis fails
            return self._get_basic_coverage_sql()
    
    def _get_source_files(self, engine_path: str) -> Dict[str, str]:
        """Read source code files for analysis."""
        sources = {}
        for file in ["parser.py", "tokenizer.py", "ast_nodes.py"]:
            path = os.path.join(engine_path, file)
            if os.path.exists(path):
                with open(path, "r") as f:
                    sources[file] = f.read()
        return sources
    
    def _analyze_parser_structure(self, sources: Dict[str, str]) -> Dict[str, Any]:
        """Analyze parser source to understand structure and coverage needs."""
        hints = {
            "functions": set(),
            "classes": set(),
            "keywords": set(),
            "patterns": set(),
            "complexities": set()
        }
        
        # Extract SQL keywords from parser
        parser_code = sources.get("parser.py", "")
        tokenizer_code = sources.get("tokenizer.py", "")
        
        # Look for token definitions
        keyword_patterns = [
            r"['\"](SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|JOIN|UNION|INTERSECT|EXCEPT|WITH)['\"]",
            r"['\"](GROUP|ORDER|BY|HAVING|LIMIT|OFFSET|DISTINCT)['\"]",
            r"['\"](INNER|LEFT|RIGHT|FULL|OUTER|CROSS|NATURAL)['\"]",
            r"['\"](AND|OR|NOT|IN|BETWEEN|LIKE|IS|NULL|TRUE|FALSE)['\"]",
            r"['\"](ASC|DESC|AS|ON|USING)['\"]",
            r"['\"](INTEGER|VARCHAR|TEXT|REAL|NUMERIC|BOOLEAN|DATE|TIMESTAMP)['\"]",
            r"['\"](PRIMARY|FOREIGN|KEY|REFERENCES|UNIQUE|CHECK|DEFAULT)['\"]",
        ]
        
        for pattern in keyword_patterns:
            matches = re.findall(pattern, parser_code + tokenizer_code)
            for match in matches:
                if isinstance(match, tuple):
                    for m in match:
                        hints["keywords"].add(m.upper())
                else:
                    hints["keywords"].add(match.upper())
        
        # Look for function definitions that might need coverage
        func_pattern = r"def\s+(\w+)\s*\("
        for match in re.finditer(func_pattern, parser_code):
            hints["functions"].add(match.group(1))
        
        # Look for AST node classes
        ast_code = sources.get("ast_nodes.py", "")
        class_pattern = r"class\s+(\w+)\s*[:\(]"
        for match in re.finditer(class_pattern, ast_code):
            hints["classes"].add(match.group(1))
        
        # Detect complexity patterns
        complexity_indicators = [
            "parse_subquery", "parse_join", "parse_expression",
            "parse_function", "parse_case", "parse_cte"
        ]
        for indicator in complexity_indicators:
            if indicator in parser_code.lower():
                hints["complexities"].add(indicator.split("_")[1])
        
        return hints
    
    def _generate_comprehensive_tests(self, hints: Dict[str, Any]) -> List[str]:
        """Generate comprehensive SQL test cases."""
        test_cases = []
        
        # Basic SELECT statements
        basic_selects = [
            "SELECT 1",
            "SELECT * FROM users",
            "SELECT id, name FROM users",
            "SELECT id, name AS username FROM users",
            "SELECT DISTINCT name FROM users",
            "SELECT COUNT(*) FROM users",
            "SELECT MAX(salary) FROM employees",
        ]
        test_cases.extend(basic_selects)
        
        # WHERE clause variations
        where_tests = [
            "SELECT * FROM users WHERE id = 1",
            "SELECT * FROM users WHERE age > 18",
            "SELECT * FROM users WHERE name = 'John'",
            "SELECT * FROM users WHERE active = TRUE",
            "SELECT * FROM users WHERE salary IS NULL",
            "SELECT * FROM users WHERE age BETWEEN 18 AND 65",
            "SELECT * FROM users WHERE name LIKE 'J%'",
            "SELECT * FROM users WHERE id IN (1, 2, 3)",
            "SELECT * FROM users WHERE department = 'IT' AND salary > 50000",
            "SELECT * FROM users WHERE department = 'IT' OR department = 'HR'",
            "SELECT * FROM users WHERE NOT inactive",
        ]
        test_cases.extend(where_tests)
        
        # JOIN operations
        join_tests = [
            "SELECT * FROM users JOIN orders ON users.id = orders.user_id",
            "SELECT * FROM users LEFT JOIN orders ON users.id = orders.user_id",
            "SELECT * FROM users RIGHT JOIN orders ON users.id = orders.user_id",
            "SELECT * FROM users INNER JOIN orders ON users.id = orders.user_id",
            "SELECT * FROM users FULL OUTER JOIN orders ON users.id = orders.user_id",
            "SELECT * FROM users CROSS JOIN orders",
            "SELECT * FROM users NATURAL JOIN orders",
            "SELECT * FROM a JOIN b ON a.id = b.a_id JOIN c ON b.id = c.b_id",
        ]
        test_cases.extend(join_tests)
        
        # GROUP BY and aggregates
        group_tests = [
            "SELECT department, COUNT(*) FROM employees GROUP BY department",
            "SELECT department, AVG(salary) FROM employees GROUP BY department",
            "SELECT department, SUM(salary) FROM employees GROUP BY department",
            "SELECT department, MIN(salary), MAX(salary) FROM employees GROUP BY department",
            "SELECT department, COUNT(*) FROM employees GROUP BY department HAVING COUNT(*) > 5",
            "SELECT YEAR(hire_date), COUNT(*) FROM employees GROUP BY YEAR(hire_date)",
        ]
        test_cases.extend(group_tests)
        
        # ORDER BY and LIMIT
        order_tests = [
            "SELECT * FROM users ORDER BY name",
            "SELECT * FROM users ORDER BY name ASC",
            "SELECT * FROM users ORDER BY name DESC",
            "SELECT * FROM users ORDER BY last_name, first_name",
            "SELECT * FROM users LIMIT 10",
            "SELECT * FROM users LIMIT 10 OFFSET 20",
            "SELECT * FROM users ORDER BY name LIMIT 10 OFFSET 5",
        ]
        test_cases.extend(order_tests)
        
        # Subqueries
        subquery_tests = [
            "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders)",
            "SELECT name, (SELECT COUNT(*) FROM orders WHERE orders.user_id = users.id) AS order_count FROM users",
            "SELECT * FROM (SELECT id, name FROM users) AS u",
            "SELECT * FROM users WHERE age > (SELECT AVG(age) FROM users)",
            "SELECT department, (SELECT name FROM managers WHERE managers.department = employees.department) FROM employees",
        ]
        test_cases.extend(subquery_tests)
        
        # Functions and expressions
        function_tests = [
            "SELECT UPPER(name) FROM users",
            "SELECT LOWER(name) FROM users",
            "SELECT CONCAT(first_name, ' ', last_name) FROM users",
            "SELECT LENGTH(name) FROM users",
            "SELECT SUBSTR(name, 1, 3) FROM users",
            "SELECT COALESCE(salary, 0) FROM employees",
            "SELECT NULLIF(salary, 0) FROM employees",
            "SELECT CASE WHEN age < 18 THEN 'minor' WHEN age < 65 THEN 'adult' ELSE 'senior' END FROM users",
            "SELECT ABS(score) FROM results",
            "SELECT ROUND(salary, 2) FROM employees",
            "SELECT CAST(age AS VARCHAR) FROM users",
            "SELECT CURRENT_DATE",
            "SELECT CURRENT_TIMESTAMP",
            "SELECT EXTRACT(YEAR FROM hire_date) FROM employees",
        ]
        test_cases.extend(function_tests)
        
        # INSERT statements
        insert_tests = [
            "INSERT INTO users (id, name) VALUES (1, 'John')",
            "INSERT INTO users VALUES (1, 'John', 30)",
            "INSERT INTO users (name, age) VALUES ('John', 30), ('Jane', 25)",
            "INSERT INTO users SELECT * FROM old_users",
        ]
        test_cases.extend(insert_tests)
        
        # UPDATE statements
        update_tests = [
            "UPDATE users SET name = 'John' WHERE id = 1",
            "UPDATE users SET age = age + 1",
            "UPDATE users SET name = 'John', age = 30 WHERE id = 1",
            "UPDATE employees SET salary = salary * 1.1 WHERE department = 'IT'",
        ]
        test_cases.extend(update_tests)
        
        # DELETE statements
        delete_tests = [
            "DELETE FROM users WHERE id = 1",
            "DELETE FROM users WHERE age < 18",
            "DELETE FROM users",
        ]
        test_cases.extend(delete_tests)
        
        # CREATE and DROP
        create_tests = [
            "CREATE TABLE users (id INTEGER, name VARCHAR(100))",
            "CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT NOT NULL, salary REAL)",
            "CREATE TABLE orders (id INTEGER, user_id INTEGER, FOREIGN KEY (user_id) REFERENCES users(id))",
            "CREATE TABLE products (id INTEGER, price NUMERIC(10,2), active BOOLEAN DEFAULT TRUE)",
            "CREATE TABLE logs (id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "DROP TABLE users",
            "DROP TABLE IF EXISTS users",
        ]
        test_cases.extend(create_tests)
        
        # ALTER TABLE
        alter_tests = [
            "ALTER TABLE users ADD COLUMN email VARCHAR(255)",
            "ALTER TABLE users DROP COLUMN email",
            "ALTER TABLE users RENAME COLUMN name TO username",
            "ALTER TABLE users ADD PRIMARY KEY (id)",
            "ALTER TABLE users ADD CONSTRAINT unique_name UNIQUE (name)",
        ]
        test_cases.extend(alter_tests)
        
        # WITH (CTE)
        cte_tests = [
            "WITH cte AS (SELECT * FROM users) SELECT * FROM cte",
            "WITH RECURSIVE cte(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM cte WHERE n < 10) SELECT * FROM cte",
            "WITH users_cte AS (SELECT * FROM users WHERE active = TRUE), orders_cte AS (SELECT * FROM orders WHERE amount > 100) SELECT * FROM users_cte JOIN orders_cte ON users_cte.id = orders_cte.user_id",
        ]
        test_cases.extend(cte_tests)
        
        # Set operations
        set_tests = [
            "SELECT * FROM users UNION SELECT * FROM customers",
            "SELECT * FROM users UNION ALL SELECT * FROM customers",
            "SELECT * FROM users INTERSECT SELECT * FROM customers",
            "SELECT * FROM users EXCEPT SELECT * FROM customers",
        ]
        test_cases.extend(set_tests)
        
        # Complex combinations
        complex_tests = [
            "SELECT u.name, COUNT(o.id) FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE u.active = TRUE GROUP BY u.name HAVING COUNT(o.id) > 0 ORDER BY u.name LIMIT 10",
            "WITH department_stats AS (SELECT department, AVG(salary) AS avg_salary FROM employees GROUP BY department) SELECT e.name, e.salary, ds.avg_salary FROM employees e JOIN department_stats ds ON e.department = ds.department WHERE e.salary > ds.avg_salary ORDER BY e.salary DESC",
            "SELECT CASE WHEN score >= 90 THEN 'A' WHEN score >= 80 THEN 'B' WHEN score >= 70 THEN 'C' ELSE 'F' END AS grade, COUNT(*) FROM students GROUP BY grade ORDER BY grade",
            "SELECT * FROM (SELECT id, name, ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS rank FROM employees) WHERE rank <= 3",
        ]
        test_cases.extend(complex_tests)
        
        return test_cases
    
    def _generate_edge_cases(self, hints: Dict[str, Any]) -> List[str]:
        """Generate edge cases for specific coverage."""
        edge_cases = []
        
        # Empty and NULL handling
        edge_cases.extend([
            "SELECT NULL",
            "SELECT ''",
            "SELECT 1 WHERE NULL",
            "SELECT 1 WHERE 1 = NULL",
            "SELECT 1 WHERE NULL IS NULL",
            "SELECT 1 WHERE NULL IS NOT NULL",
        ])
        
        # Boolean logic edge cases
        edge_cases.extend([
            "SELECT TRUE AND FALSE",
            "SELECT TRUE OR FALSE",
            "SELECT NOT TRUE",
            "SELECT 1 = 1",
            "SELECT 1 != 1",
            "SELECT 1 <> 1",
        ])
        
        # Numeric edge cases
        edge_cases.extend([
            "SELECT 1.0",
            "SELECT -1",
            "SELECT +1",
            "SELECT 1e10",
            "SELECT 1.23e-4",
            "SELECT 0.0",
            "SELECT -0.0",
        ])
        
        # String edge cases
        edge_cases.extend([
            "SELECT 'John''s car'",
            "SELECT 'line1\nline2'",
            "SELECT 'tab\ttab'",
            "SELECT 'unicode: αβγ'",
            "SELECT ''",
            "SELECT ' '",
        ])
        
        # Identifier edge cases
        edge_cases.extend([
            'SELECT "column name" FROM "table name"',
            'SELECT `backtick` FROM `table`',
            'SELECT [bracket] FROM [table]',
        ])
        
        # Empty queries and minimal forms
        edge_cases.extend([
            "SELECT",
            "FROM users",
            "SELECT (SELECT 1)",
            "SELECT * FROM (VALUES (1))",
        ])
        
        # Window functions if hinted
        if "window" in hints["complexities"] or "over" in str(hints).lower():
            edge_cases.extend([
                "SELECT ROW_NUMBER() OVER () FROM users",
                "SELECT RANK() OVER (ORDER BY salary) FROM employees",
                "SELECT DENSE_RANK() OVER (PARTITION BY department ORDER BY salary) FROM employees",
                "SELECT SUM(salary) OVER (PARTITION BY department) FROM employees",
                "SELECT LEAD(salary) OVER (ORDER BY hire_date) FROM employees",
                "SELECT LAG(salary) OVER (ORDER BY hire_date) FROM employees",
            ])
        
        return edge_cases
    
    def _get_basic_coverage_sql(self) -> List[str]:
        """Fallback basic SQL for coverage."""
        return [
            # Basic queries
            "SELECT 1",
            "SELECT * FROM t",
            "SELECT a, b FROM t",
            "SELECT DISTINCT a FROM t",
            
            # WHERE clause
            "SELECT * FROM t WHERE a = 1",
            "SELECT * FROM t WHERE a > 1",
            "SELECT * FROM t WHERE a < 1",
            "SELECT * FROM t WHERE a >= 1",
            "SELECT * FROM t WHERE a <= 1",
            "SELECT * FROM t WHERE a != 1",
            "SELECT * FROM t WHERE a <> 1",
            "SELECT * FROM t WHERE a IS NULL",
            "SELECT * FROM t WHERE a IS NOT NULL",
            "SELECT * FROM t WHERE a BETWEEN 1 AND 10",
            "SELECT * FROM t WHERE a IN (1, 2, 3)",
            "SELECT * FROM t WHERE a LIKE 'test%'",
            "SELECT * FROM t WHERE a NOT LIKE 'test%'",
            
            # Boolean logic
            "SELECT * FROM t WHERE a = 1 AND b = 2",
            "SELECT * FROM t WHERE a = 1 OR b = 2",
            "SELECT * FROM t WHERE NOT a = 1",
            "SELECT * FROM t WHERE (a = 1 OR b = 2) AND c = 3",
            
            # JOINs
            "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t1 LEFT JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t1 INNER JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t1 CROSS JOIN t2",
            
            # GROUP BY
            "SELECT a, COUNT(*) FROM t GROUP BY a",
            "SELECT a, b, COUNT(*) FROM t GROUP BY a, b",
            "SELECT a, COUNT(*) FROM t GROUP BY a HAVING COUNT(*) > 1",
            
            # ORDER BY
            "SELECT * FROM t ORDER BY a",
            "SELECT * FROM t ORDER BY a DESC",
            "SELECT * FROM t ORDER BY a, b",
            "SELECT * FROM t ORDER BY a ASC, b DESC",
            
            # LIMIT/OFFSET
            "SELECT * FROM t LIMIT 10",
            "SELECT * FROM t LIMIT 10 OFFSET 5",
            
            # Functions
            "SELECT COUNT(*) FROM t",
            "SELECT SUM(a) FROM t",
            "SELECT AVG(a) FROM t",
            "SELECT MIN(a) FROM t",
            "SELECT MAX(a) FROM t",
            "SELECT UPPER(a) FROM t",
            "SELECT LOWER(a) FROM t",
            
            # Subqueries
            "SELECT * FROM t WHERE a IN (SELECT x FROM u)",
            "SELECT * FROM (SELECT * FROM t) AS sub",
            
            # INSERT/UPDATE/DELETE
            "INSERT INTO t (a, b) VALUES (1, 2)",
            "UPDATE t SET a = 1 WHERE b = 2",
            "DELETE FROM t WHERE a = 1",
            
            # CREATE/DROP
            "CREATE TABLE t (a INTEGER, b TEXT)",
            "DROP TABLE t",
            
            # Complex
            "SELECT a, COUNT(*) FROM t WHERE b > 0 GROUP BY a HAVING COUNT(*) > 1 ORDER BY a LIMIT 10",
        ]