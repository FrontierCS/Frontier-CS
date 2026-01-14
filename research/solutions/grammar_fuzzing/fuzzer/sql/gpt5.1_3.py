import os
import re
import textwrap


class Solution:
    def solve(self, resources_path: str) -> dict:
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        keywords = set()
        try:
            with open(grammar_path, "r", encoding="utf-8") as f:
                text = f.read()
            pattern = re.compile(r"\b[A-Z_][A-Z0-9_]{1,}\b")
            for kw in pattern.findall(text):
                if len(kw) <= 1:
                    continue
                keywords.add(kw)
        except Exception:
            keywords = set()
        keywords_list = sorted(keywords)
        template = '''
import random
import string
import time

DISCOVERED_KEYWORDS = __KEYWORDS__

BASE_KEYWORDS = [
    'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'FROM', 'WHERE', 'GROUP', 'BY',
    'HAVING', 'ORDER', 'LIMIT', 'OFFSET', 'JOIN', 'LEFT', 'RIGHT', 'FULL',
    'OUTER', 'INNER', 'CROSS', 'ON', 'USING', 'UNION', 'ALL', 'DISTINCT',
    'INTERSECT', 'EXCEPT', 'VALUES', 'INTO', 'CREATE', 'TABLE', 'DROP',
    'ALTER', 'ADD', 'COLUMN', 'INDEX', 'VIEW', 'TRIGGER', 'TEMP', 'TEMPORARY',
    'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'UNIQUE', 'CHECK', 'DEFAULT',
    'NOT', 'NULL', 'AND', 'OR', 'IS', 'IN', 'BETWEEN', 'LIKE', 'GLOB', 'REGEXP',
    'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AS', 'ASC', 'DESC', 'CAST',
    'COALESCE', 'IFNULL', 'NULLIF', 'EXISTS', 'ESCAPE', 'COLLATE', 'SET',
    'PRAGMA', 'ANALYZE', 'EXPLAIN'
]

ALL_KEYWORDS = sorted(set(DISCOVERED_KEYWORDS) | set(BASE_KEYWORDS))
KEYWORDS_FOR_NOISE = ALL_KEYWORDS

IDENT_START_CHARS = string.ascii_letters + '_'
IDENT_CHARS = IDENT_START_CHARS + string.digits

MUTATION_ALPHABET = string.ascii_letters + string.digits + " \\t\\n\\r!@#$%^&*()-_=+[]{};:',.<>/?\\\\|`~\\\""

RNG = random.Random()
CORPUS = []
BATCH_SIZE = 250
TARGET_CALL_DURATION = 1.0
MAX_BATCH_SIZE = 2000

def random_identifier(rng, min_len=1, max_len=10):
    length = rng.randint(min_len, max_len)
    first = rng.choice(IDENT_START_CHARS)
    if length == 1:
        return first
    rest = ''.join(rng.choice(IDENT_CHARS) for _ in range(length - 1))
    return first + rest

def maybe_quoted_identifier(rng):
    ident = random_identifier(rng, 1, 12)
    r = rng.random()
    if r < 0.2:
        return '"' + ident + '"'
    elif r < 0.4:
        return '`' + ident + '`'
    elif r < 0.6:
        return '[' + ident + ']'
    else:
        return ident

def random_number_literal(rng):
    choice = rng.randint(0, 4)
    if choice == 0:
        return str(rng.randint(-2**31, 2**31 - 1))
    elif choice == 1:
        return str(rng.random() * rng.randint(-1000000, 1000000))
    elif choice == 2:
        return str(rng.randint(0, 100)) + '.' + str(rng.randint(0, 100000))
    elif choice == 3:
        return '.' + str(rng.randint(0, 100000))
    else:
        return str(rng.randint(0, 100000)) + '.'

def random_string_literal(rng):
    length = rng.randint(0, 20)
    chars = []
    for _ in range(length):
        ch_type = rng.randint(0, 4)
        if ch_type == 0:
            ch = rng.choice(string.ascii_letters)
        elif ch_type == 1:
            ch = rng.choice(string.digits)
        elif ch_type == 2:
            ch = rng.choice(" \\t\\n\\r")
        elif ch_type == 3:
            ch = rng.choice("!@#$%^&*()-_=+[]{};:,./<>?|\\\\")
        else:
            ch = chr(rng.randint(1, 0xFF))
        chars.append(ch)
    inner = ''.join(chars).replace("'", "''")
    s = "'" + inner
    if rng.random() < 0.8:
        s += "'"
    return s

def random_blob_literal(rng):
    length = rng.randint(0, 20)
    hex_chars = '0123456789ABCDEF'
    content = ''.join(rng.choice(hex_chars) for _ in range(length))
    return "X'" + content + ("'" if rng.random() < 0.8 else "")

def random_literal(rng):
    r = rng.random()
    if r < 0.4:
        return random_number_literal(rng)
    elif r < 0.75:
        return random_string_literal(rng)
    elif r < 0.8:
        return random_blob_literal(rng)
    elif r < 0.9:
        return rng.choice(['NULL', 'TRUE', 'FALSE'])
    else:
        if ALL_KEYWORDS:
            return rng.choice(ALL_KEYWORDS)
        return random_string_literal(rng)

def random_column_name(rng):
    if rng.random() < 0.3:
        return maybe_quoted_identifier(rng)
    else:
        col = maybe_quoted_identifier(rng)
        if rng.random() < 0.3:
            col = maybe_quoted_identifier(rng) + '.' + col
        return col

def random_table_name(rng):
    if rng.random() < 0.3:
        base = maybe_quoted_identifier(rng)
        t = maybe_quoted_identifier(rng)
        name = base + '.' + t
        if rng.random() < 0.1:
            name = maybe_quoted_identifier(rng) + '.' + name
        return name
    else:
        return maybe_quoted_identifier(rng)

BIN_OPS = [
    '+', '-', '*', '/', '%', '||',
    '=', '!=', '<>', '<', '>', '<=', '>=',
    'AND', 'OR', 'IS', 'IS NOT', 'IN', 'LIKE', 'GLOB', 'REGEXP', 'MATCH',
    '&', '|', '<<', '>>'
]

UNARY_OPS = ['-', '+', 'NOT', '~']

def random_primary(rng, allow_subselect, expr_depth, max_depth):
    r = rng.random()
    if r < 0.5:
        return random_literal(rng)
    elif r < 0.85:
        return random_column_name(rng)
    elif allow_subselect and expr_depth < max_depth:
        return '(' + generate_select(rng, depth=expr_depth + 1, max_depth=max_depth) + ')'
    else:
        return '(' + random_expression(rng, expr_depth + 1, max_depth, allow_subselect) + ')'

def random_expression(rng, depth=0, max_depth=3, allow_subselect=True):
    if depth >= max_depth:
        return random_primary(rng, allow_subselect, depth, max_depth)
    r = rng.random()
    if allow_subselect and r < 0.05:
        return '(' + generate_select(rng, depth=depth + 1, max_depth=max_depth) + ')'
    elif r < 0.5:
        left = random_expression(rng, depth + 1, max_depth, allow_subselect)
        op = rng.choice(BIN_OPS)
        if op == 'IN' and allow_subselect and rng.random() < 0.5:
            right = '(' + generate_select(rng, depth + 1, max_depth) + ')'
        else:
            right = random_expression(rng, depth + 1, max_depth, allow_subselect)
        return left + ' ' + op + ' ' + right
    elif r < 0.65:
        op = rng.choice(UNARY_OPS)
        inner = random_expression(rng, depth + 1, max_depth, allow_subselect)
        if op in ('+', '-', '~'):
            return op + inner
        else:
            return op + ' ' + inner
    elif r < 0.8:
        base_funcs = [
            'ABS', 'MAX', 'MIN', 'SUM', 'COUNT', 'AVG',
            'LENGTH', 'ROUND', 'UPPER', 'LOWER',
            'COALESCE', 'IFNULL', 'NULLIF'
        ]
        name = rng.choice(base_funcs)
        if ALL_KEYWORDS and rng.random() < 0.2:
            name = rng.choice(ALL_KEYWORDS)
        if rng.random() < 0.15:
            args = ['*']
        else:
            n_args = rng.randint(0, 4)
            args = [random_expression(rng, depth + 1, max_depth, allow_subselect) for _ in range(n_args)]
        return name + '(' + ', '.join(args) + ')'
    elif r < 0.95:
        parts = ['CASE']
        if rng.random() < 0.3:
            parts.append(random_expression(rng, depth + 1, max_depth, allow_subselect))
        for _ in range(rng.randint(1, 3)):
            parts.append('WHEN')
            parts.append(random_expression(rng, depth + 1, max_depth, allow_subselect))
            parts.append('THEN')
            parts.append(random_expression(rng, depth + 1, max_depth, allow_subselect))
        if rng.random() < 0.5:
            parts.append('ELSE')
            parts.append(random_expression(rng, depth + 1, max_depth, allow_subselect))
        parts.append('END')
        return ' '.join(parts)
    else:
        return random_primary(rng, allow_subselect, depth, max_depth)

TYPE_NAMES = [
    'INT', 'INTEGER', 'TINYINT', 'SMALLINT', 'MEDIUMINT', 'BIGINT',
    'UNSIGNED BIG INT', 'INT2', 'INT8',
    'REAL', 'DOUBLE', 'DOUBLE PRECISION', 'FLOAT',
    'NUMERIC', 'DECIMAL', 'BOOLEAN', 'DATE', 'DATETIME',
    'TEXT', 'CHAR', 'CLOB', 'BLOB'
]

def generate_column_def(rng):
    col = maybe_quoted_identifier(rng)
    type_name = rng.choice(TYPE_NAMES)
    parts = [col, type_name]
    if rng.random() < 0.5:
        parts.append('NOT NULL')
    if rng.random() < 0.3:
        if rng.random() < 0.5:
            parts.append('PRIMARY KEY')
            if rng.random() < 0.5:
                parts.append('AUTOINCREMENT')
        else:
            parts.append('UNIQUE')
    if rng.random() < 0.4:
        parts.append('DEFAULT ' + random_literal(rng))
    if rng.random() < 0.2:
        parts.append('CHECK (' + random_expression(rng, 0, 2, allow_subselect=False) + ')')
    if rng.random() < 0.2:
        parts.append('COLLATE ' + rng.choice(['BINARY', 'NOCASE', 'RTRIM']))
    return ' '.join(parts)

def generate_table_constraint(rng):
    t = rng.random()
    if t < 0.4:
        cols = [maybe_quoted_identifier(rng) for _ in range(rng.randint(1, 3))]
        kind = 'PRIMARY KEY' if rng.random() < 0.5 else 'UNIQUE'
        parts = [kind, '(' + ', '.join(cols) + ')']
        if kind == 'PRIMARY KEY' and rng.random() < 0.5:
            parts.append(rng.choice([
                'ON CONFLICT ROLLBACK',
                'ON CONFLICT ABORT',
                'ON CONFLICT FAIL',
                'ON CONFLICT IGNORE',
                'ON CONFLICT REPLACE'
            ]))
        return ' '.join(parts)
    elif t < 0.7:
        return 'CHECK (' + random_expression(rng, 0, 2, allow_subselect=False) + ')'
    else:
        cols = [maybe_quoted_identifier(rng) for _ in range(rng.randint(1, 3))]
        ref_table = random_table_name(rng)
        ref_cols = [maybe_quoted_identifier(rng) for _ in range(rng.randint(1, 3))]
        parts = [
            'FOREIGN KEY (' + ', '.join(cols) + ') REFERENCES ' +
            ref_table + ' (' + ', '.join(ref_cols) + ')'
        ]
        if rng.random() < 0.5:
            parts.append('ON DELETE ' + rng.choice([
                'CASCADE', 'SET NULL', 'SET DEFAULT',
                'RESTRICT', 'NO ACTION'
            ]))
        if rng.random() < 0.5:
            parts.append('ON UPDATE ' + rng.choice([
                'CASCADE', 'SET NULL', 'SET DEFAULT',
                'RESTRICT', 'NO ACTION'
            ]))
        return ' '.join(parts)

def generate_create_table(rng):
    table_name = random_table_name(rng)
    cols = [generate_column_def(rng) for _ in range(rng.randint(1, 6))]
    if rng.random() < 0.5:
        cols.append(generate_table_constraint(rng))
    inner = ', '.join(cols)
    sql = 'CREATE '
    if rng.random() < 0.3:
        sql += 'TEMPORARY '
    sql += 'TABLE '
    if rng.random() < 0.3:
        sql += 'IF NOT EXISTS '
    sql += table_name + ' (' + inner + ')'
    return sql

def generate_create_index(rng):
    index_name = maybe_quoted_identifier(rng)
    table_name = random_table_name(rng)
    cols = [maybe_quoted_identifier(rng) for _ in range(rng.randint(1, 4))]
    sql = 'CREATE '
    if rng.random() < 0.4:
        sql += 'UNIQUE '
    sql += 'INDEX '
    if rng.random() < 0.3:
        sql += 'IF NOT EXISTS '
    sql += index_name + ' ON ' + table_name + ' (' + ', '.join(cols) + ')'
    if rng.random() < 0.5:
        sql += ' WHERE ' + random_expression(rng, 0, 2, allow_subselect=False)
    return sql

def generate_create_view(rng):
    view_name = random_table_name(rng)
    sql = 'CREATE VIEW '
    if rng.random() < 0.3:
        sql += 'IF NOT EXISTS '
    sql += view_name + ' AS ' + generate_select(rng, 0, 2)
    return sql

def generate_drop_statement(rng):
    obj_type = rng.choice(['TABLE', 'INDEX', 'VIEW'])
    name = random_table_name(rng)
    sql = 'DROP ' + obj_type + ' '
    if rng.random() < 0.3:
        sql += 'IF EXISTS '
    sql += name
    return sql

def generate_select(rng, depth=0, max_depth=2):
    parts = []
    if rng.random() < 0.3:
        parts.append('WITH')
        if rng.random() < 0.3:
            parts.append('RECURSIVE')
        cte_count = rng.randint(1, 3)
        ctes = []
        for _ in range(cte_count):
            name = maybe_quoted_identifier(rng)
            cols = ''
            if rng.random() < 0.3:
                col_names = [maybe_quoted_identifier(rng) for _ in range(rng.randint(1, 4))]
                cols = ' (' + ', '.join(col_names) + ')'
            subquery = generate_select(rng, depth + 1, max_depth)
            ctes.append(name + cols + ' AS (' + subquery + ')')
        parts.append(', '.join(ctes))
    if parts:
        parts.append('SELECT')
    else:
        parts = ['SELECT']
    r = rng.random()
    if r < 0.25:
        parts.append('DISTINCT')
    elif r < 0.35:
        parts.append('ALL')
    select_items = []
    if rng.random() < 0.2:
        select_items.append('*')
    n_items = rng.randint(1, 5)
    for _ in range(n_items):
        expr = random_expression(rng, 0, 3, allow_subselect=(depth < max_depth))
        if rng.random() < 0.4:
            alias = maybe_quoted_identifier(rng)
            if rng.random() < 0.5:
                expr += ' AS ' + alias
            else:
                expr += ' ' + alias
        select_items.append(expr)
    parts.append(', '.join(select_items))
    if rng.random() < 0.9:
        table_entries = []
        base_tables = [random_table_name(rng) for _ in range(rng.randint(1, 3))]
        for t in base_tables:
            entry = t
            if rng.random() < 0.5:
                entry += ' AS ' + maybe_quoted_identifier(rng)
            table_entries.append(entry)
        from_clause = ' FROM ' + ', '.join(table_entries)
        join_types = [
            'JOIN',
            'LEFT JOIN',
            'LEFT OUTER JOIN',
            'INNER JOIN',
            'CROSS JOIN'
        ]
        for _ in range(rng.randint(0, 2)):
            join_table = random_table_name(rng)
            join = ' ' + rng.choice(join_types) + ' ' + join_table
            if rng.random() < 0.5:
                join += ' AS ' + maybe_quoted_identifier(rng)
            if rng.random() < 0.8:
                join += ' ON ' + random_expression(rng, 0, 2, allow_subselect=(depth < max_depth))
            elif rng.random() < 0.5:
                join += ' USING (' + ', '.join(
                    maybe_quoted_identifier(rng) for _ in range(rng.randint(1, 3))
                ) + ')'
            from_clause += join
        parts.append(from_clause)
    if rng.random() < 0.7:
        parts.append('WHERE ' + random_expression(rng, 0, 3, allow_subselect=(depth < max_depth)))
    if rng.random() < 0.4:
        group_terms = [
            random_expression(rng, 0, 2, allow_subselect=False)
            for _ in range(rng.randint(1, 3))
        ]
        group_clause = 'GROUP BY ' + ', '.join(group_terms)
        if rng.random() < 0.5:
            group_clause += ' HAVING ' + random_expression(
                rng, 0, 3, allow_subselect=(depth < max_depth)
            )
        parts.append(group_clause)
    if rng.random() < 0.6:
        order_terms = []
        for _ in range(rng.randint(1, 4)):
            term = random_expression(rng, 0, 2, allow_subselect=False)
            if rng.random() < 0.7:
                term += ' ' + rng.choice(['ASC', 'DESC'])
            if rng.random() < 0.3:
                term += ' NULLS ' + rng.choice(['FIRST', 'LAST'])
            order_terms.append(term)
        parts.append('ORDER BY ' + ', '.join(order_terms))
    if rng.random() < 0.5:
        if rng.random() < 0.4:
            parts.append('LIMIT ' + random_number_literal(rng))
            if rng.random() < 0.5:
                parts.append('OFFSET ' + random_number_literal(rng))
        else:
            parts.append(
                'LIMIT ' + random_number_literal(rng) +
                ' , ' + random_number_literal(rng)
            )
    sql = ' '.join(parts)
    if depth < max_depth and rng.random() < 0.3:
        op = rng.choice(['UNION', 'UNION ALL', 'INTERSECT', 'EXCEPT'])
        right = generate_select(rng, depth + 1, max_depth)
        sql = '(' + sql + ') ' + op + ' ' + right
    return sql

def generate_insert(rng):
    table = random_table_name(rng)
    n_cols = rng.randint(0, 6)
    columns = [maybe_quoted_identifier(rng) for _ in range(n_cols)]
    sql = 'INSERT'
    if rng.random() < 0.3:
        sql += ' OR ' + rng.choice(['ROLLBACK', 'ABORT', 'REPLACE', 'FAIL', 'IGNORE'])
    sql += ' INTO ' + table
    if columns and rng.random() < 0.8:
        sql += ' (' + ', '.join(columns) + ')'
    if rng.random() < 0.5:
        rows = []
        row_count = rng.randint(1, 3)
        for _ in range(row_count):
            if columns and rng.random() < 0.7:
                n_vals = len(columns)
            else:
                n_vals = rng.randint(1, max(1, len(columns) or 4))
            vals = [
                random_expression(rng, 0, 2, allow_subselect=False)
                for _ in range(n_vals)
            ]
            rows.append('(' + ', '.join(vals) + ')')
        sql += ' VALUES ' + ', '.join(rows)
    else:
        sql += ' ' + generate_select(rng, 0, 1)
    if rng.random() < 0.3:
        sql += ' RETURNING ' + ', '.join(
            random_column_name(rng) for _ in range(rng.randint(1, 4))
        )
    return sql

def generate_update(rng):
    table = random_table_name(rng)
    sql = 'UPDATE '
    if rng.random() < 0.3:
        sql += 'OR ' + rng.choice(['ROLLBACK', 'ABORT', 'REPLACE', 'FAIL', 'IGNORE']) + ' '
    sql += table + ' SET '
    assignments = []
    for _ in range(rng.randint(1, 6)):
        col = maybe_quoted_identifier(rng)
        expr = random_expression(rng, 0, 2, allow_subselect=False)
        assignments.append(col + ' = ' + expr)
    sql += ', '.join(assignments)
    if rng.random() < 0.7:
        sql += ' WHERE ' + random_expression(rng, 0, 3, allow_subselect=True)
    if rng.random() < 0.3:
        sql += ' RETURNING ' + ', '.join(
            random_column_name(rng) for _ in range(rng.randint(1, 4))
        )
    return sql

def generate_delete(rng):
    table = random_table_name(rng)
    sql = 'DELETE FROM ' + table
    if rng.random() < 0.7:
        sql += ' WHERE ' + random_expression(rng, 0, 3, allow_subselect=True)
    if rng.random() < 0.3:
        sql += ' RETURNING ' + ', '.join(
            random_column_name(rng) for _ in range(rng.randint(1, 4))
        )
    return sql

def generate_pragma_or_explain(rng):
    if rng.random() < 0.5:
        name = maybe_quoted_identifier(rng)
        sql = 'PRAGMA ' + name
        r = rng.random()
        if r < 0.33:
            sql += ' = ' + random_literal(rng)
        elif r < 0.66:
            sql += ' (' + random_literal(rng) + ')'
        return sql
    else:
        sql = 'EXPLAIN '
        if rng.random() < 0.5:
            sql += 'QUERY PLAN '
        inner = generate_statement_basic(rng)
        return sql + inner

def generate_keyword_statement(rng):
    if not KEYWORDS_FOR_NOISE:
        return random_noise_statement(rng)
    parts = []
    n = rng.randint(3, min(15, len(KEYWORDS_FOR_NOISE)))
    for _ in range(n):
        if rng.random() < 0.2:
            parts.append(random_identifier(rng))
        else:
            parts.append(rng.choice(KEYWORDS_FOR_NOISE))
        if rng.random() < 0.2:
            parts.append(rng.choice([",", "(", ")", ".", ";"]))
    stmt = ' '.join(parts)
    if rng.random() < 0.5:
        stmt = stmt.replace(' ,', ',').replace(' ;', ';')
    return stmt

def random_noise_statement(rng):
    length = rng.randint(1, 200)
    chars = []
    alphabet = MUTATION_ALPHABET + "/*-+"
    for _ in range(length):
        ch = rng.choice(alphabet)
        chars.append(ch)
    if length > 5 and rng.random() < 0.3:
        pos = rng.randint(0, length - 3)
        chars[pos:pos + 2] = ['-', '-']
    if length > 10 and rng.random() < 0.3:
        pos = rng.randint(0, length - 5)
        chars[pos:pos + 2] = ['/', '*']
        chars[-2:] = ['*', '/']
    return ''.join(chars)

def mutate_statement(rng, s, max_mutations=5):
    if not s:
        return s
    s_list = list(s)
    for _ in range(rng.randint(1, max_mutations)):
        op = rng.randint(0, 2)
        if op == 0 and s_list:
            idx = rng.randrange(len(s_list))
            del s_list[idx]
        elif op == 1 and s_list:
            idx = rng.randrange(len(s_list))
            s_list[idx] = rng.choice(MUTATION_ALPHABET)
        else:
            idx = rng.randrange(len(s_list) + 1)
            s_list.insert(idx, rng.choice(MUTATION_ALPHABET))
    return ''.join(s_list)

def generate_statement_basic(rng):
    r = rng.random()
    if r < 0.3:
        return generate_select(rng)
    elif r < 0.45:
        return generate_insert(rng)
    elif r < 0.6:
        return generate_update(rng)
    elif r < 0.72:
        return generate_delete(rng)
    elif r < 0.82:
        return generate_create_table(rng)
    elif r < 0.9:
        return generate_create_index(rng)
    elif r < 0.93:
        return generate_create_view(rng)
    elif r < 0.96:
        return generate_drop_statement(rng)
    elif r < 0.985:
        return generate_pragma_or_explain(rng)
    else:
        return generate_keyword_statement(rng)

def generate_statement(rng):
    r = rng.random()
    if CORPUS and r < 0.25:
        base = rng.choice(CORPUS)
        stmt = mutate_statement(rng, base, max_mutations=rng.randint(1, 12))
    elif CORPUS and r < 0.35:
        s1 = rng.choice(CORPUS)
        s2 = rng.choice(CORPUS)
        cut1 = rng.randint(0, len(s1))
        cut2 = rng.randint(0, len(s2))
        stmt = s1[:cut1] + ' ' + s2[cut2:]
    elif r > 0.97:
        stmt = random_noise_statement(rng)
    else:
        stmt = generate_statement_basic(rng)
    return stmt

def fuzz(parse_sql):
    global BATCH_SIZE
    rng = RNG
    statements = []
    for _ in range(BATCH_SIZE):
        stmt = generate_statement(rng)
        statements.append(stmt)
        if len(CORPUS) < 2000:
            if rng.random() < 0.3:
                CORPUS.append(stmt)
        else:
            if rng.random() < 0.05:
                idx = rng.randrange(len(CORPUS))
                CORPUS[idx] = stmt
    start = time.perf_counter()
    parse_sql(statements)
    end = time.perf_counter()
    dt = end - start
    if dt > 0:
        target = TARGET_CALL_DURATION
        desired = BATCH_SIZE * target / dt
        if desired < 10:
            desired = 10
        elif desired > MAX_BATCH_SIZE:
            desired = MAX_BATCH_SIZE
        BATCH_SIZE = int(BATCH_SIZE * 0.7 + desired * 0.3)
        if BATCH_SIZE < 10:
            BATCH_SIZE = 10
        elif BATCH_SIZE > MAX_BATCH_SIZE:
            BATCH_SIZE = MAX_BATCH_SIZE
    return True
'''
        code = textwrap.dedent(template).lstrip('\n')
        code = code.replace('__KEYWORDS__', repr(keywords_list))
        return {"code": code}