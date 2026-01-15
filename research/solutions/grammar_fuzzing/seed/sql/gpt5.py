import os
import sys
import re

def _load_parse_func(resources_path: str):
    parse_sql = None
    try:
        if resources_path and os.path.isdir(resources_path):
            if resources_path not in sys.path:
                sys.path.insert(0, resources_path)
        import importlib
        try:
            mod = importlib.import_module("sql_engine")
            parse_sql = getattr(mod, "parse_sql", None)
        except Exception:
            parse_sql = None
        if parse_sql is None:
            try:
                modp = importlib.import_module("sql_engine.parser")
                parse_sql = getattr(modp, "parse_sql", None)
            except Exception:
                parse_sql = None
    except Exception:
        parse_sql = None
    return parse_sql

def _try_parse(parse_sql, stmt: str) -> str | None:
    if parse_sql is None:
        return None
    s = stmt.strip()
    if not s:
        return None
    variants = []
    # original
    variants.append(s)
    # toggle semicolon
    if s.endswith(";"):
        variants.append(s[:-1].rstrip())
    else:
        variants.append(s + ";")
    # compress internal whitespace
    compact = re.sub(r"\s+", " ", s).strip()
    if compact != s:
        variants.append(compact)
        if compact.endswith(";"):
            variants.append(compact[:-1].rstrip())
        else:
            variants.append(compact + ";")
    # ensure uniqueness in variants
    seen = set()
    uniq_variants = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            uniq_variants.append(v)
    for v in uniq_variants:
        try:
            parse_sql(v)
            return v
        except Exception:
            continue
    return None

def _base_candidates():
    stmts = []
    # Simple selects
    stmts += [
        "SELECT 1",
        "select 1",
        "SELECT 1 AS one",
        "SELECT 'text' AS s",
        "SELECT 'It''s fine' AS note",
        "SELECT 1 + 2 * 3 AS calc",
        "SELECT (1 + 2) * 3 AS calc",
    ]
    # Unary operators and arithmetic precedence
    stmts += [
        "SELECT -1 AS neg, +2 AS pos, 5 - 3 + 2 AS expr",
        "SELECT 10 / 2 AS div, 10 % 3 AS mod",
    ]
    # Star and aliases
    stmts += [
        "SELECT * FROM users",
        "SELECT u.* FROM users AS u",
        "SELECT id, name FROM users",
    ]
    # Where, conjunctions, comparisons
    stmts += [
        "SELECT id FROM users WHERE age > 18",
        "SELECT id FROM users WHERE age >= 18 AND age < 30",
        "SELECT id FROM users WHERE name = 'Alice' OR name = 'Bob'",
        "SELECT id FROM users WHERE id IN (1, 2, 3)",
        "SELECT id FROM users WHERE id NOT IN (1, 2, 3)",
        "SELECT id FROM users WHERE id BETWEEN 1 AND 10",
        "SELECT id FROM users WHERE id IS NULL",
        "SELECT id FROM users WHERE id IS NOT NULL",
        "SELECT name FROM users WHERE name LIKE 'A%'",
    ]
    # Case expression, functions, casts
    stmts += [
        "SELECT CASE WHEN age < 18 THEN 'minor' WHEN age >= 65 THEN 'senior' ELSE 'adult' END AS category FROM users",
        "SELECT COALESCE(name, 'unknown') AS n FROM users",
        "SELECT CAST(age AS INTEGER) AS a FROM users",
        "SELECT ABS(-5), LENGTH(name) FROM users",
        "SELECT UPPER(name), LOWER(name) FROM users",
        "SELECT SUBSTR(name, 1, 3) FROM users",
    ]
    # Group by, having
    stmts += [
        "SELECT user_id, COUNT(*) AS c FROM orders GROUP BY user_id",
        "SELECT user_id, COUNT(*) AS c FROM orders GROUP BY user_id HAVING COUNT(*) > 1",
        "SELECT COUNT(*), SUM(amount), AVG(amount), MIN(amount), MAX(amount) FROM orders",
    ]
    # Order by, limit, offset
    stmts += [
        "SELECT * FROM users ORDER BY age DESC, name ASC",
        "SELECT * FROM users ORDER BY 1 DESC",
        "SELECT * FROM users LIMIT 10",
        "SELECT * FROM users LIMIT 5 OFFSET 10",
    ]
    # Joins
    stmts += [
        "SELECT * FROM users AS u INNER JOIN orders AS o ON u.id = o.user_id",
        "SELECT u.id, o.amount FROM users AS u LEFT JOIN orders AS o ON u.id = o.user_id",
        "SELECT * FROM users CROSS JOIN orders",
        "SELECT * FROM users JOIN orders ON users.id = orders.user_id",
    ]
    # Subqueries
    stmts += [
        "SELECT (SELECT MAX(age) FROM users) AS max_age",
        "SELECT id FROM users WHERE EXISTS (SELECT 1 FROM orders WHERE orders.user_id = users.id)",
    ]
    # Set ops
    stmts += [
        "SELECT 1 UNION SELECT 2",
        "SELECT 1 UNION ALL SELECT 1",
    ]
    # DDL
    stmts += [
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(100), age INTEGER, status TEXT, created_at TIMESTAMP)",
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, amount NUMERIC(10,2))",
        "CREATE INDEX idx_users_name ON users (name)",
        "DROP TABLE orders",
        "ALTER TABLE users ADD COLUMN email TEXT",
    ]
    # DML
    stmts += [
        "INSERT INTO users (id, name, age) VALUES (1, 'Alice', 30)",
        "INSERT INTO users VALUES (2, 'Bob', 25)",
        "INSERT INTO orders (id, user_id, amount) SELECT 1, id, 99.99 FROM users WHERE id = 1",
        "UPDATE users SET name = 'Alice', age = age + 1 WHERE id = 1",
        "UPDATE orders SET amount = amount * 1.1",
        "DELETE FROM users WHERE id = 1",
        "DELETE FROM orders WHERE user_id IN (SELECT id FROM users)",
    ]
    # Comments and whitespace variants
    stmts += [
        "SELECT /* block comment */ 1",
        "-- line comment\nSELECT 2",
        "SELECT 3 -- end comment",
        "SELECT 4 /* c */ + /* c */ 5",
    ]
    # CTEs (common but may be dropped if unsupported)
    stmts += [
        "WITH recent AS (SELECT * FROM orders WHERE amount > 100) SELECT * FROM recent",
    ]
    return stmts

def _extended_candidates():
    stmts = []
    # Additional joins
    join_ext = [
        "SELECT * FROM users RIGHT JOIN orders ON users.id = orders.user_id",
        "SELECT * FROM users RIGHT OUTER JOIN orders ON users.id = orders.user_id",
        "SELECT * FROM users LEFT OUTER JOIN orders ON users.id = orders.user_id",
        "SELECT * FROM users FULL JOIN orders ON users.id = orders.user_id",
        "SELECT * FROM users FULL OUTER JOIN orders ON users.id = orders.user_id",
        "SELECT * FROM users NATURAL JOIN orders",
        "SELECT * FROM users u JOIN orders o USING (id)",
    ]
    stmts += join_ext
    # More set operations
    stmts += [
        "SELECT 1 INTERSECT SELECT 1",
        "SELECT 1 EXCEPT SELECT 2",
    ]
    # More expressions/operators
    stmts += [
        "SELECT 1 = 1, 1 <> 2, 1 != 2, 1 < 2, 2 > 1, 2 <= 2, 2 >= 2",
        "SELECT NOT (1 = 2) AND (2 = 2) OR 0",
        "SELECT 1 << 2 AS lsh, 8 >> 1 AS rsh, 1 | 2 AS bor, 1 & 3 AS band",
    ]
    # Casting/types
    stmts += [
        "SELECT CAST(1 AS TEXT)",
        "SELECT CAST('123' AS INTEGER)",
        "SELECT NULLIF(1, 1), COALESCE(NULL, 'x')",
        "SELECT GREATEST(1, 2, 3), LEAST(3, 2, 1)",
    ]
    # Date/time literals/functions
    stmts += [
        "SELECT DATE '2020-01-01', TIMESTAMP '2020-01-01 00:00:00'",
        "SELECT CURRENT_TIMESTAMP, CURRENT_DATE, CURRENT_TIME",
        "SELECT NOW()",
    ]
    # More DML/DDL
    stmts += [
        "CREATE TEMP TABLE temp_data (k TEXT, v INT)",
        "CREATE TABLE IF NOT EXISTS products (id INT PRIMARY KEY, price DECIMAL(10,2) CHECK (price >= 0))",
        "DROP TABLE IF EXISTS temp_data",
        "ALTER TABLE users RENAME COLUMN name TO full_name",
        "ALTER TABLE users DROP COLUMN status",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_user ON orders (user_id)",
        "DROP INDEX IF EXISTS idx_orders_user",
        "CREATE VIEW active_users AS SELECT * FROM users WHERE status = 'active'",
        "DROP VIEW IF EXISTS active_users",
    ]
    # CTE recursive
    stmts += [
        "WITH RECURSIVE t(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM t WHERE n < 3) SELECT * FROM t",
    ]
    # Parameter placeholders/styles
    stmts += [
        "SELECT ?",
        "SELECT $1, $2",
        "SELECT :param",
    ]
    # Ordering nulls
    stmts += [
        "SELECT * FROM users ORDER BY age NULLS FIRST",
        "SELECT * FROM users ORDER BY age NULLS LAST",
    ]
    # Escaped like pattern with ESCAPE
    stmts += [
        "SELECT name FROM users WHERE name LIKE 'A\\_%' ESCAPE '\\'",
    ]
    # Distinct/All
    stmts += [
        "SELECT DISTINCT name FROM users",
        "SELECT ALL id FROM users",
    ]
    # Window functions (if supported)
    stmts += [
        "SELECT id, ROW_NUMBER() OVER (PARTITION BY status ORDER BY id) FROM users",
        "SELECT SUM(amount) OVER (ORDER BY id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) FROM orders",
    ]
    # Union with order/limit
    stmts += [
        "(SELECT 1) UNION ALL (SELECT 2) ORDER BY 1 LIMIT 1",
    ]
    # IS DISTINCT FROM (PostgreSQL)
    stmts += [
        "SELECT 1 IS DISTINCT FROM 2, 1 IS NOT DISTINCT FROM 1",
    ]
    return stmts

def _filter_parseable(statements, parse_sql, max_count=60):
    out = []
    seen = set()
    for s in statements:
        accepted = _try_parse(parse_sql, s)
        if accepted is not None:
            if accepted not in seen:
                seen.add(accepted)
                out.append(accepted)
                if len(out) >= max_count:
                    break
    return out

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        parse_sql = _load_parse_func(resources_path)
        base = _base_candidates()
        ext = _extended_candidates()
        # Reorder: put DDL first to potentially unlock branches in parser initialization
        ddl = [s for s in base if re.match(r"^\s*(CREATE|DROP|ALTER)\b", s, re.IGNORECASE)]
        dml = [s for s in base if re.match(r"^\s*(INSERT|UPDATE|DELETE)\b", s, re.IGNORECASE)]
        sel = [s for s in base if s not in ddl and s not in dml]
        ordered = ddl + dml + sel + ext
        if parse_sql is not None:
            res = _filter_parseable(ordered, parse_sql, max_count=70)
            # Add a few comment-wrapped variants if supported
            extra_candidates = []
            for s in list(res)[:10]:
                extra_candidates.append(f"/* before */ {s}")
                extra_candidates.append(f"{s} -- after")
            more = _filter_parseable(extra_candidates, parse_sql, max_count=80 - len(res))
            res.extend(more)
            # Ensure we don't exceed a moderate number of statements
            if len(res) > 80:
                res = res[:80]
            return res
        # Fallback: no filtering available, return a conservative baseline to keep efficiency
        # Cap to around 50 diverse and likely-parseable statements
        conservative = []
        seen = set()
        for s in ordered:
            if len(conservative) >= 50:
                break
            if s not in seen:
                seen.add(s)
                conservative.append(s)
        return conservative