import sys
import os
import re
import random
import string

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        # 1. Setup environment
        sys.path.append(resources_path)
        parser_module = None
        try:
            import sql_engine.parser
            parser_module = sql_engine.parser
        except ImportError:
            pass

        # 2. Parse Grammar
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        self.rules = self.load_grammar(grammar_path)
        
        if not self.rules:
            return ["SELECT * FROM table1"]

        # Identify start symbol (prefer <statement> or first key)
        if '<statement>' in self.rules:
            self.start_symbol = '<statement>'
        else:
            self.start_symbol = list(self.rules.keys())[0]

        # 3. Precompute depths for termination guidance
        self.min_depths = self.compute_min_depths()
        
        # 4. Coverage tracking: map symbol -> {prod_index: usage_count}
        self.coverage = {k: {i: 0 for i in range(len(v))} for k, v in self.rules.items()}
        
        test_cases = set()
        
        # Target ~80 queries to balance high coverage and efficiency penalty
        # Loop limit ensures termination
        attempts = 0
        while len(test_cases) < 80 and attempts < 600:
            attempts += 1
            # Randomize max_depth to generate both simple and complex queries
            max_depth = random.choice([5, 8, 12, 16])
            
            try:
                sql = self.generate(self.start_symbol, 0, max_depth)
                if not sql or not sql.strip():
                    continue
                
                # Cleanup whitespace
                sql = " ".join(sql.split())
                
                # Validate using actual parser
                if parser_module:
                    try:
                        parser_module.parse_sql(sql)
                        test_cases.add(sql)
                    except Exception:
                        # Parser rejected it, discard
                        pass
                else:
                    test_cases.add(sql)
            except Exception:
                continue
                
        return list(test_cases)

    def load_grammar(self, path):
        rules = {}
        try:
            with open(path, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            return {}

        # Preprocess to single line string for easier parsing
        full_content = ""
        for line in lines:
            l = line.strip()
            if not l or l.startswith("#"): continue
            full_content += " " + l
            
        # Split rules based on pattern <lhs> ::=
        # We assume standard BNF format
        raw_rules = re.split(r'\s+(?=<[\w-]+>\s*::=)', full_content)
        
        for r in raw_rules:
            if '::=' not in r: continue
            parts = r.split('::=', 1)
            lhs = parts[0].strip()
            rhs_text = parts[1].strip()
            
            # Split alternatives by |
            # Note: need to be careful if | is inside quotes, but standard SQL grammar usually quotes literals
            options = [o.strip() for o in rhs_text.split('|')]
            parsed_options = []
            
            for opt in options:
                # Tokenize: <non-term>, "lit", 'lit', KEYWORD, [, ], {, }
                opt_tokens = re.findall(r'(<[^>]+>|"[^"]+"|\'[^\']+\'|[a-zA-Z0-9_]+|\[|\]|\{|\})', opt)
                
                # Process EBNF constructs [] and {} into recursive rules
                processed = self.process_ebnf(lhs, opt_tokens, rules)
                parsed_options.append(processed)
                
            rules[lhs] = parsed_options
            
        return rules

    def process_ebnf(self, lhs, tokens, rules_dict):
        result = []
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t == '[':
                # Optional: [ ... ] -> create rule aux ::= ... | ""
                j = self.find_match(tokens, i, '[', ']')
                inner = tokens[i+1:j]
                aux = f"{lhs}_opt_{random.randint(0, 1000000)}"
                inner_proc = self.process_ebnf(aux, inner, rules_dict)
                rules_dict[aux] = [inner_proc, ['""']]
                result.append(aux)
                i = j + 1
            elif t == '{':
                # Repetition: { ... } -> create rule aux ::= ... aux | ""
                j = self.find_match(tokens, i, '{', '}')
                inner = tokens[i+1:j]
                aux = f"{lhs}_rep_{random.randint(0, 1000000)}"
                inner_proc = self.process_ebnf(aux, inner, rules_dict)
                rules_dict[aux] = [inner_proc + [aux], ['""']]
                result.append(aux)
                i = j + 1
            else:
                result.append(t)
                i += 1
        return result

    def find_match(self, tokens, start, open_c, close_c):
        cnt = 1
        for i in range(start+1, len(tokens)):
            if tokens[i] == open_c: cnt += 1
            elif tokens[i] == close_c: cnt -= 1
            if cnt == 0: return i
        return len(tokens)

    def compute_min_depths(self):
        # Calculate minimum distance to full termination (only terminals) for each symbol
        depths = {k: float('inf') for k in self.rules}
        
        changed = True
        while changed:
            changed = False
            for lhs, prods in self.rules.items():
                curr_depth = depths[lhs]
                
                # Find min depth across all productions
                min_prod_depth = float('inf')
                
                for p in prods:
                    # For a production, depth is max depth of its constituents
                    prod_max = 0
                    possible = True
                    for t in p:
                        if t.startswith('<'):
                            d = depths.get(t, float('inf'))
                            if d == float('inf'):
                                possible = False
                                break
                            prod_max = max(prod_max, d)
                        else:
                            # Terminals have depth 0 relative contribution
                            pass
                    
                    if possible:
                        min_prod_depth = min(min_prod_depth, prod_max)
                
                new_depth = 1 + min_prod_depth
                if new_depth < curr_depth:
                    depths[lhs] = new_depth
                    changed = True
                    
        return depths

    def generate(self, symbol, depth, max_depth):
        # 1. Handle explicit empty token
        if symbol == '""': return ""
        
        # 2. Handle known missing primitives (Heuristic fallback)
        # If grammar uses <identifier> but doesn't define it
        if symbol.startswith('<') and symbol not in self.rules:
            s_lower = symbol.lower()
            if 'ident' in s_lower or 'name' in s_lower:
                return "col_" + "".join(random.choices(string.ascii_lowercase, k=2))
            if 'string' in s_lower:
                return "'val_" + "".join(random.choices(string.ascii_lowercase, k=2)) + "'"
            if 'number' in s_lower or 'int' in s_lower or 'float' in s_lower:
                return str(random.randint(0, 100))
            # Fallback for unknown non-terminals
            return ""

        # 3. Handle Terminals
        if not symbol.startswith('<'):
            # Strip quotes if present
            if (symbol.startswith('"') and symbol.endswith('"')) or \
               (symbol.startswith("'") and symbol.endswith("'")):
                if len(symbol) > 2:
                    return symbol[1:-1]
                return ""
            return symbol

        # 4. Handle Non-Terminals
        prods = self.rules.get(symbol, [])
        if not prods: return ""
        
        candidates = []
        
        # If exceeding depth, prioritize terminating paths
        if depth > max_depth:
            min_dist = float('inf')
            best_indices = []
            
            for i, p in enumerate(prods):
                # Calculate termination distance for this production
                d = 0
                possible = True
                for t in p:
                    if t.startswith('<'):
                        t_depth = self.min_depths.get(t, float('inf'))
                        if t_depth == float('inf'):
                            possible = False
                            break
                        d = max(d, t_depth)
                
                if possible:
                    if d < min_dist:
                        min_dist = d
                        best_indices = [i]
                    elif d == min_dist:
                        best_indices.append(i)
            
            if best_indices:
                candidates = best_indices
            else:
                candidates = list(range(len(prods)))
        else:
            candidates = list(range(len(prods)))
            
        # Weighted random selection favoring less used rules
        # Weights = 1 / (1 + usage_count)
        weights = []
        for i in candidates:
            count = self.coverage[symbol].get(i, 0)
            weights.append(1.0 / (1.0 + count))
            
        chosen_idx = random.choices(candidates, weights=weights, k=1)[0]
        
        # Update coverage
        self.coverage[symbol][chosen_idx] += 1
        
        # Recursively generate
        chosen_prod = prods[chosen_idx]
        result_parts = []
        for token in chosen_prod:
            res = self.generate(token, depth + 1, max_depth)
            if res:
                result_parts.append(res)
                
        return " ".join(result_parts)