import os
import random
import re
import string
import time

class Solution:
    def solve(self, resources_path: str) -> dict:
        code = r'''
import random
import time
import re
import string

# Lightweight utilities
def _chance(rng, p):
    return rng.random() < p

def _rand_range(rng, a, b):
    return rng.randint(a, b)

def _weighted_choice(rng, items):
    total = sum(w for _, w in items)
    r = rng.uniform(0, total)
    upto = 0.0
    for item, weight in items:
        if upto + weight >= r:
            return item
        upto += weight
    return items[-1][0]

def _maybe_semicolon(rng):
    return ';' if _chance(rng, 0.5) else ''

class SQLFuzzer:
    def __init__(self):
        seed = int(time.time() * 1000000) ^ (id(self) << 1)
        self.rng = random.Random(seed)
        self.start_time = None
        self.parse_calls = 0
        self.max_calls = 8  # Few large batches for efficiency bonus
        self.last_duration = 0.0
        self.target_duration = 7.0  # Aim per parse_sql call duration
        self.base_batch = 900  # Initial batch size; adaptive
        self.batch_min = 300
        self.batch_max = 2400
        self.corpus = []
        self.corpus_limit = 4000
        self.generated_count = 0

        # Names and tokens
        self.base_tables = [
            'users','orders','products','customers','employees','accounts','logs','items',
            'transactions','sessions','events','messages','notes','tags','reviews',
            't','tbl','t1','t2','t3','t4','t5','a','b','c','d','e',
        ]
        # Expand with a few numbered tables
        for i in range(6, 30):
            self.base_tables.append(f"t{i}")
        self.base_columns = [
            'id','name','price','quantity','qty','age','created_at','updated_at','email',
            'status','active','value','score','count','total','amount','category','flag',
            'address','phone','description','title','rating','level','balance','percent',
            'role','date','timestamp','note','comment','ref','code','state','zip','city',
        ]
        self.types = [
            'INT','INTEGER','SMALLINT','BIGINT','REAL','FLOAT','DOUBLE','DECIMAL(10,2)','NUMERIC(12,4)',
            'TEXT','VARCHAR(255)','CHAR(32)','BOOLEAN','DATE','TIME','TIMESTAMP','BLOB',
        ]
        self.collations = ['BINARY','NOCASE','RTRIM']
        self.func_fixed = {
            'ABS': (1,1), 'ROUND': (1,2), 'COALESCE': (2,5), 'LENGTH': (1,1), 'LOWER': (1,1),
            'UPPER': (1,1), 'SUBSTR': (2,3), 'SUBSTRING': (2,3), 'TRIM': (1,2), 'RANDOM': (0,0),
            'NOW': (0,0), 'DATE': (1,1), 'TIME': (1,1), 'DATETIME': (1,1), 'STRFTIME': (2,3),
            'PRINTF': (1,4), 'IFNULL': (2,2), 'NULLIF': (2,2),
            'MIN': (1,3), 'MAX': (1,3), 'AVG': (1,1), 'SUM': (1,1), 'COUNT': (0,1),
        }
        self.agg_funcs = ['COUNT','SUM','MIN','MAX','AVG']
        self.math_ops = ['+','-','*','/','%','||']
        self.comp_ops = ['=','!=','<>','>','<','>=','<=']
        self.logic_ops = ['AND','OR']
        self.like_ops = ['LIKE','NOT LIKE','ILIKE','GLOB']
        self.is_ops = ['IS NULL','IS NOT NULL','IS TRUE','IS FALSE','IS NOT TRUE','IS NOT FALSE']
        self.bit_ops = ['&','|','^']
        self.shift_ops = ['<<','>>']
        self.join_types = [
            'JOIN','INNER JOIN','LEFT JOIN','LEFT OUTER JOIN','RIGHT JOIN','RIGHT OUTER JOIN',
            'FULL JOIN','FULL OUTER JOIN','CROSS JOIN','NATURAL JOIN','NATURAL LEFT JOIN',
            'NATURAL RIGHT JOIN','NATURAL INNER JOIN'
        ]
        self.order_mods = ['ASC','DESC']
        self.nulls_mods = ['NULLS FIRST','NULLS LAST']
        self.set_ops = ['UNION','UNION ALL','INTERSECT','EXCEPT']
        self.trx_stmts = [
            'BEGIN', 'BEGIN TRANSACTION', 'COMMIT', 'COMMIT TRANSACTION', 'ROLLBACK',
            'SAVEPOINT sp1','RELEASE sp1','ROLLBACK TO sp1'
        ]
        self.misc_stmts = [
            'PRAGMA foreign_keys = ON', 'PRAGMA journal_mode = WAL', 'PRAGMA synchronous = OFF',
            'VACUUM', 'ANALYZE', 'EXPLAIN SELECT 1'
        ]
        self.keywords = set([
            'SELECT','FROM','WHERE','GROUP','BY','HAVING','ORDER','LIMIT','OFFSET','AS',
            'INSERT','INTO','VALUES','UPDATE','SET','DELETE','CREATE','TABLE','INDEX',
            'DROP','ALTER','ADD','COLUMN','CONSTRAINT','PRIMARY','KEY','FOREIGN','REFERENCES',
            'DEFAULT','UNIQUE','CHECK','NOT','NULL','TRUE','FALSE','WITH','RECURSIVE','UNION',
            'ALL','DISTINCT','JOIN','LEFT','RIGHT','FULL','OUTER','INNER','CROSS','NATURAL',
            'ON','USING','OR','AND','IN','BETWEEN','LIKE','IS','EXISTS','CASE','WHEN','THEN','ELSE','END'
        ])
        self._ident_counter = 0

    def _random_ident_base(self):
        self._ident_counter += 1
        prefix = self.rng.choice([
            'alpha','beta','gamma','delta','eps','zeta','eta','theta','iota','kappa',
            'tmp','aux','foo','bar','baz','qux','quux','corge','grault','garply',
            'waldo','fred','plugh','xyzzy','thud','col','fld','f','g','h',
        ])
        return f"{prefix}_{self._ident_counter}"

    def _quote_ident(self, name=None):
        if name is None:
            name = self._random_ident_base()
        style = self.rng.choice(['plain','double','backtick','bracket'])
        if style == 'plain':
            # Avoid keywords for plain identifiers
            n = name
            if n.upper() in self.keywords:
                n = n + '_x'
            return n
        elif style == 'double':
            return '"' + name.replace('"','""') + '"'
        elif style == 'backtick':
            return '`' + name.replace('`','``') + '`'
        else:
            return '[' + name.replace(']',']]') + ']'

    def _random_table(self):
        if _chance(self.rng, 0.3):
            # qualified
            schema = self._quote_ident(self.rng.choice(['main','temp','public','dbo','schema']))
            return f"{schema}.{self._quote_ident(self.rng.choice(self.base_tables))}"
        else:
            return self._quote_ident(self.rng.choice(self.base_tables))

    def _random_col(self):
        if _chance(self.rng, 0.3):
            t = self._quote_ident(self.rng.choice(self.base_tables))
            c = self._quote_ident(self.rng.choice(self.base_columns))
            return f"{t}.{c}"
        else:
            return self._quote_ident(self.rng.choice(self.base_columns))

    def _random_string_literal(self, max_len=24):
        length = _rand_range(self.rng, 0, max_len)
        chars = []
        alphabet = string.ascii_letters + string.digits + " _-./:@#,$[]{}|^~"
        for _ in range(length):
            chars.append(self.rng.choice(alphabet))
        s = ''.join(chars)
        # Escape single quotes by doubling
        s = s.replace("'", "''")
        if _chance(self.rng, 0.25):
            # Add edge-case sequences
            inserts = ["\n", "\t", "\\n", "\\x00", "''", " "]
            pos = _rand_range(self.rng, 0, len(s)) if len(s) > 0 else 0
            s = s[:pos] + self.rng.choice(inserts) + s[pos:]
            s = s.replace("'", "''")
        return "'" + s + "'"

    def _random_number_literal(self):
        if _chance(self.rng, 0.5):
            # int
            if _chance(self.rng, 0.2):
                val = self.rng.choice([0,1,-1,2**31-1,-2**31,2**63-1,-2**63+1,999999999, -999999999])
            else:
                val = self.rng.randint(-1000000, 1000000)
            return str(val)
        else:
            # float
            if _chance(self.rng, 0.2):
                val = self.rng.choice([0.0, -0.0, 1.0, -1.0, 1e10, -1e10, 3.14159, -2.71828])
            else:
                val = (self.rng.random() - 0.5) * (10 ** self.rng.randint(0, 6))
                if _chance(self.rng, 0.3):
                    # Exponent notation
                    return f"{val:.6e}"
            return str(val)

    def _random_literal(self, allow_special=True):
        pick = _weighted_choice(self.rng, [
            ('num', 4), ('str', 3), ('null', 1), ('bool', 1), ('special', 0.5 if allow_special else 0.0)
        ])
        if pick == 'num':
            return self._random_number_literal()
        elif pick == 'str':
            return self._random_string_literal()
        elif pick == 'null':
            return 'NULL'
        elif pick == 'bool':
            return self.rng.choice(['TRUE','FALSE'])
        else:
            # date/time-like
            samples = [
                "DATE '2020-01-01'",
                "TIME '12:34:56'",
                "TIMESTAMP '2020-01-01 12:34:56'",
                "X'0A0B0C'",
            ]
            return self.rng.choice(samples)

    def _random_func_call(self, depth):
        name = self.rng.choice(list(self.func_fixed.keys()))
        min_a, max_a = self.func_fixed[name]
        argc = _rand_range(self.rng, min_a, max_a)
        args = []
        for _ in range(argc):
            args.append(self._gen_expr(depth-1))
        args_s = ', '.join(args)
        return f"{name}({args_s})"

    def _random_case_expr(self, depth):
        branches = _rand_range(self.rng, 1, 3)
        parts = ['CASE']
        if _chance(self.rng, 0.3):
            # Simple CASE
            parts.append(self._gen_expr(depth-1))
        for _ in range(branches):
            parts.append('WHEN ' + self._gen_bool_expr(depth-1) + ' THEN ' + self._gen_expr(depth-1))
        if _chance(self.rng, 0.7):
            parts.append('ELSE ' + self._gen_expr(depth-1))
        parts.append('END')
        return ' '.join(parts)

    def _gen_in_list(self, depth):
        if _chance(self.rng, 0.3):
            # subquery
            sub = self._gen_select(top_level=False, depth=depth-1)
            return '(' + sub + ')'
        else:
            count = _rand_range(self.rng, 1, 5)
            return '(' + ', '.join([self._gen_expr(depth-1) for _ in range(count)]) + ')'

    def _gen_expr(self, depth=3):
        if depth <= 0:
            pick = _weighted_choice(self.rng, [('lit', 3), ('col', 3), ('func', 1), ('par', 1)])
        else:
            pick = _weighted_choice(self.rng, [
                ('lit', 2), ('col', 2), ('func', 2), ('bin', 3), ('un', 1.5),
                ('par', 1), ('case', 1), ('cast', 1), ('sub', 0.7),
                ('between', 0.8), ('in', 1.0), ('like', 0.8), ('collate', 0.5)
            ])

        if pick == 'lit':
            return self._random_literal()
        if pick == 'col':
            col = self._random_col()
            if _chance(self.rng, 0.2):
                # table.* or * only for columns
                if _chance(self.rng, 0.5):
                    return self._quote_ident(self.rng.choice(self.base_tables)) + '.*'
            return col
        if pick == 'func':
            return self._random_func_call(depth)
        if pick == 'bin':
            left = self._gen_expr(depth-1)
            right = self._gen_expr(depth-1)
            op = self.rng.choice(self.math_ops + self.bit_ops + self.shift_ops)
            return f"({left} {op} {right})"
        if pick == 'un':
            op = self.rng.choice(['-','+','~','NOT'])
            if op == 'NOT':
                return f"(NOT {self._gen_expr(depth-1)})"
            return f"({op}{self._gen_expr(depth-1)})"
        if pick == 'par':
            return f"({self._gen_expr(depth-1)})"
        if pick == 'case':
            return self._random_case_expr(depth)
        if pick == 'cast':
            typ = self.rng.choice(self.types)
            return f"CAST({self._gen_expr(depth-1)} AS {typ})"
        if pick == 'sub':
            return '(' + self._gen_select(top_level=False, depth=depth-1) + ')'
        if pick == 'between':
            a = self._gen_expr(depth-1)
            b = self._gen_expr(depth-1)
            c = self._gen_expr(depth-1)
            nots = ' NOT' if _chance(self.rng, 0.3) else ''
            return f"({a}{nots} BETWEEN {b} AND {c})"
        if pick == 'in':
            expr = self._gen_expr(depth-1)
            nots = ' NOT' if _chance(self.rng, 0.3) else ''
            return f"({expr}{nots} IN {self._gen_in_list(depth)})"
        if pick == 'like':
            expr = self._gen_expr(depth-1)
            op = self.rng.choice(self.like_ops)
            esc = ''
            if _chance(self.rng, 0.2):
                esc = " ESCAPE " + self._random_string_literal(1)
            return f"({expr} {op} {self._random_string_literal()}{esc})"
        if pick == 'collate':
            return f"({self._gen_expr(depth-1)} COLLATE {self.rng.choice(self.collations)})"
        # fallback
        return self._random_literal()

    def _gen_bool_expr(self, depth=3):
        if depth <= 0:
            # simplest: comparisons or literal booleans
            pick = self.rng.choice(['cmp','lit','isnull'])
        else:
            pick = _weighted_choice(self.rng, [('cmp', 3), ('logic', 2), ('not', 0.8), ('lit', 0.5), ('exists', 0.6), ('isnull', 1.0)])
        if pick == 'cmp':
            left = self._gen_expr(depth-1)
            right = self._gen_expr(depth-1)
            op = self.rng.choice(self.comp_ops)
            return f"({left} {op} {right})"
        if pick == 'logic':
            left = self._gen_bool_expr(depth-1)
            right = self._gen_bool_expr(depth-1)
            op = self.rng.choice(self.logic_ops)
            return f"({left} {op} {right})"
        if pick == 'not':
            return f"(NOT {self._gen_bool_expr(depth-1)})"
        if pick == 'exists':
            sub = self._gen_select(top_level=False, depth=depth-1)
            return f"(EXISTS ({sub}))"
        if pick == 'isnull':
            expr = self._gen_expr(depth-1)
            return f"({expr} {self.rng.choice(self.is_ops)})"
        # boolean literal
        return self.rng.choice(['TRUE','FALSE'])

    def _gen_select_list(self, depth):
        if _chance(self.rng, 0.15):
            # heavy star style
            items = []
            if _chance(self.rng, 0.7):
                items.append('*')
            tcount = _rand_range(self.rng, 0, 2)
            for _ in range(tcount):
                items.append(self._quote_ident(self.rng.choice(self.base_tables)) + '.*')
            if not items:
                items.append('*')
            return ', '.join(items)
        n = _rand_range(self.rng, 1, 5)
        items = []
        for _ in range(n):
            if _chance(self.rng, 0.1):
                it = self.rng.choice(self.agg_funcs) + '(' + (self._gen_expr(depth-1) if _chance(self.rng, 0.8) else '*') + ')'
            else:
                it = self._gen_expr(depth-1)
            if _chance(self.rng, 0.4):
                alias = self._quote_ident()
                if _chance(self.rng, 0.5):
                    it += ' AS ' + alias
                else:
                    it += ' ' + alias
            items.append(it)
        return ', '.join(items)

    def _gen_from_clause(self, depth):
        # Base table with optional alias
        base = self._random_table()
        if _chance(self.rng, 0.5):
            base += ' ' + self._quote_ident(self.rng.choice(['a','b','c','d','e','t']))
        parts = [base]
        # Optional joins
        jcount = _rand_range(self.rng, 0, 3)
        for _ in range(jcount):
            jt = self.rng.choice(self.join_types)
            tbl = self._random_table()
            jpart = f"{jt} {tbl}"
            # NATURAL joins don't need ON/USING
            if jt.startswith('NATURAL'):
                # No ON/USING; sometimes add alias
                if _chance(self.rng, 0.3):
                    jpart += ' ' + self._quote_ident()
                parts.append(jpart)
                continue
            if _chance(self.rng, 0.4):
                # USING clause
                cols = [self._quote_ident(self.rng.choice(self.base_columns)) for _ in range(_rand_range(self.rng, 1, 3))]
                jpart += ' USING (' + ', '.join(cols) + ')'
            else:
                cond = self._gen_bool_expr(depth-1)
                jpart += ' ON ' + cond
            parts.append(jpart)
        return ' '.join(parts)

    def _gen_order_by(self, depth):
        n = _rand_range(self.rng, 1, 3)
        items = []
        for _ in range(n):
            expr = self._gen_expr(depth-1)
            mod = ''
            if _chance(self.rng, 0.6):
                mod = ' ' + self.rng.choice(self.order_mods)
                if _chance(self.rng, 0.3):
                    mod += ' ' + self.rng.choice(self.nulls_mods)
            items.append(expr + mod)
        return ' ORDER BY ' + ', '.join(items)

    def _gen_group_by_having(self, depth):
        n = _rand_range(self.rng, 1, 3)
        items = []
        for _ in range(n):
            items.append(self._gen_expr(depth-1))
        s = ' GROUP BY ' + ', '.join(items)
        if _chance(self.rng, 0.5):
            s += ' HAVING ' + self._gen_bool_expr(depth-1)
        return s

    def _gen_with_clause(self, depth):
        ctes = []
        cte_count = _rand_range(self.rng, 1, 2)
        for _ in range(cte_count):
            name = self._quote_ident()
            cols = ''
            if _chance(self.rng, 0.4):
                ncols = _rand_range(self.rng, 1, 4)
                cols = ' (' + ', '.join([self._quote_ident(self.rng.choice(self.base_columns)) for _ in range(ncols)]) + ')'
            sub = self._gen_select(top_level=False, depth=depth-1)
            ctes.append(f"{name}{cols} AS ({sub})")
        rec = ' RECURSIVE' if _chance(self.rng, 0.25) else ''
        return f"WITH{rec} " + ', '.join(ctes) + ' '

    def _gen_set_op(self, left, depth):
        op = self.rng.choice(self.set_ops)
        right = self._gen_select(top_level=False, depth=depth-1)
        if _chance(self.rng, 0.5):
            # Parenthesize to stress parser
            left = '(' + left + ')'
        if _chance(self.rng, 0.5):
            right = '(' + right + ')'
        return f"{left} {op} {right}"

    def _gen_select(self, top_level=True, depth=3):
        parts = []
        if _chance(self.rng, 0.25) and depth > 0:
            parts.append(self._gen_with_clause(depth))
        parts.append('SELECT')
        if _chance(self.rng, 0.25):
            parts.append(' DISTINCT')
        elif _chance(self.rng, 0.1):
            parts.append(' ALL')
        parts.append(' ' + self._gen_select_list(depth))
        # FROM clause optional
        if _chance(self.rng, 0.8):
            parts.append(' FROM ' + self._gen_from_clause(depth))
        # WHERE
        if _chance(self.rng, 0.6):
            parts.append(' WHERE ' + self._gen_bool_expr(depth))
        # GROUP BY / HAVING
        if _chance(self.rng, 0.4):
            parts.append(self._gen_group_by_having(depth))
        # WINDOW skipped
        # ORDER BY
        if _chance(self.rng, 0.5):
            parts.append(self._gen_order_by(depth))
        # LIMIT OFFSET
        if _chance(self.rng, 0.6):
            limit = self.rng.choice(['ALL', str(_rand_range(self.rng, 0, 1000))])
            parts.append(' LIMIT ' + limit)
            if _chance(self.rng, 0.5):
                parts.append(' OFFSET ' + str(_rand_range(self.rng, 0, 1000)))
        sel = ''.join(parts)
        # Set operations
        if _chance(self.rng, 0.3) and depth > 0:
            sel = self._gen_set_op(sel, depth)
        if top_level and _chance(self.rng, 0.6):
            sel += _maybe_semicolon(self.rng)
        return sel

    def _gen_insert(self, depth=3):
        parts = ['INSERT']
        if _chance(self.rng, 0.25):
            parts.append(' OR ' + self.rng.choice(['REPLACE','IGNORE','ABORT','FAIL','ROLLBACK']))
        parts.append(' INTO ')
        table = self._random_table()
        parts.append(table)
        if _chance(self.rng, 0.6):
            ncols = _rand_range(self.rng, 0, 5)
            if ncols > 0:
                cols = ', '.join([self._quote_ident(self.rng.choice(self.base_columns)) for _ in range(ncols)])
                parts.append(' (' + cols + ')')
        if _chance(self.rng, 0.3):
            # INSERT ... SELECT ...
            parts.append(' ' + self._gen_select(top_level=False, depth=depth-1))
        elif _chance(self.rng, 0.1):
            parts.append(' DEFAULT VALUES')
        else:
            row_count = _rand_range(self.rng, 1, 3)
            rows = []
            for _ in range(row_count):
                val_count = _rand_range(self.rng, 1, 6)
                vals = ', '.join([self._gen_expr(depth-1) for _ in range(val_count)])
                rows.append('(' + vals + ')')
            parts.append(' VALUES ' + ', '.join(rows))
        if _chance(self.rng, 0.3):
            parts.append(' RETURNING ' + self._gen_select_list(depth-1))
        s = ''.join(parts) + _maybe_semicolon(self.rng)
        return s

    def _gen_update(self, depth=3):
        table = self._random_table()
        parts = ['UPDATE ' + table]
        if _chance(self.rng, 0.3):
            parts.append(' SET ')
        else:
            parts.append(' SET ')
        assign_count = _rand_range(self.rng, 1, 5)
        assigns = []
        for _ in range(assign_count):
            col = self._quote_ident(self.rng.choice(self.base_columns))
            val = self._gen_expr(depth-1)
            assigns.append(col + ' = ' + val)
        parts.append(', '.join(assigns))
        if _chance(self.rng, 0.5):
            parts.append(' WHERE ' + self._gen_bool_expr(depth-1))
        if _chance(self.rng, 0.2):
            parts.append(' RETURNING ' + self._gen_select_list(depth-1))
        return ''.join(parts) + _maybe_semicolon(self.rng)

    def _gen_delete(self, depth=3):
        parts = ['DELETE FROM ' + self._random_table()]
        if _chance(self.rng, 0.5):
            parts.append(' WHERE ' + self._gen_bool_expr(depth-1))
        if _chance(self.rng, 0.2):
            parts.append(' RETURNING ' + self._gen_select_list(depth-1))
        return ''.join(parts) + _maybe_semicolon(self.rng)

    def _gen_column_def(self):
        name = self._quote_ident(self.rng.choice(self.base_columns))
        typ = self.rng.choice(self.types)
        parts = [name + ' ' + typ]
        # Column constraints
        if _chance(self.rng, 0.3):
            parts.append(' PRIMARY KEY')
            if _chance(self.rng, 0.3):
                parts.append(' AUTOINCREMENT')
        if _chance(self.rng, 0.3):
            parts.append(' UNIQUE')
        if _chance(self.rng, 0.4):
            parts.append(' NOT NULL')
        if _chance(self.rng, 0.35):
            parts.append(' DEFAULT ' + self._random_literal())
        if _chance(self.rng, 0.2):
            parts.append(' CHECK (' + self._gen_bool_expr(2) + ')')
        if _chance(self.rng, 0.2):
            ref_tbl = self._random_table()
            ref_col = self._quote_ident(self.rng.choice(self.base_columns))
            parts.append(f' REFERENCES {ref_tbl}({ref_col})')
        return ''.join(parts)

    def _gen_table_constraint(self):
        pick = self.rng.choice(['pk','unique','check','fk'])
        if pick == 'pk':
            cols = ', '.join([self._quote_ident(self.rng.choice(self.base_columns)) for _ in range(_rand_range(self.rng,1,3))])
            return f'PRIMARY KEY ({cols})'
        if pick == 'unique':
            cols = ', '.join([self._quote_ident(self.rng.choice(self.base_columns)) for _ in range(_rand_range(self.rng,1,3))])
            return f'UNIQUE ({cols})'
        if pick == 'check':
            return 'CHECK (' + self._gen_bool_expr(2) + ')'
        # fk
        cols = ', '.join([self._quote_ident(self.rng.choice(self.base_columns)) for _ in range(_rand_range(self.rng,1,2))])
        ref_tbl = self._random_table()
        ref_cols = ', '.join([self._quote_ident(self.rng.choice(self.base_columns)) for _ in range(_rand_range(self.rng,1,2))])
        on = ''
        if _chance(self.rng, 0.3):
            on = ' ON DELETE ' + self.rng.choice(['CASCADE','SET NULL','RESTRICT','NO ACTION'])
        return f'FOREIGN KEY ({cols}) REFERENCES {ref_tbl}({ref_cols}){on}'

    def _gen_create_table(self, depth=3):
        parts = ['CREATE']
        if _chance(self.rng, 0.15):
            parts.append(' TEMP')
        parts.append(' TABLE')
        if _chance(self.rng, 0.3):
            parts.append(' IF NOT EXISTS')
        name = self._random_table()
        parts.append(' ' + name)
        col_count = _rand_range(self.rng, 1, 6)
        col_defs = [self._gen_column_def() for _ in range(col_count)]
        if _chance(self.rng, 0.4):
            tc_count = _rand_range(self.rng, 1, 2)
            for _ in range(tc_count):
                col_defs.append(self._gen_table_constraint())
        parts.append(' (' + ', '.join(col_defs) + ')')
        if _chance(self.rng, 0.2):
            parts.append(' WITHOUT ROWID')
        return ''.join(parts) + _maybe_semicolon(self.rng)

    def _gen_alter_table(self):
        tbl = self._random_table()
        pick = self.rng.choice(['addcol','dropcol','renamecol','renametable','addconstraint','dropconstraint'])
        if pick == 'addcol':
            return f"ALTER TABLE {tbl} ADD COLUMN {self._gen_column_def()}" + _maybe_semicolon(self.rng)
        if pick == 'dropcol':
            return f"ALTER TABLE {tbl} DROP COLUMN {self._quote_ident(self.rng.choice(self.base_columns))}" + _maybe_semicolon(self.rng)
        if pick == 'renamecol':
            return f"ALTER TABLE {tbl} RENAME COLUMN {self._quote_ident()} TO {self._quote_ident()}" + _maybe_semicolon(self.rng)
        if pick == 'renametable':
            return f"ALTER TABLE {tbl} RENAME TO {self._quote_ident()}" + _maybe_semicolon(self.rng)
        if pick == 'addconstraint':
            return f"ALTER TABLE {tbl} ADD CONSTRAINT {self._quote_ident()} {self._gen_table_constraint()}" + _maybe_semicolon(self.rng)
        # drop constraint
        return f"ALTER TABLE {tbl} DROP CONSTRAINT {self._quote_ident()}" + _maybe_semicolon(self.rng)

    def _gen_drop(self):
        pick = self.rng.choice(['table','index','view'])
        if pick == 'table':
            s = 'DROP TABLE'
        elif pick == 'index':
            s = 'DROP INDEX'
        else:
            s = 'DROP VIEW'
        if _chance(self.rng, 0.4):
            s += ' IF EXISTS'
        s += ' ' + self._random_table()
        if _chance(self.rng, 0.3):
            s += ' ' + self.rng.choice(['CASCADE','RESTRICT'])
        return s + _maybe_semicolon(self.rng)

    def _gen_create_index(self):
        parts = ['CREATE']
        if _chance(self.rng, 0.3):
            parts.append(' UNIQUE')
        parts.append(' INDEX')
        if _chance(self.rng, 0.3):
            parts.append(' IF NOT EXISTS')
        idxname = self._quote_ident('idx_' + self._random_ident_base())
        parts.append(' ' + idxname + ' ON ')
        table = self._random_table()
        parts.append(table)
        n = _rand_range(self.rng, 1, 4)
        cols = []
        for _ in range(n):
            col = self._quote_ident(self.rng.choice(self.base_columns))
            mod = ''
            if _chance(self.rng, 0.5):
                mod = ' ' + self.rng.choice(self.order_mods)
            cols.append(col + mod)
        parts.append(' (' + ', '.join(cols) + ')')
        if _chance(self.rng, 0.25):
            parts.append(' WHERE ' + self._gen_bool_expr(2))
        return ''.join(parts) + _maybe_semicolon(self.rng)

    def _gen_create_view(self, depth=3):
        parts = ['CREATE']
        if _chance(self.rng, 0.1):
            parts.append(' TEMP')
        parts.append(' VIEW')
        if _chance(self.rng, 0.3):
            parts.append(' IF NOT EXISTS')
        name = self._random_table()
        parts.append(' ' + name + ' AS ')
        parts.append(self._gen_select(top_level=False, depth=depth))
        return ''.join(parts) + _maybe_semicolon(self.rng)

    def _gen_misc(self):
        # Transaction or PRAGMA or EXPLAIN variants
        if _chance(self.rng, 0.5):
            return self.rng.choice(self.trx_stmts) + _maybe_semicolon(self.rng)
        else:
            return self.rng.choice(self.misc_stmts) + _maybe_semicolon(self.rng)

    def _inject_comments(self, sql):
        # Inject a few comments at random whitespace positions
        tokens = re.split(r'(\s+)', sql)
        if len(tokens) < 3:
            return sql
        comment_types = [
            lambda: '/*' + self._random_comment_text() + '*/',
            lambda: '-- ' + self._random_comment_text() + '\n',
        ]
        # We'll inject up to 2 comments
        injections = _rand_range(self.rng, 0, 2)
        for _ in range(injections):
            idxs = [i for i, t in enumerate(tokens) if t.strip() == '' and len(t) > 0]
            if not idxs:
                break
            i = self.rng.choice(idxs)
            tokens[i] = tokens[i] + comment_types[_rand_range(self.rng, 0, 1)]()
        return ''.join(tokens)

    def _random_comment_text(self):
        l = _rand_range(self.rng, 0, 20)
        alphabet = string.ascii_letters + string.digits + " _-./:@#,$[]{}|^~"
        s = ''.join(self.rng.choice(alphabet) for _ in range(l))
        s = s.replace('*/','* /')  # avoid ending block comment prematurely
        return s

    def _mutate_sql(self, sql):
        # Simple text-based mutator with heuristic tweaks
        s = sql

        # Random case flip
        if _chance(self.rng, 0.3):
            chars = []
            for ch in s:
                if ch.isalpha() and _chance(self.rng, 0.2):
                    if ch.islower():
                        chars.append(ch.upper())
                    else:
                        chars.append(ch.lower())
                else:
                    chars.append(ch)
            s = ''.join(chars)

        # Inject comments
        if _chance(self.rng, 0.35):
            s = self._inject_comments(s)

        # Replace some operators/keywords with variants
        replacements = [
            (r'\bJOIN\b', self.rng.choice(['INNER JOIN','LEFT JOIN','RIGHT JOIN','CROSS JOIN'])),
            (r'\bWHERE\b', self.rng.choice(['WHERE','WHERE NOT','WHERE'])),

            (r'\bORDER\s+BY\b', self.rng.choice(['ORDER BY','ORDER    BY'])),
            (r'\bGROUP\s+BY\b', self.rng.choice(['GROUP BY','GROUP    BY'])),
            (r'=', self.rng.choice(['=', '==', ' = '])),
            (r'\bIS\s+NOT\s+NULL\b', self.rng.choice(['IS NOT NULL','IS    NOT     NULL'])),
        ]
        if _chance(self.rng, 0.4):
            pat, rep = self.rng.choice(replacements)
            s = re.sub(pat, rep, s)

        # Alter literals slightly
        if _chance(self.rng, 0.3):
            s = re.sub(r"\'([^\']*)\'", lambda m: "'" + m.group(1) + self.rng.choice(["","''","x"," "]) + "'", s)

        # Randomly add parentheses
        if _chance(self.rng, 0.25):
            s = '(' + s + ')'

        # Sometimes add a trailing semicolon if missing
        if _chance(self.rng, 0.4) and not s.strip().endswith(';'):
            s += ';'

        return s

    def _tokenizer_stress(self):
        cases = []
        # Unterminated string
        cases.append("SELECT 'unterminated")
        # Escaped quotes
        cases.append("SELECT 'O''Brien'")
        # Comments
        cases.append("/* comment */ SELECT 1;")
        cases.append("-- line comment\nSELECT 2;")
        # Nested comments or odd spacing
        cases.append("/* outer /* inner */ still */ SELECT * FROM t;")
        # Long identifier
        long_ident = '"' + ('A'*128) + '"'
        cases.append(f"SELECT {long_ident} FROM {long_ident};")
        # Hex blob
        cases.append("SELECT X'0AFF';")
        # Weird numbers
        cases.append("SELECT -0.0, +.5e10, 1e-10;")
        # Odd operators
        cases.append("SELECT 1<<2, 8>>1, 1|2, 1&3, 1^1;")
        # Illegal tokens to trigger tokenizer error paths (parser should catch exceptions)
        cases.append("SELECT @bad_token;")
        return cases

    def _smoke_statements(self):
        # Deterministic curated set to immediately cover many branches
        stmts = []
        # Simple selects
        stmts.append("SELECT 1;")
        stmts.append("SELECT * FROM users;")
        stmts.append("SELECT id, name FROM users WHERE id = 1;")
        stmts.append("SELECT DISTINCT name FROM customers ORDER BY name DESC;")
        # Joins
        for jt in ['JOIN','INNER JOIN','LEFT JOIN','RIGHT JOIN','FULL JOIN','CROSS JOIN','NATURAL JOIN']:
            stmts.append(f"SELECT * FROM a {jt} b ON a.id = b.id;")
        # Group / having
        stmts.append("SELECT category, COUNT(*) AS c FROM products GROUP BY category HAVING COUNT(*) > 1;")
        # In / Between / Like
        stmts.append("SELECT * FROM items WHERE price BETWEEN 10 AND 20;")
        stmts.append("SELECT * FROM items WHERE name LIKE 'A%';")
        stmts.append("SELECT * FROM items WHERE id IN (1,2,3);")
        # Set ops
        stmts.append("SELECT 1 UNION SELECT 2;")
        stmts.append("SELECT 1 INTERSECT SELECT 1;")
        # Insert
        stmts.append("INSERT INTO orders (id, name) VALUES (1, 'x');")
        stmts.append("INSERT OR REPLACE INTO orders VALUES (2, 'y');")
        # Update
        stmts.append("UPDATE products SET price = price + 1 WHERE id = 5;")
        # Delete
        stmts.append("DELETE FROM logs WHERE id <> 0;")
        # Create table variations
        stmts.append("CREATE TABLE IF NOT EXISTS t1 (id INTEGER PRIMARY KEY, name TEXT NOT NULL);")
        stmts.append("CREATE TABLE t2 (a INT, b TEXT, c REAL, CONSTRAINT uq UNIQUE (a,b));")
        # Alter / Drop
        stmts.append("ALTER TABLE t2 ADD COLUMN d INT;")
        stmts.append("DROP TABLE IF EXISTS old_table;")
        # Index
        stmts.append("CREATE UNIQUE INDEX IF NOT EXISTS idx_t1_name ON t1 (name COLLATE NOCASE);")
        # View
        stmts.append("CREATE VIEW IF NOT EXISTS v1 AS SELECT id, name FROM t1;")
        # Transactions and PRAGMAs
        stmts.extend([
            "BEGIN;", "COMMIT;", "ROLLBACK;", "SAVEPOINT sp1;", "ROLLBACK TO sp1;", "RELEASE sp1;",
            "PRAGMA foreign_keys = ON;", "VACUUM;", "ANALYZE;"
        ])
        # Explain
        stmts.append("EXPLAIN SELECT * FROM t1 WHERE id = 1;")
        # Tokenizer stress
        stmts.extend(self._tokenizer_stress())
        return stmts

    def _random_statement(self, depth=3):
        pick = _weighted_choice(self.rng, [
            ('select', 5.0), ('insert', 1.5), ('update', 1.2), ('delete', 1.2),
            ('create_table', 1.3), ('alter_table', 0.9), ('drop', 0.7), ('create_index', 1.0),
            ('create_view', 0.7), ('misc', 0.6)
        ])
        if pick == 'select':
            return self._gen_select(top_level=True, depth=depth)
        if pick == 'insert':
            return self._gen_insert(depth=depth)
        if pick == 'update':
            return self._gen_update(depth=depth)
        if pick == 'delete':
            return self._gen_delete(depth=depth)
        if pick == 'create_table':
            return self._gen_create_table(depth=depth)
        if pick == 'alter_table':
            return self._gen_alter_table()
        if pick == 'drop':
            return self._gen_drop()
        if pick == 'create_index':
            return self._gen_create_index()
        if pick == 'create_view':
            return self._gen_create_view(depth=depth)
        return self._gen_misc()

    def _mutate_batch(self, base_list, target_count):
        out = []
        if not base_list:
            return out
        for _ in range(target_count):
            s = self.rng.choice(base_list)
            out.append(self._mutate_sql(s))
        return out

    def _adaptive_batch_size(self):
        if self.last_duration <= 0:
            return self.base_batch
        # Adjust batch size based on previous call duration
        factor = self.target_duration / max(0.1, self.last_duration)
        # Limit factor
        if factor > 1.4:
            factor = 1.4
        if factor < 0.7:
            factor = 0.7
        new_size = int(self.base_batch * factor)
        if new_size < self.batch_min:
            new_size = self.batch_min
        if new_size > self.batch_max:
            new_size = self.batch_max
        self.base_batch = new_size
        return new_size

    def generate_batch(self, phase):
        batch = []
        if phase == 0:
            # Curated set plus modest random additions
            batch.extend(self._smoke_statements())
            for _ in range(200):
                batch.append(self._random_statement(depth=3))
        elif phase == 1:
            # Focus on SELECT/JOIN variants
            for jt in self.join_types:
                base = f"SELECT * FROM {self._quote_ident('tA')} {jt} {self._quote_ident('tB')}"
                if jt.startswith('NATURAL'):
                    batch.append(base + ';')
                else:
                    cond = f" ON {self._quote_ident('tA')}.id = {self._quote_ident('tB')}.id"
                    batch.append(base + cond + ';')
            for op in self.comp_ops + self.like_ops:
                if op in self.like_ops:
                    batch.append(f"SELECT * FROM {self._random_table()} WHERE {self._random_col()} {op} 'abc%';")
                else:
                    batch.append(f"SELECT * FROM {self._random_table()} WHERE {self._random_col()} {op} {self._gen_expr(2)};")
            for _ in range(300):
                batch.append(self._gen_select(top_level=True, depth=3))
        else:
            # Adaptive size random plus mutations
            target = self._adaptive_batch_size()
            gen_count = int(target * 0.6)
            mut_count = target - gen_count

            for _ in range(gen_count):
                # Alternate depth to vary complexity
                depth = self.rng.choice([2,3,4])
                batch.append(self._random_statement(depth=depth))

            # Ensure we keep a corpus to mutate
            selectable = self.corpus[-min(len(self.corpus), 1000):] if self.corpus else batch
            batch.extend(self._mutate_batch(selectable, mut_count))

            # Append a handful of tokenizer stress cases occasionally
            if _chance(self.rng, 0.2):
                batch.extend(self._tokenizer_stress())

        # Clean and cap overly long statements
        cleaned = []
        for s in batch:
            t = s.strip()
            if not t:
                continue
            # Enforce max length to avoid pathological cases
            if len(t) > 5000:
                t = t[:5000]
            cleaned.append(t)
        # Update corpus with a sample
        if cleaned:
            sample_sz = min(200, len(cleaned))
            for s in self.rng.sample(cleaned, sample_sz):
                if len(self.corpus) < self.corpus_limit:
                    self.corpus.append(s)
                else:
                    # Reservoir-like: replace random
                    idx = self.rng.randint(0, self.corpus_limit - 1)
                    self.corpus[idx] = s
        return cleaned

    def fuzz(self, parse_sql):
        if self.start_time is None:
            self.start_time = time.time()
        if self.parse_calls >= self.max_calls:
            return False
        phase = min(self.parse_calls, 2)  # 0,1 special; >=2 random/mutate
        batch = self.generate_batch(phase)
        t0 = time.time()
        try:
            parse_sql(batch)
        except Exception:
            # parse_sql is expected to handle exceptions internally, but be safe
            pass
        t1 = time.time()
        self.last_duration = t1 - t0
        self.parse_calls += 1
        # Continue until we hit max_calls
        return self.parse_calls < self.max_calls

_fuzzer_instance = SQLFuzzer()

def fuzz(parse_sql):
    return _fuzzer_instance.fuzz(parse_sql)
'''
        return {"code": code}