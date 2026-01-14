import sys
import os

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        sql_statements = [
            # 1. Comprehensive SELECT with complex WHERE clause
            "SELECT id, name FROM products WHERE (price > 100 AND category = 'A') OR (stock < 10 AND category = 'B') AND name LIKE 'T%' AND id IN (1, 2, 3) AND description IS NOT NULL AND id NOT BETWEEN 10 AND 20 AND EXISTS (SELECT 1 FROM orders WHERE orders.product_id = products.id);",

            # 2. SELECT with aggregation, grouping, ordering, and pagination
            "SELECT DISTINCT category, COUNT(*) AS p_count, AVG(price) FROM products GROUP BY category HAVING COUNT(*) > 5 ORDER BY p_count DESC NULLS LAST, category ASC NULLS FIRST LIMIT 100 OFFSET 20;",

            # 3. SELECT exercising all JOIN types
            "SELECT * FROM t1 INNER JOIN t2 ON t1.id = t2.id, t3 LEFT OUTER JOIN t4 USING(common_col) NATURAL JOIN t5 RIGHT JOIN t6 ON t5.key = t6.key FULL OUTER JOIN t7 ON t6.id = t7.id CROSS JOIN t8;",

            # 4. SELECT with a Common Table Expression (CTE) and subquery in FROM
            "WITH product_counts AS (SELECT category, COUNT(*) AS n FROM products GROUP BY category) SELECT * FROM (SELECT category, n FROM product_counts) AS counts WHERE n > 10;",

            # 5. Set operations: UNION, INTERSECT, EXCEPT
            "SELECT id, name FROM products WHERE price > 1000 UNION ALL SELECT id, name FROM archived_products INTERSECT SELECT id, name FROM special_offers EXCEPT SELECT id, name FROM returned_items ORDER BY name;",
            
            # 6. Recursive CTE
            "WITH RECURSIVE subordinates (id, name, manager_id) AS (SELECT id, name, manager_id FROM employees WHERE id = 1 UNION ALL SELECT e.id, e.name, e.manager_id FROM employees e JOIN subordinates s ON s.id = e.manager_id) SELECT * FROM subordinates;",

            # 7. Comprehensive CREATE TABLE with various data types and constraints
            "CREATE TEMP TABLE IF NOT EXISTS users (id INT PRIMARY KEY, login VARCHAR(255) NOT NULL UNIQUE, email TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_active BOOLEAN DEFAULT TRUE, balance DECIMAL(12, 4), user_type TEXT, CHECK (balance >= 0), FOREIGN KEY (user_type) REFERENCES user_types(type) ON DELETE SET NULL ON UPDATE CASCADE);",
            
            # 8. CREATE INDEX with multiple options
            "CREATE UNIQUE INDEX IF NOT EXISTS users_email_idx ON users (email DESC, login ASC);",

            # 9. DROP TABLE with IF EXISTS and multiple tables
            "DROP TABLE IF EXISTS old_users, temp_users;",
            
            # 10. DROP INDEX
            "DROP INDEX IF EXISTS users_email_idx;",

            # 11. INSERT with a column list and multiple value tuples
            "INSERT INTO products (id, name, category, price) VALUES (101, 'Gadget', 'A', 99.99), (102, 'Widget', 'B', 150.0);",
            
            # 12. INSERT from a SELECT statement
            "INSERT INTO product_archive (id, name, price) SELECT id, name, price FROM products WHERE stock = 0;",

            # 13. UPDATE with a WHERE clause
            "UPDATE products SET price = price * 1.1, stock = stock - 1 WHERE id = 101;",
            
            # 14. UPDATE without a WHERE clause
            "UPDATE products SET price = price * 0.95;",
            
            # 15. DELETE with a WHERE clause
            "DELETE FROM logs WHERE created_at < '2020-01-01';",
            
            # 16. DELETE without a WHERE clause
            "DELETE FROM staging_table;",
            
            # 17. Expressions, functions, and CAST
            "SELECT -price, +stock, price * stock AS total_value, name || ' (' || category || ')', CAST(price AS INTEGER), COALESCE(description, 'N/A') FROM products;",

            # 18. CASE expressions (simple and searched)
            "SELECT name, CASE category WHEN 'A' THEN 'Category A' WHEN 'B' THEN 'Category B' ELSE 'Other' END, CASE WHEN price > 100 THEN 'Expensive' ELSE 'Cheap' END FROM products;",

            # 19. EXPLAIN a SELECT statement
            "EXPLAIN SELECT * FROM products WHERE price > 100;",
            
            # 20. EXPLAIN QUERY PLAN for a DML statement
            "EXPLAIN QUERY PLAN UPDATE products SET price = 1 WHERE id = 1;",

            # 21. Tokenizer edge cases: comments, quoted identifiers
            "SELECT 1; -- EOL comment\n/* Block\n   Comment */ SELECT id, \"product name\" FROM \"Products\";",

            # 22. Syntax variations: OFFSET without LIMIT
            "SELECT * FROM products ORDER BY name OFFSET 50;",
            
            # 23. All literal types
            "SELECT 123, 123.456, 'a string', TRUE, FALSE, NULL;",
            
            # 24. ALL and ANY subquery operators
            "SELECT * FROM t1 WHERE col1 > ALL (SELECT val FROM t2);",
        ]
        
        cleaned_statements = [" ".join(s.strip().split()) for s in sql_statements]
        
        return cleaned_statements