class Solution:
    def solve(self, resources_path: str) -> list[str]:
        sql_statements = [
            # 1. Comprehensive SELECT: Covers most clauses, joins, aggregates, and a subquery.
            """
            SELECT
                t1.col_a AS alias_a,
                t2.col_b,
                COUNT(DISTINCT t1.col_c),
                AVG(t1.col_d + 5)
            FROM
                table1 AS t1
            JOIN
                table2 t2 ON t1.id = t2.fk_id
            WHERE
                t1.col_a > 100
                AND t2.col_b LIKE 'test%'
                AND t1.col_c NOT IN (SELECT bad_id FROM black_list)
            GROUP BY
                t1.col_a, t2.col_b
            HAVING
                COUNT(t1.id) > 1
            ORDER BY
                alias_a DESC, 2 ASC
            LIMIT 50 OFFSET 10;
            """,
            # 2. All JOIN Types: Systematically tests different join syntaxes.
            """
            SELECT *
            FROM t1
            LEFT OUTER JOIN t2 ON t1.id = t2.id
            RIGHT OUTER JOIN t3 ON t1.id = t3.id
            FULL OUTER JOIN t4 ON t1.id = t4.id
            CROSS JOIN t5;
            """,
            # 3. Expression Torture Test: Hits many different operator code paths.
            """
            SELECT
                -c1, c1+c2, c1*c2, c1/c2, c1%c2,
                c1 > c2, c1 <= c2, c1 = c2, c1 <> c2,
                c1 IS NULL, c2 IS NOT NULL,
                c3 BETWEEN 10 AND 20,
                c3 NOT BETWEEN 30 AND 40,
                CASE c4 WHEN 1 THEN 'one' ELSE 'other' END
            FROM
                expressions_table
            WHERE
                (c1 > 0 AND c2 < 0) OR NOT c3;
            """,
            # 4. Literals, Functions, and Quoted IDs: Tests the tokenizer and literal parsing.
            """SELECT 123, -1.23e-4, 'a string', "quoted id", TRUE, FALSE, NULL, ABS(-5), LOWER('TEXT') FROM dummy_table;""",
            # 5. Comprehensive CREATE TABLE: Tests DDL parsing and various column constraints.
            """
            CREATE TABLE IF NOT EXISTS new_employees (
                id INT PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                salary DECIMAL(10, 2) DEFAULT 50000.00 CHECK (salary > 0),
                dept_id INT,
                FOREIGN KEY (dept_id) REFERENCES departments(id)
            );
            """,
            # 6. Simple CREATE TABLE: For the non-constrained path.
            """CREATE TABLE simple_table (col1 INT, col2 VARCHAR);""",
            # 7. Multi-row INSERT: Tests parsing of value lists.
            """INSERT INTO new_employees (id, name, salary) VALUES (1, 'John', 60000), (2, 'Jane', 70000);""",
            # 8. INSERT without Column List: A common syntax variation.
            """INSERT INTO simple_table VALUES (1, 'data');""",
            # 9. Comprehensive UPDATE: Multiple SET clauses, expressions, and WHERE.
            """UPDATE new_employees SET salary = salary * 1.1, name = 'John Doe' WHERE id = 1;""",
            # 10. Update all rows
            """UPDATE simple_table SET col1 = col1 + 1;""",
            # 11. DELETE with WHERE: Standard delete operation.
            """DELETE FROM new_employees WHERE salary > 100000;""",
            # 12. DELETE all rows: No WHERE clause.
            """DELETE FROM simple_table;""",
            # 13. DROP TABLE with IF EXISTS: Conditional DDL.
            """DROP TABLE IF EXISTS old_table;""",
            # 14. Simple DROP TABLE: Unconditional DDL.
            """DROP TABLE new_employees;""",
            # 15. Comprehensive CREATE INDEX: Covers UNIQUE, IF NOT EXISTS, and multiple columns.
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_emp_name ON employees (last_name, first_name);""",
            # 16. Simple CREATE INDEX: Basic DDL path.
            """CREATE INDEX idx_dept ON employees (dept_id);""",
            # 17. DROP INDEX with IF EXISTS and table name.
            """DROP INDEX IF EXISTS idx_emp_name ON employees;""",
            # 18. Simple DROP INDEX: Unconditional DDL.
            """DROP INDEX idx_dept;""",
            # 19. SELECT *: A very common and distinct parsing path.
            """SELECT * FROM employees;""",
            # 20. Syntax Variations: Case-insensitivity, extra whitespace.
            """sElEcT     id,   name   fRoM   employees    ;""",
            # 21. Subqueries (EXISTS, Scalar, Derived Table): Covers various subquery integrations.
            """
            SELECT
                id,
                (SELECT name FROM categories c WHERE c.id = p.category_id)
            FROM
                products p, (SELECT * FROM discounts) d
            WHERE
                EXISTS (SELECT 1 FROM stock s WHERE s.product_id = p.id AND s.quantity > 0)
                AND p.id IN (SELECT product_id FROM top_sales);
            """,
            # 22. Simple SELECT without FROM: Tests parsing of constant expressions.
            """SELECT 1+1;""",
            # 23. ORDER BY Expression: Another common variation.
            """SELECT name, price, weight FROM products ORDER BY price / weight DESC;""",
            # 24. LEFT and RIGHT JOINs (without OUTER keyword)
            """SELECT * FROM t1 LEFT JOIN t2 ON t1.id = t2.id RIGHT JOIN t3 ON t1.id = t3.id;""",
            # 25. Select DISTINCT on multiple columns
            """SELECT DISTINCT dept_id, manager_id FROM employees;""",
        ]
        return sql_statements