import os
import sys
import re
import importlib
from typing import List, Tuple, Dict, Set


class Solution:
    def solve(self, resources_path: str) -> list[str]:
        # Helper: import parse_sql from the target engine if possible
        parse_sql = self._load_parse_fn(resources_path)
        keywords = self._extract_keywords(resources_path)
        # Candidates (category, sql)
        candidates: List[Tuple[str, str]] = []
        add = candidates.append

        # Utility lambdas
        k = keywords
        has = lambda *kw: all(w in k for w in kw)

        # Identifiers to use
        tables = ["employees", "departments", "orders", "products", "t1", "t2", "A", "B"]
        cols = ["id", "name", "price", "quantity", "department_id", "salary", "created_at", "active", "category"]

        # Build SQL templates conditioned on detected keyword support (best-effort).
        # Even if we over-generate, we filter by trying to parse via parse_sql.
        # SELECT statements
        if has("SELECT"):
            add(("select_basic", "SELECT 1"))
            add(("select_basic", "SELECT 1 + 2 * 3"))
            add(("select_basic", "SELECT -42"))
            add(("select_basic", "SELECT 3.14159"))
            add(("select_basic", "SELECT 1e10"))
            add(("select_basic", "SELECT NULL"))
            add(("select_basic", "SELECT 'hello'"))
            add(("select_basic", "SELECT 'O''Reilly'"))
            if has("FROM"):
                add(("select_from", "SELECT * FROM employees"))
                add(("select_from", "SELECT id, name FROM employees"))
                add(("select_from", "SELECT id AS emp_id, name AS emp_name FROM employees AS e"))
                add(("select_from", "SELECT e.id, e.name FROM employees e"))
                # Comments
                add(("select_comments", "-- single line comment\nSELECT * FROM employees"))
                add(("select_comments", "/* block comment */ SELECT id, name FROM employees"))
                add(("select_comments", "SELECT id, name FROM employees -- trailing comment\n"))
                # Expressions and aliases
                add(("select_expr", "SELECT salary * 1.1 AS new_salary FROM employees"))
                add(("select_expr", "SELECT (salary + 1000) / 2 AS half FROM employees"))
                add(("select_expr", "SELECT COALESCE(name, 'Unknown') AS n FROM employees"))
                add(("select_expr", "SELECT CASE WHEN active = 1 THEN 'Y' ELSE 'N' END AS flag FROM employees"))
                add(("select_expr", "SELECT CAST(salary AS INT) AS s FROM employees"))
                add(("select_expr", "SELECT name || ' ' || CAST(salary AS TEXT) AS info FROM employees"))
                # WHERE and predicates
                if has("WHERE"):
                    add(("select_where", "SELECT * FROM employees WHERE salary > 50000"))
                    add(("select_where", "SELECT * FROM employees WHERE salary BETWEEN 30000 AND 60000"))
                    add(("select_where", "SELECT * FROM employees WHERE NOT (active = 1)"))
                    add(("select_where", "SELECT * FROM employees WHERE department_id IN (1,2,3)"))
                    add(("select_where", "SELECT * FROM employees WHERE department_id NOT IN (4,5)"))
                    add(("select_where", "SELECT * FROM employees WHERE name LIKE 'A%' OR (name LIKE '%son' AND NOT (active = 1))"))
                    add(("select_where", "SELECT * FROM employees WHERE name IS NULL"))
                    add(("select_where", "SELECT * FROM employees WHERE name IS NOT NULL"))
                    add(("select_where", "SELECT * FROM employees WHERE id != 0"))
                # DISTINCT
                if has("DISTINCT"):
                    add(("select_distinct", "SELECT DISTINCT name FROM employees"))
                    add(("select_distinct", "SELECT COUNT(DISTINCT department_id) FROM employees"))
                # GROUP BY / HAVING
                if has("GROUP", "BY"):
                    add(("group_having", "SELECT department_id, COUNT(*) AS cnt FROM employees GROUP BY department_id"))
                    if has("HAVING"):
                        add(("group_having", "SELECT department_id, COUNT(*) AS cnt FROM employees GROUP BY department_id HAVING COUNT(*) > 5"))
                # ORDER BY
                if has("ORDER", "BY"):
                    add(("order_by", "SELECT name FROM employees ORDER BY name ASC"))
                    add(("order_by", "SELECT name FROM employees ORDER BY name DESC, id ASC"))
                    add(("order_by", "SELECT name FROM employees ORDER BY 1"))
                # LIMIT/OFFSET
                if has("LIMIT"):
                    add(("limit_offset", "SELECT name FROM employees LIMIT 10"))
                    if has("OFFSET"):
                        add(("limit_offset", "SELECT name FROM employees LIMIT 10 OFFSET 5"))
                # Subqueries
                add(("subquery", "SELECT name FROM employees WHERE id IN (SELECT id FROM employees WHERE salary > 10000)"))
                if has("EXISTS"):
                    add(("subquery", "SELECT name FROM employees WHERE EXISTS (SELECT 1 FROM departments WHERE departments.id = employees.department_id)"))
                if has("FROM"):
                    add(("subquery", "SELECT * FROM (SELECT id, name FROM employees) AS sub WHERE id > 10"))
                # Joins
                if has("JOIN"):
                    # INNER JOIN
                    if has("FROM", "JOIN", "ON"):
                        add(("join_inner", "SELECT e.name, d.name FROM employees e INNER JOIN departments d ON e.department_id = d.id"))
                        add(("join_inner", "SELECT * FROM employees e JOIN departments d ON e.department_id = d.id"))
                    # LEFT [OUTER] JOIN
                    if has("LEFT", "JOIN"):
                        if has("OUTER"):
                            add(("join_left", "SELECT e.name FROM employees e LEFT OUTER JOIN departments d ON e.department_id = d.id"))
                        else:
                            add(("join_left", "SELECT e.name FROM employees e LEFT JOIN departments d ON e.department_id = d.id"))
                    # RIGHT [OUTER] JOIN
                    if has("RIGHT", "JOIN"):
                        if has("OUTER"):
                            add(("join_right", "SELECT e.name FROM employees e RIGHT OUTER JOIN departments d ON e.department_id = d.id"))
                        else:
                            add(("join_right", "SELECT e.name FROM employees e RIGHT JOIN departments d ON e.department_id = d.id"))
                    # FULL [OUTER] JOIN
                    if has("FULL", "JOIN"):
                        if has("OUTER"):
                            add(("join_full", "SELECT e.name FROM employees e FULL OUTER JOIN departments d ON e.department_id = d.id"))
                        else:
                            add(("join_full", "SELECT e.name FROM employees e FULL JOIN departments d ON e.department_id = d.id"))
                    # CROSS JOIN
                    if has("CROSS", "JOIN"):
                        add(("join_cross", "SELECT e.name FROM employees e CROSS JOIN departments d"))
                    # NATURAL JOIN
                    if has("NATURAL", "JOIN"):
                        add(("join_natural", "SELECT * FROM employees NATURAL JOIN departments"))
                    # USING
                    if has("USING"):
                        add(("join_using", "SELECT * FROM employees e JOIN departments d USING (department_id)"))
                # Set operations
                if has("UNION"):
                    add(("set_ops", "SELECT name FROM employees UNION SELECT name FROM departments"))
                    if has("ALL"):
                        add(("set_ops", "SELECT id FROM employees UNION ALL SELECT id FROM departments"))
                if has("INTERSECT"):
                    add(("set_ops", "SELECT id FROM t1 INTERSECT SELECT id FROM t2"))
                if has("EXCEPT"):
                    add(("set_ops", "SELECT id FROM t1 EXCEPT SELECT id FROM t2"))
                # WITH CTE
                if has("WITH"):
                    add(("with_cte", "WITH cte AS (SELECT id FROM employees WHERE salary > 10000) SELECT * FROM cte"))
                # Functions in select list
                add(("functions", "SELECT COUNT(*) AS cnt FROM employees"))
                add(("functions", "SELECT SUM(salary), AVG(salary) FROM employees"))

        # INSERT
        if has("INSERT", "INTO"):
            add(("insert", "INSERT INTO employees (id, name, salary, department_id, active) VALUES (1, 'Alice', 50000, 10, 1)"))
            add(("insert", "INSERT INTO employees VALUES (2, 'Bob', 60000, 20, 0)"))
            if has("VALUES"):
                add(("insert", "INSERT INTO employees (id, name) VALUES (3, 'Carol'), (4, 'Dave')"))
            if has("SELECT", "FROM"):
                add(("insert", "INSERT INTO employees (id, name) SELECT id, name FROM t1"))

        # UPDATE
        if has("UPDATE", "SET"):
            add(("update", "UPDATE employees SET salary = salary * 1.05, active = 1 WHERE id = 1"))
            if has("SELECT"):
                add(("update", "UPDATE employees SET department_id = (SELECT id FROM departments WHERE name = 'HR') WHERE name = 'Alice'"))

        # DELETE
        if has("DELETE", "FROM"):
            add(("delete", "DELETE FROM employees WHERE id = 2"))
            add(("delete", "DELETE FROM employees"))

        # CREATE TABLE
        if has("CREATE", "TABLE"):
            add(("create_table", "CREATE TABLE employees (id INT PRIMARY KEY, name VARCHAR(100) NOT NULL, salary DECIMAL(10,2) DEFAULT 0, department_id INT, active BOOLEAN, created_at TIMESTAMP)"))
            add(("create_table", "CREATE TABLE departments (id INT PRIMARY KEY, name TEXT UNIQUE, parent_id INT, CHECK (parent_id >= 0))"))
            if has("IF", "NOT", "EXISTS"):
                add(("create_table", "CREATE TABLE IF NOT EXISTS t1 (c1 INTEGER, c2 TEXT)"))

        # ALTER TABLE
        if has("ALTER", "TABLE"):
            if has("ADD", "COLUMN"):
                add(("alter_table", "ALTER TABLE employees ADD COLUMN age INT"))
            if has("DROP", "COLUMN"):
                add(("alter_table", "ALTER TABLE employees DROP COLUMN active"))
            if has("RENAME", "TO"):
                add(("alter_table", "ALTER TABLE employees RENAME TO employees_old"))

        # CREATE INDEX
        if has("CREATE", "INDEX"):
            if has("ON"):
                add(("create_index", "CREATE INDEX idx_emp_dept ON employees (department_id)"))
                if has("UNIQUE"):
                    add(("create_index", "CREATE UNIQUE INDEX idx_emp_name ON employees (name)"))

        # DROP
        if has("DROP", "TABLE"):
            add(("drop", "DROP TABLE employees"))
            if has("IF", "EXISTS"):
                add(("drop", "DROP TABLE IF EXISTS employees"))
        if has("DROP", "INDEX"):
            add(("drop", "DROP INDEX idx_emp_dept"))
            if has("IF", "EXISTS"):
                add(("drop", "DROP INDEX IF EXISTS idx_emp_dept"))

        # Quoted identifiers
        if has("SELECT"):
            add(("quoted_ident", 'SELECT "name" FROM "employees"'))
            add(("quoted_ident", 'SELECT "e"."id", "e"."name" FROM "employees" AS "e"'))

        # Edge cases for tokenizer/operators
        if has("SELECT"):
            add(("operators", "SELECT ~1"))
            add(("operators", "SELECT 1 << 2"))
            add(("operators", "SELECT 8 >> 1"))
            add(("operators", "SELECT 5 | 3, 5 & 3, 5 ^ 3"))
            add(("operators", "SELECT +1, -2, +(+3), -(+4)"))
            add(("operators", "SELECT 10/2, 10%3, 10-3, 10+3"))

        # Fallback minimal if no keywords
        if not candidates:
            fallback = [
                "SELECT 1",
                "SELECT 'hello'",
                "SELECT 1 + 2 * 3",
                "SELECT NULL",
            ]
            return fallback

        # Now filter candidates by actually parsing them when possible
        seen: Set[str] = set()
        valid_by_cat: Dict[str, List[str]] = {}

        def normalize(s: str) -> str:
            # normalize whitespace for deduplication
            return re.sub(r"\s+", " ", s.strip())

        for cat, sql in candidates:
            key = normalize(sql).lower()
            if key in seen:
                continue
            if parse_sql is not None:
                try:
                    parse_sql(sql)
                except Exception:
                    continue
            seen.add(key)
            valid_by_cat.setdefault(cat, []).append(sql)

        # If parse_sql is not available, just return a curated trimmed set (cap at 50)
        if parse_sql is None:
            flat = []
            for _, sql in candidates:
                nk = normalize(sql).lower()
                if nk not in seen:
                    seen.add(nk)
                    flat.append(sql)
                if len(flat) >= 50:
                    break
            return flat

        # Build final list with prioritization and cap total size
        priority_order = [
            "create_table",
            "create_index",
            "insert",
            "update",
            "delete",
            "select_basic",
            "select_from",
            "select_expr",
            "select_where",
            "select_distinct",
            "group_having",
            "order_by",
            "limit_offset",
            "join_inner",
            "join_left",
            "join_right",
            "join_full",
            "join_cross",
            "join_natural",
            "join_using",
            "subquery",
            "set_ops",
            "with_cte",
            "functions",
            "quoted_ident",
            "operators",
            "select_comments",
            "alter_table",
            "drop",
        ]

        final: List[str] = []

        # ensure we cover as many categories as possible, limit per category
        per_cat_limit = {
            "select_basic": 3,
            "select_from": 3,
            "select_expr": 3,
            "select_where": 5,
            "group_having": 3,
            "order_by": 3,
            "limit_offset": 2,
            "join_inner": 2,
            "join_left": 2,
            "join_right": 1,
            "join_full": 1,
            "join_cross": 1,
            "join_natural": 1,
            "join_using": 1,
            "subquery": 3,
            "set_ops": 3,
            "with_cte": 1,
            "functions": 2,
            "quoted_ident": 2,
            "operators": 4,
            "select_comments": 2,
            "create_table": 3,
            "create_index": 2,
            "insert": 4,
            "update": 2,
            "delete": 2,
            "alter_table": 3,
            "drop": 3,
        }

        cap_total = 50

        for cat in priority_order:
            items = valid_by_cat.get(cat, [])
            if not items:
                continue
            limit = per_cat_limit.get(cat, 2)
            for sql in items[:limit]:
                final.append(sql)
                if len(final) >= cap_total:
                    return final

        # If still room, add any remaining valid statements not yet added
        if len(final) < cap_total:
            # Flatten remaining
            for cat, items in valid_by_cat.items():
                for sql in items:
                    if sql not in final:
                        final.append(sql)
                        if len(final) >= cap_total:
                            break
                if len(final) >= cap_total:
                    break

        return final

    def _load_parse_fn(self, resources_path: str):
        try:
            if not os.path.isdir(resources_path):
                return None
            sys.path.insert(0, resources_path)
            parser_mod = importlib.import_module("sql_engine.parser")
            parse_sql = getattr(parser_mod, "parse_sql", None)
            return parse_sql
        except Exception:
            return None
        finally:
            # Do not remove path to avoid breaking imports during evaluation
            pass

    def _extract_keywords(self, resources_path: str) -> Set[str]:
        keywords: Set[str] = set()
        try:
            tok_path = os.path.join(resources_path, "sql_engine", "tokenizer.py")
            if os.path.isfile(tok_path):
                with open(tok_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                # Extract uppercase words inside quotes
                for m in re.finditer(r"['\"]([A-Z_]+)['\"]", text):
                    kw = m.group(1)
                    if kw.isupper():
                        keywords.add(kw)
                # Also catch bare uppercase tokens in enums or patterns
                for m in re.finditer(r"\b([A-Z]{2,})\b", text):
                    keywords.add(m.group(1))
        except Exception:
            pass

        # Also scan grammar if exists for keyword-like tokens
        try:
            gram_path = os.path.join(resources_path, "sql_grammar.txt")
            if os.path.isfile(gram_path):
                with open(gram_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                for m in re.finditer(r"\b([A-Z][A-Z_]+)\b", text):
                    keywords.add(m.group(1))
        except Exception:
            pass

        return keywords