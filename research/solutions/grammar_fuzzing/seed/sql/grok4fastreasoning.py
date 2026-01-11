import sys
import os

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        sql_engine_path = os.path.join(resources_path, 'sql_engine')
        sys.path.insert(0, sql_engine_path)
        from parser import parse_sql

        test_cases = [
            "SELECT * FROM users;",
            "SELECT name, age FROM users WHERE age > 18;",
            "SELECT * FROM users ORDER BY name ASC;",
            "SELECT COUNT(*) FROM users;",
            "SELECT name FROM users GROUP BY name HAVING COUNT(*) > 1;",
            "INSERT INTO users (name, age) VALUES ('Alice', 25);",
            "UPDATE users SET age = 26 WHERE name = 'Alice';",
            "DELETE FROM users WHERE age < 18;",
            "CREATE TABLE products (id INT, name VARCHAR(50));",
            "DROP TABLE products;",
            "SELECT u.name, p.name AS product FROM users u INNER JOIN orders o ON u.id = o.user_id INNER JOIN products p ON o.product_id = p.id;",
            "SELECT * FROM users WHERE name LIKE '%son';",
            "SELECT * FROM users WHERE age BETWEEN 18 AND 65;",
            "SELECT * FROM (SELECT * FROM users) AS subquery;",
            "SELECT CASE WHEN age > 18 THEN 'Adult' ELSE 'Minor' END AS status FROM users;",
            "SELECT UPPER(name) FROM users;",
            "SELECT name FROM users UNION SELECT name FROM employees;",
            "SELECT * FROM users LIMIT 10;",
            "SELECT * FROM users OFFSET 5 LIMIT 10;",
            "INSERT INTO users VALUES (1, 'Bob', 30);",
            "SELECT DISTINCT name FROM users;",
            "SELECT * FROM users WHERE age IS NULL;",
            "SELECT AVG(age) FROM users;",
            "SELECT SUM(age), MIN(age), MAX(age) FROM users GROUP BY department;",
            "UPDATE users SET age = age + 1 WHERE id = 1;",
            "DELETE FROM users WHERE id = 1;",
            "CREATE INDEX idx_name ON users(name);",
            "DROP INDEX idx_name;",
            "SELECT * FROM users WHERE name IN ('Alice', 'Bob');",
            "SELECT * FROM users WHERE age NOT IN (18, 19);",
            "SELECT u.* FROM users u LEFT JOIN orders o ON u.id = o.user_id;",
            "SELECT * FROM users u RIGHT JOIN orders o ON u.id = o.user_id;",
            "SELECT CURRENT_DATE AS today;",
            "SELECT 'hello' || ' world' AS greeting;",
            "SELECT * FROM users u WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id);",
            "SELECT name FROM users ORDER BY age DESC, name ASC;",
            "CREATE VIEW user_view AS SELECT * FROM users;",
            "DROP VIEW user_view;",
            "SELECT 1 + 2 * 3;",
            "SELECT (1 + 2) * 3;",
            "SELECT 'single quoted';",
            "SELECT \"double quoted\";",
            "SELECT NULL;",
            "SELECT TRUE;",
            "SELECT 123.45;",
            "SELECT * FROM users WHERE age = 25 OR name = 'Alice';",
            "SELECT * FROM users WHERE NOT (age < 18);",
            "INSERT INTO products (id, name) VALUES (1, 'Laptop'), (2, 'Phone');",
            "UPDATE products SET name = 'Tablet' WHERE id = 2;",
            "DELETE FROM products WHERE id > 10;"
        ]

        valid_tests = []
        for test in test_cases:
            try:
                parse_sql(test)
                valid_tests.append(test)
            except Exception:
                pass

        return valid_tests