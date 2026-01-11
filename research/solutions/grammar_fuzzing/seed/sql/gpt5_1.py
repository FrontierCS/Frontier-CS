import os
import sys
import re
import importlib
from typing import List, Optional, Set, Tuple


class Solution:
    def _import_sql_engine(self, resources_path: str):
        parser_mod = None
        tokenizer_mod = None
        # Insert resources_path to sys.path for package import
        if resources_path not in sys.path:
            sys.path.insert(0, resources_path)
        try:
            parser_mod = importlib.import_module("sql_engine.parser")
        except Exception:
            parser_mod = None
        try:
            tokenizer_mod = importlib.import_module("sql_engine.tokenizer")
        except Exception:
            tokenizer_mod = None
        return parser_mod, tokenizer_mod

    def _collect_keywords_from_tokenizer(self, tokenizer_mod, tokenizer_path: str) -> Set[str]:
        kws: Set[str] = set()
        # Try to inspect objects
        if tokenizer_mod is not None:
            try:
                for name in dir(tokenizer_mod):
                    obj = getattr(tokenizer_mod, name, None)
                    if isinstance(obj, dict):
                        for k in obj.keys():
                            if isinstance(k, str):
                                kws.add(k.upper())
                        for v in obj.values():
                            if isinstance(v, str):
                                kws.add(v.upper())
                    elif isinstance(obj, (list, tuple, set)):
                        for k in obj:
                            if isinstance(k, str):
                                kws.add(k.upper())
            except Exception:
                pass
        # Fallback to regex parse of file
        try:
            with open(tokenizer_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            # Find uppercase words within quotes, common in KEYWORDS or token definitions
            for m in re.finditer(r"['\"]([A-Z_][A-Z0-9_]*)['\"]", text):
                kws.add(m.group(1).upper())
            # Also raw uppercase words around KEYWORDS or RESERVED definitions
            for m in re.finditer(r"\b([A-Z]{3,})\b", text):
                kws.add(m.group(1).upper())
        except Exception:
            pass
        return kws

    def _parse_ok(self, parser_mod, stmt: str) -> Tuple[bool, str]:
        """
        Try parsing given statement; if it fails, try with semicolon variant.
        Return (ok, chosen_statement_variant)
        """
        parse_fn = getattr(parser_mod, "parse_sql", None) if parser_mod else None
        if parse_fn is None:
            # Cannot validate; assume ok with original
            return True, stmt

        def try_one(s: str) -> bool:
            try:
                parse_fn(s)
                return True
            except Exception:
                return False

        # Try without semicolon first
        if try_one(stmt):
            return True, stmt
        # Try with single trailing semicolon
        semi = stmt.rstrip() + ";"
        if try_one(semi):
            return True, semi
        # Some parsers accept multiple statements; try wrapping with comment
        wrapped = "/* test */ " + stmt
        if try_one(wrapped):
            return True, wrapped
        # Try uppercase
        upper = stmt.upper()
        if upper != stmt and try_one(upper):
            return True, upper
        return False, stmt

    def _unique_preserve(self, seq: List[str]) -> List[str]:
        seen = set()
        out = []
        for s in seq:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    def _generate_candidates(self, keywords: Set[str]) -> List[str]:
        cands: List[str] = []

        # DDL
        cands += [
            "DROP TABLE IF EXISTS t1",
            "DROP TABLE IF EXISTS t2",
            "DROP TABLE IF EXISTS t3",
            "CREATE TABLE t1 (id INTEGER PRIMARY KEY, name TEXT, age INTEGER, amount NUMERIC, active INTEGER, created_at TEXT, notes TEXT)",
            "CREATE TABLE t2 (id INTEGER PRIMARY KEY, t1_id INTEGER, value TEXT, price REAL, count INTEGER NOT NULL, created TEXT, updated TEXT, data TEXT, FOREIGN KEY (t1_id) REFERENCES t1(id), UNIQUE(value), CHECK (price >= 0))",
            "CREATE TABLE IF NOT EXISTS t3 (a INT, b TEXT, c REAL, d NUMERIC)",
            'CREATE TABLE "MixedCase" ("select" INTEGER, "from" TEXT)',
        ]
        # Views and indexes, if CREATE/VIEW/INDEX seem supported
        cands += [
            "CREATE VIEW v1 AS SELECT id, name FROM t1 WHERE active = 1",
            "CREATE UNIQUE INDEX idx_t2_value ON t2 (value, id)",
        ]
        # Inserts
        cands += [
            "INSERT INTO t1 (id, name, age, amount, active) VALUES (1, 'Alice', 30, 10.5, 1)",
            "INSERT INTO t1 (id, name, age, amount, active, created_at, notes) VALUES (2, 'Bob', 25, -3.14, 0, '2020-01-01', 'note')",
            "INSERT INTO t2 (id, t1_id, value, price, count) VALUES (1, 1, 'A', 9.99, 2)",
            "INSERT INTO t2 (id, t1_id, value, price, count) VALUES (2, 1, 'B', 0.0, 0), (3, 2, 'C', 5.5, 1)",
            "INSERT INTO t1 DEFAULT VALUES",
            "INSERT INTO t1 (id, name) SELECT id, value FROM t2",
            'INSERT INTO "MixedCase" ("select","from") VALUES (1, \'x\')',
        ]
        # Updates
        cands += [
            "UPDATE t1 SET amount = amount + 10, name = 'Charlie' WHERE id IN (1,2,3) AND amount BETWEEN 0 AND 100",
            "UPDATE t2 SET value = NULL WHERE price <= 0 OR value LIKE 'B%'",
            "UPDATE t1 SET active = 1 WHERE name IS NOT NULL",
        ]
        # Deletes
        cands += [
            "DELETE FROM t2 WHERE id > 10",
            "DELETE FROM t1 WHERE id NOT IN (SELECT t1_id FROM t2)",
        ]
        # Basic selects and expressions
        cands += [
            "SELECT 1",
            "SELECT -1 + 2 AS sum, 'text' AS txt, 3.14 AS pi",
            "SELECT -0.5e-2 AS tiny, +42 AS pos",
            "SELECT 'O''Reilly' AS author",
            "SELECT id, name AS n FROM t1 WHERE age >= 18 AND name LIKE 'A%'",
            "SELECT DISTINCT name FROM t1",
            "SELECT COUNT(*) FROM t1",
            "SELECT SUM(amount + 5) / 2.0 AS x FROM t1 WHERE amount BETWEEN -10 AND 100",
            "SELECT CASE WHEN age < 18 THEN 'minor' WHEN age >= 65 THEN 'senior' ELSE 'adult' END AS age_group FROM t1",
            "SELECT COALESCE(name, 'Unknown') FROM t1",
            "SELECT name FROM t1 ORDER BY name DESC, id ASC LIMIT 10 OFFSET 5",
            "SELECT t1.id, t2.value FROM t1 JOIN t2 ON t1.id = t2.t1_id",
            "SELECT a.id FROM t1 a LEFT OUTER JOIN t2 b ON a.id = b.t1_id WHERE b.value IS NULL",
            "SELECT * FROM t1 CROSS JOIN t3",
            "SELECT id FROM t1 UNION SELECT t1_id FROM t2",
            "SELECT id FROM t1 UNION ALL SELECT t1_id FROM t2",
            "SELECT id FROM t1 INTERSECT SELECT id FROM t1",
            "SELECT id FROM t1 EXCEPT SELECT t1_id FROM t2",
            "WITH cte AS (SELECT id FROM t1 WHERE id > 10) SELECT * FROM cte",
            "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r WHERE n < 5) SELECT n FROM r",
            "SELECT (SELECT MAX(id) FROM t2 WHERE t2.t1_id = t1.id) AS m FROM t1",
            "SELECT EXISTS (SELECT 1 FROM t2 WHERE t2.t1_id = t1.id) FROM t1",
            "SELECT sub.cnt FROM (SELECT COUNT(*) AS cnt FROM t1) sub",
            "SELECT t1.*, t2.* FROM t1, t2 WHERE t1.id = t2.t1_id",
            "SELECT id FROM t1 ORDER BY 1",
            "SELECT id FROM t1 WHERE name BETWEEN 'A' AND 'Z'",
            "SELECT id FROM t1 WHERE name NOT BETWEEN 'A' AND 'Z'",
            "SELECT id FROM t1 WHERE name IN ('Alice','Bob') AND id NOT IN (SELECT id FROM t1 WHERE id > 10)",
            "SELECT id FROM t1 WHERE name IS NULL OR name IS NOT NULL",
            "SELECT 'first line -- not comment', '/* not comment inside string */'",
            "/* comment */ SELECT 1 -- trailing comment",
            'SELECT "MixedCase"."select", "MixedCase"."from" FROM "MixedCase" ORDER BY "select" DESC',
        ]
        # More joins and aliases variants
        cands += [
            "SELECT a.name, b.value FROM t1 AS a INNER JOIN t2 AS b ON a.id = b.t1_id WHERE b.value LIKE '%C%'",
            "SELECT a.id FROM t1 AS a RIGHT JOIN t2 AS b ON a.id = b.t1_id",
            "SELECT a.id FROM t1 AS a FULL JOIN t2 AS b ON a.id = b.t1_id",
            "SELECT * FROM t1 NATURAL JOIN t2",
            "SELECT * FROM t1 LEFT JOIN t2 USING (id)",
        ]
        # Casts and functions
        cands += [
            "SELECT CAST(amount AS INTEGER), NULLIF(name, ''), LENGTH(name) FROM t1",
            "SELECT CASE WHEN amount > 100 THEN 'big' ELSE 'small' END FROM t1",
            "SELECT MAX(price), MIN(price), AVG(price) FROM t2",
            "SELECT ABS(-42), ROUND(3.14159, 2) FROM t3",
        ]
        # Transaction statements
        cands += [
            "BEGIN",
            "BEGIN TRANSACTION",
            "COMMIT",
            "ROLLBACK",
        ]
        # Drops
        cands += [
            "DROP VIEW v1",
            "DROP INDEX idx_t2_value",
            "DROP TABLE t3",
        ]
        # Alter table variations
        cands += [
            "ALTER TABLE t1 ADD COLUMN extra TEXT DEFAULT 'x'",
            "ALTER TABLE t2 RENAME TO t2_renamed",
        ]
        # Additional selects to test operator precedence and NOT
        cands += [
            "SELECT id FROM t1 WHERE NOT (age < 10 OR name = 'X') AND amount >= 0",
            "SELECT id FROM t1 WHERE (age + 5) * 2 > 30 AND (amount / 2) < 10",
        ]
        # ESCAPE sequence in LIKE (if supported)
        cands += [
            r"SELECT id FROM t1 WHERE name LIKE 'A\_%' ESCAPE '\'",
        ]
        # If tokenizer hints that ANALYZE or VACUUM exist
        if "ANALYZE" in keywords:
            cands.append("ANALYZE")
            cands.append("ANALYZE t1")
        if "VACUUM" in keywords:
            cands.append("VACUUM")
        # If tokenizer hints TRUNCATE
        if "TRUNCATE" in keywords:
            cands.append("TRUNCATE TABLE t1")
        # If tokenizer hints REPLACE
        if "REPLACE" in keywords and "INTO" in keywords:
            cands.append("REPLACE INTO t1 (id, name) VALUES (99, 'rep')")

        # Try to exercise boolean literals if supported
        if "TRUE" in keywords and "FALSE" in keywords:
            cands.append("SELECT TRUE, FALSE, NULL")
            cands.append("INSERT INTO t1 (id, name, active) VALUES (3, 'Bool', TRUE)")
            cands.append("UPDATE t1 SET active = FALSE WHERE id = 3")

        return self._unique_preserve(cands)

    def solve(self, resources_path: str) -> List[str]:
        parser_mod, tokenizer_mod = self._import_sql_engine(resources_path)
        tokenizer_path = os.path.join(resources_path, "sql_engine", "tokenizer.py")
        keywords = self._collect_keywords_from_tokenizer(tokenizer_mod, tokenizer_path)

        candidates = self._generate_candidates(keywords)

        # Validate candidates via parse_sql if available; choose semicolon variant if needed
        valid_statements: List[str] = []
        chosen_variants: Set[str] = set()
        for stmt in candidates:
            ok, chosen = self._parse_ok(parser_mod, stmt)
            if ok and chosen not in chosen_variants:
                chosen_variants.add(chosen)
                valid_statements.append(chosen)

        # Ensure at least some minimal fallback statements if validation unavailable or all failed
        if not valid_statements:
            # Minimal conservative set
            fallback = [
                "SELECT 1",
                "CREATE TABLE t1 (id INTEGER PRIMARY KEY, name TEXT)",
                "INSERT INTO t1 (id, name) VALUES (1, 'a')",
                "UPDATE t1 SET name = 'b'",
                "DELETE FROM t1",
                "DROP TABLE t1",
            ]
            # If parser exists try with semicolons
            final_fb = []
            for s in fallback:
                ok, chosen = self._parse_ok(parser_mod, s)
                if ok:
                    final_fb.append(chosen)
            valid_statements = final_fb if final_fb else fallback

        # Limit to a reasonable number to keep efficiency bonus; prioritize diverse coverage
        # Keep up to 100 statements
        if len(valid_statements) > 100:
            valid_statements = valid_statements[:100]

        return valid_statements