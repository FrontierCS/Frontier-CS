import sys
import os
import re
import random
import collections

class Grammar:
    def __init__(self, rules, start_symbol):
        self.rules = rules
        self.start_symbol = start_symbol
        self.min_depths = {}
        self.parent_map = collections.defaultdict(list)
        self._analyze()

    def _analyze(self):
        self.min_depths = {k: float('inf') for k in self.rules}
        changed = True
        while changed:
            changed = False
            for lhs, alts in self.rules.items():
                curr_min = float('inf')
                for alt in alts:
                    d = 0
                    for token in alt:
                        if token['type'] == 'NT':
                            d = max(d, self.min_depths.get(token['val'], float('inf')))
                    if d < float('inf'): d += 1
                    if d < curr_min: curr_min = d
                if curr_min < self.min_depths[lhs]:
                    self.min_depths[lhs] = curr_min
                    changed = True
        
        for lhs, alts in self.rules.items():
            for alt in alts:
                for token in alt:
                    if token['type'] == 'NT':
                        self.parent_map[token['val']].append(lhs)

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        sys.setrecursionlimit(5000)
        sys.path.append(resources_path)
        
        parse_func = None
        try:
            import sql_engine
            if hasattr(sql_engine, 'parse_sql'):
                parse_func = sql_engine.parse_sql
            elif hasattr(sql_engine, 'parser') and hasattr(sql_engine.parser, 'parse_sql'):
                parse_func = sql_engine.parser.parse_sql
            else:
                from sql_engine import parser
                if hasattr(parser, 'parse_sql'):
                    parse_func = parser.parse_sql
                elif hasattr(parser, 'Parser'):
                    p = parser.Parser()
                    parse_func = p.parse
        except Exception:
            pass

        grammar_path = os.path.join(resources_path, 'sql_grammar.txt')
        grammar = self._load_grammar(grammar_path)
        
        if not grammar.rules:
            return ["SELECT 1"]

        targets = []
        for lhs, alts in grammar.rules.items():
            for i in range(len(alts)):
                targets.append((lhs, i))
        random.shuffle(targets)
        
        covered = set()
        results = []
        seen_sql = set()
        
        for target in targets:
            if target in covered:
                continue
            
            lhs, alt_idx = target
            path = self._find_path(grammar, grammar.start_symbol, lhs)
            if path is None:
                continue
                
            try:
                visited = set()
                sql = self._generate(grammar, grammar.start_symbol, path, 0, target, visited)
                sql = " ".join(sql.split())
                
                if sql and sql not in seen_sql:
                    valid = True
                    if parse_func:
                        try:
                            parse_func(sql)
                        except Exception:
                            valid = False
                    
                    if valid:
                        seen_sql.add(sql)
                        results.append(sql)
                        covered.update(visited)
            except Exception:
                continue
        
        return results

    def _load_grammar(self, path):
        with open(path, 'r') as f:
            lines = f.readlines()
        
        rules = {}
        start = None
        buffer = ""
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'): continue
            if '::=' in line:
                if buffer: self._parse_rule(buffer, rules)
                buffer = line
            else:
                buffer += " " + line
        if buffer: self._parse_rule(buffer, rules)
        
        if rules:
            start = list(rules.keys())[0]
            
        return Grammar(rules, start)

    def _parse_rule(self, line, rules):
        parts = line.split('::=', 1)
        lhs = parts[0].strip()
        rhs = parts[1].strip()
        
        alts_raw = []
        curr = ""
        q = None
        for c in rhs:
            if c in "'\"":
                if q == c: q = None
                elif q is None: q = c
            if c == '|' and q is None:
                alts_raw.append(curr)
                curr = ""
            else:
                curr += c
        alts_raw.append(curr)
        
        parsed_alts = []
        for r in alts_raw:
            tokens = []
            for t in re.findall(r"<[^>]+>|'[^']*'|\"[^\"]*\"|[^\s]+", r):
                if t.startswith('<'):
                    tokens.append({'type': 'NT', 'val': t})
                elif t.startswith("'") or t.startswith('"'):
                     tokens.append({'type': 'T', 'val': t[1:-1]})
                else:
                     tokens.append({'type': 'T', 'val': t})
            parsed_alts.append(tokens)
        rules[lhs] = parsed_alts

    def _find_path(self, grammar, start, target):
        if start == target: return [start]
        q = [[target]]
        v = {target}
        while q:
            p = q.pop(0)
            curr = p[-1]
            if curr == start: return p[::-1]
            for par in grammar.parent_map[curr]:
                if par not in v:
                    v.add(par)
                    q.append(p + [par])
        return None

    def _generate(self, grammar, symbol, path, path_idx, target, visited):
        if symbol not in grammar.rules: return ""
        alts = grammar.rules[symbol]
        
        choice = -1
        on_path = False
        
        if path_idx is not None and path_idx < len(path) and path[path_idx] == symbol:
            on_path = True
            if path_idx == len(path) - 1:
                choice = target[1]
            else:
                next_node = path[path_idx+1]
                cands = [i for i, alt in enumerate(alts) if any(t['type']=='NT' and t['val']==next_node for t in alt)]
                if cands: choice = random.choice(cands)
        
        if choice == -1:
            cands = []
            for i, alt in enumerate(alts):
                c = 0
                for t in alt:
                    if t['type']=='NT': c = max(c, grammar.min_depths.get(t['val'], 9999))
                cands.append((c, i))
            cands.sort(key=lambda x: x[0])
            if cands:
                min_cost = cands[0][0]
                best = [x[1] for x in cands if x[0] == min_cost]
                choice = random.choice(best)
            else:
                choice = 0

        if 0 <= choice < len(alts):
            visited.add((symbol, choice))
            alt = alts[choice]
            res = []
            step_taken = False
            for t in alt:
                if t['type'] == 'T':
                    res.append(t['val'])
                else:
                    new_idx = None
                    if on_path and not step_taken and path_idx < len(path)-1 and t['val'] == path[path_idx+1]:
                        new_idx = path_idx + 1
                        step_taken = True
                    res.append(self._generate(grammar, t['val'], path, new_idx, target, visited))
            return " ".join(res)
        return ""