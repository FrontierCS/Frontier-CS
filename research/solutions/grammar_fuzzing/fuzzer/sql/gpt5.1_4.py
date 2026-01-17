import os

class Solution:
    def solve(self, resources_path: str) -> dict:
        abs_path = os.path.abspath(resources_path)
        template = '''import os
import random
import time
import string
import re

RESOURCES_PATH = __RESOURCES_PATH_PLACEHOLDER__

class _FuzzerState:
    def __init__(self):
        self.initialized = False
        self.rng = random.Random()
        self.iteration = 0
        self.corpus = []
        self.max_corpus = 2000
        self.base_keywords = [
            'SELECT','INSERT','UPDATE','DELETE','FROM','WHERE','GROUP','BY','HAVING','ORDER',
            'LIMIT','OFFSET','JOIN','LEFT','RIGHT','FULL','OUTER','INNER','CROSS','ON','USING',
            'UNION','ALL','DISTINCT','INTO','VALUES','SET','AND','OR','NOT','NULL','IS','IN',
            'BETWEEN','LIKE','GLOB','REGEXP','AS','CASE','WHEN','THEN','ELSE','END','CREATE',
            'TABLE','VIEW','INDEX','UNIQUE','PRIMARY','KEY','FOREIGN','REFERENCES','CHECK',
            'DEFAULT','COLLATE','CONSTRAINT','DROP','ALTER','ADD','COLUMN','RENAME','TO',
            'CASCADE','RESTRICT','TRIGGER','BEFORE','AFTER','INSTEAD','OF','FOR','EACH','ROW',
            'BEGIN','TRANSACTION','COMMIT','ROLLBACK','SAVEPOINT','RELEASE','EXPLAIN','ANALYZE',
        ]
        self.base_functions = [
            'ABS','SUM','COUNT','AVG','MIN','MAX','COALESCE','IFNULL','LENGTH','UPPER','LOWER',
            'SUBSTR','ROUND','RANDOM','NOW','CURRENT_DATE','CURRENT_TIME','CURRENT_TIMESTAMP'
        ]
        self.base_types = [
            'INT','INTEGER','SMALLINT','BIGINT','REAL','DOUBLE','FLOAT','NUMERIC','DECIMAL',
            'CHAR','VARCHAR','TEXT','BLOB','BOOLEAN','DATE','TIME','TIMESTAMP'
        ]
        self.base_operators = [
            '+','-','*','/','%','=','!=','<>','<','>','<=','>=','||'
        ]
        self.tables = ['users','orders','products','t','u','v','accounts','logs','items']
        self.columns = [
            'id','user_id','order_id','product_id','name','email','status','created_at',
            'updated_at','price','quantity','amount','description','flag','category','type',
            'value','count','total','balance','age','level','score'
        ]
        self.grammar_keywords = set()
        self.grammar_functions = set()
        self.all_keywords = set(self.base_keywords)
        self.all_functions = set(self.base_functions)
        self.all_types = set(self.base_types)
        self.all_operators = set(self.base_operators)
        self.start_time = time.time()
        self.max_expr_depth = 3
        self.max_select_depth = 2

    def initialize(self):
        try:
            seed = int(time.time() * 1000) ^ os.getpid()
        except Exception:
            seed = int(time.time() * 1000)
        self.rng.seed(seed)
        self._load_grammar()
        self.all_keywords |= self.grammar_keywords
        self.all_functions |= self.grammar_functions
        self.all_keywords = list(self.all_keywords)
        self.all_functions = list(self.all_functions)
        self.all_types = list(self.all_types)
        self.all_operators = list(self.all_operators)
        self._init_seed_corpus()
        self.initialized = True

    def _load_grammar(self):
        if not RESOURCES_PATH:
            return
        path = os.path.join(RESOURCES_PATH, 'sql_grammar.txt')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception:
            return
        try:
            words = re.findall(r"[A-Z_][A-Z0-9_]*", text)
            self.grammar_keywords.update(words)
            sq = re.findall(r"'([^']+)'", text)
            for tok in sq:
                if re.fullmatch(r"[A-Z_][A-Z0-9_]*", tok):
                    self.grammar_keywords.add(tok)
                elif re.fullmatch(r"[<>=!]+", tok) or tok in (',','(',')',';','+','-','*','/','%','.'):
                    self.all_operators.add(tok)
        except Exception:
            return

    def _init_seed_corpus(self):
        seeds = [
            "SELECT 1",
            "SELECT id, name FROM users",
            "SELECT u.id, o.id FROM users u JOIN orders o ON u.id = o.user_id",
            "SELECT name, COUNT(*) FROM products GROUP BY name HAVING COUNT(*) > 1",
            "SELECT * FROM orders WHERE price > 100 AND status = 'PAID'",
            "INSERT INTO users (id, name, email) VALUES (1, 'alice', 'a@example.com')",
            "UPDATE users SET email = 'new@example.com' WHERE id = 1",
            "DELETE FROM orders WHERE created_at < '2020-01-01'",
            "CREATE TABLE t (id INT PRIMARY KEY, name VARCHAR(100) NOT NULL, price DECIMAL(10,2), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "ALTER TABLE t ADD COLUMN status VARCHAR(20)",
            "ALTER TABLE t DROP COLUMN status",
            "CREATE INDEX idx_t_id ON t(id)",
            "DROP INDEX idx_t_id",
            "DROP TABLE IF EXISTS t",
            "BEGIN TRANSACTION",
            "COMMIT",
            "ROLLBACK",
            "SELECT CASE WHEN price > 100 THEN 'expensive' ELSE 'cheap' END AS label FROM products",
            "SELECT id, SUM(amount) AS total FROM orders GROUP BY id ORDER BY total DESC LIMIT 10 OFFSET 5",
            "SELECT * FROM users WHERE name LIKE 'A%' OR email IS NULL",
            "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE amount > 100)",
            "SELECT DISTINCT status FROM orders",
        ]
        for s in seeds:
            self._add_to_corpus(s)

    def _add_to_corpus(self, stmt):
        if not stmt:
            return
        if len(self.corpus) < self.max_corpus:
            self.corpus.append(stmt)
        else:
            if self.rng.random() < 0.05:
                idx = self.rng.randint(0, self.max_corpus - 1)
                self.corpus[idx] = stmt

    def chance(self, p):
        return self.rng.random() < p

    def gen_identifier(self):
        roll = self.rng.random()
        if roll < 0.4 and self.columns:
            return self.rng.choice(self.columns)
        elif roll < 0.8 and self.tables:
            return self.rng.choice(self.tables)
        else:
            length = self.rng.randint(1, 10)
            first_chars = string.ascii_letters + '_'
            other_chars = first_chars + string.digits
            name_chars = [self.rng.choice(first_chars)]
            for _ in range(length - 1):
                name_chars.append(self.rng.choice(other_chars))
            name = "".join(name_chars)
            if self.chance(0.2):
                quote = self.rng.choice(['"', '`'])
                return quote + name + quote
            return name

    def gen_table_name(self):
        if self.chance(0.6) and self.tables:
            return self.rng.choice(self.tables)
        return self.gen_identifier()

    def gen_column_name(self):
        if self.chance(0.7) and self.columns:
            return self.rng.choice(self.columns)
        return self.gen_identifier()

    def gen_number_literal(self):
        if self.chance(0.5):
            return str(self.rng.randint(-100000, 100000))
        whole = self.rng.randint(-1000, 1000)
        frac = self.rng.randint(0, 9999)
        return f"{whole}.{frac}"

    def gen_string_literal(self):
        length = self.rng.randint(0, 10)
        chars = []
        alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-"
        for _ in range(length):
            chars.append(self.rng.choice(alphabet))
        s = "".join(chars)
        s = s.replace("'", "''")
        return "'" + s + "'"

    def gen_literal(self):
        r = self.rng.random()
        if r < 0.4:
            return self.gen_number_literal()
        elif r < 0.8:
            return self.gen_string_literal()
        else:
            return self.rng.choice(['NULL', 'TRUE', 'FALSE', 'CURRENT_DATE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP'])

    def gen_type(self):
        base_types = self.all_types or self.base_types
        base = self.rng.choice(list(base_types))
        if base in ('CHAR','VARCHAR','VARBINARY') or self.chance(0.2):
            length = self.rng.randint(1, 255)
            return f"{base}({length})"
        if base in ('DECIMAL','NUMERIC') or self.chance(0.1):
            p = self.rng.randint(1, 18)
            s = self.rng.randint(0, min(6, p))
            return f"{base}({p},{s})"
        return base

    def gen_function_call_tokens(self, depth):
        funcs = self.all_functions or self.base_functions
        func = self.rng.choice(list(funcs))
        tokens = [func, '(']
        n_args = self.rng.randint(0, 3)
        for i in range(n_args):
            tokens.extend(self.gen_expression_tokens(depth + 1))
            if i != n_args - 1:
                tokens.append(',')
        tokens.append(')')
        return tokens

    def gen_simple_expression_tokens(self):
        r = self.rng.random()
        if r < 0.4:
            return [self.gen_column_name()]
        elif r < 0.8:
            return [self.gen_literal()]
        else:
            return [self.gen_identifier()]

    def gen_expression_tokens(self, depth=0):
        if depth >= self.max_expr_depth:
            return self.gen_simple_expression_tokens()
        r = self.rng.random()
        if r < 0.25:
            left = self.gen_expression_tokens(depth + 1)
            op = self.rng.choice(self.base_operators + ['AND','OR'])
            right = self.gen_expression_tokens(depth + 1)
            return left + [op] + right
        elif r < 0.45:
            return self.gen_function_call_tokens(depth + 1)
        elif r < 0.6:
            left = self.gen_expression_tokens(depth + 1)
            mode = self.rng.randint(0, 3)
            if mode == 0:
                op = self.rng.choice(['=','!=','<>','<','>','<=','>=','IS','IS NOT','LIKE','IN'])
                if op in ('IS','IS NOT'):
                    right = [self.rng.choice(['NULL', 'TRUE', 'FALSE'])]
                elif op == 'IN':
                    right = ['(']
                    n = self.rng.randint(1, 5)
                    for i in range(n):
                        right.extend(self.gen_expression_tokens(depth + 1))
                        if i != n - 1:
                            right.append(',')
                    right.append(')')
                else:
                    right = self.gen_expression_tokens(depth + 1)
                if ' ' in op:
                    op_tokens = op.split(' ')
                    return left + op_tokens + right
                return left + [op] + right
            elif mode == 1:
                expr1 = self.gen_expression_tokens(depth + 1)
                expr2 = self.gen_expression_tokens(depth + 1)
                return left + ['BETWEEN'] + expr1 + ['AND'] + expr2
            elif mode == 2:
                return left + ['IS', 'NULL']
            else:
                return left + ['LIKE', self.gen_string_literal()]
        elif r < 0.75:
            inner = self.gen_expression_tokens(depth + 1)
            return ['('] + inner + [')']
        elif r < 0.9:
            return self.gen_case_expression_tokens(depth + 1)
        else:
            return self.gen_simple_expression_tokens()

    def gen_case_expression_tokens(self, depth):
        tokens = ['CASE']
        n_when = self.rng.randint(1, 3)
        for _ in range(n_when):
            tokens.append('WHEN')
            tokens.extend(self.gen_expression_tokens(depth + 1))
            tokens.append('THEN')
            tokens.extend(self.gen_expression_tokens(depth + 1))
        if self.chance(0.5):
            tokens.append('ELSE')
            tokens.extend(self.gen_expression_tokens(depth + 1))
        tokens.append('END')
        return tokens

    def gen_select_list_tokens(self, depth):
        tokens = []
        n = self.rng.randint(1, 5)
        for i in range(n):
            if self.chance(0.1):
                tokens.append('*')
            else:
                tokens.extend(self.gen_expression_tokens(depth + 1))
                if self.chance(0.3):
                    if self.chance(0.5):
                        tokens.append('AS')
                    tokens.append(self.gen_identifier())
            if i != n - 1:
                tokens.append(',')
        return tokens

    def gen_table_ref_tokens(self, depth):
        tokens = [self.gen_table_name()]
        if self.chance(0.4):
            if self.chance(0.5):
                tokens.append('AS')
            tokens.append(self.gen_identifier())
        return tokens

    def gen_joined_table_tokens(self, depth):
        tokens = []
        tokens.extend(self.gen_table_ref_tokens(depth))
        n_joins = self.rng.randint(0, 3)
        for _ in range(n_joins):
            join_type = self.rng.choice([
                'JOIN','INNER JOIN','LEFT JOIN','LEFT OUTER JOIN','RIGHT JOIN','RIGHT OUTER JOIN',
                'FULL JOIN','FULL OUTER JOIN','CROSS JOIN'
            ])
            tokens.extend(join_type.split(' '))
            tokens.extend(self.gen_table_ref_tokens(depth))
            if self.chance(0.7):
                tokens.append('ON')
                tokens.extend(self.gen_expression_tokens(depth + 1))
            else:
                tokens.append('USING')
                tokens.append('(')
                ncols = self.rng.randint(1, 3)
                for i in range(ncols):
                    tokens.append(self.gen_column_name())
                    if i != ncols - 1:
                        tokens.append(',')
                tokens.append(')')
        return tokens

    def gen_order_by_tokens(self, depth):
        tokens = ['ORDER', 'BY']
        n = self.rng.randint(1, 3)
        for i in range(n):
            tokens.extend(self.gen_expression_tokens(depth + 1))
            if self.chance(0.5):
                tokens.append(self.rng.choice(['ASC','DESC']))
            if i != n - 1:
                tokens.append(',')
        return tokens

    def gen_group_by_tokens(self, depth):
        tokens = ['GROUP', 'BY']
        n = self.rng.randint(1, 3)
        for i in range(n):
            tokens.extend(self.gen_expression_tokens(depth + 1))
            if i != n - 1:
                tokens.append(',')
        return tokens

    def gen_select_tokens(self, depth=0):
        tokens = ['SELECT']
        if self.chance(0.2):
            tokens.append('DISTINCT')
        tokens.extend(self.gen_select_list_tokens(depth + 1))
        if self.chance(0.9):
            tokens.append('FROM')
            if self.chance(0.2) and depth < self.max_select_depth:
                tokens.append('(')
                tokens.extend(self.gen_select_tokens(depth + 1))
                tokens.append(')')
                if self.chance(0.5):
                    tokens.append('AS')
                tokens.append(self.gen_identifier())
            else:
                tokens.extend(self.gen_joined_table_tokens(depth + 1))
        if self.chance(0.7):
            tokens.append('WHERE')
            tokens.extend(self.gen_expression_tokens(depth + 1))
        if self.chance(0.4):
            tokens.extend(self.gen_group_by_tokens(depth + 1))
            if self.chance(0.5):
                tokens.append('HAVING')
                tokens.extend(self.gen_expression_tokens(depth + 1))
        if depth < self.max_select_depth and self.chance(0.3):
            op = self.rng.choice(['UNION','UNION ALL','INTERSECT','EXCEPT'])
            tokens.extend(op.split(' '))
            tokens.extend(self.gen_select_tokens(depth + 1))
        if self.chance(0.5):
            tokens.extend(self.gen_order_by_tokens(depth + 1))
        if self.chance(0.5):
            tokens.append('LIMIT')
            tokens.append(self.gen_number_literal())
            if self.chance(0.5):
                tokens.append('OFFSET')
                tokens.append(self.gen_number_literal())
        return tokens

    def gen_insert_tokens(self):
        tokens = ['INSERT']
        if self.chance(0.2):
            tokens.append('OR')
            tokens.append(self.rng.choice(['ROLLBACK','ABORT','REPLACE','FAIL','IGNORE']))
        tokens.append('INTO')
        tokens.append(self.gen_table_name())
        if self.chance(0.7):
            tokens.append('(')
            ncols = self.rng.randint(1, 5)
            for i in range(ncols):
                tokens.append(self.gen_column_name())
                if i != ncols - 1:
                    tokens.append(',')
            tokens.append(')')
        if self.chance(0.7):
            tokens.append('VALUES')
            nrows = self.rng.randint(1, 3)
            for r in range(nrows):
                tokens.append('(')
                nvals = self.rng.randint(1, 5)
                for i in range(nvals):
                    tokens.extend(self.gen_expression_tokens())
                    if i != nvals - 1:
                        tokens.append(',')
                tokens.append(')')
                if r != nrows - 1:
                    tokens.append(',')
        else:
            tokens.extend(self.gen_select_tokens())
        return tokens

    def gen_update_tokens(self):
        tokens = ['UPDATE']
        tokens.append(self.gen_table_name())
        tokens.append('SET')
        n = self.rng.randint(1, 5)
        for i in range(n):
            tokens.append(self.gen_column_name())
            tokens.append('=')
            tokens.extend(self.gen_expression_tokens())
            if i != n - 1:
                tokens.append(',')
        if self.chance(0.7):
            tokens.append('WHERE')
            tokens.extend(self.gen_expression_tokens())
        return tokens

    def gen_delete_tokens(self):
        tokens = ['DELETE']
        if self.chance(0.3):
            tokens.append('FROM')
        tokens.append(self.gen_table_name())
        if self.chance(0.7):
            tokens.append('WHERE')
            tokens.extend(self.gen_expression_tokens())
        return tokens

    def gen_column_def_tokens(self):
        tokens = [self.gen_column_name(), self.gen_type()]
        if self.chance(0.3):
            tokens.append('PRIMARY')
            tokens.append('KEY')
        if self.chance(0.3):
            tokens.append('NOT')
            tokens.append('NULL')
        if self.chance(0.3):
            tokens.append('UNIQUE')
        if self.chance(0.3):
            tokens.append('DEFAULT')
            tokens.extend(self.gen_expression_tokens())
        if self.chance(0.2):
            tokens.append('CHECK')
            tokens.append('(')
            tokens.extend(self.gen_expression_tokens())
            tokens.append(')')
        return tokens

    def gen_create_table_tokens(self):
        tokens = ['CREATE']
        if self.chance(0.3):
            tokens.append('TEMP')
        tokens.append('TABLE')
        if self.chance(0.3):
            tokens.append('IF')
            tokens.append('NOT')
            tokens.append('EXISTS')
        tokens.append(self.gen_table_name())
        tokens.append('(')
        ncols = self.rng.randint(1, 6)
        for i in range(ncols):
            tokens.extend(self.gen_column_def_tokens())
            if i != ncols - 1 or self.chance(0.3):
                tokens.append(',')
        if self.chance(0.3):
            tokens.append('PRIMARY')
            tokens.append('KEY')
            tokens.append('(')
            npk = self.rng.randint(1, min(3, ncols))
            for i in range(npk):
                tokens.append(self.gen_column_name())
                if i != npk - 1:
                    tokens.append(',')
            tokens.append(')')
        tokens.append(')')
        return tokens

    def gen_alter_table_tokens(self):
        tokens = ['ALTER', 'TABLE', self.gen_table_name()]
        action = self.rng.randint(0, 3)
        if action == 0:
            tokens.append('ADD')
            if self.chance(0.5):
                tokens.append('COLUMN')
            tokens.extend(self.gen_column_def_tokens())
        elif action == 1:
            tokens.append('DROP')
            if self.chance(0.5):
                tokens.append('COLUMN')
            tokens.append(self.gen_column_name())
        elif action == 2:
            tokens.append('RENAME')
            if self.chance(0.5):
                tokens.append('COLUMN')
            tokens.append(self.gen_column_name())
            tokens.append('TO')
            tokens.append(self.gen_column_name())
        else:
            tokens.append('RENAME')
            tokens.append('TO')
            tokens.append(self.gen_table_name())
        return tokens

    def gen_drop_tokens(self):
        obj = self.rng.choice(['TABLE','VIEW','INDEX'])
        tokens = ['DROP', obj]
        if self.chance(0.3):
            tokens.append('IF')
            tokens.append('EXISTS')
        tokens.append(self.gen_identifier())
        return tokens

    def gen_create_index_tokens(self):
        tokens = ['CREATE']
        if self.chance(0.3):
            tokens.append('UNIQUE')
        tokens.append('INDEX')
        if self.chance(0.3):
            tokens.append('IF')
            tokens.append('NOT')
            tokens.append('EXISTS')
        tokens.append(self.gen_identifier())
        tokens.append('ON')
        tokens.append(self.gen_table_name())
        tokens.append('(')
        ncols = self.rng.randint(1, 4)
        for i in range(ncols):
            tokens.append(self.gen_column_name())
            if self.chance(0.3):
                tokens.append(self.rng.choice(['ASC','DESC']))
            if i != ncols - 1:
                tokens.append(',')
        tokens.append(')')
        return tokens

    def gen_transaction_tokens(self):
        kind = self.rng.randint(0, 3)
        if kind == 0:
            return ['BEGIN', 'TRANSACTION']
        elif kind == 1:
            return ['COMMIT']
        elif kind == 2:
            return ['ROLLBACK']
        else:
            return ['SAVEPOINT', self.gen_identifier()]

    def gen_random_statement_tokens(self):
        r = self.rng.random()
        if r < 0.45:
            return self.gen_select_tokens()
        elif r < 0.6:
            return self.gen_insert_tokens()
        elif r < 0.7:
            return self.gen_update_tokens()
        elif r < 0.8:
            return self.gen_delete_tokens()
        elif r < 0.87:
            return self.gen_create_table_tokens()
        elif r < 0.92:
            return self.gen_alter_table_tokens()
        elif r < 0.96:
            return self.gen_create_index_tokens()
        elif r < 0.99:
            return self.gen_drop_tokens()
        else:
            return self.gen_transaction_tokens()

    def gen_comment(self):
        style = self.rng.randint(0, 2)
        if style == 0:
            txt = "-- " + self.rng.choice(["comment", "todo", "note", "random"]) + "\n"
            return txt
        elif style == 1:
            txt = "/* " + self.rng.choice(["multi", "nested", "strange"]) + " */"
            return txt
        else:
            txt = "# " + self.rng.choice(["hash", "remark"]) + "\n"
            return txt

    def render_sql(self, tokens):
        parts = []
        n = len(tokens)
        for i, tok in enumerate(tokens):
            parts.append(tok)
            if i != n - 1:
                r = self.rng.random()
                if r < 0.05:
                    parts.append("\n")
                elif r < 0.1:
                    parts.append("\t")
                else:
                    parts.append(" ")
                if self.chance(0.03):
                    parts.append(self.gen_comment())
                    parts.append(" ")
        sql = "".join(parts)
        if self.chance(0.3):
            sql += ';'
        return sql

    def generate_from_grammar(self):
        if self.grammar_keywords:
            kw_list = list(self.grammar_keywords)
            n_kw = self.rng.randint(3, 8)
            random_keywords = [self.rng.choice(kw_list) for _ in range(n_kw)]
            tokens = ['SELECT', '*', 'FROM', self.gen_table_name()]
            if self.chance(0.8):
                tokens.append('WHERE')
                for i, kw in enumerate(random_keywords):
                    if i > 0:
                        tokens.append(self.rng.choice(['AND','OR']))
                    if self.chance(0.5):
                        tokens.append(kw)
                    else:
                        tokens.append("'" + kw + "'")
            return self.render_sql(tokens)
        return self.render_sql(self.gen_select_tokens())

    def generate_token_soup(self):
        tokens = []
        length = self.rng.randint(3, 40)
        all_keywords = self.all_keywords or self.base_keywords
        operators = list(self.all_operators) or self.base_operators
        for _ in range(length):
            r = self.rng.random()
            if r < 0.3:
                tokens.append(self.rng.choice(list(all_keywords)))
            elif r < 0.5:
                tokens.append(self.gen_identifier())
            elif r < 0.7:
                tokens.append(self.gen_literal())
            else:
                tokens.append(self.rng.choice(list(operators)))
        return self.render_sql(tokens)

    def _random_mutation_snippet(self):
        r = self.rng.random()
        if r < 0.3:
            kw_source = self.all_keywords or self.base_keywords
            return " " + self.rng.choice(list(kw_source)) + " "
        elif r < 0.5:
            op_source = self.all_operators or self.base_operators
            return " " + self.rng.choice(list(op_source)) + " "
        elif r < 0.7:
            return " " + self.gen_identifier() + " "
        elif r < 0.9:
            return " " + self.gen_literal() + " "
        else:
            return ","

    def mutate_statement(self, stmt):
        s = stmt
        max_len = 1500
        if len(s) > max_len:
            s = s[:max_len]
        n_ops = self.rng.randint(1, 4)
        for _ in range(n_ops):
            if not s:
                break
            op = self.rng.random()
            if op < 0.4:
                pos = self.rng.randint(0, len(s))
                insert = self._random_mutation_snippet()
                s = s[:pos] + insert + s[pos:]
            elif op < 0.7 and len(s) > 5:
                start = self.rng.randint(0, len(s) - 1)
                end = min(len(s), start + self.rng.randint(1, 10))
                s = s[:start] + s[end:]
            else:
                start = self.rng.randint(0, len(s) - 1)
                end = min(len(s), start + self.rng.randint(1, 8))
                s = s[:start] + self._random_mutation_snippet() + s[end:]
            if len(s) > max_len * 2:
                s = s[:max_len * 2]
        return s

    def generate_statement(self):
        r = self.rng.random()
        if self.corpus and r < 0.3:
            base = self.rng.choice(self.corpus)
            stmt = self.mutate_statement(base)
        elif r < 0.6:
            tokens = self.gen_random_statement_tokens()
            stmt = self.render_sql(tokens)
        elif r < 0.8:
            stmt = self.generate_from_grammar()
        else:
            stmt = self.generate_token_soup()
        self._add_to_corpus(stmt)
        return stmt

    def generate_batch(self):
        self.iteration += 1
        if self.iteration <= 5:
            batch_size = 300
        elif self.iteration <= 20:
            batch_size = 220
        elif self.iteration <= 100:
            batch_size = 150
        else:
            batch_size = 100
        elapsed = time.time() - self.start_time
        if elapsed > 40:
            batch_size = max(60, batch_size // 2)
        elif elapsed > 20:
            batch_size = int(batch_size * 0.8)
        statements = [self.generate_statement() for _ in range(batch_size)]
        return statements

_state = _FuzzerState()

def fuzz(parse_sql):
    if not _state.initialized:
        _state.initialize()
    stmts = _state.generate_batch()
    parse_sql(stmts)
    return True
'''
        code = template.replace('__RESOURCES_PATH_PLACEHOLDER__', repr(abs_path))
        return {"code": code}