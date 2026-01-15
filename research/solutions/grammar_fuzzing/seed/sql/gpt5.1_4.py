import os
import sys
import random
import re
import importlib
import inspect
from typing import List, Set, Dict, Tuple, Optional, Any


class BnfExpr:
    def generate(self, grammar: "Grammar", depth: int, rng: random.Random) -> str:
        raise NotImplementedError


class Terminal(BnfExpr):
    def __init__(self, text: str):
        self.text = text

    def generate(self, grammar: "Grammar", depth: int, rng: random.Random) -> str:
        return self.text


class NonTerminal(BnfExpr):
    def __init__(self, name: str):
        self.name = name

    def generate(self, grammar: "Grammar", depth: int, rng: random.Random) -> str:
        return grammar.generate_from_nonterminal(self.name, depth + 1, rng)


class Sequence(BnfExpr):
    def __init__(self, elements: List[BnfExpr]):
        self.elements = [e for e in elements if e is not None]

    def generate(self, grammar: "Grammar", depth: int, rng: random.Random) -> str:
        parts: List[str] = []
        for elem in self.elements:
            if elem is None:
                continue
            val = elem.generate(grammar, depth + 1, rng)
            if val:
                parts.append(val)
        return " ".join(parts).strip()


class Choice(BnfExpr):
    def __init__(self, options: List[BnfExpr]):
        self.options = [o for o in options if o is not None]

    def generate(self, grammar: "Grammar", depth: int, rng: random.Random) -> str:
        if not self.options:
            return ""
        option = rng.choice(self.options)
        return option.generate(grammar, depth + 1, rng)


class OptionalExpr(BnfExpr):
    def __init__(self, child: BnfExpr):
        self.child = child

    def generate(self, grammar: "Grammar", depth: int, rng: random.Random) -> str:
        if depth > grammar.max_depth - 1:
            include = False
        else:
            include = rng.random() < 0.7
        if include and self.child is not None:
            return self.child.generate(grammar, depth + 1, rng)
        return ""


class Repeat(BnfExpr):
    def __init__(self, child: BnfExpr):
        self.child = child

    def generate(self, grammar: "Grammar", depth: int, rng: random.Random) -> str:
        if depth > grammar.max_depth - 1:
            count = 0
        else:
            r = rng.random()
            if r < 0.3:
                count = 0
            elif r < 0.7:
                count = 1
            else:
                count = 2
        parts: List[str] = []
        for _ in range(count):
            if self.child is None:
                break
            val = self.child.generate(grammar, depth + 1, rng)
            if val:
                parts.append(val)
        return " ".join(parts).strip()


class Grammar:
    def __init__(self):
        self.rules: Dict[str, BnfExpr] = {}
        self.order: List[str] = []
        self.start_symbol: Optional[str] = None
        self.max_depth: int = 6
        self._id_counter: int = 0

    def add_rule(self, name: str, expr: BnfExpr) -> None:
        if name not in self.rules:
            self.order.append(name)
        self.rules[name] = expr

    def guess_start_symbol(self) -> Optional[str]:
        if not self.order:
            return None
        for name in self.order:
            lname = name.lower()
            if "statement_list" in lname or "statements" in lname:
                return name
        for name in self.order:
            lname = name.lower()
            if "statement" in lname or "stmt" in lname:
                return name
        for name in self.order:
            lname = name.lower()
            if "query" in lname or "select" in lname or "sql" in lname or "script" in lname:
                return name
        return self.order[0]

    def generate_start(self, rng: random.Random) -> str:
        if self.start_symbol is None:
            self.start_symbol = self.guess_start_symbol()
        if self.start_symbol is None:
            return ""
        return self.generate_from_nonterminal(self.start_symbol, 0, rng).strip()

    def generate_from_nonterminal(self, name: str, depth: int, rng: random.Random) -> str:
        if depth > self.max_depth:
            return self.generate_terminal_like(name, rng)
        expr = self.rules.get(name)
        if expr is None:
            return self.generate_terminal_like(name, rng)
        try:
            result = expr.generate(self, depth, rng)
        except RecursionError:
            result = self.generate_terminal_like(name, rng)
        if not result:
            return self.generate_terminal_like(name, rng)
        return result

    def _next_counter(self) -> int:
        self._id_counter += 1
        return self._id_counter

    def random_identifier(self, rng: random.Random, prefix: Optional[str] = None) -> str:
        if prefix is None:
            prefix = "id"
        return f"{prefix}{self._next_counter()}"

    def random_string_literal(self, rng: random.Random) -> str:
        return f"'s{self._next_counter()}'"

    def random_number_literal(self, rng: random.Random) -> str:
        return str(rng.randint(0, 1000))

    def generate_terminal_like(self, name: str, rng: random.Random) -> str:
        lname = name.lower()
        if any(sub in lname for sub in ("ident", "name", "column", "col", "field")):
            return self.random_identifier(rng, prefix="c")
        if any(sub in lname for sub in ("table", "relation", "view", "schema", "database")):
            return self.random_identifier(rng, prefix="t")
        if any(sub in lname for sub in ("string", "char", "text", "varchar", "clob")):
            return self.random_string_literal(rng)
        if any(sub in lname for sub in ("int", "integer", "number", "numeric", "decimal", "float", "double")):
            return self.random_number_literal(rng)
        if "bool" in lname or "boolean" in lname:
            return rng.choice(["TRUE", "FALSE"])
        if "date" in lname or "time" in lname:
            return "'2020-01-01'"
        if "literal" in lname:
            return rng.choice([self.random_number_literal(rng), self.random_string_literal(rng)])
        if "value" in lname or "expr" in lname or "expression" in lname:
            return rng.choice(
                [
                    self.random_identifier(rng, prefix="v"),
                    self.random_number_literal(rng),
                    self.random_string_literal(rng),
                ]
            )
        if "operator" in lname or lname.endswith("op"):
            return rng.choice(["+", "-", "*", "/", "AND", "OR"])
        if "comparison" in lname or "comp" in lname:
            return rng.choice(["=", "<>", "<", ">", "<=", ">="])
        return self.random_identifier(rng, prefix="x")


def grammar_tokenize(s: str) -> List[str]:
    tokens: List[str] = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "[]{}()|":
            tokens.append(ch)
            i += 1
            continue
        if ch == '"' or ch == "'":
            quote = ch
            i += 1
            buf_chars: List[str] = []
            while i < n and s[i] != quote:
                if s[i] == "\\" and i + 1 < n:
                    buf_chars.append(s[i + 1])
                    i += 2
                else:
                    buf_chars.append(s[i])
                    i += 1
            if i < n and s[i] == quote:
                i += 1
            val = "".join(buf_chars)
            tokens.append(quote + val + quote)
            continue
        if ch == "<":
            i += 1
            buf_chars = []
            while i < n and s[i] != ">":
                buf_chars.append(s[i])
                i += 1
            if i < n and s[i] == ">":
                i += 1
            name = "".join(buf_chars).strip()
            tokens.append("<" + name + ">")
            continue
        buf_chars = []
        while i < n and (not s[i].isspace()) and s[i] not in "[]{}()|":
            buf_chars.append(s[i])
            i += 1
        tokens.append("".join(buf_chars))
    return tokens


def parse_symbol(tok: str) -> BnfExpr:
    if not tok:
        return Terminal("")
    if tok[0] == "<" and tok[-1] == ">":
        name = tok[1:-1].strip()
        return NonTerminal(name)
    if (tok[0] == '"' and tok[-1] == '"') or (tok[0] == "'" and tok[-1] == "'"):
        return Terminal(tok[1:-1])
    return Terminal(tok)


def parse_E(tokens: List[str], i: int) -> Tuple[BnfExpr, int]:
    node, i = parse_T(tokens, i)
    options: List[BnfExpr] = [node]
    while i < len(tokens) and tokens[i] == "|":
        i += 1
        right, i = parse_T(tokens, i)
        options.append(right)
    if len(options) == 1:
        return options[0], i
    return Choice(options), i


def parse_T(tokens: List[str], i: int) -> Tuple[BnfExpr, int]:
    factors: List[BnfExpr] = []
    while i < len(tokens) and tokens[i] not in ("]", "}", "|", ")"):
        node, i = parse_F(tokens, i)
        if node is not None:
            factors.append(node)
    if not factors:
        return Sequence([]), i
    if len(factors) == 1:
        return factors[0], i
    return Sequence(factors), i


def parse_F(tokens: List[str], i: int) -> Tuple[BnfExpr, int]:
    tok = tokens[i]
    if tok == "[":
        inner, i = parse_E(tokens, i + 1)
        if i < len(tokens) and tokens[i] == "]":
            i += 1
        return OptionalExpr(inner), i
    if tok == "{":
        inner, i = parse_E(tokens, i + 1)
        if i < len(tokens) and tokens[i] == "}":
            i += 1
        return Repeat(inner), i
    if tok == "(":
        inner, i = parse_E(tokens, i + 1)
        if i < len(tokens) and tokens[i] == ")":
            i += 1
        return inner, i
    return parse_symbol(tok), i + 1


def load_grammar(grammar_path: str) -> Optional[Grammar]:
    if not os.path.isfile(grammar_path):
        return None
    grammar = Grammar()
    try:
        with open(grammar_path, "r", encoding="utf-8") as f:
            current_rule_name: Optional[str] = None
            current_rhs_parts: List[str] = []
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("#") or line.startswith("//") or line.startswith("--"):
                    continue
                if "::=" in line:
                    if current_rule_name is not None:
                        rhs_text = " ".join(current_rhs_parts).strip()
                        if rhs_text:
                            try:
                                tokens = grammar_tokenize(rhs_text)
                                expr, _ = parse_E(tokens, 0)
                                grammar.add_rule(current_rule_name, expr)
                            except Exception:
                                pass
                    lhs, rhs = line.split("::=", 1)
                    lhs = lhs.strip()
                    rhs = rhs.strip()
                    if lhs.startswith("<") and lhs.endswith(">"):
                        rule_name = lhs[1:-1].strip()
                    else:
                        rule_name = lhs
                    current_rule_name = rule_name
                    current_rhs_parts = [rhs]
                else:
                    if current_rule_name is not None:
                        current_rhs_parts.append(line)
            if current_rule_name is not None:
                rhs_text = " ".join(current_rhs_parts).strip()
                if rhs_text:
                    try:
                        tokens = grammar_tokenize(rhs_text)
                        expr, _ = parse_E(tokens, 0)
                        grammar.add_rule(current_rule_name, expr)
                    except Exception:
                        pass
    except Exception:
        return None
    if not grammar.rules:
        return None
    return grammar


def collect_ast_types(
    root: Any, ast_class_tuple: Tuple[type, ...], ast_class_set: Set[type]
) -> Tuple[Set[str], str]:
    types_set: Set[str] = set()
    if root is None:
        return types_set, "NONE"
    root_type_name = type(root).__name__
    visited_ids: Set[int] = set()
    stack: List[Any] = [root]
    while stack:
        obj = stack.pop()
        oid = id(obj)
        if oid in visited_ids:
            continue
        visited_ids.add(oid)
        cls = obj.__class__
        if cls in ast_class_set:
            types_set.add(cls.__name__)
            try:
                attrs = vars(obj)
            except TypeError:
                attrs = {}
            for val in attrs.values():
                if isinstance(val, ast_class_tuple):
                    stack.append(val)
                elif isinstance(val, (list, tuple, set, frozenset)):
                    for item in val:
                        if isinstance(item, ast_class_tuple):
                            stack.append(item)
                elif isinstance(val, dict):
                    for item in val.values():
                        if isinstance(item, ast_class_tuple):
                            stack.append(item)
        else:
            if isinstance(obj, (list, tuple, set, frozenset)):
                for item in obj:
                    if isinstance(item, ast_class_tuple):
                        stack.append(item)
                    elif isinstance(item, (list, tuple, set, frozenset, dict)):
                        stack.append(item)
            elif isinstance(obj, dict):
                for item in obj.values():
                    if isinstance(item, ast_class_tuple):
                        stack.append(item)
                    elif isinstance(item, (list, tuple, set, frozenset, dict)):
                        stack.append(item)
    return types_set, root_type_name


def extract_sql_features(sql: str, keyword_set: Set[str]) -> Set[str]:
    if not keyword_set:
        return set()
    tokens = re.findall(r"[A-Za-z_]+", sql)
    features: Set[str] = set()
    for tok in tokens:
        up = tok.upper()
        if up in keyword_set:
            features.add(up)
    return features


def load_keyword_set(tokenizer_module: Any) -> Set[str]:
    keywords: Set[str] = set()
    if tokenizer_module is None:
        return keywords
    for _, val in vars(tokenizer_module).items():
        try:
            if isinstance(val, dict):
                for k in val.keys():
                    if isinstance(k, str):
                        up = k.upper()
                        if up.isalpha():
                            keywords.add(up)
            elif isinstance(val, (list, tuple, set, frozenset)):
                for x in val:
                    if isinstance(x, str):
                        up = x.upper()
                        if up.isalpha():
                            keywords.add(up)
        except Exception:
            continue
    return keywords


def make_manual_templates() -> List[str]:
    stmts: List[str] = []
    stmts.append("SELECT 1;")
    stmts.append("SELECT * FROM users;")
    stmts.append("SELECT id, name FROM users WHERE age > 30;")
    stmts.append("SELECT DISTINCT country FROM users;")
    stmts.append(
        "SELECT u.id, u.name, o.amount FROM users u INNER JOIN orders o ON u.id = o.user_id;"
    )
    stmts.append(
        "SELECT u.id, COUNT(*) AS order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id HAVING COUNT(*) > 1;"
    )
    stmts.append("SELECT id, name FROM users ORDER BY name ASC, id DESC;")
    stmts.append("SELECT id, name FROM users LIMIT 10;")
    stmts.append("SELECT id, name FROM users LIMIT 10 OFFSET 5;")
    stmts.append(
        "SELECT CASE WHEN age < 18 THEN 'minor' WHEN age < 65 THEN 'adult' ELSE 'senior' END AS age_group FROM users;"
    )
    stmts.append("SELECT COALESCE(email, 'unknown') FROM users;")
    stmts.append(
        "SELECT id, (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.id) AS order_count FROM users u;"
    )
    stmts.append(
        "SELECT * FROM users WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = users.id);"
    )
    stmts.append(
        "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE amount > 100);"
    )
    stmts.append("SELECT name FROM users WHERE name LIKE 'A%';")
    stmts.append(
        "SELECT name FROM users WHERE created_at BETWEEN '2020-01-01' AND '2020-12-31';"
    )
    stmts.append(
        "SELECT name FROM users WHERE age IS NULL OR deleted IS NOT NULL;"
    )
    stmts.append("SELECT COUNT(*), country FROM users GROUP BY country;")
    stmts.append("SELECT MAX(age), MIN(age), AVG(age) FROM users;")
    stmts.append(
        "SELECT id, SUM(amount) OVER (PARTITION BY user_id ORDER BY created_at ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total FROM orders;"
    )
    stmts.append("SELECT id FROM users UNION SELECT user_id FROM admins;")
    stmts.append(
        "SELECT id FROM users UNION ALL SELECT user_id FROM admins;"
    )
    stmts.append(
        "SELECT id FROM users INTERSECT SELECT user_id FROM orders;"
    )
    stmts.append(
        "SELECT id FROM users EXCEPT SELECT user_id FROM banned_users;"
    )
    stmts.append(
        "WITH recent_orders AS (SELECT * FROM orders WHERE created_at > '2020-01-01') SELECT * FROM recent_orders;"
    )
    stmts.append(
        "WITH RECURSIVE nums AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM nums WHERE n < 10) SELECT * FROM nums;"
    )
    stmts.append(
        "INSERT INTO users (id, name, age) VALUES (1, 'Alice', 30);"
    )
    stmts.append(
        "INSERT INTO users (id, name) SELECT id, name FROM temp_users;"
    )
    stmts.append(
        "UPDATE users SET name = 'Bob', age = age + 1 WHERE id = 1;"
    )
    stmts.append("UPDATE users SET last_login = NOW();")
    stmts.append("DELETE FROM users WHERE id = 1;")
    stmts.append("DELETE FROM users;")
    stmts.append(
        "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100) NOT NULL, age INT, country VARCHAR(50));"
    )
    stmts.append(
        "CREATE TABLE orders (id INT PRIMARY KEY, user_id INT REFERENCES users(id), amount DECIMAL(10,2), created_at TIMESTAMP);"
    )
    stmts.append(
        "ALTER TABLE users ADD COLUMN email VARCHAR(255);"
    )
    stmts.append("ALTER TABLE users DROP COLUMN age;")
    stmts.append("CREATE INDEX idx_users_name ON users(name);")
    stmts.append("DROP INDEX idx_users_name;")
    stmts.append(
        "CREATE VIEW active_users AS SELECT * FROM users WHERE deleted IS NULL;"
    )
    stmts.append("DROP VIEW active_users;")
    stmts.append("DROP TABLE IF EXISTS temp_users;")
    stmts.append("TRUNCATE TABLE logs;")
    stmts.append("BEGIN TRANSACTION;")
    stmts.append("COMMIT;")
    stmts.append("ROLLBACK;")
    stmts.append("SAVEPOINT sp1;")
    stmts.append("RELEASE SAVEPOINT sp1;")
    stmts.append("ROLLBACK TO SAVEPOINT sp1;")
    return stmts


class Solution:
    def solve(self, resources_path: str) -> List[str]:
        rng = random.Random(42)
        resources_abs = os.path.abspath(resources_path)
        if resources_abs not in sys.path:
            sys.path.insert(0, resources_abs)
        importlib.invalidate_caches()

        parse_sql = None
        ast_class_set: Set[type] = set()
        ast_class_tuple: Tuple[type, ...] = tuple()
        keyword_set: Set[str] = set()

        try:
            engine_pkg = importlib.import_module("sql_engine")
        except Exception:
            engine_pkg = None

        if engine_pkg is not None:
            try:
                if hasattr(engine_pkg, "parse_sql"):
                    parse_sql = getattr(engine_pkg, "parse_sql")
                else:
                    parser_mod = importlib.import_module("sql_engine.parser")
                    if hasattr(parser_mod, "parse_sql"):
                        parse_sql = getattr(parser_mod, "parse_sql")
            except Exception:
                parse_sql = None

            try:
                ast_nodes_mod = importlib.import_module("sql_engine.ast_nodes")
                for _, cls in inspect.getmembers(ast_nodes_mod, inspect.isclass):
                    if getattr(cls, "__module__", "") == ast_nodes_mod.__name__:
                        ast_class_set.add(cls)
                if ast_class_set:
                    ast_class_tuple = tuple(ast_class_set)
            except Exception:
                ast_class_set = set()
                ast_class_tuple = tuple()

            try:
                tokenizer_mod = importlib.import_module("sql_engine.tokenizer")
            except Exception:
                tokenizer_mod = None
            keyword_set = load_keyword_set(tokenizer_mod)
        else:
            parse_sql = None
            ast_class_set = set()
            ast_class_tuple = tuple()
            keyword_set = set()

        grammar: Optional[Grammar] = None
        grammar_file = os.path.join(resources_abs, "sql_grammar.txt")
        grammar = load_grammar(grammar_file)

        if parse_sql is None:
            candidates: List[str] = []
            candidates.extend(make_manual_templates())
            if grammar is not None:
                for _ in range(50):
                    stmt = grammar.generate_start(rng)
                    if stmt:
                        candidates.append(stmt)
            seen_simple: Set[str] = set()
            result: List[str] = []
            for sql in candidates:
                sql = (sql or "").strip()
                if not sql:
                    continue
                if sql in seen_simple:
                    continue
                seen_simple.add(sql)
                result.append(sql)
                if len(result) >= 80:
                    break
            if not result:
                result.append("SELECT 1;")
            return result

        seen_sqls: Set[str] = set()
        best_sqls: List[str] = []
        ast_cov: Set[str] = set()
        kw_cov: Set[str] = set()
        root_type_counts: Dict[str, int] = {}
        parse_attempts = 0
        max_best = 80
        max_parse_attempts = 700

        def try_parse_with_variants(sql: str) -> Tuple[bool, Any, str]:
            nonlocal parse_attempts
            if parse_attempts >= max_parse_attempts:
                return False, None, sql
            stripped = (sql or "").strip()
            variants = [stripped]
            if stripped.endswith(";"):
                variants.append(stripped.rstrip(";\n\t ").rstrip())
            else:
                variants.append(stripped + ";")
            for variant in variants:
                if not variant:
                    continue
                if parse_attempts >= max_parse_attempts:
                    break
                try:
                    parse_attempts += 1
                    root = parse_sql(variant)
                    return True, root, variant
                except Exception:
                    continue
            return False, None, sql

        def process_sql_candidate(sql: str) -> None:
            nonlocal best_sqls, ast_cov, kw_cov
            sql = (sql or "").strip()
            if not sql:
                return
            if sql in seen_sqls:
                return
            success, root, used_sql = try_parse_with_variants(sql)
            if not success or root is None:
                return
            used_sql = (used_sql or "").strip()
            if not used_sql:
                return
            if used_sql in seen_sqls:
                return
            seen_sqls.add(used_sql)
            if ast_class_tuple:
                ast_types, root_type_name = collect_ast_types(
                    root, ast_class_tuple, ast_class_set
                )
            else:
                ast_types, root_type_name = set(), type(root).__name__
            features = extract_sql_features(used_sql, keyword_set)
            new_ast = ast_types - ast_cov
            new_kw = features - kw_cov
            accept = False
            if new_ast or new_kw:
                accept = True
            else:
                if len(best_sqls) < max_best:
                    key = root_type_name
                    count = root_type_counts.get(key, 0)
                    if count < 3:
                        root_type_counts[key] = count + 1
                        accept = True
            if accept and len(best_sqls) < max_best:
                best_sqls.append(used_sql)
                ast_cov.update(new_ast)
                kw_cov.update(new_kw)

        for sql in make_manual_templates():
            if parse_attempts >= max_parse_attempts or len(best_sqls) >= max_best:
                break
            process_sql_candidate(sql)

        if (
            grammar is not None
            and parse_attempts < max_parse_attempts
            and len(best_sqls) < max_best
        ):
            stagnation = 0
            max_iterations = 500
            iterations = 0
            while (
                parse_attempts < max_parse_attempts
                and len(best_sqls) < max_best
                and iterations < max_iterations
            ):
                iterations += 1
                stmt = grammar.generate_start(rng)
                if not stmt:
                    continue
                before_cov_size = len(ast_cov) + len(kw_cov)
                before_len = len(best_sqls)
                process_sql_candidate(stmt)
                after_cov_size = len(ast_cov) + len(kw_cov)
                if after_cov_size == before_cov_size and len(best_sqls) == before_len:
                    stagnation += 1
                    if stagnation > 150:
                        break
                else:
                    stagnation = 0

        if len(best_sqls) < max_best:
            extra_candidates: List[str] = []
            for s in list(best_sqls):
                stripped = (s or "").strip()
                if not stripped:
                    continue
                if stripped.endswith(";"):
                    extra = stripped.rstrip(";\n\t ").rstrip()
                else:
                    extra = stripped + ";"
                extra_candidates.append(extra)
            for sql in extra_candidates:
                if parse_attempts >= max_parse_attempts or len(best_sqls) >= max_best:
                    break
                process_sql_candidate(sql)

        if not best_sqls:
            best_sqls.append("SELECT 1;")

        return best_sqls