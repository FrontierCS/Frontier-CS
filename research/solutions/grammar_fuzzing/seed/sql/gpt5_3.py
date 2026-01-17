import os
import re
from typing import List, Set, Dict

class Solution:
    def solve(self, resources_path: str) -> List[str]:
        def safe_read(path: str) -> str:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except:
                return ""
        
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        engine_dir = os.path.join(resources_path, "sql_engine")
        parser_path = os.path.join(engine_dir, "parser.py")
        tokenizer_path = os.path.join(engine_dir, "tokenizer.py")
        ast_path = os.path.join(engine_dir, "ast_nodes.py")
        
        text_sources = [
            safe_read(grammar_path),
            safe_read(parser_path),
            safe_read(tokenizer_path),
            safe_read(ast_path),
        ]
        all_text = "\n".join(text_sources).upper()
        
        def has_word(word: str) -> bool:
            try:
                return re.search(r'(?<![A-Z0-9_])' + re.escape(word.upper()) + r'(?![A-Z0-9_])', all_text, re.IGNORECASE) is not None
            except:
                return word.upper() in all_text
        
        # High-level feature detection
        supports: Dict[str, bool] = {
            "select": True if all_text else True,
            "from": has_word("FROM"),
            "joins": has_word("JOIN"),
            "left_join": has_word("LEFT") and has_word("JOIN"),
            "right_join": has_word("RIGHT") and has_word("JOIN"),
            "full_join": has_word("FULL") and has_word("JOIN"),
            "cross_join": has_word("CROSS") and has_word("JOIN"),
            "using_join": has_word("USING"),
            "natural_join": has_word("NATURAL") and has_word("JOIN"),
            "where": has_word("WHERE"),
            "order_by": has_word("ORDER") and has_word("BY"),
            "nulls": has_word("NULLS"),
            "limit": has_word("LIMIT"),
            "offset": has_word("OFFSET"),
            "distinct": has_word("DISTINCT"),
            "group_by": has_word("GROUP") and has_word("BY"),
            "having": has_word("HAVING"),
            "union": has_word("UNION"),
            "intersect": has_word("INTERSECT"),
            "except": has_word("EXCEPT"),
            "cte": has_word("WITH"),
            "recursive": has_word("RECURSIVE"),
            "exists": has_word("EXISTS"),
            "case": has_word("CASE"),
            "between": has_word("BETWEEN"),
            "like": has_word("LIKE"),
            "ilike": has_word("ILIKE"),
            "is_null": has_word("IS") and has_word("NULL"),
            "window": has_word("OVER"),
            "insert": has_word("INSERT"),
            "update": has_word("UPDATE"),
            "delete": has_word("DELETE"),
            "create_table": has_word("CREATE") and has_word("TABLE"),
            "alter_table": has_word("ALTER") and has_word("TABLE"),
            "drop_table": has_word("DROP") and has_word("TABLE"),
            "indexes": has_word("CREATE") and has_word("INDEX"),
            "drop_index": has_word("DROP") and has_word("INDEX"),
            "views": has_word("CREATE") and has_word("VIEW"),
            "drop_view": has_word("DROP") and has_word("VIEW"),
            "foreign": has_word("FOREIGN") and has_word("REFERENCES"),
            "returning": has_word("RETURNING"),
            "if_exists": has_word("IF") and has_word("EXISTS"),
            "rename_column": has_word("RENAME") and has_word("COLUMN"),
            "add_column": has_word("ADD") and has_word("COLUMN"),
            "drop_column": has_word("DROP") and has_word("COLUMN"),
        }
        
        # Helper to add statements conditionally
        cases: List[str] = []
        def add(stmt: str, feats: Set[str] = None):
            if feats is None:
                feats = set()
            for f in feats:
                if not supports.get(f, False):
                    return
            cases.append(stmt.strip())
        
        # Basic SELECTs and expressions
        add("SELECT 1;", {"select"})
        add("SELECT 1+2*3 AS a, -4 AS b, 5.5 AS c, 6e-2 AS d;", {"select"})
        add("SELECT 'A' || 'B' AS ab, 'O''Reilly' AS quoted;", {"select"})
        add("SELECT NULL;", {"select"})
        if supports["is_null"]:
            add("SELECT NULL IS NULL AS isnull, 1 = 1 AS eq, 2 <> 3 AS ne, 4 >= 4 AS ge, 5 <= 6 AS le;", {"select", "is_null"})
        add("SELECT COALESCE(NULL, 'X') AS c, ABS(-1) AS a, LOWER('ABC') AS l, UPPER('abc') AS u;", {"select"})
        
        # Simple FROM
        if supports["from"]:
            add("SELECT * FROM employees;", {"select", "from"})
            add("SELECT t.id, t.name FROM employees AS t;", {"select", "from"})
        
        # WHERE, ORDER BY, LIMIT, OFFSET, LIKE/IS NULL
        if supports["from"]:
            feat_set = {"select", "from"}
            if supports["joins"]:
                join_stmt = "INNER JOIN departments d ON e.dept_id = d.id"
                if supports["left_join"]:
                    join_stmt = "LEFT JOIN departments d ON e.dept_id = d.id"
                add(
                    "SELECT e.id AS emp_id, e.name, d.name AS dept FROM employees e " + join_stmt +
                    " WHERE e.salary >= 1000" +
                    (" AND (e.name LIKE 'A%%'" if supports["like"] else "") +
                    (" OR e.name IS NULL)" if supports["is_null"] and supports["like"] else "") +
                    (" ORDER BY e.salary DESC, e.id ASC" if supports["order_by"] else "") +
                    (" LIMIT 10" if supports["limit"] else "") +
                    (" OFFSET 5" if supports["offset"] else "") + ";",
                    feat_set.union({"joins"}) \
                        .union({"order_by"} if supports["order_by"] else set()) \
                        .union({"limit"} if supports["limit"] else set()) \
                        .union({"offset"} if supports["offset"] else set()) \
                        .union({"like"} if supports["like"] else set()) \
                        .union({"is_null"} if supports["is_null"] else set())
                )
            if supports["distinct"]:
                add(
                    "SELECT DISTINCT dept_id FROM employees" +
                    (" WHERE dept_id IS NOT NULL" if supports["is_null"] else "") +
                    (" ORDER BY dept_id" if supports["order_by"] else "") + ";",
                    {"select", "from", "distinct"} \
                        .union({"order_by"} if supports["order_by"] else set()) \
                        .union({"is_null"} if supports["is_null"] else set())
                )
        
        # GROUP BY, HAVING
        if supports["from"] and supports["group_by"]:
            add(
                "SELECT dept_id, COUNT(*) AS c, SUM(salary) AS s FROM employees GROUP BY dept_id" +
                (" HAVING SUM(salary) > 1000" if supports["having"] else "") +
                (" ORDER BY s DESC" if supports["order_by"] else "") + ";",
                {"select", "from", "group_by"} \
                    .union({"having"} if supports["having"] else set()) \
                    .union({"order_by"} if supports["order_by"] else set())
            )
        
        # Subqueries IN and EXISTS
        if supports["from"]:
            add(
                "SELECT name FROM employees WHERE dept_id IN (SELECT id FROM departments WHERE name <> 'X');",
                {"select", "from"}
            )
            if supports["exists"]:
                add(
                    "SELECT name FROM employees e WHERE EXISTS (SELECT 1 FROM departments d WHERE d.id = e.dept_id);",
                    {"select", "from", "exists"}
                )
        
        # CASE
        if supports["from"] and supports["case"]:
            add(
                "SELECT CASE WHEN salary > 1000 THEN 'High' WHEN salary = 1000 THEN 'Mid' ELSE 'Low' END AS category FROM employees;",
                {"select", "from", "case"}
            )
        
        # BETWEEN, LIKE/ILIKE
        if supports["from"] and supports["between"]:
            add("SELECT * FROM employees WHERE salary BETWEEN 100 AND 2000;", {"select", "from", "between"})
        if supports["from"] and supports["like"]:
            add("SELECT * FROM employees WHERE name LIKE 'A%';", {"select", "from", "like"})
        if supports["from"] and supports["ilike"]:
            add("SELECT * FROM employees WHERE name ILIKE 'a%';", {"select", "from", "ilike"})
        
        # Joins
        if supports["from"] and supports["joins"]:
            add("SELECT * FROM employees INNER JOIN departments ON employees.dept_id = departments.id;", {"select", "from", "joins"})
            if supports["left_join"]:
                add("SELECT * FROM employees LEFT OUTER JOIN departments ON employees.dept_id = departments.id;", {"select", "from", "left_join"})
            if supports["right_join"]:
                add("SELECT * FROM employees RIGHT OUTER JOIN departments ON employees.dept_id = departments.id;", {"select", "from", "right_join"})
            if supports["full_join"]:
                add("SELECT * FROM employees FULL OUTER JOIN departments ON employees.dept_id = departments.id;", {"select", "from", "full_join"})
            if supports["cross_join"]:
                add("SELECT * FROM employees CROSS JOIN departments;", {"select", "from", "cross_join"})
            if supports["using_join"]:
                add("SELECT * FROM t1 JOIN t2 USING (id);", {"select", "from", "using_join"})
        
        # Window functions
        if supports["from"] and supports["window"]:
            add("SELECT e.id, ROW_NUMBER() OVER (PARTITION BY e.dept_id ORDER BY e.salary DESC) AS rn FROM employees e;", {"select", "from", "window"})
        
        # Set operations
        if supports["from"] and supports["union"]:
            add("SELECT id FROM employees UNION SELECT id FROM departments;", {"select", "from", "union"})
            # attempt union all if ALL token visible anywhere
            if has_word("ALL"):
                add("SELECT id FROM employees UNION ALL SELECT id FROM departments;", {"select", "from", "union"})
        if supports["from"] and supports["intersect"]:
            add("SELECT id FROM employees INTERSECT SELECT id FROM departments;", {"select", "from", "intersect"})
        if supports["from"] and supports["except"]:
            add("SELECT id FROM employees EXCEPT SELECT id FROM departments;", {"select", "from", "except"})
        
        # CTEs
        if supports["cte"] and supports["from"]:
            add("WITH cte AS (SELECT dept_id, COUNT(*) c FROM employees GROUP BY dept_id) SELECT * FROM cte WHERE c > 0;", {"select", "cte", "group_by", "from"})
            if supports["recursive"] and supports["union"]:
                add("WITH RECURSIVE nums(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM nums WHERE n < 3) SELECT * FROM nums;", {"cte", "recursive", "union"})
        
        # ORDER BY nulls last
        if supports["from"] and supports["order_by"]:
            add("SELECT * FROM employees ORDER BY salary DESC" + (" NULLS LAST" if supports["nulls"] else "") + ";", {"select", "from", "order_by"}.union({"nulls"} if supports["nulls"] else set()))
        
        # Comments coverage
        if supports["from"]:
            add("-- comment line\nSELECT * FROM employees;", {"select", "from"})
        add("/* block comment */ SELECT 42 AS answer;", {"select"})
        
        # DDL - CREATE TABLE
        if supports["create_table"]:
            add("CREATE TABLE employees (id INT PRIMARY KEY, name TEXT NOT NULL, salary REAL DEFAULT 0.0, dept_id INT, created_at DATE);", {"create_table"})
            add("CREATE TABLE departments (id INT PRIMARY KEY, name TEXT UNIQUE);", {"create_table"})
            add("CREATE TABLE projects (id INT PRIMARY KEY, name TEXT, dept_id INT);", {"create_table"})
            add("CREATE TABLE emp_proj (emp_id INT, project_id INT, PRIMARY KEY (emp_id, project_id));", {"create_table"})
            if supports["foreign"]:
                add("CREATE TABLE fktable (id INT, dept_id INT, CONSTRAINT fk_dept FOREIGN KEY (dept_id) REFERENCES departments(id));", {"create_table", "foreign"})
        
        # Indexes
        if supports["indexes"]:
            add("CREATE INDEX idx_emp_dept ON employees (dept_id);", {"indexes"})
            add("CREATE UNIQUE INDEX idx_dept_name ON departments (name);", {"indexes"})
        if supports["drop_index"]:
            add("DROP INDEX idx_emp_dept;", {"drop_index"})
        
        # Views
        if supports["views"] and supports["from"]:
            add("CREATE VIEW v_emps AS SELECT id, name FROM employees;", {"views"})
        if supports["drop_view"]:
            add("DROP VIEW v_emps;", {"drop_view"})
        
        # DML - INSERT
        if supports["insert"]:
            add("INSERT INTO employees (id, name, salary, dept_id, created_at) VALUES (1, 'Alice', 1000.50, 10, '2020-01-01');", {"insert"})
            add("INSERT INTO employees (id, name, salary, dept_id, created_at) VALUES (2, 'Bob', 2000, 20, '2020-01-02'), (3, 'Carol', 3000, NULL, NULL);", {"insert"})
            if supports["from"] and supports["select"]:
                add("INSERT INTO departments (id, name) SELECT 1, 'HR' FROM employees;", {"insert"})
            if supports["returning"]:
                add("INSERT INTO departments (id, name) VALUES (2, 'IT') RETURNING id;", {"insert", "returning"})
        
        # UPDATE
        if supports["update"]:
            add("UPDATE employees SET salary = salary * 1.1 WHERE id = 1;", {"update"})
            if supports["like"]:
                add("UPDATE employees SET dept_id = NULL WHERE name LIKE 'A%';", {"update", "like"})
            else:
                add("UPDATE employees SET dept_id = NULL WHERE id = 2;", {"update"})
            if supports["returning"]:
                add("UPDATE employees SET salary = 1234.56 WHERE id = 3 RETURNING id;", {"update", "returning"})
        
        # DELETE
        if supports["delete"]:
            add("DELETE FROM employees WHERE id = 1;", {"delete"})
            add("DELETE FROM employees;", {"delete"})
            if supports["returning"]:
                add("DELETE FROM employees WHERE id = 2 RETURNING id;", {"delete", "returning"})
        
        # ALTER TABLE
        if supports["alter_table"]:
            if supports["add_column"]:
                add("ALTER TABLE employees ADD COLUMN age INT DEFAULT 0;", {"alter_table", "add_column"})
            add("ALTER TABLE employees RENAME TO employees_renamed;", {"alter_table"})
            if supports["rename_column"]:
                add("ALTER TABLE employees RENAME COLUMN name TO full_name;", {"alter_table", "rename_column"})
            if supports["drop_column"]:
                add("ALTER TABLE employees DROP COLUMN age;", {"alter_table", "drop_column"})
        
        # DROP TABLE
        if supports["drop_table"]:
            if supports["if_exists"]:
                add("DROP TABLE IF EXISTS temp_table;", {"drop_table", "if_exists"})
            else:
                add("DROP TABLE temp_table;", {"drop_table"})
        
        # Remove duplicates while preserving order
        seen = set()
        unique_cases = []
        for s in cases:
            if s not in seen:
                seen.add(s)
                unique_cases.append(s)
        
        # Cap the number to avoid excessive statements, but keep diversity
        # Aim for around 45 max, keeping earlier (more foundational) statements first
        if len(unique_cases) > 48:
            unique_cases = unique_cases[:48]
        
        return unique_cases