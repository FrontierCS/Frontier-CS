import os
import sys
import re
import random
from typing import List, Dict, Tuple, Optional


class Terminal:
    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text


class NonTerminal:
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name


class OptionalGroup:
    __slots__ = ("elements",)

    def __init__(self, elements) -> None:
        self.elements = elements


class RepeatGroup:
    __slots__ = ("elements",)

    def __init__(self, elements) -> None:
        self.elements = elements


class EBNFParser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.length = len(text)
        self.pos = 0

    def skip_ws(self) -> None:
        while self.pos < self.length and self.text[self.pos].isspace():
            self.pos += 1

    def parse(self):
        alts = []
        while self.pos < self.length:
            seq = self.parse_sequence()
            alts.append(seq)
            self.skip_ws()
            if self.pos >= self.length or self.text[self.pos] != '|':
                break
            self.pos += 1  # skip '|'
        return alts

    def parse_sequence(self, closing: Optional[str] = None):
        elements = []
        while self.pos < self.length:
            self.skip_ws()
            if self.pos >= self.length:
                break
            ch = self.text[self.pos]
            if closing is not None and ch == closing:
                self.pos += 1
                break
            if ch == '|' and closing is None:
                break
            if ch == '<':
                name = self.read_nonterminal()
                if name:
                    elements.append(NonTerminal(name))
                continue
            if ch == '"' or ch == "'":
                term = self.read_quoted()
                if term is not None:
                    elements.append(Terminal(term))
                continue
            if ch == '[':
                self.pos += 1
                group_elements = self.parse_sequence(']')
                elements.append(OptionalGroup(group_elements))
                continue
            if ch == '{':
                self.pos += 1
                group_elements = self.parse_sequence('}')
                elements.append(RepeatGroup(group_elements))
                continue
            token = self.read_token()
            if token:
                elements.append(Terminal(token))
                continue
            # Safety: advance to avoid infinite loop
            self.pos += 1
        return elements

    def read_nonterminal(self) -> Optional[str]:
        # assumes current char is '<'
        start = self.pos + 1
        end = self.text.find('>', start)
        if end == -1:
            # malformed; skip '<'
            self.pos += 1
            return None
        name = self.text[start:end].strip()
        self.pos = end + 1
        return name

    def read_quoted(self) -> Optional[str]:
        quote = self.text[self.pos]
        self.pos += 1
        result_chars = []
        while self.pos < self.length:
            ch = self.text[self.pos]
            if ch == '\\' and self.pos + 1 < self.length:
                # escaped char
                result_chars.append(self.text[self.pos + 1])
                self.pos += 2
                continue
            if ch == quote:
                self.pos += 1
                break
            result_chars.append(ch)
            self.pos += 1
        return ''.join(result_chars)

    def read_token(self) -> str:
        start = self.pos
        while self.pos < self.length:
            ch = self.text[self.pos]
            if ch.isspace() or ch in '|[]{}':
                break
            self.pos += 1
        return self.text[start:self.pos]


class GrammarBasedSQLGenerator:
    def __init__(self, grammar_path: str) -> None:
        self.grammar_path = grammar_path
        self.rules: Dict[str, List[List]] = {}
        self.rule_order: List[str] = []
        self.alt_use_counts: Dict[str, List[int]] = {}
        self.alt_recursion: Dict[Tuple[str, int], bool] = {}
        self.depth_limit = 10

        self.sample_identifiers = [
            "t1",
            "t2",
            "users",
            "orders",
            "employees",
            "products",
            "tbl",
            "x",
        ]
        self.sample_string_literals = ["'foo'", "'bar'", "'baz'", "'str'"]
        self.sample_numbers = ["0", "1", "2", "42", "100"]
        self.sample_types = ["INT", "VARCHAR(100)", "BOOLEAN", "DECIMAL(10,2)"]

        self._parse_grammar()

    def _parse_grammar(self) -> None:
        if not os.path.exists(self.grammar_path):
            return
        try:
            with open(self.grammar_path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError:
            return

        # Remove C-style and SQL-style comments
        text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
        text = re.sub(r"--.*?$", " ", text, flags=re.M)

        current_rule: Optional[str] = None
        current_rhs_parts: List[str] = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#") or line.startswith("//"):
                continue

            if "::=" in line:
                # finalize previous rule
                if current_rule is not None:
                    rhs_text = " ".join(current_rhs_parts).strip()
                    if rhs_text:
                        parser = EBNFParser(rhs_text)
                        alts = parser.parse()
                    else:
                        alts = [[]]
                    self.rules[current_rule] = alts
                    self.alt_use_counts[current_rule] = [0] * len(alts)
                    if current_rule not in self.rule_order:
                        self.rule_order.append(current_rule)

                lhs, rhs = line.split("::=", 1)
                lhs = lhs.strip()
                if lhs.startswith("<") and lhs.endswith(">"):
                    lhs_name = lhs[1:-1].strip()
                else:
                    lhs_name = lhs
                current_rule = lhs_name
                current_rhs_parts = [rhs.strip()]
            else:
                if current_rule is not None:
                    current_rhs_parts.append(line)

        if current_rule is not None:
            rhs_text = " ".join(current_rhs_parts).strip()
            if rhs_text:
                parser = EBNFParser(rhs_text)
                alts = parser.parse()
            else:
                alts = [[]]
            self.rules[current_rule] = alts
            self.alt_use_counts[current_rule] = [0] * len(alts)
            if current_rule not in self.rule_order:
                self.rule_order.append(current_rule)

        # Precompute simple direct recursion flags
        for name, alts in self.rules.items():
            for idx, alt in enumerate(alts):
                self.alt_recursion[(name, idx)] = self._alt_has_direct_recursion(
                    name, alt
                )

    def _alt_has_direct_recursion(self, rule_name: str, elements) -> bool:
        def check(elems) -> bool:
            for e in elems:
                if isinstance(e, NonTerminal) and e.name == rule_name:
                    return True
                if isinstance(e, (OptionalGroup, RepeatGroup)):
                    if check(e.elements):
                        return True
            return False

        return check(elements)

    def _random_identifier(self) -> str:
        return random.choice(self.sample_identifiers)

    def _random_string_literal(self) -> str:
        return random.choice(self.sample_string_literals)

    def _random_number(self) -> str:
        return random.choice(self.sample_numbers)

    def _random_type(self) -> str:
        return random.choice(self.sample_types)

    def _expand_unknown_nonterminal(self, name: str):
        n = name.lower()
        if (
            "ident" in n
            or "name" in n
            or "alias" in n
            or "column" in n
            or "field" in n
            or n in ("table", "column", "col", "tbl")
        ):
            return [self._random_identifier()]
        if "string" in n or "char" in n or "text" in n:
            return [self._random_string_literal()]
        if (
            "number" in n
            or "int" in n
            or "integer" in n
            or "numeric" in n
            or "decimal" in n
            or "float" in n
            or "double" in n
            or "real" in n
        ):
            return [self._random_number()]
        if "bool" in n:
            return ["TRUE"]
        if "type" in n:
            return [self._random_type()]
        if "schema" in n:
            return ["main_schema"]
        if "index" in n:
            return ["idx_sample"]
        if "view" in n:
            return ["v_sample"]
        if "database" in n or "catalog" in n:
            return ["main_db"]
        if "operator" in n or n == "op":
            return ["="]
        if "value" in n or "literal" in n or "const" in n:
            return [self._random_number()]
        # Fallback: generic identifier
        return [self._random_identifier()]

    def _expand_elements(self, elements, depth: int):
        tokens: List[str] = []
        for elem in elements:
            if isinstance(elem, Terminal):
                if elem.text:
                    tokens.append(elem.text)
            elif isinstance(elem, NonTerminal):
                tokens.extend(self._expand_nonterminal(elem.name, depth + 1))
            elif isinstance(elem, OptionalGroup):
                include = False
                if depth < self.depth_limit:
                    include = random.choice((True, False))
                if include:
                    tokens.extend(self._expand_elements(elem.elements, depth + 1))
            elif isinstance(elem, RepeatGroup):
                count = 0
                if depth < self.depth_limit:
                    count = random.randint(0, 2)
                for _ in range(count):
                    tokens.extend(self._expand_elements(elem.elements, depth + 1))
        return tokens

    def _expand_nonterminal(self, name: str, depth: int):
        if depth > self.depth_limit * 2:
            return self._expand_unknown_nonterminal(name)

        if name not in self.rules:
            return self._expand_unknown_nonterminal(name)

        alts = self.rules[name]
        if not alts:
            return []

        use_counts = self.alt_use_counts.get(name)
        if use_counts is None:
            use_counts = [0] * len(alts)
            self.alt_use_counts[name] = use_counts

        best_idx = 0
        best_score = None
        for idx, alt in enumerate(alts):
            base = use_counts[idx]
            if depth > self.depth_limit and self.alt_recursion.get((name, idx), False):
                base += 1000
            if best_score is None or base < best_score:
                best_score = base
                best_idx = idx

        self.alt_use_counts[name][best_idx] += 1
        selected_alt = alts[best_idx]
        return self._expand_elements(selected_alt, depth + 1)

    def generate_one(self) -> str:
        if not self.rule_order:
            return ""
        root = self.rule_order[0]
        tokens = self._expand_nonterminal(root, 0)
        # Normalize spaces
        tokens = [t for t in tokens if t and t.strip() != ""]
        sql = " ".join(tokens).strip()
        return sql

    def generate_valid_statements(
        self, parse_sql, max_count: int = 60, max_attempts: int = 400
    ) -> List[str]:
        results: List[str] = []
        seen: set = set()
        attempts = 0
        while len(results) < max_count and attempts < max_attempts:
            attempts += 1
            try:
                sql = self.generate_one()
            except Exception:
                continue
            if not sql:
                continue
            sql = sql.strip()
            if not sql or sql in seen:
                continue
            try:
                parse_sql(sql)
            except Exception:
                continue
            seen.add(sql)
            results.append(sql)
        return results


class Solution:
    def _build_manual_statements(self) -> List[str]:
        stmts: List[str] = []

        # Basic SELECTs
        stmts.append("SELECT 1")
        stmts.append("SELECT 1, 2, 3")
        stmts.append("SELECT 'a' AS col1, 2 AS col2")
        stmts.append("SELECT * FROM users")
        stmts.append("SELECT users.id, users.name FROM users")
        stmts.append("SELECT DISTINCT name FROM users")
        stmts.append("SELECT name, age FROM users WHERE age > 18")

        # WHERE clauses and predicates
        stmts.append("SELECT * FROM users WHERE age >= 18 AND active = TRUE")
        stmts.append("SELECT * FROM users WHERE name LIKE 'A%' OR name IS NULL")
        stmts.append("SELECT * FROM users WHERE id IN (1, 2, 3)")
        stmts.append(
            "SELECT * FROM users WHERE created_at BETWEEN '2020-01-01' AND '2020-12-31'"
        )
        stmts.append("SELECT * FROM users WHERE NOT (age < 18 OR active = FALSE)")

        # GROUP BY / HAVING / ORDER BY / LIMIT
        stmts.append("SELECT country, COUNT(*) AS cnt FROM users GROUP BY country")
        stmts.append(
            "SELECT country, COUNT(*) AS cnt FROM users GROUP BY country HAVING COUNT(*) > 10"
        )
        stmts.append(
            "SELECT department, SUM(salary) AS total_salary FROM employees GROUP BY department ORDER BY total_salary DESC"
        )
        stmts.append("SELECT * FROM users ORDER BY name ASC")
        stmts.append("SELECT * FROM users ORDER BY created_at DESC LIMIT 10")
        stmts.append(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT 10 OFFSET 20"
        )
        stmts.append("SELECT * FROM users LIMIT 5")

        # Joins
        stmts.append(
            "SELECT u.id, o.id FROM users AS u INNER JOIN orders AS o ON u.id = o.user_id"
        )
        stmts.append(
            "SELECT u.id, o.id FROM users u LEFT JOIN orders o ON u.id = o.user_id"
        )
        stmts.append(
            "SELECT u.id, o.id FROM users u RIGHT JOIN orders o ON u.id = o.user_id"
        )
        stmts.append(
            "SELECT u.id, o.id FROM users u FULL OUTER JOIN orders o ON u.id = o.user_id"
        )
        stmts.append("SELECT u.id, o.id FROM users u CROSS JOIN orders o")

        # JOIN variations
        stmts.append("SELECT * FROM users u JOIN orders o USING (id)")
        stmts.append("SELECT * FROM users NATURAL JOIN orders")

        # Subqueries
        stmts.append("SELECT id FROM users WHERE id IN (SELECT user_id FROM orders)")
        stmts.append(
            "SELECT id FROM users WHERE EXISTS (SELECT 1 FROM orders WHERE orders.user_id = users.id)"
        )
        stmts.append(
            "SELECT id, (SELECT COUNT(*) FROM orders WHERE orders.user_id = users.id) AS order_count FROM users"
        )
        stmts.append("SELECT * FROM (SELECT id, name FROM users) AS sub")

        # Set operations
        stmts.append("SELECT id FROM users UNION SELECT id FROM admins")
        stmts.append("SELECT id FROM users UNION ALL SELECT id FROM admins")
        stmts.append("SELECT id FROM users INTERSECT SELECT id FROM admins")
        stmts.append("SELECT id FROM users EXCEPT SELECT id FROM admins")

        # Functions, expressions, CASE
        stmts.append("SELECT ABS(-5), ROUND(3.1415, 2)")
        stmts.append("SELECT COALESCE(nickname, name) FROM users")
        stmts.append(
            "SELECT CASE WHEN age < 18 THEN 'minor' WHEN age < 65 THEN 'adult' ELSE 'senior' END AS age_group FROM users"
        )
        stmts.append("SELECT CAST(age AS INTEGER) FROM users")
        stmts.append("SELECT SUM(price * quantity) AS total FROM orders")
        stmts.append("SELECT DATE('2020-01-01')")
        stmts.append("SELECT NOW()")
        stmts.append("SELECT LENGTH(name) FROM users")
        stmts.append("SELECT SUBSTR(name, 1, 3) FROM users")
        stmts.append("SELECT 1 + 2 * 3 - 4 / 5")

        # Window functions
        stmts.append(
            "SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) AS rn FROM users"
        )
        stmts.append(
            "SELECT id, SUM(amount) OVER (PARTITION BY user_id ORDER BY created_at) AS running_total FROM payments"
        )
        stmts.append(
            "SELECT id, AVG(salary) OVER (PARTITION BY department) AS dept_avg FROM employees"
        )

        # DML: INSERT
        stmts.append(
            "INSERT INTO users (id, name, age) VALUES (1, 'Alice', 30)"
        )
        stmts.append("INSERT INTO users VALUES (2, 'Bob', 25)")
        stmts.append(
            "INSERT INTO users (id, name) SELECT id, name FROM admins"
        )

        # DML: UPDATE
        stmts.append("UPDATE users SET name = 'Charlie' WHERE id = 1")
        stmts.append(
            "UPDATE users SET name = 'NoAge', age = NULL WHERE age IS NULL"
        )

        # DML: DELETE
        stmts.append("DELETE FROM users WHERE id = 1")
        stmts.append("DELETE FROM users")

        # DDL: CREATE TABLE
        stmts.append(
            "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100) NOT NULL, age INT, created_at TIMESTAMP)"
        )
        stmts.append(
            "CREATE TABLE orders (id INT PRIMARY KEY, user_id INT REFERENCES users(id), amount DECIMAL(10,2), created_at TIMESTAMP)"
        )
        stmts.append(
            "CREATE TABLE IF NOT EXISTS logs (id INT, message TEXT)"
        )

        # DDL: DROP TABLE
        stmts.append("DROP TABLE users")
        stmts.append("DROP TABLE IF EXISTS logs")

        # DDL: ALTER TABLE
        stmts.append("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
        stmts.append("ALTER TABLE users DROP COLUMN age")
        stmts.append("ALTER TABLE users RENAME COLUMN name TO full_name")

        # Indexes
        stmts.append("CREATE INDEX idx_users_name ON users (name)")
        stmts.append("DROP INDEX idx_users_name")

        # Views
        stmts.append(
            "CREATE VIEW active_users AS SELECT * FROM users WHERE active = TRUE"
        )
        stmts.append("DROP VIEW active_users")

        # Truncate
        stmts.append("TRUNCATE TABLE users")

        # Transactions & schema
        stmts.append("BEGIN")
        stmts.append("BEGIN TRANSACTION")
        stmts.append("COMMIT")
        stmts.append("ROLLBACK")
        stmts.append("CREATE SCHEMA reporting")
        stmts.append("DROP SCHEMA reporting")

        return stmts

    def _default_fallback_statements(self) -> List[str]:
        base = self._build_manual_statements()
        final: List[str] = []
        seen: set = set()
        for stmt in base:
            s = stmt.strip()
            for variant in (s, s + ";"):
                if variant and variant not in seen:
                    seen.add(variant)
                    final.append(variant)
                    if len(final) >= 100:
                        return final
        if not final:
            final = ["SELECT 1", "SELECT 1;"]
        return final

    def solve(self, resources_path: str) -> List[str]:
        random.seed(0)

        # Try to import sql_engine and parse_sql
        try:
            if resources_path not in sys.path:
                sys.path.append(resources_path)
            import importlib

            sql_engine = importlib.import_module("sql_engine")
            parse_sql = getattr(sql_engine, "parse_sql", None)
            if parse_sql is None:
                parser_mod = importlib.import_module("sql_engine.parser")
                parse_sql = getattr(parser_mod, "parse_sql")
        except Exception:
            # Fallback: cannot import, return generic statements
            return self._default_fallback_statements()

        all_results: List[str] = []
        seen: set = set()
        max_total = 120

        # Grammar-based generation
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        if os.path.exists(grammar_path):
            try:
                generator = GrammarBasedSQLGenerator(grammar_path)
                grammar_statements = generator.generate_valid_statements(
                    parse_sql, max_count=60, max_attempts=400
                )
                for stmt in grammar_statements:
                    s = stmt.strip()
                    if s and s not in seen:
                        seen.add(s)
                        all_results.append(s)
                        if len(all_results) >= max_total:
                            return all_results[:max_total]
            except Exception:
                pass

        # Manual statements with and without semicolons
        manual_base = self._build_manual_statements()
        manual_variants: List[str] = []
        seen_variants: set = set()
        for stmt in manual_base:
            base = stmt.strip()
            for variant in (base, base + ";"):
                if variant and variant not in seen_variants:
                    seen_variants.add(variant)
                    manual_variants.append(variant)

        for sql in manual_variants:
            if sql in seen:
                continue
            try:
                parse_sql(sql)
            except Exception:
                continue
            seen.add(sql)
            all_results.append(sql)
            if len(all_results) >= max_total:
                return all_results[:max_total]

        if not all_results:
            return self._default_fallback_statements()

        return all_results[:max_total]