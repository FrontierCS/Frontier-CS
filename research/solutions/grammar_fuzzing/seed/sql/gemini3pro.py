import os
import re
import random
import sys
import collections

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        grammar_path = os.path.join(resources_path, 'sql_grammar.txt')
        grammar = Grammar(grammar_path)
        generator = Generator(grammar)
        
        # We aim for high coverage. 
        # Strategies:
        # 1. Structural coverage: Ensure every grammar rule and alternative is touched.
        # 2. Depth variation: Simple vs complex queries.
        # 3. Semantic variation: Different keywords/operators.
        
        test_cases = set()
        
        # Phase 1: Targeted expansion of all grammar rules
        # Attempt to cover every alternative of every rule
        
        # We define a 'budget' of attempts. 
        # Efficiency metric: 50 is ref. We target ~60-80 diverse queries.
        
        # Generate queries trying to hit uncovered production rules
        for _ in range(100):
            # Reset generator transient state if needed, but keep coverage stats
            sql = generator.generate_guided()
            if sql:
                test_cases.add(sql)
                
        # Phase 2: Random deep exploration
        for _ in range(20):
            sql = generator.generate_random(depth_limit=6)
            if sql:
                test_cases.add(sql)
                
        return list(test_cases)

class Grammar:
    def __init__(self, filepath):
        self.rules = {}
        self.start_rule = None
        self._load(filepath)
        self.min_lengths = {}
        self._compute_min_lengths()

    def _load(self, filepath):
        with open(filepath, 'r') as f:
            lines = f.readlines()
            
        current_lhs = None
        current_rhs_text = []
        
        raw_defs = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Check for new rule definition (::= or :)
            # Standard BNF usually uses ::=
            # We assume the grammar is reasonably standard
            if '::=' in line:
                parts = line.split('::=', 1)
                if current_lhs:
                    raw_defs.append((current_lhs, " ".join(current_rhs_text)))
                current_lhs = parts[0].strip()
                current_rhs_text = [parts[1].strip()]
            else:
                if current_lhs:
                    current_rhs_text.append(line)
        
        if current_lhs:
            raw_defs.append((current_lhs, " ".join(current_rhs_text)))
            
        if not raw_defs:
            return

        self.start_rule = raw_defs[0][0]
        
        for lhs, rhs in raw_defs:
            # Split alternatives by |
            # Need to be careful not to split quoted pipes, but usually pipe is top level
            # Simple split is risky if grammar has literals with pipe.
            # Assuming standard BNF where | is a metacharacter.
            
            # Simple tokenizer for the RHS string to respect quotes
            # We just split by | that is not in quotes.
            alternatives = self._split_alternatives(rhs)
            
            parsed_alts = []
            for alt in alternatives:
                tokens = self._tokenize(alt)
                parsed_alts.append(tokens)
            
            self.rules[lhs] = parsed_alts

    def _split_alternatives(self, text):
        # Split by | but ignore within quotes
        alts = []
        current = []
        in_quote = None
        for char in text:
            if char == '"' or char == "'":
                if in_quote == char:
                    in_quote = None
                elif in_quote is None:
                    in_quote = char
                current.append(char)
            elif char == '|' and in_quote is None:
                alts.append("".join(current).strip())
                current = []
            else:
                current.append(char)
        alts.append("".join(current).strip())
        return [a for a in alts if a] # Filter empty if any (unless epsilon explicitly handled later)

    def _tokenize(self, text):
        # Matches: <non-terminal>, "terminal", 'terminal', or bare words
        pattern = re.compile(r'(<[^>]+>|"[^"]*"|\'[^\']*\'|\S+)')
        return pattern.findall(text)

    def _compute_min_lengths(self):
        # Compute minimum expansion cost for each rule (avoid infinite recursion)
        # Dijkstra / Bellman-Ford style
        for rule in self.rules:
            self.min_lengths[rule] = float('inf')
        
        changed = True
        while changed:
            changed = False
            for rule, alts in self.rules.items():
                current_min = self.min_lengths[rule]
                new_min = float('inf')
                
                for alt in alts:
                    alt_len = 0
                    for token in alt:
                        if token.startswith('<') and token.endswith('>'):
                            # Non-terminal
                            alt_len += self.min_lengths.get(token, 1) # If unknown, assume 1 (primitive)
                        else:
                            # Terminal
                            alt_len += 1
                    
                    if alt_len < new_min:
                        new_min = alt_len
                
                if new_min < current_min:
                    self.min_lengths[rule] = new_min
                    changed = True

class Generator:
    def __init__(self, grammar):
        self.grammar = grammar
        self.covered_alts = set() # (rule_name, alt_index)
        
        # Primitives definitions for undefined non-terminals
        self.primitives = {
            'identifier': ['id_1', 'col_a', 'table_x', 'my_var'],
            'ident': ['x', 'y', 'z'],
            'string': ["'test'", "'data'"],
            'number': ['1', '42', '100', '3.14'],
            'integer': ['1', '0', '99'],
            'int': ['5', '10'],
            'boolean': ['TRUE', 'FALSE']
        }
        
    def generate_guided(self):
        # Try to generate a query that hits uncovered alternatives
        # We start from start_rule and prefer paths with uncovered nodes
        return self._gen(self.grammar.start_rule, depth=0, mode='guided')

    def generate_random(self, depth_limit=5):
        return self._gen(self.grammar.start_rule, depth=0, mode='random', max_depth=depth_limit)

    def _gen(self, symbol, depth, mode='random', max_depth=8):
        # 1. Handle Primitives and Terminals
        if not (symbol.startswith('<') and symbol.endswith('>')):
            # It's a terminal. Strip quotes if present.
            if (symbol.startswith('"') and symbol.endswith('"')) or \
               (symbol.startswith("'") and symbol.endswith("'")):
                return symbol[1:-1]
            return symbol

        # 2. Check if rule exists
        if symbol not in self.grammar.rules:
            # Fallback for undefined non-terminals
            key = symbol.strip('<>').lower()
            # Try partial match in primitives
            for p_key, vals in self.primitives.items():
                if p_key in key:
                    return random.choice(vals)
            # Generic fallback
            if 'name' in key or 'ident' in key: return 'obj_1'
            if 'num' in key: return '123'
            return 'NULL' # Last resort

        # 3. Select Alternative
        alternatives = self.grammar.rules[symbol]
        
        # Depth Control: If too deep, prefer shortest path
        if depth > max_depth:
            # Pick alternative with minimum expansion cost
            best_alt = None
            min_cost = float('inf')
            for alt in alternatives:
                cost = 0
                for token in alt:
                    if token.startswith('<'):
                        cost += self.grammar.min_lengths.get(token, 1)
                    else:
                        cost += 1
                if cost < min_cost:
                    min_cost = cost
                    best_alt = alt
            choice = best_alt if best_alt else alternatives[0]
        else:
            # Selection Logic
            if mode == 'guided':
                # Prioritize alternatives not yet fully covered
                candidates = []
                uncovered_indices = []
                
                for i, alt in enumerate(alternatives):
                    candidates.append(alt)
                    if (symbol, i) not in self.covered_alts:
                        uncovered_indices.append(i)
                
                if uncovered_indices:
                    # Pick an uncovered one
                    idx = random.choice(uncovered_indices)
                    choice = alternatives[idx]
                    self.covered_alts.add((symbol, idx))
                else:
                    # All covered, pick random
                    choice = random.choice(alternatives)
            else:
                # Random mode
                choice = random.choice(alternatives)

        # 4. Expand Choice
        result_parts = []
        for token in choice:
            part = self._gen(token, depth + 1, mode, max_depth)
            result_parts.append(part)
            
        return " ".join(result_parts)