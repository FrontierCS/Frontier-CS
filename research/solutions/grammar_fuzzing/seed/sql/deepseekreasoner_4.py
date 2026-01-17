import sys
import os
import ast
import itertools
from collections import defaultdict, deque
from typing import List, Dict, Set, Tuple, Optional
import random
import re

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        # Parse grammar to understand SQL structure
        grammar_path = os.path.join(resources_path, 'sql_grammar.txt')
        engine_path = os.path.join(resources_path, 'sql_engine')
        
        # Import the parser module
        sys.path.insert(0, resources_path)
        sys.path.insert(0, engine_path)
        
        # Read and analyze grammar
        grammar = self._parse_grammar(grammar_path)
        
        # Analyze parser source code for coverage hints
        coverage_targets = self._analyze_parser(engine_path)
        
        # Generate diverse SQL statements
        statements = self._generate_statements(grammar, coverage_targets)
        
        # Optimize for efficiency (remove redundant statements)
        optimized = self._optimize_statements(statements, engine_path)
        
        return optimized
    
    def _parse_grammar(self, grammar_path: str) -> Dict:
        """Parse BNF grammar file into structured format"""
        grammar = {
            'statements': [],
            'expressions': [],
            'clauses': [],
            'keywords': set(),
            'operators': set(),
            'functions': []
        }
        
        with open(grammar_path, 'r') as f:
            lines = f.readlines()
        
        current_rule = None
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '::=' in line:
                parts = line.split('::=')
                rule_name = parts[0].strip()
                rule_body = parts[1].strip()
                
                if rule_name.startswith('<') and rule_name.endswith('>'):
                    rule_name = rule_name[1:-1]
                
                # Categorize rules
                if any(keyword in rule_name.lower() for keyword in ['stmt', 'statement', 'select', 'insert', 'update', 'delete']):
                    grammar['statements'].append((rule_name, rule_body))
                elif any(keyword in rule_name.lower() for keyword in ['expr', 'expression']):
                    grammar['expressions'].append((rule_name, rule_body))
                elif any(keyword in rule_name.lower() for keyword in ['clause', 'where', 'having', 'group', 'order', 'limit']):
                    grammar['clauses'].append((rule_name, rule_body))
                elif 'function' in rule_name.lower():
                    grammar['functions'].append((rule_name, rule_body))
                
                # Extract keywords and operators
                tokens = re.findall(r'\b[A-Z_]+\b', rule_body)
                for token in tokens:
                    if len(token) > 2:  # Likely keyword
                        grammar['keywords'].add(token.lower())
                    elif token in ['=', '<', '>', '<=', '>=', '!=', '+', '-', '*', '/']:
                        grammar['operators'].add(token)
        
        return grammar
    
    def _analyze_parser(self, engine_path: str) -> Dict:
        """Analyze parser source code to identify coverage targets"""
        targets = {
            'statement_types': set(),
            'clause_types': set(),
            'expression_types': set(),
            'join_types': set(),
            'function_calls': set(),
            'error_cases': set()
        }
        
        # Parse parser.py
        parser_file = os.path.join(engine_path, 'parser.py')
        if os.path.exists(parser_file):
            with open(parser_file, 'r') as f:
                parser_code = f.read()
            
            # Look for parse methods
            tree = ast.parse(parser_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    if func_name.startswith('parse_'):
                        target = func_name[6:]  # Remove 'parse_'
                        if 'stmt' in func_name or 'statement' in func_name:
                            targets['statement_types'].add(target)
                        elif 'clause' in func_name or any(clause in func_name for clause in ['where', 'having', 'group', 'order', 'limit']):
                            targets['clause_types'].add(target)
                        elif 'expr' in func_name:
                            targets['expression_types'].add(target)
                        elif 'join' in func_name:
                            targets['join_types'].add(target)
                
                # Look for error handling
                if isinstance(node, ast.Raise):
                    targets['error_cases'].add('raise')
        
        # Parse tokenizer.py
        tokenizer_file = os.path.join(engine_path, 'tokenizer.py')
        if os.path.exists(tokenizer_file):
            with open(tokenizer_file, 'r') as f:
                tokenizer_code = f.read()
            
            # Look for token types
            tree = ast.parse(tokenizer_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if 'Token' in node.name:
                        for subnode in node.body:
                            if isinstance(subnode, ast.Assign):
                                for target in subnode.targets:
                                    if isinstance(target, ast.Name):
                                        if target.id.isupper():
                                            targets['keywords'].add(target.id.lower())
        
        # Parse ast_nodes.py
        ast_file = os.path.join(engine_path, 'ast_nodes.py')
        if os.path.exists(ast_file):
            with open(ast_file, 'r') as f:
                ast_code = f.read()
            
            # Look for node classes
            tree = ast.parse(ast_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    if 'Node' in class_name or 'AST' in class_name:
                        targets['ast_nodes'].add(class_name)
        
        return targets
    
    def _generate_statements(self, grammar: Dict, targets: Dict) -> List[str]:
        """Generate diverse SQL statements based on grammar and coverage targets"""
        statements = []
        
        # Basic SELECT statements
        statements.extend([
            "SELECT 1",
            "SELECT * FROM users",
            "SELECT id, name FROM users WHERE active = true",
            "SELECT COUNT(*) FROM orders",
            "SELECT DISTINCT category FROM products",
            "SELECT name, price FROM products ORDER BY price DESC",
            "SELECT department, AVG(salary) FROM employees GROUP BY department",
            "SELECT * FROM users LIMIT 10",
            "SELECT * FROM users OFFSET 5",
            "SELECT * FROM users ORDER BY name LIMIT 10 OFFSET 5",
        ])
        
        # JOIN operations
        statements.extend([
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id",
            "SELECT u.name, o.total FROM users u LEFT JOIN orders o ON u.id = o.user_id",
            "SELECT u.name, o.total FROM users u RIGHT JOIN orders o ON u.id = o.user_id",
            "SELECT u.name, o.total FROM users u INNER JOIN orders o ON u.id = o.user_id",
            "SELECT a.name, b.name FROM table1 a, table2 b WHERE a.id = b.ref_id",
            "SELECT * FROM a JOIN b ON a.id = b.a_id JOIN c ON b.id = c.b_id",
        ])
        
        # Complex WHERE clauses
        statements.extend([
            "SELECT * FROM products WHERE price > 100 AND stock > 0",
            "SELECT * FROM users WHERE age BETWEEN 18 AND 65",
            "SELECT * FROM products WHERE category IN ('electronics', 'books')",
            "SELECT * FROM users WHERE name LIKE 'J%'",
            "SELECT * FROM logs WHERE timestamp > '2024-01-01'",
            "SELECT * FROM items WHERE (price > 100 OR discount = true) AND available = true",
            "SELECT * FROM data WHERE value IS NOT NULL",
            "SELECT * FROM users WHERE NOT banned",
        ])
        
        # Aggregations and HAVING
        statements.extend([
            "SELECT department, COUNT(*) FROM employees GROUP BY department HAVING COUNT(*) > 5",
            "SELECT category, AVG(price) FROM products GROUP BY category HAVING AVG(price) > 100",
            "SELECT user_id, SUM(amount) FROM transactions GROUP BY user_id HAVING SUM(amount) > 1000",
            "SELECT YEAR(date), MONTH(date), COUNT(*) FROM sales GROUP BY YEAR(date), MONTH(date)",
        ])
        
        # Subqueries
        statements.extend([
            "SELECT name FROM users WHERE id IN (SELECT user_id FROM orders)",
            "SELECT * FROM products WHERE price > (SELECT AVG(price) FROM products)",
            "SELECT name, (SELECT COUNT(*) FROM orders WHERE orders.user_id = users.id) as order_count FROM users",
            "SELECT * FROM (SELECT * FROM users WHERE active = true) AS active_users",
            "SELECT a.* FROM products a WHERE EXISTS (SELECT 1 FROM inventory WHERE product_id = a.id)",
        ])
        
        # INSERT statements
        statements.extend([
            "INSERT INTO users (name, email) VALUES ('John', 'john@example.com')",
            "INSERT INTO products SELECT * FROM new_products",
            "INSERT INTO logs (message) VALUES ('test'), ('debug'), ('info')",
        ])
        
        # UPDATE statements
        statements.extend([
            "UPDATE users SET active = true WHERE last_login > '2024-01-01'",
            "UPDATE products SET price = price * 0.9 WHERE category = 'clearance'",
            "UPDATE employees SET salary = salary * 1.1 WHERE performance_rating > 4",
        ])
        
        # DELETE statements
        statements.extend([
            "DELETE FROM users WHERE banned = true",
            "DELETE FROM logs WHERE timestamp < '2023-01-01'",
            "DELETE FROM temp_data",
        ])
        
        # Functions and expressions
        statements.extend([
            "SELECT UPPER(name), LOWER(email) FROM users",
            "SELECT CONCAT(first_name, ' ', last_name) as full_name FROM customers",
            "SELECT COALESCE(description, 'No description') FROM products",
            "SELECT NOW(), CURRENT_DATE, CURRENT_TIMESTAMP",
            "SELECT LENGTH(name), SUBSTRING(email, 1, 5) FROM users",
            "SELECT ROUND(price, 2), CEIL(price), FLOOR(price) FROM products",
            "SELECT CAST(price AS INTEGER) FROM products",
            "SELECT NULLIF(column1, column2) FROM table",
            "SELECT CASE WHEN price > 100 THEN 'expensive' ELSE 'cheap' END FROM products",
        ])
        
        # Set operations
        statements.extend([
            "SELECT name FROM active_users UNION SELECT name FROM inactive_users",
            "SELECT id FROM table1 INTERSECT SELECT id FROM table2",
            "SELECT id FROM all_items EXCEPT SELECT id FROM purchased_items",
        ])
        
        # Transactions
        statements.extend([
            "BEGIN TRANSACTION",
            "COMMIT",
            "ROLLBACK",
            "SAVEPOINT sp1",
            "ROLLBACK TO SAVEPOINT sp1",
        ])
        
        # Complex combinations
        statements.extend([
            "SELECT u.name, COUNT(o.id), SUM(o.total) FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE u.active = true GROUP BY u.id, u.name HAVING COUNT(o.id) > 0 ORDER BY SUM(o.total) DESC LIMIT 10",
            "SELECT department, employee_count, avg_salary FROM (SELECT department, COUNT(*) as employee_count, AVG(salary) as avg_salary FROM employees GROUP BY department) AS dept_stats WHERE avg_salary > 50000 ORDER BY employee_count DESC",
            "WITH recursive_cte (n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM recursive_cte WHERE n < 10) SELECT * FROM recursive_cte",
            "SELECT * FROM users WHERE id = ANY(SELECT user_id FROM orders WHERE total > 100)",
            "SELECT name, price, price * 0.8 as discounted_price FROM products WHERE category = 'electronics' ORDER BY price DESC LIMIT 5 OFFSET 2",
        ])
        
        # Edge cases and special syntax
        statements.extend([
            "SELECT /* comment */ 1",
            "SELECT 1 -- inline comment",
            "SELECT \"quoted identifier\" FROM table",
            "SELECT `backtick identifier` FROM table",
            "SELECT [bracket identifier] FROM table",
            "SELECT 1.23e-4, -100, +50",
            "SELECT * FROM \"table-with-dashes\"",
            "SELECT * FROM `table.with.dots`",
        ])
        
        return statements
    
    def _optimize_statements(self, statements: List[str], engine_path: str) -> List[str]:
        """Optimize statement list to remove redundancies while maintaining coverage"""
        # Deduplicate
        unique_statements = []
        seen = set()
        for stmt in statements:
            # Normalize whitespace for comparison
            normalized = ' '.join(stmt.split())
            if normalized not in seen:
                seen.add(normalized)
                unique_statements.append(stmt)
        
        # Prioritize statements that cover different syntactic structures
        # Group by statement type
        categorized = defaultdict(list)
        for stmt in unique_statements:
            stmt_lower = stmt.lower().strip()
            if stmt_lower.startswith('select'):
                if ' join ' in stmt_lower:
                    categorized['select_join'].append(stmt)
                elif ' where ' in stmt_lower:
                    categorized['select_where'].append(stmt)
                elif ' group by ' in stmt_lower:
                    categorized['select_group'].append(stmt)
                elif ' order by ' in stmt_lower:
                    categorized['select_order'].append(stmt)
                elif ' limit ' in stmt_lower or ' offset ' in stmt_lower:
                    categorized['select_limit'].append(stmt)
                elif ' union ' in stmt_lower or ' intersect ' in stmt_lower or ' except ' in stmt_lower:
                    categorized['select_set'].append(stmt)
                elif ' subquery' in stmt_lower or ' in (' in stmt_lower or ' exists (' in stmt_lower:
                    categorized['select_subquery'].append(stmt)
                else:
                    categorized['select_basic'].append(stmt)
            elif stmt_lower.startswith('insert'):
                categorized['insert'].append(stmt)
            elif stmt_lower.startswith('update'):
                categorized['update'].append(stmt)
            elif stmt_lower.startswith('delete'):
                categorized['delete'].append(stmt)
            elif stmt_lower.startswith('begin') or stmt_lower.startswith('commit') or stmt_lower.startswith('rollback'):
                categorized['transaction'].append(stmt)
            else:
                categorized['other'].append(stmt)
        
        # Select representative statements from each category
        optimized = []
        for category in categorized:
            # Take up to 3 statements from each category
            samples = categorized[category][:3]
            optimized.extend(samples)
        
        # Ensure we have a good mix, but limit total to reasonable number
        # (target ~50 statements for efficiency bonus)
        if len(optimized) > 50:
            # Prioritize more complex statements
            def complexity_score(stmt: str) -> int:
                score = 0
                stmt_lower = stmt.lower()
                # Add points for various complex features
                score += stmt_lower.count(' join ')
                score += stmt_lower.count(' where ')
                score += stmt_lower.count(' group by ')
                score += stmt_lower.count(' having ')
                score += stmt_lower.count(' order by ')
                score += stmt_lower.count(' limit ')
                score += stmt_lower.count(' offset ')
                score += stmt_lower.count(' union ')
                score += stmt_lower.count(' intersect ')
                score += stmt_lower.count(' except ')
                score += stmt_lower.count(' case ')
                score += stmt_lower.count('(')  # subqueries/functions
                return score
            
            optimized.sort(key=complexity_score, reverse=True)
            optimized = optimized[:50]
        
        return optimized