import os
import sys
import importlib
from typing import List, Set, Dict, Any


FEATURE_PATTERNS = [
    ("DISTINCT", " DISTINCT "),
    ("NOT_EQUAL_ANGLE", " <> "),
    ("NOT_EQUAL_BANG", " != "),
    ("LESS_EQUAL", " <= "),
    ("GREATER_EQUAL", " >= "),
    ("LESS", " < "),
    ("GREATER", " > "),
    ("LIKE", " LIKE "),
    ("BETWEEN", " BETWEEN "),
    ("IS_NOT_NULL", " IS NOT NULL"),
    ("IS_NULL", " IS NULL"),
    ("NOT_IN", " NOT IN "),
    ("IN", " IN "),
    ("AND", " AND "),
    ("OR", " OR "),
    ("NOT", " NOT "),
    ("INNER_JOIN", " INNER JOIN "),
    ("LEFT_JOIN", " LEFT JOIN "),
    ("RIGHT_JOIN", " RIGHT JOIN "),
    ("FULL_OUTER_JOIN", " FULL OUTER JOIN "),
    ("CROSS_JOIN", " CROSS JOIN "),
    ("JOIN", " JOIN "),
    ("ON", " ON "),
    ("GROUP_BY", " GROUP BY "),
    ("HAVING", " HAVING "),
    ("ORDER_BY", " ORDER BY "),
    ("ASC", " ASC"),
    ("DESC", " DESC"),
    ("LIMIT", " LIMIT "),
    ("OFFSET", " OFFSET "),
    ("UNION_ALL", " UNION ALL "),
    ("UNION", " UNION "),
    ("INTERSECT", " INTERSECT "),
    ("EXCEPT", " EXCEPT "),
    ("EXISTS", " EXISTS "),
    ("CASE", " CASE "),
    ("WHEN", " WHEN "),
    ("THEN", " THEN "),
    ("ELSE", " ELSE "),
    ("END", " END "),
    ("INSERT", "INSERT INTO "),
    ("UPDATE", "UPDATE "),
    ("DELETE", "DELETE FROM "),
    ("CREATE_TABLE", "CREATE TABLE "),
    ("ALTER_TABLE", "ALTER TABLE "),
    ("DROP_TABLE", "DROP TABLE "),
    ("CREATE_INDEX", "CREATE INDEX "),
    ("DROP_INDEX", "DROP INDEX "),
    ("CREATE_VIEW", "CREATE VIEW "),
    ("DROP_VIEW", "DROP VIEW "),
    ("BEGIN", "BEGIN TRANSACTION"),
    ("COMMIT", "COMMIT"),
    ("ROLLBACK", "ROLLBACK"),
    ("TRUNCATE", "TRUNCATE TABLE "),
    ("PRIMARY_KEY", "PRIMARY KEY"),
    ("FOREIGN_KEY", "FOREIGN KEY"),
    ("REFERENCES", "REFERENCES "),
    ("UNIQUE", " UNIQUE "),
    ("CHECK", " CHECK("),
    ("DEFAULT", " DEFAULT "),
]


def dedupe_preserve_order(seq: List[str]) -> List[str]:
    seen = set()
    res: List[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            res.append(item)
    return res


def generate_candidates() -> List[str]:
    stmts: List[str] = []
    s = stmts.append

    # Basic SELECTs
    s("SELECT * FROM users")
    s("SELECT id, name, age FROM users")
    s("SELECT DISTINCT status FROM users")
    s("SELECT id AS user_id, name AS user_name FROM users AS u WHERE u.status = 'active'")
    s("SELECT id, age + 1 AS age_plus_one FROM users")
    s("SELECT id, price * qty AS total_price FROM orders")
    s("SELECT id, (price - 1) / 2 AS adjusted_price FROM orders")

    # Aggregate and scalar functions
    s("SELECT COUNT(*) AS total_users FROM users")
    s("SELECT MIN(age) AS min_age, MAX(age) AS max_age, AVG(age) AS avg_age FROM users")
    s("SELECT UPPER(name) AS uname, LOWER(status) AS lstatus FROM users")
    s("SELECT COALESCE(name, 'unknown') AS name_or_unknown FROM users")
    s("SELECT CAST(age AS INTEGER) AS age_int FROM users")
    s("SELECT COALESCE(status, 'unknown') AS status_or_unknown FROM users")

    # Comparisons and predicates
    s("SELECT * FROM users WHERE age = 30")
    s("SELECT * FROM users WHERE age <> 30")
    s("SELECT * FROM users WHERE age != 30")
    s("SELECT * FROM users WHERE age < 30")
    s("SELECT * FROM users WHERE age <= 30")
    s("SELECT * FROM users WHERE age > 30")
    s("SELECT * FROM users WHERE age >= 30")
    s("SELECT * FROM users WHERE name LIKE 'A%'")
    s("SELECT * FROM users WHERE status IS NULL")
    s("SELECT * FROM users WHERE status IS NOT NULL")
    s("SELECT * FROM users WHERE age BETWEEN 18 AND 65")
    s("SELECT * FROM users WHERE age NOT BETWEEN 18 AND 65")
    s("SELECT * FROM users WHERE age > 18 AND status = 'active'")
    s("SELECT * FROM users WHERE age > 18 OR status = 'active'")
    s("SELECT * FROM users WHERE NOT (status = 'inactive')")
    s("SELECT * FROM users WHERE status IN ('active', 'pending')")
    s("SELECT * FROM users WHERE id NOT IN (1, 2, 3)")
    s("SELECT * FROM logs WHERE success IS TRUE")

    # Joins
    s("SELECT u.id, u.name, o.id AS order_id, o.price FROM users u INNER JOIN orders o ON u.id = o.user_id")
    s("SELECT u.id, o.id FROM users u LEFT JOIN orders o ON u.id = o.user_id")
    s("SELECT u.id, o.id FROM users u RIGHT JOIN orders o ON u.id = o.user_id")
    s("SELECT u.id, o.id FROM users u FULL OUTER JOIN orders o ON u.id = o.user_id")
    s("SELECT u.id, p.id FROM users u CROSS JOIN products p")
    s("SELECT u.id, o.id FROM users u JOIN orders o USING (id)")

    # Group by / Having / Order by
    s("SELECT user_id, COUNT(*) AS order_count FROM orders GROUP BY user_id")
    s("SELECT user_id, status, COUNT(*) AS cnt FROM orders GROUP BY user_id, status HAVING COUNT(*) > 1")
    s("SELECT status, AVG(age) AS avg_age FROM users WHERE age > 18 GROUP BY status HAVING AVG(age) >= 30 ORDER BY AVG(age) DESC")
    s("SELECT * FROM users ORDER BY created_at DESC, id ASC")
    s("SELECT id, name FROM users ORDER BY 1")
    s("SELECT * FROM orders ORDER BY price DESC LIMIT 10")
    s("SELECT * FROM orders ORDER BY price DESC LIMIT 10 OFFSET 5")
    s("SELECT * FROM users LIMIT 5")
    s("SELECT * FROM users LIMIT 5 OFFSET 10")
    s("SELECT * FROM users ORDER BY id OFFSET 10")

    # Set operations
    s("SELECT id FROM users UNION SELECT user_id AS id FROM orders")
    s("SELECT id FROM users UNION ALL SELECT user_id FROM orders")
    s("SELECT id FROM users INTERSECT SELECT user_id FROM orders")
    s("SELECT id FROM users EXCEPT SELECT user_id FROM orders")

    # Subqueries
    s("SELECT id, name FROM users WHERE id IN (SELECT user_id FROM orders WHERE price > 100)")
    s("SELECT id FROM users WHERE EXISTS (SELECT 1 FROM orders WHERE orders.user_id = users.id)")
    s("SELECT (SELECT MAX(price) FROM orders) AS max_price")
    s("SELECT u.id, (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.id) AS order_count FROM users u")
    s("SELECT * FROM users WHERE id = (SELECT MIN(id) FROM users)")
    s("SELECT sub.user_id, sub.total FROM (SELECT user_id, SUM(price) AS total FROM orders GROUP BY user_id) AS sub")
    s("SELECT * FROM products WHERE price > ALL (SELECT price FROM orders)")
    s("SELECT * FROM products WHERE price = ANY (SELECT price FROM orders)")

    # CASE expressions
    s("SELECT id, CASE WHEN age < 18 THEN 'minor' WHEN age >= 65 THEN 'senior' ELSE 'adult' END AS age_group FROM users")
    s("SELECT id, CASE status WHEN 'active' THEN 1 WHEN 'pending' THEN 0 ELSE -1 END AS status_code FROM users")

    # Window-like functions (if supported)
    s("SELECT id, name, ROW_NUMBER() OVER (PARTITION BY status ORDER BY created_at) AS rn FROM users")
    s("SELECT user_id, SUM(price) OVER (PARTITION BY user_id ORDER BY id) AS running_total FROM orders")

    # DML
    s("INSERT INTO users (id, name, age, status) VALUES (1, 'Alice', 30, 'active')")
    s("INSERT INTO users VALUES (2, 'Bob', 17, 'inactive')")
    s("INSERT INTO orders (id, user_id, price, qty) VALUES (1, 1, 10.5, 2), (2, 1, 20.0, 1)")
    s("INSERT INTO archive_orders SELECT * FROM orders WHERE created_at < '2020-01-01'")
    s("UPDATE users SET status = 'inactive' WHERE created_at < '2020-01-01'")
    s("UPDATE orders SET price = price * 1.1, qty = qty + 1 WHERE status = 'open'")
    s("UPDATE users SET status = 'active'")
    s("DELETE FROM orders WHERE price <= 0 OR status = 'cancelled'")
    s("DELETE FROM users")

    # DDL - tables
    s("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL, age INTEGER, status VARCHAR(20), created_at TIMESTAMP)")
    s("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), price NUMERIC(10,2) NOT NULL, qty INTEGER DEFAULT 1, status VARCHAR(20))")
    s("CREATE TABLE products (id INTEGER, name VARCHAR(100), price NUMERIC, CONSTRAINT pk_products PRIMARY KEY (id))")
    s("CREATE TABLE logs (id INTEGER PRIMARY KEY, message TEXT, level INTEGER CHECK(level >= 0 AND level <= 5))")
    s("CREATE TABLE categories (id INTEGER PRIMARY KEY, name VARCHAR(50) UNIQUE)")
    s("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
    s("ALTER TABLE users DROP COLUMN age")
    s("ALTER TABLE orders ADD CONSTRAINT fk_orders_users FOREIGN KEY (user_id) REFERENCES users(id)")
    s("DROP TABLE IF EXISTS temp_table")
    s("DROP TABLE users")

    # Indexes and views
    s("CREATE INDEX idx_users_status ON users(status)")
    s("DROP INDEX idx_users_status")
    s("CREATE VIEW active_users AS SELECT id, name FROM users WHERE status = 'active'")
    s("DROP VIEW active_users")

    # Transactions and utility
    s("BEGIN TRANSACTION")
    s("COMMIT")
    s("ROLLBACK")
    s("TRUNCATE TABLE orders")

    # Multi-statement script
    s("SELECT * FROM users; SELECT * FROM orders")

    return stmts


def extract_feature_items(sql: str) -> Set[str]:
    text = " " + sql.upper() + " "
    items: Set[str] = set()
    for name, pattern in FEATURE_PATTERNS:
        if pattern in text:
            items.add("FEAT_" + name)
    return items


def extract_ast_class_names(roots: List[Any], target_classes: List[type]) -> Set[str]:
    if not roots or not target_classes:
        return set()

    target_class_set = set(target_classes)
    primitives = (str, int, float, bool, bytes, type(None))
    seen_ids: Set[int] = set()
    found: Set[str] = set()

    def visit(node: Any) -> None:
        if node is None or isinstance(node, primitives):
            return
        if isinstance(node, (list, tuple, set)):
            for item in node:
                visit(item)
            return
        if isinstance(node, dict):
            for k, v in node.items():
                visit(k)
                visit(v)
            return
        obj_id = id(node)
        if obj_id in seen_ids:
            return
        seen_ids.add(obj_id)
        cls = node.__class__
        if cls in target_class_set:
            found.add(cls.__name__)
        try:
            attrs = vars(node)
        except TypeError:
            return
        for v in attrs.values():
            if isinstance(v, primitives):
                continue
            visit(v)

    for r in roots:
        visit(r)
    return found


def select_statements(
    valid_queries: List[str],
    coverage_by_stmt: List[Set[str]],
    max_statements: int = 60,
    min_statements_if_any: int = 20,
) -> List[str]:
    n = len(valid_queries)
    if n == 0:
        return []

    if not any(coverage_by_stmt):
        idxs = list(range(n))
        idxs.sort(key=lambda i: len(valid_queries[i]), reverse=True)
        return [valid_queries[i] for i in idxs[:max_statements]]

    covered: Set[str] = set()
    remaining_items: Set[str] = set()
    for cov in coverage_by_stmt:
        remaining_items |= cov

    selected_indices: List[int] = []
    used: Set[int] = set()

    while len(selected_indices) < max_statements:
        best_idx = None
        best_gain = -1
        best_score = -1.0
        for i in range(n):
            if i in used:
                continue
            cov = coverage_by_stmt[i]
            gain = len(cov - covered)
            score = gain * 1000.0 + len(valid_queries[i]) / 10.0
            if gain > best_gain or (gain == best_gain and score > best_score):
                best_idx = i
                best_gain = gain
                best_score = score
        if best_idx is None:
            break
        if best_gain <= 0 and len(selected_indices) >= min_statements_if_any:
            break
        used.add(best_idx)
        selected_indices.append(best_idx)
        covered |= coverage_by_stmt[best_idx]
        if covered >= remaining_items:
            break

    if len(selected_indices) < max_statements:
        remaining = [i for i in range(n) if i not in used]
        remaining.sort(key=lambda i: len(valid_queries[i]), reverse=True)
        extra_slots = max_statements - len(selected_indices)
        for i in remaining[:extra_slots]:
            selected_indices.append(i)

    return [valid_queries[i] for i in selected_indices]


class Solution:
    def solve(self, resources_path: str) -> List[str]:
        candidates = generate_candidates()

        # Add variants with semicolons to handle dialects that require them
        with_semicolons: List[str] = []
        for q in candidates:
            q_strip = q.strip()
            if not q_strip:
                continue
            with_semicolons.append(q_strip)
            if not q_strip.endswith(";"):
                with_semicolons.append(q_strip + ";")

        candidates = dedupe_preserve_order(with_semicolons)

        # Try to import parser and ast_nodes from provided resources
        sys.path.insert(0, resources_path)
        parse_sql = None
        ast_classes: List[type] = []

        try:
            importlib.import_module("sql_engine")
            engine_prefix = "sql_engine."
        except ImportError:
            engine_prefix = ""

        # Import parser
        parser_mod = None
        try:
            parser_mod = importlib.import_module(engine_prefix + "parser")  # type: ignore[arg-type]
        except ImportError:
            try:
                parser_mod = importlib.import_module("parser")
            except ImportError:
                parser_mod = None

        if parser_mod is not None and hasattr(parser_mod, "parse_sql"):
            parse_sql = getattr(parser_mod, "parse_sql")

        # Import ast_nodes
        ast_nodes_mod = None
        try:
            ast_nodes_mod = importlib.import_module(engine_prefix + "ast_nodes")  # type: ignore[arg-type]
        except ImportError:
            try:
                ast_nodes_mod = importlib.import_module("ast_nodes")
            except ImportError:
                ast_nodes_mod = None

        if ast_nodes_mod is not None:
            for name, obj in vars(ast_nodes_mod).items():
                if isinstance(obj, type) and obj.__module__ == ast_nodes_mod.__name__:
                    ast_classes.append(obj)

        # If we cannot import parser, fall back to static list
        if parse_sql is None:
            cleaned = [c.strip() for c in candidates if c.strip()]
            cleaned = dedupe_preserve_order(cleaned)
            cleaned.sort(key=lambda s: len(s), reverse=True)
            return cleaned[:60]

        valid_queries: List[str] = []
        coverage_by_stmt: List[Set[str]] = []

        for q in candidates:
            query = q.strip()
            if not query:
                continue
            try:
                res = parse_sql(query)
            except Exception:
                continue

            if isinstance(res, (list, tuple)):
                roots = [r for r in res if r is not None]
            elif res is None:
                roots = []
            else:
                roots = [res]

            ast_items = extract_ast_class_names(roots, ast_classes) if ast_classes else set()
            feature_items = extract_feature_items(query)
            coverage_items: Set[str] = set()
            for name in ast_items:
                coverage_items.add("AST_" + name)
            coverage_items |= feature_items

            valid_queries.append(query)
            coverage_by_stmt.append(coverage_items)

        if not valid_queries:
            fallback = [
                "SELECT 1",
                "SELECT * FROM users",
                "SELECT id FROM users",
            ]
            return dedupe_preserve_order([f.strip() for f in fallback if f.strip()])

        selected = select_statements(
            valid_queries,
            coverage_by_stmt,
            max_statements=60,
            min_statements_if_any=20,
        )
        return selected