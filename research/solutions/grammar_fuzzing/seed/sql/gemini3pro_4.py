import sys
import os
import re
import random
from collections import defaultdict

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        # Setup paths
        sys.path.append(resources_path)
        
        # Attempt to import parse_sql for validation
        parse_func = None
        try:
            from sql_engine.parser import parse_sql
            parse_func = parse_sql
        except ImportError:
            pass

        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        with open(grammar_path, 'r') as f:
            grammar_content = f.read()

        # Parse Grammar
        grammar = Grammar(grammar_content)
        
        # Generator
        generator = SQLGenerator(grammar)
        
        candidates = []
        unique_queries = set()
        history = [] # List of {'q': query, 'cov': coverage_set}

        # Generation Loop
        # We aim for high coverage. We'll generate a significant number of candidates
        # using different depth heuristics to ensure we hit both shallow and deep logic.
        max_attempts = 400
        attempts = 0
        
        while attempts < max_attempts:
            attempts += 1
            # Vary max_depth to encourage recursion or termination
            depth = random.choice([3, 5, 8, 10, 15])
            
            try:
                query, coverage = generator.generate(max_depth=depth)
            except Exception:
                continue

            if query in unique_queries:
                continue
            
            # Validate Syntax
            if parse_func:
                try:
                    parse_func(query)
                except Exception:
                    # Invalid query generated (grammar might be loose or generation unlucky)
                    continue
            
            unique_queries.add(query)
            history.append({'q': query, 'cov': coverage})

        # Select minimal set covering maximum grammar branches (Greedy Set Cover)
        final_suite = self.greedy_set_cover(history)
        
        # Post-processing: Inject comments/whitespace into a few queries for Tokenizer coverage
        if final_suite:
            # Append a comment to the first query
            final_suite[0] += " -- auto-generated comment"
            if len(final_suite) > 1:
                # Wrap second query in whitespace
                final_suite[1] = f"  \n  {final_suite[1]}  \t  "

        return final_suite

    def greedy_set_cover(self, history):
        if not history:
            return []
            
        universe = set()
        for h in history:
            universe.update(h['cov'])
            
        covered = set()
        selected_queries = []
        
        # Try to pick queries that contribute maximum new coverage
        remaining_candidates = list(history)
        
        while len(covered) < len(universe):
            best_candidate = None
            best_gain = -1
            best_idx = -1
            
            for i, h in enumerate(remaining_candidates):
                gain = len(h['cov'] - covered)
                if gain > best_gain:
                    best_gain = gain
                    best_candidate = h
                    best_idx = i
            
            if best_gain <= 0:
                break
                
            selected_queries.append(best_candidate['q'])
            covered.update(best_candidate['cov'])
            # Remove selected to avoid re-checking
            remaining_candidates.pop(best_idx)
            
        return selected_queries


class Grammar:
    def __init__(self, content):
        self.rules = {} # name -> list of list of tokens
        self.start_symbol = None
        self._parse(content)
        
    def _parse(self, content):
        # Clean comments
        lines = content.splitlines()
        clean_content = "\n".join(line.split('#')[0] for line in lines)
        
        # Tokenize
        # Captures: NonTerminal, Assignment, OR, Groups, Literals
        token_pattern = re.compile(r'(<[\w-]+>)|(::=)|(\|)|([\[\]\{\}\(\)])|("[^"]*")|(\'[^\']*\')|([^\s\[\]\{\}\(\)]+)')
        
        tokens = []
        for match in token_pattern.finditer(clean_content):
            tokens.append(match.group(0))
            
        idx = 0
        current_lhs = None
        current_rhs_tokens = []
        
        while idx < len(tokens):
            token = tokens[idx]
            
            # Check for Rule start: <Name> ::=
            if token.startswith('<') and token.endswith('>') and idx + 1 < len(tokens) and tokens[idx+1] == '::=':
                if current_lhs:
                    self.rules[current_lhs] = self.process_rhs(current_rhs_tokens)
                
                current_lhs = token.lower() # Normalize keys
                if not self.start_symbol:
                    self.start_symbol = current_lhs
                    
                current_rhs_tokens = []
                idx += 2 
                continue
            
            if current_lhs:
                current_rhs_tokens.append(token)
            idx += 1
            
        if current_lhs:
            self.rules[current_lhs] = self.process_rhs(current_rhs_tokens)

    def process_rhs(self, tokens):
        # Splits tokens by top-level | respecting brackets
        productions = []
        current_prod = []
        balance_stack = []
        
        for t in tokens:
            if t == '|' and not balance_stack:
                productions.append(current_prod)
                current_prod = []
            else:
                if t in ['[', '{', '(']:
                    balance_stack.append(t)
                elif t in [']', '}', ')']:
                    if balance_stack:
                        balance_stack.pop()
                current_prod.append(t)
        
        if current_prod:
            productions.append(current_prod)
        elif not productions and tokens: 
            # Case where only empty string? unlikely in BNF usually
            pass
            
        return productions


class SQLGenerator:
    def __init__(self, grammar):
        self.grammar = grammar
        self.coverage_stats = defaultdict(int) 
        
        # Primitives
        self.primitives = {
            '<identifier>': self._gen_id,
            '<string>': self._gen_str,
            '<string_literal>': self._gen_str,
            '<number>': self._gen_num,
            '<integer>': self._gen_int,
            '<float>': self._gen_float,
            '<boolean>': lambda: random.choice(['TRUE', 'FALSE']),
        }

    def _gen_id(self):
        return f"col_{random.randint(0, 3)}"
    
    def _gen_str(self):
        return f"'{random.choice(['foo', 'bar', 'test'])}'"
    
    def _gen_num(self):
        return str(random.choice([0, 1, 42, 123]))
        
    def _gen_int(self):
        return str(random.randint(0, 100))
        
    def _gen_float(self):
        return f"{random.randint(0,99)}.{random.randint(0,99)}"

    def generate(self, max_depth=10):
        self.current_coverage = set()
        res = self._gen_rule(self.grammar.start_symbol, 0, max_depth)
        return " ".join(res), self.current_coverage

    def _gen_rule(self, symbol, depth, max_depth):
        norm_symbol = symbol.lower()
        
        # Handle Primitives
        if norm_symbol in self.primitives:
            return [self.primitives[norm_symbol]()]
        
        # If unknown symbol, might be a primitive implicitly defined or just a token?
        if norm_symbol not in self.grammar.rules:
            # Check if it has semantic meaning like <INTEGER_LITERAL>
            if 'int' in norm_symbol: return [self._gen_int()]
            if 'float' in norm_symbol: return [self._gen_float()]
            if 'string' in norm_symbol: return [self._gen_str()]
            if 'ident' in norm_symbol or 'name' in norm_symbol: return [self._gen_id()]
            return [symbol] # Return as literal if nothing else matches
            
        productions = self.grammar.rules[norm_symbol]
        
        # Decision Logic
        candidates = list(range(len(productions)))
        
        # Depth limiting: prefer shorter productions if deep
        if depth > max_depth:
            candidates.sort(key=lambda i: len(productions[i]))
            candidates = candidates[:max(1, len(candidates)//2)]
            
        # Bias towards least used productions
        best_cand = random.choice(candidates)
        min_usage = float('inf')
        
        # Shuffle to break ties randomly
        random.shuffle(candidates)
        
        for i in candidates:
            usage = self.coverage_stats[(norm_symbol, i)]
            if usage < min_usage:
                min_usage = usage
                best_cand = i
        
        # Update stats
        self.coverage_stats[(norm_symbol, best_cand)] += 1
        self.current_coverage.add((norm_symbol, best_cand))
        
        return self._gen_sequence(productions[best_cand], depth + 1, max_depth)

    def _gen_sequence(self, tokens, depth, max_depth):
        result = []
        idx = 0
        while idx < len(tokens):
            token = tokens[idx]
            
            if token.startswith('<') and token.endswith('>'):
                result.extend(self._gen_rule(token, depth, max_depth))
            elif token in ['[', '{', '(']:
                close_map = {'[': ']', '{': '}', '(': ')'}
                close_char = close_map[token]
                block, new_idx = self._extract_block(tokens, idx, token, close_char)
                idx = new_idx
                
                # Parse block content as alternatives (handles | inside)
                sub_alts = self.grammar.process_rhs(block)
                
                if token == '[':
                    # Optional: 0 or 1
                    if random.random() > 0.3: # 70% chance to include
                        picked = random.choice(sub_alts)
                        result.extend(self._gen_sequence(picked, depth, max_depth))
                elif token == '{':
                    # Repeat: 0 to N
                    count = random.choice([0, 1, 1, 2, 3])
                    for _ in range(count):
                        picked = random.choice(sub_alts)
                        result.extend(self._gen_sequence(picked, depth, max_depth))
                elif token == '(':
                    # Group: exactly 1
                    picked = random.choice(sub_alts)
                    result.extend(self._gen_sequence(picked, depth, max_depth))
                    
            elif token in [']', '}', ')', '|']:
                # Should not be hit if block logic is correct, but safe ignore/literal
                pass
            else:
                # Terminal
                clean = token.strip("'").strip('"')
                result.append(clean)
            
            idx += 1
        return result

    def _extract_block(self, tokens, start_idx, open_char, close_char):
        balance = 1
        i = start_idx + 1
        block = []
        while i < len(tokens):
            t = tokens[i]
            if t == open_char:
                balance += 1
            elif t == close_char:
                balance -= 1
                if balance == 0:
                    return block, i
            block.append(t)
            i += 1
        return block, i