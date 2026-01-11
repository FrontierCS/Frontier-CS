import os
import sys
import importlib
from typing import List

class Solution:
    def _import_parse_sql(self, resources_path: str):
        parse_sql = None
        # Ensure import path
        if resources_path not in sys.path:
            sys.path.insert(0, resources_path)
        try:
            pkg = importlib.import_module('sql_engine')
            parse_sql = getattr(pkg, 'parse_sql', None)
            if parse_sql is None:
                parser_mod = importlib.import_module('sql_engine.parser')
                parse_sql = getattr(parser_mod, 'parse_sql', None)
        except Exception:
            try:
                parser_mod = importlib.import_module('sql_engine.parser')
                parse_sql = getattr(parser_mod, 'parse_sql', None)
            except Exception:
                parse_sql = None
        return parse_sql

    def _attempt_parse(self, parse_sql, stmt: str) -> str | None:
        if parse_sql is None:
            # If we cannot import parser, don't filter
            return stmt
        tries = []
        s = stmt.strip()
        tries.append(s)
        if not s.endswith(';'):
            tries.append(s + ';')
        # Also try with a leading comment variant if not already commented
        if not s.lstrip().startswith('--') and not s.lstrip().startswith('/*'):
            tries.append("/* leading */ " + s)
            if not s.endswith(';'):
                tries.append("/* leading */ " + s + ';')
        for t in tries:
            try:
                parse_sql(t)
                return t
            except Exception:
                continue
        return None

    def _generate_candidates(self) -> List[str]:
        candidates: List[str] = []
        # Comments and simple selects
        candidates += [
            "/* leading comment */ SELECT 1",
            "SELECT /* inline */ 1",
            "SELECT 1; -- trailing comment",
            "-- full line comment\nSELECT 1",
        ]
        # DDL
        candidates += [
            "CREATE TABLE employees (id INT PRIMARY KEY, full_name TEXT NOT NULL, department_id INT, salary DECIMAL(10,2) DEFAULT 0, active BOOLEAN DEFAULT TRUE, hire_date DATE, email VARCHAR(255), CHECK (salary >= 0), UNIQUE(full_name))",
            "CREATE TABLE departments (id INT PRIMARY KEY, name TEXT UNIQUE)",
            "CREATE INDEX idx_emp_dept ON employees(department_id, salary DESC)",
            "CREATE UNIQUE INDEX idx_dept_name ON departments(name)",
            "ALTER TABLE employees ADD COLUMN bonus NUMERIC(10,2) DEFAULT 0",
            "ALTER TABLE employees RENAME COLUMN full_name TO name",
            "ALTER TABLE employees DROP COLUMN bonus",
            "DROP INDEX idx_emp_dept",
            "DROP TABLE departments",
            "CREATE VIEW emp_view AS SELECT id, name FROM employees WHERE active = TRUE",
            "DROP VIEW emp_view",
        ]
        # Transactions (if supported)
        candidates += [
            "BEGIN",
            "BEGIN TRANSACTION",
            "COMMIT",
            "ROLLBACK",
        ]
        # INSERTs
        candidates += [
            "INSERT INTO departments (id, name) VALUES (1, 'HR'), (2, 'Engineering'), (3, 'Sales')",
            "INSERT INTO employees (id, name, department_id, salary, active, hire_date, email) VALUES (1, 'Alice', 1, 100000.50, TRUE, '2020-01-01', 'alice@example.com')",
            "INSERT INTO employees SELECT id, name, id, 0, TRUE, NULL, NULL FROM departments",
            "INSERT INTO employees (id, name, department_id) VALUES (2, 'Bob', 2)",
        ]
        # UPDATEs
        candidates += [
            "UPDATE employees SET salary = salary + 1000, active = NOT active WHERE department_id IN (SELECT id FROM departments WHERE name LIKE 'E%')",
            "UPDATE employees SET department_id = 3 WHERE id = 2",
        ]
        # DELETEs
        candidates += [
            "DELETE FROM employees WHERE NOT active OR salary IS NULL",
            "DELETE FROM employees",
        ]
        # VALUES-only statement (if supported)
        candidates += [
            "VALUES (1), (2), (3)"
        ]
        # SELECT basics
        candidates += [
            "SELECT * FROM employees",
            "SELECT DISTINCT department_id FROM employees WHERE active = TRUE ORDER BY department_id DESC",
            "SELECT id, name AS full_name, salary + 1000 AS salary_plus, COALESCE(email, 'n/a') AS email FROM employees WHERE salary >= 50000 AND name LIKE '%a%' ORDER BY 4 ASC, full_name DESC LIMIT 10 OFFSET 5",
        ]
        # Joins
        candidates += [
            "SELECT e.id, d.name AS dept_name FROM employees e INNER JOIN departments d ON e.department_id = d.id",
            "SELECT e.id, d.name FROM employees e LEFT JOIN departments d ON e.department_id = d.id WHERE d.id IS NULL",
            "SELECT e.id FROM employees e RIGHT JOIN departments d ON e.department_id = d.id",
            "SELECT e.id FROM employees e CROSS JOIN departments d",
            "SELECT e.id FROM employees e JOIN departments d USING (department_id)",
            "SELECT e.id, d.name FROM employees e NATURAL JOIN departments d",
        ]
        # Aggregates and GROUP BY/HAVING
        candidates += [
            "SELECT COUNT(*) AS cnt, MIN(salary), MAX(salary), AVG(salary), SUM(salary) FROM employees GROUP BY department_id HAVING SUM(salary) > 0 ORDER BY cnt",
            "SELECT department_id, COUNT(*) FROM employees GROUP BY department_id",
        ]
        # CASE
        candidates += [
            "SELECT CASE WHEN salary > 100000 THEN 'high' WHEN salary BETWEEN 70000 AND 100000 THEN 'mid' ELSE 'low' END AS band FROM employees",
            "SELECT SUM(CASE WHEN active THEN 1 ELSE 0 END) AS active_count FROM employees",
        ]
        # Expressions and predicates
        candidates += [
            "SELECT (salary + 1000) / 2 AS avg_comp FROM employees",
            "SELECT EXISTS(SELECT 1 FROM employees WHERE active) AS has_active",
            "SELECT id FROM employees WHERE id IN (1, 2, 3) AND department_id IN (SELECT id FROM departments WHERE name = 'HR')",
            "SELECT id FROM employees WHERE name IS NOT NULL AND email IS NULL",
            "SELECT id FROM employees WHERE name LIKE 'A%' AND name NOT LIKE '%z%'",
            "SELECT id FROM employees WHERE salary BETWEEN 50000 AND 70000",
            "SELECT id FROM employees WHERE (salary > 100000 OR department_id = 2) AND NOT active",
            "SELECT id FROM employees ORDER BY salary DESC, id ASC LIMIT 5",
            "SELECT id FROM employees WHERE name BETWEEN 'A' AND 'M'",
            "SELECT id FROM employees ORDER BY 1",
        ]
        # Set operations
        candidates += [
            "SELECT id FROM employees UNION SELECT id FROM departments",
            "SELECT id FROM employees UNION ALL SELECT id FROM employees WHERE id < 10",
            "SELECT id FROM employees INTERSECT SELECT department_id FROM employees",
            "SELECT id FROM employees EXCEPT SELECT department_id FROM employees",
        ]
        # Subqueries in FROM and scalar subqueries
        candidates += [
            "SELECT t.id FROM (SELECT id, department_id FROM employees WHERE id > 0) t WHERE t.department_id IS NOT NULL",
            "SELECT (SELECT COUNT(*) FROM employees e2 WHERE e2.department_id = e.department_id) AS cnt FROM employees e",
        ]
        # Functions and numeric ops
        candidates += [
            "SELECT LENGTH(name), LOWER(name), UPPER(name), ABS(salary) FROM employees",
            "SELECT +1, -2, 3 * -4",
            "SELECT 'a', 'b''c'",
            "SELECT TRUE, FALSE, NULL",
            "SELECT 1 = 1, 2 <> 3, 4 <= 5, 6 >= 7, 8 != 9",
            "SELECT 1 + 2 * 3 - 4 / 5, (1 + 2) * 3",
            'SELECT id FROM "employees"',
            "SELECT now()",
            "SELECT CAST(salary AS INT), CAST('1' AS INTEGER) FROM employees",
            "WITH cte AS (SELECT id, department_id FROM employees) SELECT id FROM cte WHERE department_id IS NOT NULL",
            "SELECT COALESCE(NULL, 1, 2), NULLIF(1, 1)",
        ]
        # Potential tokenizer edge-cases: decimals and scientific notation
        candidates += [
            "SELECT 0.5, 1., .25, 1e3, 2.5e-2",
        ]
        # Potential NULLS FIRST/LAST if supported
        candidates += [
            "SELECT id FROM employees ORDER BY salary DESC NULLS LAST",
            "SELECT id FROM employees ORDER BY salary ASC NULLS FIRST",
        ]
        return candidates

    def solve(self, resources_path: str) -> List[str]:
        parse_sql = self._import_parse_sql(resources_path)
        candidates = self._generate_candidates()
        accepted: List[str] = []
        seen = set()
        for stmt in candidates:
            ok_stmt = self._attempt_parse(parse_sql, stmt)
            if ok_stmt is not None:
                s_norm = ok_stmt.strip()
                if s_norm not in seen:
                    seen.add(s_norm)
                    accepted.append(ok_stmt)
            # Limit to keep efficiency reasonable
            if len(accepted) >= 60:
                break

        # Fallback minimal set if nothing parsed
        if not accepted:
            minimal = [
                "SELECT 1",
                "SELECT 1 + 2 * 3",
                "SELECT 'a'",
                "SELECT TRUE, FALSE, NULL",
            ]
            for m in minimal:
                ok_m = self._attempt_parse(parse_sql, m)
                if ok_m is not None:
                    if ok_m.strip() not in seen:
                        seen.add(ok_m.strip())
                        accepted.append(ok_m)
                if len(accepted) >= 10:
                    break
            if not accepted:
                # Ultimate fallback: return a basic SELECT
                return ["SELECT 1"]
        return accepted