import os
import sys
import importlib


class Solution:
    def solve(self, resources_path: str) -> list[str]:
        parse_sql = self._load_parse_sql(resources_path)
        candidates = self._generate_candidates()

        # Deduplicate and normalize
        seen = set()
        unique_candidates = []
        for stmt in candidates:
            if stmt is None:
                continue
            normalized = stmt.strip()
            if not normalized:
                continue
            if normalized not in seen:
                seen.add(normalized)
                unique_candidates.append(normalized)

        max_keep = 120
        min_keep = 25

        # If we cannot import or call parse_sql, just return a subset
        if parse_sql is None:
            return unique_candidates[:max_keep]

        selected: list[str] = []
        global_signatures = set()

        for stmt in unique_candidates:
            if len(selected) >= max_keep:
                break
            try:
                ast = parse_sql(stmt)
            except Exception:
                continue

            new_sigs = self._collect_signatures(ast)

            if len(selected) < min_keep:
                selected.append(stmt)
                global_signatures |= new_sigs
            else:
                if not global_signatures or (new_sigs - global_signatures):
                    selected.append(stmt)
                    global_signatures |= new_sigs

        if not selected:
            # Fallback: at least return some reasonable statements
            return unique_candidates[:min(max_keep, 50)]

        return selected

    def _load_parse_sql(self, resources_path):
        if resources_path and resources_path not in sys.path:
            sys.path.append(resources_path)

        parse_fn = None

        try:
            engine = importlib.import_module("sql_engine")
            if hasattr(engine, "parse_sql"):
                parse_fn = getattr(engine, "parse_sql")
        except Exception:
            parse_fn = None

        if parse_fn is None:
            try:
                parser_module = importlib.import_module("sql_engine.parser")
                if hasattr(parser_module, "parse_sql"):
                    parse_fn = getattr(parser_module, "parse_sql")
            except Exception:
                parse_fn = None

        return parse_fn

    def _collect_signatures(self, root):
        signatures = set()
        visited = set()

        def visit(node):
            node_id = id(node)
            if node_id in visited:
                return
            visited.add(node_id)

            # Primitive types
            if isinstance(node, (str, int, float, bool, type(None))):
                return

            # Containers
            if isinstance(node, (list, tuple, set, frozenset)):
                for item in node:
                    visit(item)
                return

            if isinstance(node, dict):
                for k, v in node.items():
                    visit(k)
                    visit(v)
                return

            cls = type(node)
            module = getattr(cls, "__module__", "")

            # Determine attributes
            attr_items = []
            if hasattr(node, "__dict__"):
                attr_items.extend(node.__dict__.items())
            else:
                names = set()
                for name in dir(node):
                    if name.startswith("_"):
                        continue
                    names.add(name)
                for name in names:
                    try:
                        value = getattr(node, name)
                    except Exception:
                        continue
                    if callable(value):
                        continue
                    attr_items.append((name, value))

            if module.startswith("sql_engine"):
                key_attrs = []
                for attr, value in attr_items:
                    if isinstance(value, (str, int, float, bool, type(None))):
                        lower_attr = attr.lower()
                        if any(
                            key in lower_attr
                            for key in (
                                "op",
                                "operator",
                                "join",
                                "kind",
                                "type",
                                "func",
                                "function",
                                "agg",
                                "aggregate",
                                "direction",
                                "order",
                                "distinct",
                                "null",
                                "set_op",
                                "setop",
                                "union",
                                "except",
                                "intersect",
                                "quantifier",
                                "exists",
                                "like",
                                "between",
                                "in_",
                                "case",
                                "when",
                                "else",
                                "limit",
                                "offset",
                                "all",
                                "any",
                                "some",
                                "update",
                                "insert",
                                "delete",
                                "create",
                                "drop",
                                "alter",
                            )
                        ):
                            key_attrs.append((attr, repr(value)))

                signature = (module, cls.__name__, tuple(sorted(key_attrs)))
                signatures.add(signature)

            # Recurse into children
            for _, child in attr_items:
                visit(child)

        visit(root)
        return signatures

    def _generate_candidates(self) -> list[str]:
        stmts: list[str] = []
        add = stmts.append

        # Basic selects and literals
        add("SELECT 1;")
        add("select 1 + 2 AS sum;")
        add("SELECT NULL, TRUE, FALSE;")
        add("SELECT -1 AS negative, +2 AS positive, 3 * 4 AS product, 10 / 2 AS quotient, 7 % 2 AS mod;")
        add("SELECT 42 AS answer, 'hello' AS greeting, 'O''Reilly' AS escaped;")

        # Comments and whitespace handling
        add("-- leading line comment\nSELECT 1;")
        add("SELECT 1 -- inline comment\n;")
        add("SELECT /* block comment */ 1;")
        add("/* multi\n   line\n   comment */\nSELECT 2;")

        # Simple FROM and WHERE
        add("SELECT * FROM users;")
        add("SELECT id, name FROM users WHERE age >= 18 AND active = 1;")
        add("SELECT u.id, u.name FROM users AS u WHERE u.age < 30 OR u.active = 0;")
        add("SELECT u.id, o.id, o.total FROM users u, orders o WHERE u.id = o.user_id;")

        # Comparison operators
        comparators = ["=", "<>", "!=", ">", ">=", "<", "<="]
        for op in comparators:
            add(f"SELECT * FROM users WHERE age {op} 30;")

        # BETWEEN / NOT BETWEEN
        add("SELECT * FROM users WHERE age BETWEEN 18 AND 30;")
        add("SELECT * FROM users WHERE age NOT BETWEEN 18 AND 30;")

        # IN / NOT IN
        add("SELECT * FROM users WHERE id IN (1, 2, 3);")
        add("SELECT * FROM users WHERE id NOT IN (4, 5, 6);")

        # LIKE / NOT LIKE
        add("SELECT * FROM users WHERE name LIKE 'A%';")
        add("SELECT * FROM users WHERE name NOT LIKE '%test%';")

        # IS NULL / IS NOT NULL
        add("SELECT * FROM users WHERE email IS NULL;")
        add("SELECT * FROM users WHERE email IS NOT NULL;")

        # Boolean logic and parentheses
        add(
            "SELECT * FROM users WHERE (age > 18 AND active = 1) OR (age < 18 AND active = 0);"
        )

        # CASE expression
        add(
            """
SELECT id,
       CASE
           WHEN age < 18 THEN 'minor'
           WHEN age < 65 THEN 'adult'
           ELSE 'senior'
       END AS age_group
FROM users;
""".strip()
        )

        # GROUP BY / HAVING
        add("SELECT department_id, COUNT(*) AS cnt FROM employees GROUP BY department_id;")
        add(
            "SELECT department_id, COUNT(*) AS cnt FROM employees GROUP BY department_id HAVING COUNT(*) > 5;"
        )

        # DISTINCT
        add("SELECT DISTINCT name FROM users;")
        add("SELECT DISTINCT department_id, role FROM employees;")

        # ORDER BY
        add("SELECT id, name FROM users ORDER BY name ASC, id DESC;")
        add("SELECT id, name FROM users ORDER BY 2 ASC, 1 DESC;")

        # LIMIT / OFFSET
        add("SELECT * FROM orders ORDER BY created_at DESC LIMIT 10;")
        add("SELECT * FROM orders ORDER BY created_at DESC LIMIT 10 OFFSET 5;")

        # Subqueries and correlated subqueries
        add(
            "SELECT id FROM users WHERE id IN (SELECT user_id FROM orders WHERE total > 100);"
        )
        add(
            "SELECT u.id FROM users u WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id AND o.total > 100);"
        )
        add("SELECT * FROM (SELECT id, name FROM users) sub WHERE sub.id > 10;")
        add(
            """
SELECT u.id,
       (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.id) AS order_count
FROM users u;
""".strip()
        )

        # JOIN variations
        join_types = [
            "JOIN",
            "INNER JOIN",
            "LEFT JOIN",
            "LEFT OUTER JOIN",
            "RIGHT JOIN",
            "RIGHT OUTER JOIN",
            "FULL JOIN",
            "FULL OUTER JOIN",
        ]
        for jt in join_types:
            add(
                f"SELECT u.id, o.id, o.total FROM users u {jt} orders o ON u.id = o.user_id;"
            )

        # CROSS / NATURAL JOIN
        add("SELECT u.id, o.id FROM users u CROSS JOIN orders o;")
        add("SELECT u.id, o.id FROM users u NATURAL JOIN orders o;")

        # More complex join chains
        add(
            """
SELECT u.id, o.id, p.name
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
INNER JOIN products p ON p.id = o.product_id;
""".strip()
        )

        add(
            """
SELECT u.id, o.id, p.name
FROM users u
LEFT OUTER JOIN orders o ON u.id = o.user_id AND o.total > 0
RIGHT JOIN products p ON p.id = o.product_id;
""".strip()
        )

        # Set operations
        add("SELECT id FROM users UNION SELECT id FROM employees;")
        add("SELECT id FROM users UNION ALL SELECT id FROM employees;")
        add("SELECT user_id FROM orders INTERSECT SELECT id FROM users;")
        add("SELECT user_id FROM orders EXCEPT SELECT id FROM banned_users;")

        # CTEs
        add(
            """
WITH recent_orders AS (
    SELECT id, user_id, total
    FROM orders
    WHERE created_at > '2020-01-01'
),
big_spenders AS (
    SELECT user_id, SUM(total) AS total_spent
    FROM recent_orders
    GROUP BY user_id
)
SELECT * FROM big_spenders WHERE total_spent > 1000;
""".strip()
        )

        add(
            """
WITH t AS (SELECT id, name FROM users)
SELECT * FROM t WHERE id > 10;
""".strip()
        )

        # Aggregates and scalar functions
        add("SELECT COUNT(*) FROM users;")
        add("SELECT SUM(total), AVG(total), MIN(total), MAX(total) FROM orders;")
        add("SELECT UPPER(name) AS uname, LOWER(email) AS lemail FROM users;")
        add("SELECT COALESCE(email, 'none') AS email FROM users;")
        add("SELECT ABS(balance) FROM accounts;")
        add("SELECT ROUND(total, 2) FROM orders;")
        add("SELECT LENGTH(name) FROM users;")
        add("SELECT CAST(age AS VARCHAR(10)) FROM users;")
        add("SELECT CURRENT_TIMESTAMP;")
        add("SELECT NOW();")
        add("SELECT my_custom_function(id, name) FROM users;")

        # Window functions (if supported)
        add(
            """
SELECT user_id,
       SUM(total) OVER (PARTITION BY user_id ORDER BY created_at
                        ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) AS running_total
FROM orders;
""".strip()
        )

        add(
            """
SELECT user_id,
       ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at) AS rn
FROM orders;
""".strip()
        )

        # DML: INSERT, UPDATE, DELETE
        add(
            "INSERT INTO users (id, name, age, active) VALUES (1, 'Alice', 30, 1);"
        )
        add("INSERT INTO users VALUES (2, 'Bob', 25, 0);")
        add(
            "INSERT INTO users (id, name, age) SELECT id, name, age FROM employees WHERE active = 1;"
        )
        add(
            "INSERT INTO orders (id, user_id, total) VALUES (1, 1, 100.0), (2, 2, 50.5);"
        )

        add("UPDATE users SET name = 'Charlie' WHERE id = 3;")
        add("UPDATE users SET age = age + 1, updated_at = CURRENT_TIMESTAMP;")
        add("UPDATE orders SET total = total * 1.1 WHERE total < 100;")

        add("DELETE FROM users WHERE id = 4;")
        add("DELETE FROM orders;")

        # Upsert / MERGE-style constructs (if supported)
        add(
            """
INSERT INTO users (id, name) VALUES (5, 'Eve')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;
""".strip()
        )

        add(
            """
MERGE INTO users u
USING employees e ON (u.id = e.id)
WHEN MATCHED THEN UPDATE SET name = e.name
WHEN NOT MATCHED THEN INSERT (id, name) VALUES (e.id, e.name);
""".strip()
        )

        # DDL: CREATE / ALTER / DROP
        add(
            """
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INT,
    active BOOLEAN DEFAULT TRUE
);
""".strip()
        )

        add(
            """
CREATE TABLE orders (
    id INT PRIMARY KEY,
    user_id INT REFERENCES users(id),
    total NUMERIC(10,2),
    created_at TIMESTAMP
);
""".strip()
        )

        add(
            """
CREATE TABLE departments (
    id INT,
    name VARCHAR(100),
    parent_id INT,
    PRIMARY KEY (id)
);
""".strip()
        )

        add("CREATE TABLE IF NOT EXISTS logs (id INT, message TEXT);")
        add("DROP TABLE users;")
        add("DROP TABLE IF EXISTS logs;")
        add("ALTER TABLE users ADD COLUMN email VARCHAR(255);")
        add("ALTER TABLE users DROP COLUMN email;")
        add("ALTER TABLE users RENAME TO app_users;")
        add("ALTER TABLE users RENAME COLUMN name TO full_name;")
        add("CREATE INDEX idx_users_name ON users(name);")
        add("CREATE UNIQUE INDEX idx_orders_user_id ON orders(user_id);")
        add("DROP INDEX idx_users_name;")

        # Transactions and savepoints
        add("BEGIN;")
        add("BEGIN TRANSACTION;")
        add("COMMIT;")
        add("ROLLBACK;")
        add("SAVEPOINT sp1;")
        add("RELEASE SAVEPOINT sp1;")

        # Identifier quoting variations
        add('SELECT "id", "name" FROM "users";')
        add("SELECT [id], [name] FROM [users];")
        add("SELECT `id`, `name` FROM `users`;")

        # Mixed-case keywords and identifiers
        add("SeLeCt id, NaMe FrOm UsErS WhErE aGe > 20;")

        # VALUES clause (if supported)
        add("VALUES (1), (2), (3);")

        # FOR UPDATE (if supported)
        add("SELECT * FROM users FOR UPDATE;")

        # DISTINCT ON (dialect-specific)
        add(
            "SELECT DISTINCT ON (department_id) id, department_id FROM employees ORDER BY department_id, id;"
        )

        return stmts