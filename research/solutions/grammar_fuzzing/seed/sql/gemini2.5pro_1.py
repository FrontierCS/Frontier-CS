import sys
import os

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        """
        Return SQL test cases designed to maximize parser coverage.
        
        Args:
            resources_path: Path to the resources directory containing:
                - sql_grammar.txt: BNF-style grammar file
                - sql_engine/: Target SQL parser package (parser.py, tokenizer.py, ast_nodes.py)
        
        Returns:
            list[str]: List of SQL statement strings
        """
        
        sql_test_cases = [
            # 1. Basic Data Types and Literals
            "SELECT 1, -2.3, 4.5e6, 'a string', \"another string\", TRUE, FALSE, NULL;",

            # 2. Expressions and Operators
            "SELECT 1 + 2 * 3, (1 + 2) * 3, -c1, +c2 FROM t1;",
            "SELECT 1 = 1, 2 != 3, 4 <> 5, 6 < 7, 8 > 9, 10 <= 11, 12 >= 13;",

            # 3. Comprehensive WHERE clause
            "SELECT * FROM t1 WHERE (c1 > 10 AND c2 = 'a') OR (c3 < 5.0 AND NOT c4) AND c5 IS NULL AND c6 IS NOT NULL AND name LIKE 'A%' AND id BETWEEN 100 AND 200;",

            # 4. Kitchen-sink SELECT statement with all major clauses
            "SELECT DISTINCT c1, c2 AS alias2, COUNT(c3) FROM t1 WHERE c4 > 0 GROUP BY c1, c2 HAVING COUNT(c3) > 1 ORDER BY c1 DESC, alias2 ASC LIMIT 10 OFFSET 5;",

            # 5. SELECT *, Aliasing, and Qualified Names
            "SELECT * FROM my_table;",
            "SELECT t1.c1, t2.c2 FROM table1 AS t1 JOIN table2 AS t2 ON t1.id = t2.id;",
            
            # 6. JOIN variations
            "SELECT * FROM t1 INNER JOIN t2 ON t1.id = t2.id LEFT JOIN t3 ON t2.id = t3.id RIGHT JOIN t4 ON t3.id = t4.id;",
            "SELECT * FROM t1, t2;", # Implicit Cross Join (Comma Join)
            "SELECT * FROM t1 CROSS JOIN t2;", # Explicit Cross Join

            # 7. Subqueries in SELECT, FROM, WHERE (IN, EXISTS)
            "SELECT c1, (SELECT MAX(c2) FROM t2 WHERE t2.id = t1.id) FROM t1;",
            "SELECT * FROM (SELECT c1, c2 FROM t1 WHERE c1 > 10) AS subquery_alias;",
            "SELECT c1 FROM t1 WHERE c2 IN (SELECT c1 FROM t2);",
            "SELECT c1 FROM t1 WHERE EXISTS (SELECT 1 FROM t2 WHERE t1.id = t2.id);",

            # 8. INSERT statements variations
            "INSERT INTO t1 (c1, c2) VALUES (1, 'a');",
            "INSERT INTO t1 VALUES (1, 'a', 2.3);", # Without column list
            "INSERT INTO t1 (c1, c2) VALUES (1, 'a'), (2, 'b');", # Multi-row insert

            # 9. UPDATE statement
            "UPDATE t1 SET c1 = 1, c2 = c2 + 1 WHERE c3 = 'a';",

            # 10. DELETE statement variations
            "DELETE FROM t1 WHERE c1 = 1;",
            "DELETE FROM t1;", # No WHERE clause

            # 11. CREATE TABLE statement variations
            "CREATE TABLE t1 (c1 INT, c2 VARCHAR(255), c3 DECIMAL(10, 2));",
            "CREATE TABLE t2 (c1 INT PRIMARY KEY, c2 TEXT NOT NULL, c3 TIMESTAMP DEFAULT CURRENT_TIMESTAMP, c4 VARCHAR(100) UNIQUE);",
            "CREATE TABLE IF NOT EXISTS t3 (c1 INT);",
            "CREATE TABLE t4 AS SELECT * FROM t1 WHERE c1 > 100;",

            # 12. Set operations
            "SELECT c1, c2 FROM t1 UNION SELECT c1, c2 FROM t2;",
            "SELECT c1, c2 FROM t1 UNION ALL SELECT c1, c2 FROM t2;",

            # 13. CASE expressions
            "SELECT CASE WHEN c1 > 0 THEN 'positive' WHEN c1 < 0 THEN 'negative' ELSE 'zero' END FROM t1;",
            "SELECT CASE c1 WHEN 1 THEN 'one' WHEN 2 THEN 'two' ELSE 'other' END FROM t1;",

            # 14. IN operator with a list and negated operators
            "SELECT * FROM t1 WHERE c2 IN ('a', 'b', 'c');",
            "SELECT * FROM t1 WHERE c2 NOT IN ('a', 'b', 'c');",
            "SELECT * FROM t1 WHERE c1 NOT BETWEEN 1 AND 10;",

            # 15. Function calls
            "SELECT COUNT(*), COUNT(c1), SUM(c2), AVG(c2), MIN(c3), MAX(c3), SUBSTRING(c4, 1, 3), NOW() FROM t1;",
            
            # 16. Quoted identifiers
            "SELECT \"id-col\", \"col with space\" FROM \"my-table\" AS \"m\";",

            # 17. CAST expression
            "SELECT CAST(c1 AS VARCHAR(50)) FROM t1;",
            
            # 18. Comments
            "SELECT 1; -- This is a line comment",
            "SELECT 1 /* This is a block comment */ + 2;",

            # 19. Ordinals in ORDER BY and GROUP BY
            "SELECT c1, COUNT(*) FROM t1 GROUP BY 1 ORDER BY 2 DESC;",
            
            # 20. Statement termination
            "SELECT 1", # No semicolon
            "SELECT 1;", # With semicolon
        ]
        
        return sql_test_cases