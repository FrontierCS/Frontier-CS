import os
import sys
import re
import random

def parse_grammar(file_path):
    rules = {}
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or '::=' not in line:
                continue
            parts = line.split('::=', 1)
            if len(parts) != 2:
                continue
            left, right = parts
            rule = left.strip().strip('<>')
            if not rule:
                continue
            alternatives = [alt.strip() for alt in right.split('|') if alt.strip()]
            productions = []
            for alt in alternatives:
                symbols = re.findall(r'<[^>]+>|\S+', alt)
                productions.append(symbols)
            if productions:
                rules[rule] = productions
    return rules

def generate(rules, symbol, max_depth=20):
    if max_depth <= 0:
        return ''
    s = symbol.strip('<>')
    if s not in rules:
        return symbol
    prods = rules[s]
    if not prods:
        return ''
    prod = random.choice(prods)
    parts = []
    for sym in prod:
        if sym.startswith('<') and sym.endswith('>'):
            sub = generate(rules, sym, max_depth - 1)
            if sub is not None:
                parts.append(sub)
        else:
            parts.append(sym)
    return ' '.join(str(p) for p in parts if p)

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        grammar_path = os.path.join(resources_path, 'sql_grammar.txt')
        grammar = parse_grammar(grammar_path)
        if not grammar:
            return []

        start_rule = None
        for r in grammar:
            if r.lower() in ['sql', 'statement', 'query', 'sql_statement']:
                start_rule = r
                break
        if start_rule is None:
            start_rule = list(grammar.keys())[0]
        start_sym = f'<{start_rule}>'

        sys.path.insert(0, os.path.join(resources_path, 'sql_engine'))
        try:
            from parser import parse_sql
            can_validate = True
        except ImportError:
            can_validate = False

        random.seed(42)
        tests = []
        generated = set()
        attempts = 0
        max_attempts = 1000

        while len(tests) < 50 and attempts < max_attempts:
            attempts += 1
            sql = generate(grammar, start_sym)
            if sql and sql.strip() and sql not in generated:
                generated.add(sql)
                if can_validate:
                    try:
                        parse_sql(sql)
                        tests.append(sql)
                    except:
                        pass
                else:
                    tests.append(sql)
                if len(tests) >= 50:
                    break

        return tests[:50]