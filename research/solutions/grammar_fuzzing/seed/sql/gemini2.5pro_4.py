import sys
import os

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        """
        Return SQL test cases designed to maximize parser coverage.
        
        This solution uses a curated list of SQL statements designed to exercise
        a wide range of syntactic features of a typical SQL parser. The approach
        is white-box, assuming a recursive descent parser structure where different
        SQL clauses, expressions, and statement types correspond to different
        functions and conditional branches in the code.

        The list is structured to be efficient, using a few complex queries
        to cover common paths and many smaller, targeted queries to hit
        specific corner cases, alternative syntaxes, and less common features.
        """
        
        queries = [
            # 1. Complex SELECT statement to cover a wide range of common features.
            # Covers: WITH RECURSIVE, aliases, quoted identifiers, CAST, CASE WHEN,
            # Window Functions (ROW_NUMBER), scalar subqueries, LEFT OUTER JOIN, 
            # IN subquery, LIKE, BETWEEN, GROUP BY, HAVING, ORDER BY with NULLS, LIMIT/OFFSET.
            """
            WITH RECURSIVE cte(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM cte WHERE n < 10)
            SELECT
                t1.c1, t2."c2", CAST(t1.c3 AS VARCHAR(255)),
                CASE WHEN t1.c4 > 10 THEN 'big' WHEN t1.c4 > 5 THEN 'medium' ELSE 'small' END,
                ROW_NUMBER() OVER (PARTITION BY t1.c1 ORDER BY t2.c6 DESC NULLS LAST),
                (SELECT MAX(c7) FROM t3 WHERE t3.id = t1.id)
            FROM t1 AS table1
            LEFT OUTER JOIN t2 ON t1.id = t2.t1_id
            WHERE t1.c1 IN (SELECT n FROM cte) AND t1.c8 LIKE 'a%' AND t1.c9 BETWEEN -10.5 AND 10e2
            GROUP BY t1.c1, t2."c2", t1.c3, t1.c4
            HAVING COUNT(DISTINCT t1.c1) > 0 ORDER BY t1.c1 ASC NULLS FIRST
            LIMIT 100 OFFSET 10;
            """,

            # 2. Alternative SELECT features and clauses not in the main query.
            "SELECT * FROM t1, t2 WHERE t1.id = t2.id;",
            "SELECT * FROM t1 NATURAL JOIN t2 CROSS JOIN t3;",
            "SELECT * FROM t1 RIGHT JOIN t2 USING(id);",
            "SELECT * FROM t1 FULL OUTER JOIN t2 ON t1.id = t2.id;",
            "SELECT c1 FROM t1 INTERSECT SELECT c1 FROM t2;",
            "SELECT c1 FROM t1 EXCEPT SELECT c1 FROM t2;",
            "SELECT c1 FROM t1 UNION SELECT c1 FROM t2 ORDER BY c1;",
            "SELECT CASE c1 WHEN 1 THEN 'one' WHEN 2 THEN 'two' ELSE 'other' END FROM t1;",
            "SELECT * FROM t1 WHERE c1 > ALL (SELECT c1 FROM t2);",
            "SELECT * FROM t1 WHERE c1 = ANY (SELECT c1 FROM t2);",
            "SELECT * FROM t1 WHERE c1 <> SOME (SELECT c1 FROM t2);",
            "SELECT * FROM t1 WHERE EXISTS (SELECT 1 FROM t2 WHERE t1.id = t2.id);",
            "SELECT * FROM t1 WHERE NOT EXISTS (SELECT 1 FROM t2 WHERE t1.id = t2.id);",
            "SELECT * FROM t1 OFFSET 20;",

            # 3. DDL (CREATE/DROP) with various constraints and options.
            """
            CREATE TABLE IF NOT EXISTS my_table (
                id INT, name VARCHAR(100) NOT NULL UNIQUE DEFAULT 'anonymous', age INT,
                c1 INT, c2 INT,
                CONSTRAINT pk PRIMARY KEY (id),
                CHECK (age >= 18),
                UNIQUE (c1, c2)
            );
            """,
            "CREATE TABLE tbl (id INT CONSTRAINT pkey PRIMARY KEY, val TEXT);",
            "CREATE OR REPLACE VIEW my_view AS SELECT id, name FROM my_table WHERE age > 30;",
            "CREATE TABLE t_copy AS SELECT * FROM my_table WITH NO DATA;",
            "CREATE TABLE t_copy2 AS SELECT * FROM my_table;",
            "DROP TABLE IF EXISTS my_table, t_copy CASCADE;",
            "DROP VIEW IF EXISTS my_view RESTRICT;",

            # 4. DML (INSERT/UPDATE/DELETE) variations.
            "INSERT INTO my_table (id, name, age) VALUES (1, 'Alice', 30), (2, 'Bob', 40);",
            "INSERT INTO my_table (name, id) SELECT name, id FROM employees;",
            "INSERT INTO my_table DEFAULT VALUES;",
            "UPDATE my_table SET age = age + 1, name = 'Robert' WHERE id = 2;",
            "DELETE FROM my_table WHERE age < 20;",

            # 5. Transaction and Utility statements.
            "BEGIN;", "COMMIT;", "ROLLBACK;", "EXPLAIN SELECT * FROM my_table;",

            # 6. Tokenizer targets, expressions, and miscellaneous syntax.
            "SELECT 1, 1.0, .5, 5., 1e-5, 'it''s a string', TRUE, FALSE, NULL; -- comment",
            "SELECT * FROM t1 /* multi-line\ncomment */ WHERE name ILIKE '_ob%';",
            "SELECT * FROM t1 WHERE name NOT LIKE 'A%';",
            "SELECT * FROM t1 WHERE age NOT IN (18, 21, 65);",
            "SELECT * FROM t1 WHERE age NOT BETWEEN 18 AND 65;",
            "SELECT c1, -c1, +c1, NOT (c1 > 0), c1 IS NULL, c2 IS NOT NULL FROM t1;",
            "SELECT COUNT(*), SUM(c1), AVG(DISTINCT c1), MIN(c1), MAX(c1) FROM t1;",
            "SELECT c1 || c2 FROM t1;",
            "SELECT RANK() OVER (), DENSE_RANK() OVER (ORDER BY c1) FROM t1;"
        ]

        # Sanitize queries to be single-line and space-separated, which is a robust
        # format for feeding into a parser.
        sanitized_queries = [" ".join(q.strip().split()) for q in queries]
        
        return sanitized_queries