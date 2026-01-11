import os

class Solution:
    def solve(self, resources_path: str) -> dict:
        grammar_path = os.path.join(resources_path, 'sql_grammar.txt')
        productions = {}
        with open(grammar_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or '::=' not in line:
                    continue
                parts = line.split('::=', 1)
                if len(parts) != 2:
                    continue
                left, right = [p.strip() for p in parts]
                nt = left
                if not (nt.startswith('<') and nt.endswith('>')):
                    continue
                alts_str = right
                alts = [a.strip() for a in alts_str.split('|') if a.strip()]
                prod_list = []
                for alt_str in alts:
                    symbols = [s.strip() for s in alt_str.split() if s.strip()]
                    prod_list.append(symbols)
                productions[nt] = prod_list
        all_rhs = set()
        for prod_list in productions.values():
            for alt in prod_list:
                for sym in alt:
                    if sym.startswith('<') and sym.endswith('>'):
                        all_rhs.add(sym)
        start_symbols = [nt for nt in productions if nt not in all_rhs]
        start_symbol = start_symbols[0] if start_symbols else list(productions.keys())[0]
        prod_str = str(productions)
        code = f'''import random

productions = {prod_str}
start_symbol = "{start_symbol}"

def is_nonterminal(symbol):
    return symbol.startswith('<') and symbol.endswith('>')

def generate(symbol, productions, max_depth=20, current_depth=0):
    if current_depth >= max_depth:
        return None
    if not is_nonterminal(symbol):
        return symbol
    if symbol not in productions:
        return symbol
    alts = productions[symbol]
    if not alts:
        return None
    alt = random.choice(alts)
    parts = []
    for sym in alt:
        if is_nonterminal(sym):
            gen = generate(sym, productions, max_depth, current_depth + 1)
            if gen is None:
                return None
            parts.append(str(gen))
        else:
            parts.append(sym)
    result = ' '.join(parts)
    if not result.strip():
        return None
    return result

def mutate(sql):
    if random.random() < 0.5:
        return sql
    words = sql.split()
    if len(words) <= 1:
        return sql
    action = random.choice([1, 2, 3])
    if action == 1:  # replace
        idx = random.randint(0, len(words) - 1)
        words[idx] = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_+-*/=<>(),;[]{}', k=random.randint(1, 15)))
    elif action == 2:  # delete
        idx = random.randint(0, len(words) - 1)
        del words[idx]
    else:  # insert
        idx = random.randint(0, len(words))
        insert = random.choice(['FOO', 'BAR', 'INVALID', 'EXTRA', 'NULL', 'TRUE', 'FALSE', ';', ',', '(', ')', '[', ']', '{', '}', '/*', '*/', '--', '&&', '||', '%', '^'])
        words.insert(idx, insert)
    return ' '.join(words)

def fuzz(parse_sql):
    batch_size = 20000
    statements = []
    generated_count = 0
    target = batch_size
    while generated_count < target:
        max_d = random.randint(8, 25)
        sql = generate(start_symbol, productions, max_d)
        if sql is None or len(sql.strip()) < 5 or len(sql) > 1500:
            continue
        statements.append(sql.strip())
        generated_count += 1
        if random.random() < 0.4:
            mutated = mutate(sql)
            if len(mutated.strip()) > 0 and len(mutated) < 1500:
                statements.append(mutated.strip())
                generated_count += 1
        if generated_count >= target:
            break
    # Add fixed seeds and invalids
    seeds = [
        "SELECT * FROM users",
        "INSERT INTO users (id, name) VALUES (1, 'test')",
        "UPDATE users SET name = 'new' WHERE id = 1",
        "DELETE FROM users WHERE id = 1",
        "CREATE TABLE test (id INT)",
        "DROP TABLE test",
        "",
        "SELECT",
        "SELECT * FROM",
        "INSERT INTO",
        "( ( ) )",
        "'; DROP TABLE users; --",
        "SELECT * FROM t WHERE 1=1 AND 2=3",
        "UPDATE t SET x = y + z * (1/0)",
        "SELECT COUNT(*) FROM t GROUP BY x HAVING y > 1 ORDER BY z LIMIT 10",
        "BEGIN TRANSACTION; COMMIT;",
        "SELECT 'hello' || 'world'",
        "SELECT 1 + 2 * 3 / 4 % 5",
        "SELECT CASE WHEN 1=1 THEN 'yes' ELSE 'no' END",
        "SELECT * FROM t WHERE x IN (1,2,3) OR y NOT IN (4,5)",
    ]
    statements.extend(seeds * (target // len(seeds) + 1))
    # Limit total to avoid time overrun
    statements = statements[:50000]
    parse_sql(statements)
    return False
'''
        return {"code": code}