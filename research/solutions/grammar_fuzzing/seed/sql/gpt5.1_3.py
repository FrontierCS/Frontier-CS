import os
import sys
import random
import inspect
import ast
import re


class Solution:
    def solve(self, resources_path: str) -> list[str]:
        # Ensure resources_path on sys.path to import sql_engine
        if resources_path and resources_path not in sys.path:
            sys.path.insert(0, resources_path)

        try:
            import sql_engine  # type: ignore
        except Exception:
            # If we cannot import the engine at all, just return generic statements
            rng = random.Random(12345)
            keywords = set()
            return self._fallback_sql_list(keywords, rng)

        # Try to extract parse_sql
        parse_sql_func = self._load_parse_sql(sql_engine)

        # Extract keywords from tokenizer if possible
        keywords = self._extract_keywords_from_tokenizer()

        # RNG for deterministic behavior
        rng = random.Random(123456)

        # If we can't use parse_sql or coverage, fall back to static generation
        coverage_module = self._import_coverage()
        if parse_sql_func is None or coverage_module is None:
            return self._fallback_sql_list(keywords, rng)

        # Build base candidate statements (diverse SQL)
        base_candidates = self._build_base_statements(keywords, rng)

        # Prepare coverage-guided selection
        try:
            engine_dir = os.path.dirname(sql_engine.__file__)
        except Exception:
            engine_dir = None

        accepted_statements: list[str] = []
        global_lines: set[tuple[str, int]] = set()
        global_arcs: set[tuple[str, int, int]] = set()
        seen_sql: set[str] = set()

        def run_candidate(sql: str) -> bool:
            nonlocal accepted_statements, global_lines, global_arcs

            if sql in seen_sql:
                return False
            seen_sql.add(sql)

            # Create a fresh Coverage instance for this candidate
            try:
                if engine_dir:
                    cov = coverage_module.Coverage(branch=True, source=[engine_dir], data_file=None)  # type: ignore
                else:
                    cov = coverage_module.Coverage(branch=True, data_file=None)  # type: ignore
            except TypeError:
                # Older coverage versions may not support data_file argument
                try:
                    if engine_dir:
                        cov = coverage_module.Coverage(branch=True, source=[engine_dir])  # type: ignore
                    else:
                        cov = coverage_module.Coverage(branch=True)  # type: ignore
                except TypeError:
                    cov = coverage_module.Coverage()  # type: ignore

            cov_started = False
            try:
                cov.start()
                cov_started = True
            except Exception:
                cov_started = False

            parse_error = False
            try:
                if parse_sql_func is not None:
                    parse_sql_func(sql)
                else:
                    parse_error = True
            except Exception:
                parse_error = True
            finally:
                if cov_started:
                    try:
                        cov.stop()
                    except Exception:
                        pass

            # Per problem spec, statements that raise parser exceptions shouldn't count
            if parse_error:
                return False

            # Gather coverage data
            try:
                data = cov.get_data()
            except Exception:
                return False

            new_lines_count = 0
            new_arcs_count = 0

            try:
                measured_files = list(data.measured_files())
            except Exception:
                measured_files = []

            for filename in measured_files:
                try:
                    lines = data.lines(filename) or []
                except Exception:
                    lines = []
                try:
                    arcs = data.arcs(filename) or []
                except Exception:
                    arcs = []

                for ln in lines:
                    key = (filename, ln)
                    if key not in global_lines:
                        global_lines.add(key)
                        new_lines_count += 1

                for arc in arcs:
                    if not arc:
                        continue
                    frm, to = arc
                    key = (filename, frm, to)
                    if key not in global_arcs:
                        global_arcs.add(key)
                        new_arcs_count += 1

            if new_lines_count > 0 or new_arcs_count > 0:
                accepted_statements.append(sql)
                return True
            return False

        # Run base candidates through coverage-guided filter
        for stmt in base_candidates:
            run_candidate(stmt)

        # If nothing succeeded, fall back to static generation
        if not accepted_statements:
            return self._fallback_sql_list(keywords, rng)

        # Dynamic coverage-guided generation using random SELECT-based statements
        max_extra_candidates = 80
        max_no_improve_streak = 60
        no_improve_streak = 0
        attempts = 0
        max_total_accepted = 120

        while (
            attempts < max_extra_candidates
            and no_improve_streak < max_no_improve_streak
            and len(accepted_statements) < max_total_accepted
        ):
            attempts += 1
            stmt = self._gen_random_select(rng, keywords)
            improved = run_candidate(stmt)
            if improved:
                no_improve_streak = 0
            else:
                no_improve_streak += 1

        # Ensure we don't return an excessively long list
        if len(accepted_statements) > max_total_accepted:
            accepted_statements = accepted_statements[:max_total_accepted]

        return accepted_statements

    # ------------------------------------------------------------------
    # Helper: load parse_sql from sql_engine package
    # ------------------------------------------------------------------
    def _load_parse_sql(self, sql_engine_module):
        parse_sql_func = None
        # Try sql_engine.parse_sql directly
        try:
            if hasattr(sql_engine_module, "parse_sql") and callable(sql_engine_module.parse_sql):
                parse_sql_func = sql_engine_module.parse_sql
        except Exception:
            parse_sql_func = None

        if parse_sql_func is not None:
            return parse_sql_func

        # Try sql_engine.parser.parse_sql or Parser class
        try:
            from sql_engine import parser as parser_mod  # type: ignore
        except Exception:
            parser_mod = None

        if parser_mod is not None:
            try:
                if hasattr(parser_mod, "parse_sql") and callable(parser_mod.parse_sql):
                    return parser_mod.parse_sql
            except Exception:
                pass

            try:
                if hasattr(parser_mod, "Parser"):
                    ParserCls = parser_mod.Parser

                    def _wrapper(sql: str, _Parser=ParserCls):
                        parser_instance = _Parser()
                        if hasattr(parser_instance, "parse") and callable(parser_instance.parse):
                            return parser_instance.parse(sql)
                        if hasattr(parser_instance, "parse_sql") and callable(parser_instance.parse_sql):
                            return parser_instance.parse_sql(sql)
                        raise RuntimeError("Parser class has no parse/parse_sql method")

                    return _wrapper
            except Exception:
                pass

        return None

    # ------------------------------------------------------------------
    # Helper: import coverage module safely
    # ------------------------------------------------------------------
    def _import_coverage(self):
        try:
            import coverage as coverage_module  # type: ignore

            return coverage_module
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Helper: extract keywords from tokenizer.py via AST
    # ------------------------------------------------------------------
    def _extract_keywords_from_tokenizer(self) -> set[str]:
        try:
            from sql_engine import tokenizer as tokenizer_mod  # type: ignore
        except Exception:
            return set()

        try:
            src = inspect.getsource(tokenizer_mod)
        except (OSError, IOError, TypeError):
            return set()

        try:
            tree = ast.parse(src)
        except SyntaxError:
            return set()

        keywords: set[str] = set()

        class Visitor(ast.NodeVisitor):
            def visit_Assign(self, node):
                def gather_strings(v):
                    out = set()
                    if isinstance(v, ast.Constant) and isinstance(v.value, str):
                        out.add(v.value.upper())
                    elif isinstance(v, (ast.Set, ast.List, ast.Tuple)):
                        for e in v.elts:
                            out.update(gather_strings(e))
                    elif isinstance(v, ast.Dict):
                        for k in v.keys or []:
                            out.update(gather_strings(k))
                        for val in v.values or []:
                            out.update(gather_strings(val))
                    elif isinstance(v, ast.Call):
                        for a in v.args:
                            out.update(gather_strings(a))
                        for k in v.keywords:
                            out.update(gather_strings(k.value))
                    return out

                try:
                    vals = gather_strings(node.value)
                    for s in vals:
                        if isinstance(s, str) and len(s) >= 2 and s.isupper():
                            keywords.add(s)
                except Exception:
                    pass
                self.generic_visit(node)

        Visitor().visit(tree)
        return keywords

    # ------------------------------------------------------------------
    # Helper: build a diverse set of base SQL statements
    # ------------------------------------------------------------------
    def _build_base_statements(self, keywords: set[str], rng: random.Random) -> list[str]:
        stmts: list[str] = []

        # Simple SELECTs and literals
        stmts.append("SELECT 1")
        stmts.append("SELECT 1;")
        stmts.append("SELECT 1 AS col1")
        stmts.append("SELECT -1 AS negative, 1.5 AS decimal, 1e10 AS sci")
        stmts.append("SELECT 'hello' AS greeting")
        stmts.append("SELECT 'it''s escaped' AS escaped_str")
        stmts.append("SELECT NULL AS nothing")
        stmts.append("SELECT 1 /* inline comment */")
        stmts.append("SELECT 1 -- trailing comment\n")
        stmts.append("SELECT 1 + 2 * 3 AS arithmetic_result")

        # Simple FROM/GROUP/WHERE/ORDER/LIMIT
        stmts.append("SELECT col1 FROM table1")
        stmts.append("SELECT t1.col1, t2.col2 FROM table1 AS t1, table2 AS t2")
        stmts.append("SELECT * FROM table1 WHERE col1 = 1")
        stmts.append("SELECT * FROM table1 WHERE col1 <> 1 AND col2 BETWEEN 10 AND 20")
        stmts.append("SELECT * FROM table1 WHERE col1 IN (1, 2, 3) OR col2 IS NULL")
        stmts.append("SELECT * FROM table1 WHERE col1 LIKE 'ab%'")
        stmts.append(
            "SELECT CASE WHEN col1 > 0 THEN 'pos' WHEN col1 < 0 THEN 'neg' ELSE 'zero' END FROM table1"
        )
        stmts.append("SELECT DISTINCT col1 FROM table1")
        stmts.append("SELECT COUNT(*) AS cnt FROM table1")
        stmts.append("SELECT SUM(col1) AS total, AVG(col1) AS avg FROM table1 GROUP BY col2")
        stmts.append("SELECT col1, COUNT(*) FROM table1 GROUP BY col1 HAVING COUNT(*) > 1")
        stmts.append("SELECT col1 FROM table1 ORDER BY col1 DESC")
        stmts.append(
            "SELECT col1 FROM table1 ORDER BY col1 DESC, col2 ASC LIMIT 10"
        )
        stmts.append("SELECT col1 FROM table1 LIMIT 5 OFFSET 10")

        # Joins
        stmts.append(
            "SELECT t1.col1, t2.col2 FROM table1 AS t1 INNER JOIN table2 AS t2 ON t1.id = t2.id"
        )
        stmts.append(
            "SELECT t1.col1 FROM table1 t1 LEFT OUTER JOIN table2 t2 ON t1.id = t2.fk_id"
        )
        stmts.append(
            "SELECT t1.col1 FROM table1 t1 RIGHT JOIN table2 t2 ON t1.id = t2.id"
        )
        stmts.append(
            "SELECT t1.col1 FROM table1 t1 FULL OUTER JOIN table2 t2 ON t1.id = t2.id"
        )
        stmts.append("SELECT t1.col1 FROM table1 t1 CROSS JOIN table2 t2")
        stmts.append("SELECT * FROM table1 NATURAL JOIN table2")
        stmts.append("SELECT * FROM (SELECT col1, col2 FROM table1) AS sub")
        stmts.append(
            "SELECT * FROM table1 WHERE EXISTS (SELECT 1 FROM table2 WHERE table2.fk = table1.id)"
        )
        stmts.append(
            "SELECT * FROM table1 WHERE col1 IS NOT NULL AND (col2 > 10 OR col3 < 5)"
        )

        # Window function if likely supported
        stmts.append(
            "SELECT col1, MAX(col2) OVER (PARTITION BY col3 ORDER BY col4 ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) FROM table1"
        )

        # Set operations (if UNION etc seem supported)
        if "UNION" in keywords:
            stmts.append("SELECT col1 FROM table1 UNION SELECT col1 FROM table2")
            stmts.append(
                "SELECT col1 FROM table1 UNION ALL SELECT col1 FROM table2 EXCEPT SELECT col1 FROM table3"
            )
        if "INTERSECT" in keywords:
            stmts.append("SELECT col1 FROM table1 INTERSECT SELECT col1 FROM table2")
        if "EXCEPT" in keywords:
            stmts.append("SELECT col1 FROM table1 EXCEPT SELECT col1 FROM table2")

        # CTEs
        if "WITH" in keywords:
            stmts.append("WITH sub AS (SELECT col1 FROM table1) SELECT * FROM sub")
            stmts.append(
                "WITH a AS (SELECT 1 AS x), b AS (SELECT x + 1 AS y FROM a) SELECT * FROM b"
            )

        # Inserts
        if "INSERT" in keywords and "INTO" in keywords:
            stmts.append(
                "INSERT INTO table1 (col1, col2) VALUES (1, 'a')"
            )
            stmts.append(
                "INSERT INTO table1 (col1, col2) VALUES (1, 'a'), (2, 'b'), (3, 'c')"
            )
            stmts.append(
                "INSERT INTO table1 SELECT col1, col2 FROM table2 WHERE col3 > 100"
            )

        # Updates
        if "UPDATE" in keywords:
            stmts.append("UPDATE table1 SET col1 = 1 WHERE col2 = 2")
            stmts.append(
                "UPDATE table1 SET col1 = col1 + 1, col2 = 'x' WHERE col3 IS NULL"
            )

        # Deletes
        if "DELETE" in keywords:
            stmts.append("DELETE FROM table1")
            stmts.append(
                "DELETE FROM table1 WHERE col1 IN (SELECT col1 FROM table2)"
            )

        # CREATE TABLE and related DDL
        if "CREATE" in keywords and "TABLE" in keywords:
            stmts.append(
                "CREATE TABLE table1 (id INT PRIMARY KEY, col1 INT, col2 VARCHAR(100))"
            )
            stmts.append(
                "CREATE TABLE IF NOT EXISTS table2 (id INTEGER, name TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )

        if "DROP" in keywords and "TABLE" in keywords:
            stmts.append("DROP TABLE table1")
            stmts.append("DROP TABLE IF EXISTS table1")

        if "ALTER" in keywords and "TABLE" in keywords:
            stmts.append("ALTER TABLE table1 ADD COLUMN col3 INT")
            stmts.append("ALTER TABLE table1 DROP COLUMN col2")

        if "CREATE" in keywords and "INDEX" in keywords:
            stmts.append(
                "CREATE INDEX idx_table1_col1 ON table1 (col1)"
            )
            stmts.append(
                "CREATE UNIQUE INDEX idx_table1_col1_col2 ON table1 (col1, col2)"
            )

        # Add a few random SELECTs for more variability even before dynamic stage
        for _ in range(10):
            stmts.append(self._gen_random_select(rng, keywords))

        # Deduplicate while preserving order
        unique_stmts: list[str] = []
        seen: set[str] = set()
        for s in stmts:
            if s not in seen:
                seen.add(s)
                unique_stmts.append(s)

        return unique_stmts

    # ------------------------------------------------------------------
    # Helper: generic fallback when parse_sql or coverage is unavailable
    # ------------------------------------------------------------------
    def _fallback_sql_list(self, keywords: set[str], rng: random.Random) -> list[str]:
        base = self._build_base_statements(keywords, rng)
        # Add some extra random SELECTs for diversity
        extra: list[str] = []
        for _ in range(40):
            extra.append(self._gen_random_select(rng, keywords))

        final: list[str] = []
        seen: set[str] = set()
        for s in base + extra:
            if s not in seen:
                seen.add(s)
                final.append(s)
            if len(final) >= 80:
                break
        return final

    # ------------------------------------------------------------------
    # SQL random generation helpers
    # ------------------------------------------------------------------
    def _random_identifier(self, rng: random.Random, prefix: str = "id") -> str:
        return f"{prefix}_{rng.randint(1, 20)}"

    def _random_string_literal(self, rng: random.Random) -> str:
        length = rng.randint(1, 8)
        chars = []
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
        for _ in range(length):
            chars.append(rng.choice(alphabet))
        s = "".join(chars)
        s = s.replace("'", "''")
        return f"'{s}'"

    def _random_numeric_literal(self, rng: random.Random) -> str:
        choice = rng.random()
        if choice < 0.5:
            return str(rng.randint(-1000, 1000))
        elif choice < 0.8:
            val = rng.uniform(-1000.0, 1000.0)
            return f"{val:.3f}"
        else:
            # scientific notation
            base = rng.uniform(1.0, 1000.0)
            exp = rng.randint(-5, 5)
            return f"{base:.1f}e{exp}"

    def _random_literal(self, rng: random.Random, keywords: set[str]) -> str:
        r = rng.random()
        if r < 0.4:
            return self._random_numeric_literal(rng)
        elif r < 0.7:
            return self._random_string_literal(rng)
        elif r < 0.85 and "TRUE" in keywords and "FALSE" in keywords:
            return rng.choice(["TRUE", "FALSE"])
        else:
            # NULL literal
            return "NULL"

    def _random_column_ref(self, rng: random.Random, alias_pool: list[str]) -> str:
        col_names = ["id", "col1", "col2", "col3", "value", "flag"]
        if alias_pool and rng.random() < 0.7:
            alias = rng.choice(alias_pool)
            return f"{alias}.{rng.choice(col_names)}"
        return rng.choice(col_names)

    def _random_sql_type(self, rng: random.Random, keywords: set[str]) -> str:
        # Prefer types that appear in tokenizer keywords if possible
        preferred = [
            "INT",
            "INTEGER",
            "BIGINT",
            "SMALLINT",
            "TEXT",
            "VARCHAR",
            "CHAR",
            "BOOLEAN",
            "NUMERIC",
            "DECIMAL",
            "DATE",
            "TIMESTAMP",
        ]
        avail = [t for t in preferred if t in keywords]
        if not avail:
            avail = preferred
        base = rng.choice(avail)
        if base in ("VARCHAR", "CHAR", "NUMERIC", "DECIMAL") and rng.random() < 0.7:
            if base in ("NUMERIC", "DECIMAL"):
                p = rng.randint(4, 10)
                s = rng.randint(0, min(4, p))
                return f"{base}({p}, {s})"
            else:
                size = rng.randint(10, 255)
                return f"{base}({size})"
        return base

    def _random_expression(
        self,
        rng: random.Random,
        depth: int,
        alias_pool: list[str],
        keywords: set[str],
    ) -> str:
        if depth >= 2:
            if rng.random() < 0.5 and alias_pool:
                return self._random_column_ref(rng, alias_pool)
            return self._random_literal(rng, keywords)

        choice = rng.randint(0, 9)

        if choice == 0:
            return self._random_literal(rng, keywords)
        elif choice == 1:
            return self._random_column_ref(rng, alias_pool)
        elif choice == 2:
            inner = self._random_expression(rng, depth + 1, alias_pool, keywords)
            if rng.random() < 0.5:
                return f"-({inner})"
            else:
                return f"NOT ({inner})"
        elif choice == 3:
            left = self._random_expression(rng, depth + 1, alias_pool, keywords)
            right = self._random_expression(rng, depth + 1, alias_pool, keywords)
            op = rng.choice(["+", "-", "*", "/", "%"])
            return f"({left} {op} {right})"
        elif choice == 4:
            left = self._random_expression(rng, depth + 1, alias_pool, keywords)
            right = self._random_expression(rng, depth + 1, alias_pool, keywords)
            op = rng.choice(["=", "<>", "!=", "<", ">", "<=", ">="])
            return f"({left} {op} {right})"
        elif choice == 5:
            left = self._random_expression(rng, depth + 1, alias_pool, keywords)
            right = self._random_expression(rng, depth + 1, alias_pool, keywords)
            op = rng.choice(["AND", "OR"])
            return f"({left} {op} {right})"
        elif choice == 6:
            val = self._random_expression(rng, depth + 1, alias_pool, keywords)
            low = self._random_literal(rng, keywords)
            high = self._random_literal(rng, keywords)
            return f"({val} BETWEEN {low} AND {high})"
        elif choice == 7:
            val = self._random_expression(rng, depth + 1, alias_pool, keywords)
            items = [
                self._random_literal(rng, keywords)
                for _ in range(rng.randint(1, 4))
            ]
            return f"({val} IN ({', '.join(items)}))"
        elif choice == 8:
            funcs = ["ABS", "COALESCE", "LOWER", "UPPER", "ROUND", "LENGTH"]
            func = rng.choice(funcs)
            if func == "COALESCE":
                e1 = self._random_expression(
                    rng, depth + 1, alias_pool, keywords
                )
                e2 = self._random_expression(
                    rng, depth + 1, alias_pool, keywords
                )
                return f"COALESCE({e1}, {e2})"
            elif func == "ROUND":
                e1 = self._random_expression(
                    rng, depth + 1, alias_pool, keywords
                )
                prec = rng.randint(0, 4)
                return f"ROUND({e1}, {prec})"
            else:
                inner = self._random_expression(
                    rng, depth + 1, alias_pool, keywords
                )
                return f"{func}({inner})"
        else:
            # CASE expression
            cond1 = self._random_expression(rng, depth + 1, alias_pool, keywords)
            res1 = self._random_expression(rng, depth + 1, alias_pool, keywords)
            case_expr = f"CASE WHEN {cond1} THEN {res1}"
            if rng.random() < 0.5:
                cond2 = self._random_expression(
                    rng, depth + 1, alias_pool, keywords
                )
                res2 = self._random_expression(
                    rng, depth + 1, alias_pool, keywords
                )
                case_expr += f" WHEN {cond2} THEN {res2}"
            if rng.random() < 0.7:
                else_expr = self._random_expression(
                    rng, depth + 1, alias_pool, keywords
                )
                case_expr += f" ELSE {else_expr}"
            case_expr += " END"
            return case_expr

    def _build_from_clause(
        self, rng: random.Random, base_tables: list[str]
    ) -> tuple[str, list[str]]:
        # Occasionally omit FROM completely
        if rng.random() < 0.1 or not base_tables:
            return "", []

        alias_pool: list[str] = []
        first_table = rng.choice(base_tables)
        first_alias = "t1"
        alias_pool.append(first_alias)
        from_parts: list[str] = [f"{first_table} AS {first_alias}"]

        join_count = rng.randint(0, 2)
        for i in range(join_count):
            table = rng.choice(base_tables)
            alias = f"t{i + 2}"
            join_type = rng.choice(
                [
                    "INNER JOIN",
                    "LEFT JOIN",
                    "LEFT OUTER JOIN",
                    "RIGHT JOIN",
                    "FULL JOIN",
                ]
            )
            # Simple join predicate using ids
            cond = f"{alias_pool[0]}.id = {alias}.id"
            from_parts.append(f"{join_type} {table} AS {alias} ON {cond}")
            alias_pool.append(alias)

        from_clause = "FROM " + " ".join(from_parts)
        return from_clause, alias_pool

    def _gen_random_select(
        self, rng: random.Random, keywords: set[str]
    ) -> str:
        # WITH clause
        with_clause = ""
        base_tables = ["table1", "table2", "table3", "table4"]
        if "WITH" in keywords and rng.random() < 0.35:
            cte_count = rng.randint(1, 2)
            ctes: list[str] = []
            for i in range(cte_count):
                cte_name = f"cte{i + 1}"
                cte_select = "SELECT col1, col2 FROM table1"
                ctes.append(f"{cte_name} AS ({cte_select})")
                base_tables.append(cte_name)
            with_clause = "WITH " + ", ".join(ctes) + " "

        # FROM clause and aliases
        from_clause, alias_pool = self._build_from_clause(rng, base_tables)

        # SELECT list
        select_items: list[str] = []
        col_count = rng.randint(1, 4)
        for i in range(col_count):
            if i == 0 and rng.random() < 0.25:
                if alias_pool and rng.random() < 0.5:
                    alias = rng.choice(alias_pool)
                    expr = f"{alias}.*"
                else:
                    expr = "*"
            else:
                expr = self._random_expression(
                    rng, 0, alias_pool, keywords
                )

            if rng.random() < 0.6:
                alias = self._random_identifier(rng, "c")
                expr = f"{expr} AS {alias}"
            select_items.append(expr)

        distinct = " DISTINCT" if rng.random() < 0.3 else ""
        select_clause = f"SELECT{distinct} " + ", ".join(select_items)

        # WHERE clause
        where_clause = ""
        if rng.random() < 0.7:
            cond = self._random_expression(rng, 1, alias_pool, keywords)
            where_clause = f" WHERE {cond}"

        # GROUP BY / HAVING
        group_clause = ""
        having_clause = ""
        if rng.random() < 0.4 and alias_pool:
            group_cols: list[str] = []
            for _ in range(rng.randint(1, 3)):
                group_cols.append(self._random_column_ref(rng, alias_pool))
            group_clause = " GROUP BY " + ", ".join(group_cols)
            if rng.random() < 0.6:
                having_expr = self._random_expression(
                    rng, 1, alias_pool, keywords
                )
                having_clause = f" HAVING {having_expr}"

        # ORDER BY
        order_clause = ""
        if rng.random() < 0.7:
            order_items: list[str] = []
            for _ in range(rng.randint(1, 3)):
                expr = self._random_expression(
                    rng, 1, alias_pool, keywords
                )
                direction = rng.choice(["ASC", "DESC"])
                order_items.append(f"{expr} {direction}")
            order_clause = " ORDER BY " + ", ".join(order_items)

        # LIMIT / OFFSET
        limit_clause = ""
        if "LIMIT" in keywords and rng.random() < 0.7:
            limit_val = rng.randint(1, 100)
            limit_clause = f" LIMIT {limit_val}"
            if "OFFSET" in keywords and rng.random() < 0.5:
                offset_val = rng.randint(0, 100)
                limit_clause += f" OFFSET {offset_val}"

        sql = ""
        if with_clause:
            sql += with_clause
        sql += select_clause
        if from_clause:
            sql += " " + from_clause
        if where_clause:
            sql += where_clause
        if group_clause:
            sql += group_clause
        if having_clause:
            sql += having_clause
        if order_clause:
            sql += order_clause
        if limit_clause:
            sql += limit_clause

        if rng.random() < 0.5:
            sql += ";"
        return sql