import os
import sys

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        """
        Generates a curated list of SQL test cases designed to maximize parser coverage.
        
        The strategy is to manually craft a set of SQL statements that target specific
        syntactic features of the SQL grammar and corresponding code paths in the parser.
        This approach aims for high coverage with a minimal number of test cases,
        balancing the coverage score and the efficiency bonus.

        The test cases are grouped by the features they target:
        1.  Literals and Basic Expressions: Covering all data types and basic operators.
        2.  SELECT Clauses: Targeting specific clauses like WHERE, GROUP BY, ORDER BY, etc.
        3.  JOIN Variations: Covering all types of JOINs (INNER, LEFT, RIGHT, FULL) and syntax (ON, USING).
        4.  Complex Expressions: Testing operator precedence, CASE statements, CAST, etc.
        5.  Functions and Subqueries: Window functions, aggregate functions, and subqueries in various contexts.
        6.  Set Operations: UNION, INTERSECT, EXCEPT.
        7.  DML Statements: INSERT, UPDATE, DELETE.
        8.  DDL Statements: CREATE/DROP TABLE/INDEX, with various constraints.
        9.  Miscellaneous: Comments and other lexical features.
        """
        sql_test_cases = [
            # 1. Literals and Basic Expressions
            "SELECT 1, 123.45, .67, 8e-2, 'hello', 'it''s a quote', TRUE, FALSE, NULL;",

            # 2. SELECT statements with various clauses
            "SELECT * FROM t1;",
            "SELECT c1, t1.c2 AS a2, \"c3\" FROM t1 AS \"t_alias\";",
            "SELECT DISTINCT c1, c2 FROM t1;",
            "SELECT * FROM t1 WHERE c1 > 10 AND c2 = 'abc' OR c3 IS NOT NULL;",
            "SELECT c1, COUNT(c2) FROM t1 GROUP BY c1 HAVING COUNT(c2) > 1;",
            "SELECT * FROM t1 ORDER BY c1 ASC NULLS FIRST, c2 DESC NULLS LAST;",
            "SELECT * FROM t1 ORDER BY c1;",
            "SELECT * FROM t1 LIMIT 10 OFFSET 5;",

            # 3. Join variations
            "SELECT * FROM t1, t2;",
            "SELECT * FROM t1 INNER JOIN t2 ON t1.id = t2.id;",
            "SELECT * FROM t1 LEFT OUTER JOIN t2 ON t1.id = t2.id;",
            "SELECT * FROM t1 RIGHT JOIN t2 ON t1.id = t2.id;",
            "SELECT * FROM t1 FULL OUTER JOIN t2 USING (id, name);",

            # 4. Expression coverage
            "SELECT -c1, +c2, NOT c3, (c1+c2)*c3, c4/c5, c6%c7, 'a'||'b' FROM t1;",
            "SELECT * FROM t1 WHERE c2 LIKE 'a%' AND c3 NOT LIKE '_b';",
            "SELECT * FROM t1 WHERE c1 BETWEEN 5 AND 10 AND c2 NOT BETWEEN 'a' AND 'z';",
            "SELECT * FROM t1 WHERE c1 IN (1, 2, 3) AND c2 NOT IN ('a', 'b');",
            "SELECT CASE WHEN c1 > 10 THEN 'high' WHEN c1 > 5 THEN 'mid' ELSE 'low' END FROM t1;",
            "SELECT CASE c1 WHEN 1 THEN 'one' WHEN 2 THEN 'two' ELSE 'other' END FROM t1;",
            "SELECT CAST(c1 AS TEXT) FROM t1;",

            # 5. Functions and Subqueries
            "SELECT my_func(c1, 1), COUNT(*), COUNT(c1), COUNT(DISTINCT c1), SUM(c1), AVG(c1), MIN(c1), MAX(c1) FROM t1;",
            "SELECT RANK() OVER (PARTITION BY c1 ORDER BY c2 DESC) FROM t1;",
            "SELECT SUM(c1) OVER () FROM t1;",
            "SELECT * FROM (SELECT c1 FROM t1 WHERE c1 > 0) AS dt;",
            "SELECT * FROM t1 WHERE c1 IN (SELECT id FROM t2);",
            "SELECT (SELECT MAX(c1) FROM t2) FROM t1;",
            "SELECT c1 FROM t1 WHERE EXISTS (SELECT 1 FROM t2 WHERE t1.id = t2.id);",

            # 6. Set Operations
            "SELECT c1 FROM t1 UNION SELECT c1 FROM t2;",
            "SELECT c1 FROM t1 UNION ALL SELECT c1 FROM t2;",
            "SELECT c1 FROM t1 INTERSECT SELECT c1 FROM t2;",
            "SELECT c1 FROM t1 EXCEPT SELECT c1 FROM t2;",
            
            # 7. DML Statements
            "INSERT INTO t1 VALUES (1, 'a'), (2, 'b');",
            "INSERT INTO t1 (c1, c2) SELECT c1, c2 FROM t2;",
            "UPDATE t1 SET c1 = 1, c2 = 'a' WHERE id = 0;",
            "DELETE FROM t1 WHERE id = 0;",

            # 8. DDL Statements
            "CREATE TABLE IF NOT EXISTS t1 (c1 INT PRIMARY KEY, c2 TEXT NOT NULL UNIQUE, c3 REAL DEFAULT 1.0, c4 VARCHAR(20), c5 BOOLEAN, CHECK (c3 > 0));",
            "CREATE TABLE t2 (c1 INT, c2 INT, PRIMARY KEY (c1, c2), UNIQUE (c2), FOREIGN KEY (c2) REFERENCES t1(c1));",
            "DROP TABLE IF EXISTS t1;",
            "CREATE INDEX i1 ON t1 (c1 ASC, c2 DESC);",
            "DROP INDEX i1;",

            # 9. Comments and misc
            "SELECT 1; -- line comment",
            "/* block comment */ SELECT 1 /* nested */ + 1;",
        ]
        return sql_test_cases