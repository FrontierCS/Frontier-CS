import os
import textwrap


class Solution:
    def solve(self, resources_path: str) -> dict:
        resources_path_abs = os.path.abspath(resources_path)
        header = (
            "import os\n"
            "import re\n"
            "import random\n"
            "import time\n"
            "from typing import List\n\n"
            f"RESOURCES_PATH = {resources_path_abs!r}\n\n"
        )

        rest_code = textwrap.dedent("""
class SQLFuzzer:
    def __init__(self):
        self.start_time = time.perf_counter()
        # Use slightly less than the full external budget to reduce risk of timeout
        self.max_time = 55.0
        self.deadline = self.start_time + self.max_time
        self.rand = random.Random()
        try:
            pid = os.getpid()
        except Exception:
            pid = 0
        seed = int(self.start_time * 1000) ^ pid
        self.rand.seed(seed)

        self.grammar_keywords: List[str] = []
        self.base_keywords: List[str] = [
            "SELECT", "INSERT", "UPDATE", "DELETE",
            "CREATE", "ALTER", "DROP", "FROM", "WHERE",
            "GROUP", "BY", "HAVING", "ORDER", "LIMIT",
            "OFFSET", "VALUES", "INTO", "TABLE", "INDEX",
            "VIEW", "TRIGGER", "BEGIN", "COMMIT", "ROLLBACK",
            "SAVEPOINT", "RELEASE", "UNION", "ALL", "INTERSECT",
            "EXCEPT", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER",
            "CROSS", "ON", "AND", "OR", "NOT", "NULL", "IS", "IN",
            "BETWEEN", "LIKE", "CASE", "WHEN", "THEN", "ELSE", "END",
            "AS", "DISTINCT", "ASC", "DESC", "PRIMARY", "KEY",
            "UNIQUE", "CHECK", "DEFAULT"
        ]
        self._load_grammar()
        self.all_keywords: List[str] = list(set(self.base_keywords + self.grammar_keywords))

        self.data_types: List[str] = [
            "INT", "INTEGER", "SMALLINT", "BIGINT",
            "REAL", "DOUBLE", "FLOAT", "NUMERIC",
            "DECIMAL(10,2)", "BOOLEAN", "CHAR(10)",
            "VARCHAR(255)", "TEXT", "BLOB", "DATE",
            "TIME", "TIMESTAMP"
        ]
        self.functions: List[str] = [
            "ABS", "ROUND", "LOWER", "UPPER", "LENGTH",
            "SUBSTR", "COALESCE", "IFNULL", "NULLIF",
            "MIN", "MAX", "SUM", "AVG", "COUNT",
            "RANDOM"
        ]
        self.zero_arg_functions = {"RANDOM"}
        self.binary_operators: List[str] = [
            "=", "!=", "<>", "<", ">", "<=", ">=",
            "LIKE", "IS", "IS NOT", "IN", "BETWEEN",
            "+", "-", "*", "/", "%", "AND", "OR"
        ]
        self.max_expr_depth = 3
        self.max_select_depth = 2

        # Batching and mutation parameters
        self.batch_size = 200          # Initial batch size, dynamically tuned
        self.min_batch_size = 50
        self.max_batch_size = 4000
        self.corpus: List[str] = []
        self.max_corpus_size = 5000
        self.mutation_chars = (
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789 ,()=<>!+-*/%\"'\\n\\t"
        )
        self.total_statements = 0
        self.total_parse_sql_calls = 0
        self.finished = False

    def _load_grammar(self) -> None:
        path = os.path.join(RESOURCES_PATH, "sql_grammar.txt")
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            return
        tokens = set()
        # Extract uppercase tokens that look like SQL keywords
        for m in re.finditer(r"\\b([A-Z_]{2,})\\b", text):
            w = m.group(1)
            if not w:
                continue
            if w.startswith("<") or w.endswith(">"):
                # Skip BNF non-terminals of the form <NAME>
                continue
            tokens.add(w)
        if tokens:
            self.grammar_keywords = sorted(tokens)

    def _time_remaining(self) -> float:
        return self.deadline - time.perf_counter()

    # ----------- Random primitive generators -----------

    def random_identifier(self) -> str:
        r = self.rand
        # Occasionally reuse a keyword as identifier (with or without quotes)
        if self.all_keywords and r.random() < 0.2:
            word = r.choice(self.all_keywords)
            style = r.randint(0, 3)
            if style == 0:
                return word.lower()
            elif style == 1:
                return '"' + word.lower() + '"'
            elif style == 2:
                return "[" + word + "]"
            else:
                return "`" + word.lower() + "`"
        length = r.randint(1, 10)
        first_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
        rest_chars = first_chars + "0123456789$"
        s = [r.choice(first_chars)]
        for _ in range(length - 1):
            s.append(r.choice(rest_chars))
        if r.random() < 0.3:
            s.append(str(r.randint(0, 100)))
        return "".join(s)

    def random_integer_literal(self) -> str:
        r = self.rand
        if r.random() < 0.1:
            return str(r.randint(-2**31, 2**31 - 1))
        return str(r.randint(-1000, 1000))

    def random_real_literal(self) -> str:
        r = self.rand
        value = (r.random() - 0.5) * 1000.0
        return "{0:.3f}".format(value)

    def random_string_literal(self) -> str:
        r = self.rand
        length = r.randint(0, 12)
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-"
        s: List[str] = []
        for _ in range(length):
            s.append(r.choice(chars))
        raw = "".join(s)
        # Occasionally escape quotes
        if r.random() < 0.3:
            raw = raw.replace("'", "''")
        return "'" + raw + "'"

    def random_literal(self) -> str:
        r = self.rand
        p = r.random()
        if p < 0.4:
            return self.random_integer_literal()
        elif p < 0.6:
            return self.random_real_literal()
        elif p < 0.8:
            return self.random_string_literal()
        else:
            return r.choice(["NULL", "TRUE", "FALSE", "CURRENT_TIMESTAMP"])

    def random_column_ref(self) -> str:
        r = self.rand
        col = self.random_identifier()
        if r.random() < 0.4:
            table = self.random_identifier()
            return table + "." + col
        return col

    # ----------- Expression and table reference generators -----------

    def random_expr(self, depth: int = 0) -> str:
        r = self.rand
        if depth >= self.max_expr_depth:
            if r.random() < 0.5:
                return self.random_literal()
            else:
                return self.random_column_ref()
        choice = r.random()
        if choice < 0.35:
            # Binary operator
            left = self.random_expr(depth + 1)
            op = r.choice(self.binary_operators)
            if op == "BETWEEN":
                mid = self.random_expr(depth + 1)
                right = self.random_expr(depth + 1)
                return f"{left} BETWEEN {mid} AND {right}"
            elif op == "IN":
                if r.random() < 0.4 and depth < self.max_expr_depth:
                    # IN (subquery)
                    sub = self.gen_select(depth + 1, terminate=False)
                    return f"{left} IN ({sub})"
                n = r.randint(1, 5)
                values = ", ".join(self.random_expr(depth + 1) for _ in range(n))
                return f"{left} IN ({values})"
            elif op in ("AND", "OR"):
                right = self.random_expr(depth + 1)
                return f"({left} {op} {right})"
            else:
                right = self.random_expr(depth + 1)
                return f"{left} {op} {right}"
        elif choice < 0.55:
            # Unary operator
            op = r.choice(["NOT", "+", "-", "~"])
            inner = self.random_expr(depth + 1)
            if op == "NOT":
                return f"NOT {inner}"
            else:
                return f"{op}{inner}"
        elif choice < 0.8:
            # Function call
            func = r.choice(self.functions)
            if func in self.zero_arg_functions and r.random() < 0.7:
                arg_str = ""
            else:
                if func == "COUNT" and r.random() < 0.3:
                    arg_str = "*"
                else:
                    n_args = r.randint(1, 3)
                    args = [self.random_expr(depth + 1) for _ in range(n_args)]
                    arg_str = ", ".join(args)
            return f"{func}({arg_str})"
        else:
            # Parenthesized or CASE
            if r.random() < 0.5:
                return "(" + self.random_expr(depth + 1) + ")"
            else:
                base = self.random_expr(depth + 1)
                when1 = self.random_expr(depth + 1)
                then1 = self.random_expr(depth + 1)
                else_expr = self.random_expr(depth + 1)
                return f"CASE {base} WHEN {when1} THEN {then1} ELSE {else_expr} END"

    def random_table_ref(self, depth: int = 0) -> str:
        r = self.rand
        if depth >= 2 or r.random() < 0.4:
            name = self.random_identifier()
            alias = ""
            if r.random() < 0.4:
                alias = " AS " + self.random_identifier()
            return name + alias
        left = self.random_table_ref(depth + 1)
        join_type = r.choice([
            "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN",
            "LEFT OUTER JOIN", "CROSS JOIN"
        ])
        right = self.random_table_ref(depth + 1)
        on_clause = ""
        if r.random() < 0.8:
            on_expr = self.random_expr()
            on_clause = " ON " + on_expr
        return f"{left} {join_type} {right}{on_clause}"

    # ----------- Statement generators -----------

    def gen_select(self, depth: int = 0, terminate: bool = True) -> str:
        r = self.rand
        distinct = "DISTINCT " if r.random() < 0.3 else ""
        # Select list
        if r.random() < 0.2:
            columns = "*"
        else:
            n_cols = r.randint(1, 5)
            col_exprs: List[str] = []
            for _ in range(n_cols):
                expr = self.random_expr()
                if r.random() < 0.4:
                    alias = self.random_identifier()
                    expr = f"{expr} AS {alias}"
                col_exprs.append(expr)
            columns = ", ".join(col_exprs)
        # FROM clause
        from_clause = ""
        if r.random() < 0.9:
            if depth < self.max_select_depth and r.random() < 0.25:
                sub = self.gen_select(depth + 1, terminate=False)
                table = f"({sub}) AS {self.random_identifier()}"
            else:
                table = self.random_table_ref()
            from_clause = " FROM " + table
        # WHERE
        where_clause = ""
        if r.random() < 0.7:
            where_clause = " WHERE " + self.random_expr()
        # GROUP BY / HAVING
        group_by = ""
        if r.random() < 0.4:
            n = r.randint(1, 3)
            cols = ", ".join(self.random_column_ref() for _ in range(n))
            group_by = " GROUP BY " + cols
            if r.random() < 0.5:
                group_by += " HAVING " + self.random_expr()
        # ORDER BY
        order_by = ""
        if r.random() < 0.6:
            n = r.randint(1, 3)
            terms: List[str] = []
            for _ in range(n):
                term = self.random_expr()
                if r.random() < 0.7:
                    term += " " + r.choice(["ASC", "DESC"])
                terms.append(term)
            order_by = " ORDER BY " + ", ".join(terms)
        # LIMIT / OFFSET
        limit_clause = ""
        if r.random() < 0.5:
            limit = self.rand.randint(0, 1000)
            limit_clause = " LIMIT " + str(limit)
            if r.random() < 0.5:
                offset = self.rand.randint(0, 1000)
                if r.random() < 0.5:
                    limit_clause += " OFFSET " + str(offset)
                else:
                    limit_clause += ", " + str(offset)
        # Set operations
        union_clause = ""
        if depth < self.max_select_depth and r.random() < 0.3:
            right = self.gen_select(depth + 1, terminate=False)
            op = r.choice(["UNION", "UNION ALL", "INTERSECT", "EXCEPT"])
            union_clause = f" {op} {right}"
        stmt = f"SELECT {distinct}{columns}{from_clause}{where_clause}{group_by}{order_by}{limit_clause}{union_clause}"
        if terminate and r.random() < 0.8:
            stmt += ";"
        return stmt

    def gen_insert(self) -> str:
        r = self.rand
        table = self.random_identifier()
        conflict_clause = ""
        if r.random() < 0.2:
            conflict_clause = " OR " + r.choice(["ROLLBACK", "ABORT", "REPLACE", "FAIL", "IGNORE"])
        column_list = ""
        if r.random() < 0.7:
            n_cols = r.randint(1, 6)
            cols = [self.random_identifier() for _ in range(n_cols)]
            column_list = " (" + ", ".join(cols) + ")"
        n_rows = r.randint(1, 4)
        rows: List[str] = []
        for _ in range(n_rows):
            n_vals = r.randint(1, 6)
            vals = [self.random_expr() for _ in range(n_vals)]
            rows.append("(" + ", ".join(vals) + ")")
        values_list = ", ".join(rows)
        stmt = f"INSERT{conflict_clause} INTO {table}{column_list} VALUES {values_list}"
        if r.random() < 0.8:
            stmt += ";"
        return stmt

    def gen_update(self) -> str:
        r = self.rand
        table = self.random_identifier()
        conflict_clause = ""
        if r.random() < 0.2:
            conflict_clause = " OR " + r.choice(["ROLLBACK", "ABORT", "REPLACE", "FAIL", "IGNORE"])
        n_sets = r.randint(1, 5)
        sets: List[str] = []
        for _ in range(n_sets):
            col = self.random_identifier()
            expr = self.random_expr()
            sets.append(f"{col} = {expr}")
        where_clause = ""
        if r.random() < 0.8:
            where_clause = " WHERE " + self.random_expr()
        stmt = f"UPDATE{conflict_clause} {table} SET " + ", ".join(sets) + where_clause
        if r.random() < 0.8:
            stmt += ";"
        return stmt

    def gen_delete(self) -> str:
        r = self.rand
        table = self.random_identifier()
        where_clause = ""
        if r.random() < 0.8:
            where_clause = " WHERE " + self.random_expr()
        stmt = f"DELETE FROM {table}{where_clause}"
        if r.random() < 0.8:
            stmt += ";"
        return stmt

    def gen_create_table(self) -> str:
        r = self.rand
        if_not_exists = " IF NOT EXISTS" if r.random() < 0.5 else ""
        table = self.random_identifier()
        n_cols = r.randint(1, 8)
        col_defs: List[str] = []
        for _ in range(n_cols):
            name = self.random_identifier()
            dtype = r.choice(self.data_types)
            parts: List[str] = [name, dtype]
            if r.random() < 0.5:
                parts.append("NOT NULL")
            if r.random() < 0.3:
                parts.append("UNIQUE")
            if r.random() < 0.25:
                parts.append("PRIMARY KEY")
            if r.random() < 0.2:
                parts.append("DEFAULT " + self.random_literal())
            col_defs.append(" ".join(parts))
        table_constraints: List[str] = []
        if r.random() < 0.3 and n_cols >= 1:
            n = r.randint(1, min(3, n_cols))
            cols = [self.random_identifier() for _ in range(n)]
            table_constraints.append("PRIMARY KEY (" + ", ".join(cols) + ")")
        all_parts = col_defs + table_constraints
        stmt = f"CREATE TABLE{if_not_exists} {table} (" + ", ".join(all_parts) + ")"
        if r.random() < 0.8:
            stmt += ";"
        return stmt

    def gen_alter_table(self) -> str:
        r = self.rand
        table = self.random_identifier()
        kind = r.randint(0, 2)
        if kind == 0:
            new_col = self.random_identifier()
            dtype = r.choice(self.data_types)
            stmt = f"ALTER TABLE {table} ADD COLUMN {new_col} {dtype}"
        elif kind == 1:
            new_name = self.random_identifier()
            stmt = f"ALTER TABLE {table} RENAME TO {new_name}"
        else:
            old_col = self.random_identifier()
            new_col = self.random_identifier()
            stmt = f"ALTER TABLE {table} RENAME COLUMN {old_col} TO {new_col}"
        if r.random() < 0.8:
            stmt += ";"
        return stmt

    def gen_drop_table(self) -> str:
        r = self.rand
        if_exists = " IF EXISTS" if r.random() < 0.5 else ""
        table = self.random_identifier()
        stmt = f"DROP TABLE{if_exists} {table}"
        if r.random() < 0.8:
            stmt += ";"
        return stmt

    def gen_create_index(self) -> str:
        r = self.rand
        unique = " UNIQUE" if r.random() < 0.4 else ""
        if_not_exists = " IF NOT EXISTS" if r.random() < 0.5 else ""
        index = self.random_identifier()
        table = self.random_identifier()
        n_cols = r.randint(1, 4)
        cols = [self.random_identifier() for _ in range(n_cols)]
        where_clause = ""
        if r.random() < 0.3:
            where_clause = " WHERE " + self.random_expr()
        stmt = (
            f"CREATE{unique} INDEX{if_not_exists} {index} ON {table} ("
            + ", ".join(cols)
            + ")"
            + where_clause
        )
        if r.random() < 0.8:
            stmt += ";"
        return stmt

    def gen_with_select(self) -> str:
        r = self.rand
        n_ctes = r.randint(1, 3)
        ctes: List[str] = []
        for _ in range(n_ctes):
            name = self.random_identifier()
            n_cols = r.randint(0, 3)
            if n_cols:
                cols = "(" + ", ".join(self.random_identifier() for _ in range(n_cols)) + ")"
            else:
                cols = ""
            sub = self.gen_select(depth=1, terminate=False)
            ctes.append(f"{name}{cols} AS ({sub})")
        recursive_kw = "RECURSIVE " if r.random() < 0.3 else ""
        main = self.gen_select(depth=1, terminate=False)
        stmt = f"WITH {recursive_kw}" + ", ".join(ctes) + " " + main
        if not stmt.strip().endswith(";") and r.random() < 0.8:
            stmt += ";"
        return stmt

    def gen_transaction_stmt(self) -> str:
        r = self.rand
        kind = r.randint(0, 4)
        if kind == 0:
            stmt = "BEGIN"
            if r.random() < 0.5:
                stmt += " TRANSACTION"
            if r.random() < 0.3:
                stmt += " " + r.choice(["DEFERRED", "IMMEDIATE", "EXCLUSIVE"])
        elif kind == 1:
            stmt = "COMMIT"
        elif kind == 2:
            stmt = "ROLLBACK"
        elif kind == 3:
            name = self.random_identifier()
            stmt = "SAVEPOINT " + name
        else:
            name = self.random_identifier()
            stmt = "RELEASE " + name
        if r.random() < 0.8:
            stmt += ";"
        return stmt

    # ----------- Mutation and random-gibberish generators -----------

    def generate_random_gibberish(self) -> str:
        r = self.rand
        length = r.randint(1, 20)
        tokens: List[str] = []
        for _ in range(length):
            p = r.random()
            if self.all_keywords and p < 0.4:
                tokens.append(r.choice(self.all_keywords))
            elif p < 0.7:
                tokens.append(self.random_identifier())
            elif p < 0.9:
                tokens.append(self.random_literal())
            else:
                tokens.append(r.choice([",", "(", ")", ";", ".", "*", "+", "-", "/"]))
        separators = [" ", " ", " ", "\\n", "\\t", ", ", " , "]
        parts: List[str] = []
        for i, tok in enumerate(tokens):
            parts.append(tok)
            if i != len(tokens) - 1:
                parts.append(r.choice(separators))
        s = "".join(parts)
        if r.random() < 0.5:
            s += ";"
        return s

    def mutate_statement(self, s: str) -> str:
        r = self.rand
        if not s:
            return s
        op = r.randint(0, 4)
        if op == 0:
            # Insert random character
            pos = r.randint(0, len(s))
            ch = r.choice(self.mutation_chars)
            return s[:pos] + ch + s[pos:]
        elif op == 1:
            # Delete a span
            if len(s) <= 1:
                return s
            start = r.randint(0, len(s) - 1)
            end = min(len(s), start + r.randint(1, 4))
            return s[:start] + s[end:]
        elif op == 2:
            # Replace a span with random characters
            start = r.randint(0, len(s) - 1)
            end = min(len(s), start + r.randint(1, 4))
            insert_len = r.randint(1, 4)
            insert = "".join(r.choice(self.mutation_chars) for _ in range(insert_len))
            return s[:start] + insert + s[end:]
        elif op == 3:
            # Duplicate a substring
            start = r.randint(0, len(s) - 1)
            end = min(len(s), start + r.randint(1, 6))
            sub = s[start:end]
            pos = r.randint(0, len(s))
            return s[:pos] + sub + s[pos:]
        else:
            # Shuffle whitespace-separated tokens
            parts = re.split(r"(\\s+)", s)
            if len(parts) < 4:
                return s
            i = r.randint(0, len(parts) - 2)
            j = r.randint(0, len(parts) - 2)
            parts[i], parts[j] = parts[j], parts[i]
            return "".join(parts)

    def generate_structured_statement(self) -> str:
        r = self.rand
        generators = [
            self.gen_select,
            self.gen_insert,
            self.gen_update,
            self.gen_delete,
            self.gen_create_table,
            self.gen_alter_table,
            self.gen_drop_table,
            self.gen_create_index,
            self.gen_with_select,
            self.gen_transaction_stmt,
        ]
        gen = r.choice(generators)
        try:
            return gen()
        except Exception:
            # Ensure the fuzzer itself never fails
            return "SELECT 1;"

    def generate_batch(self, max_size: int) -> List[str]:
        r = self.rand
        batch: List[str] = []
        for _ in range(max_size):
            if self._time_remaining() <= 0.0:
                break
            p = r.random()
            if p < 0.7:
                stmt = self.generate_structured_statement()
            elif self.corpus and p < 0.9:
                base = r.choice(self.corpus)
                stmt = self.mutate_statement(base)
            else:
                stmt = self.generate_random_gibberish()
            batch.append(stmt)
            self.total_statements += 1
            # Maintain a capped corpus
            if len(self.corpus) < self.max_corpus_size:
                if r.random() < 0.5:
                    self.corpus.append(stmt)
            else:
                if r.random() < 0.1:
                    idx = r.randint(0, len(self.corpus) - 1)
                    self.corpus[idx] = stmt
        return batch

    def run(self, parse_sql) -> None:
        # Main fuzzing loop: run until local time budget is exhausted
        batch_size = self.batch_size
        while self._time_remaining() > 0.0:
            batch = self.generate_batch(batch_size)
            if not batch:
                break
            t0 = time.perf_counter()
            parse_sql(batch)
            t1 = time.perf_counter()
            self.total_parse_sql_calls += 1
            elapsed = t1 - t0
            # Dynamically tune batch size to target moderate parse_sql call cost
            if elapsed < 0.05 and batch_size < self.max_batch_size:
                batch_size = min(self.max_batch_size, batch_size * 2)
            elif elapsed > 0.5 and batch_size > self.min_batch_size:
                batch_size = max(self.min_batch_size, batch_size // 2)
            self.batch_size = batch_size
        self.finished = True


_SQL_FUZZER = None

def fuzz(parse_sql):
    global _SQL_FUZZER
    if _SQL_FUZZER is None:
        _SQL_FUZZER = SQLFuzzer()
    if _SQL_FUZZER.finished:
        return False
    _SQL_FUZZER.run(parse_sql)
    # We perform all fuzzing work in a single call for efficiency.
    return False
""")

        code = header + rest_code
        return {"code": code}