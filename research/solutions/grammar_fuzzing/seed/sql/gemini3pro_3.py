import sys
import os
import re
import random

class Solution:
    def solve(self, resources_path: str) -> list[str]:
        # Ensure we can import from the engine if needed (though we mostly rely on grammar)
        if resources_path not in sys.path:
            sys.path.append(resources_path)
            
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        
        # 1. Parse Grammar
        try:
            with open(grammar_path, "r") as f:
                grammar_text = f.read()
        except FileNotFoundError:
            # Fallback if file not found, return edge cases
            return self._get_edge_cases()

        grammar = Grammar(grammar_text)
        generator = SQLGenerator(grammar)
        
        test_cases = set()
        
        # 2. Coverage-Guided Generation
        # Strategy: Generate enough statements to cover grammar branches while keeping N low for efficiency score.
        # We aim for ~60-80 high-quality statements.
        
        # Attempt to saturate the visited rules set
        for _ in range(250):
            stmt = generator.generate()
            if stmt:
                test_cases.add(stmt)
            # Cap at reasonable number to protect efficiency score
            if len(test_cases) > 80:
                break
        
        # 3. Add Hardcoded Edge Cases
        # These ensure tokenizer coverage (comments, weird numbers) and common paths potentially missed by random walk.
        edge_cases = self._get_edge_cases()
        
        final_suite = list(test_cases)
        for ec in edge_cases:
            if ec not in test_cases:
                final_suite.append(ec)
        
        # Shuffle result
        random.shuffle(final_suite)
        
        return final_suite

    def _get_edge_cases(self) -> list[str]:
        return [
            # Basic
            "SELECT 1",
            "SELECT * FROM t1",
            
            # Comments (Tokenizer coverage)
            "SELECT 1 -- line comment",
            "SELECT 1 /* block comment */ FROM t1",
            "SELECT 1 /* multi\nline\ncomment */ FROM t1",
            
            # Numeric formats (Tokenizer coverage)
            "SELECT 123",
            "SELECT -123",
            "SELECT +123",
            "SELECT 12.34",
            "SELECT .56",
            "SELECT 12.",
            "SELECT 1.2E3",
            "SELECT 1.2e-3",
            
            # Strings and Escapes
            "SELECT 'simple'",
            "SELECT 'with '' quote'",
            "SELECT \"double quoted identifier\"",
            
            # Operators
            "SELECT 1+1, 2-2, 3*3, 4/4, 5%5",
            "SELECT * FROM t1 WHERE a=1 AND b<>2 OR c!=3",
            "SELECT * FROM t1 WHERE a<1 AND b>2 AND c<=3 AND d>=4",
            
            # Optional clauses logic
            "SELECT * FROM t1 WHERE 1=1",
            "SELECT * FROM t1 ORDER BY c1",
            "SELECT * FROM t1 GROUP BY c1",
            "SELECT * FROM t1 GROUP BY c1 HAVING count(*) > 1",
            
            # Joins
            "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t1 LEFT JOIN t2 ON t1.id = t2.id",
        ]

class Grammar:
    def __init__(self, text):
        self.rules = {}
        self.start_symbol = None
        self._parse_grammar(text)
        
    def _parse_grammar(self, text):
        # Remove comments
        lines = [l.split('#')[0].strip() for l in text.split('\n')]
        clean_text = " ".join([l for l in lines if l])
        
        # Regex to tokenize the grammar definition
        # Matches: ::=, |, [, ], {, }, <non-term>, 'term', "term", word, symbols
        token_pattern = re.compile(r"(::=|\||\[|\]|\{|\}|\(|\)|<[\w-]+>|'[^']*'|\"[^\"]*\"|[a-zA-Z_]\w*|[^\s\w]+)")
        tokens = token_pattern.findall(clean_text)
        
        idx = 0
        while idx < len(tokens):
            tok = tokens[idx]
            # Look for Rule Definition: <name> ::= ...
            if tok.startswith('<') and idx + 1 < len(tokens) and tokens[idx+1] == '::=':
                rule_name = tok
                idx += 2 # Skip name and ::=
                
                # Extract tokens for this rule until next rule starts
                rule_tokens = []
                while idx < len(tokens):
                    # Peek ahead to see if a new rule is starting
                    if tokens[idx].startswith('<') and idx + 1 < len(tokens) and tokens[idx+1] == '::=':
                        break
                    rule_tokens.append(tokens[idx])
                    idx += 1
                
                if not self.start_symbol:
                    self.start_symbol = rule_name
                    
                self.rules[rule_name] = self._parse_rhs(rule_tokens)
            else:
                idx += 1
                
    def _parse_rhs(self, tokens):
        # Returns a list of alternatives.
        # Each alternative is a list of nodes.
        # Node: ('TERM', val), ('NONTERM', val), ('OPT', list_of_alts), ('REP', list_of_alts)
        
        alts = []
        current_alt = []
        
        idx = 0
        while idx < len(tokens):
            t = tokens[idx]
            
            if t == '|':
                alts.append(current_alt)
                current_alt = []
                idx += 1
            elif t == '[':
                # Optional block
                depth = 1
                end = idx + 1
                while end < len(tokens) and depth > 0:
                    if tokens[end] == '[': depth += 1
                    elif tokens[end] == ']': depth -= 1
                    end += 1
                
                inner_tokens = tokens[idx+1:end-1]
                inner_alts = self._parse_rhs(inner_tokens)
                current_alt.append(('OPT', inner_alts))
                idx = end
            elif t == '{':
                # Repetition block
                depth = 1
                end = idx + 1
                while end < len(tokens) and depth > 0:
                    if tokens[end] == '{': depth += 1
                    elif tokens[end] == '}': depth -= 1
                    end += 1
                
                inner_tokens = tokens[idx+1:end-1]
                inner_alts = self._parse_rhs(inner_tokens)
                current_alt.append(('REP', inner_alts))
                idx = end
            elif t.startswith("'") or t.startswith('"'):
                current_alt.append(('TERM', t[1:-1]))
                idx += 1
            elif t.startswith('<'):
                current_alt.append(('NONTERM', t))
                idx += 1
            elif re.match(r"[a-zA-Z_]\w*", t):
                # Unquoted terminal word
                current_alt.append(('TERM', t))
                idx += 1
            else:
                # Symbols like , ; ( ) *
                current_alt.append(('TERM', t))
                idx += 1
                
        if current_alt:
            alts.append(current_alt)
        elif not alts:
            alts.append([]) # Empty production
            
        return alts

class SQLGenerator:
    def __init__(self, grammar):
        self.grammar = grammar
        self.visited = set() # (rule_name, alt_index)
        self.max_depth = 10
        self.recursion_counts = {}
        
    def generate(self):
        self.recursion_counts = {}
        if not self.grammar.start_symbol:
            return ""
        return self._gen_node(self.grammar.start_symbol, 0)
        
    def _gen_node(self, symbol, depth):
        if depth > self.max_depth:
            return self._fallback(symbol)
            
        if symbol not in self.grammar.rules:
            return self._gen_terminal(symbol)
            
        # Select Alternative
        alts = self.grammar.rules[symbol]
        candidates = list(range(len(alts)))
        
        # Biased selection towards unvisited alternatives to maximize coverage
        unvisited = [i for i in candidates if (symbol, i) not in self.visited]
        if unvisited:
            choice = random.choice(unvisited)
        else:
            choice = random.choice(candidates)
            
        self.visited.add((symbol, choice))
        
        # Build string
        parts = []
        for node in alts[choice]:
            res = self._process_node(node, depth + 1)
            if res:
                parts.append(res)
                
        return " ".join(parts)
        
    def _process_node(self, node, depth):
        type_, val = node
        
        if type_ == 'TERM':
            return val
        elif type_ == 'NONTERM':
            # Check recursion limit for this specific symbol to prevent infinite loops
            if val not in self.recursion_counts: self.recursion_counts[val] = 0
            self.recursion_counts[val] += 1
            if self.recursion_counts[val] > 3: 
                return self._fallback(val)
            return self._gen_node(val, depth)
        elif type_ == 'OPT':
            # Optional: 50/50 chance
            if random.random() < 0.5:
                return ""
            # Pick one sub-alternative
            sub_alts = val
            sub_choice = random.choice(sub_alts)
            res = []
            for n in sub_choice:
                p = self._process_node(n, depth)
                if p: res.append(p)
            return " ".join(res)
        elif type_ == 'REP':
            # Repetition: 1 to 3 times
            count = random.randint(1, 3)
            res = []
            sub_alts = val
            for _ in range(count):
                sub_choice = random.choice(sub_alts)
                parts = []
                for n in sub_choice:
                    p = self._process_node(n, depth)
                    if p: parts.append(p)
                res.append(" ".join(parts))
            return " ".join(res)
        return ""
        
    def _gen_terminal(self, symbol):
        s = symbol.lower()
        if 'ident' in s or 'name' in s:
            return random.choice(['t1', 't2', 'col1', 'col2', 'id', 'idx', 'users'])
        if 'int' in s: return str(random.randint(0, 100))
        if 'float' in s: return str(round(random.random() * 100, 2))
        if 'string' in s or 'literal' in s: return "'val'"
        if 'op' in s: return random.choice(['=', '<', '>', '<=', '>=', '<>', '!='])
        return "x" # Generic fallback

    def _fallback(self, symbol):
        # Minimal valid production to stop recursion
        s = symbol.lower()
        if 'expr' in s: return "1"
        if 'stmt' in s: return "SELECT 1"
        if 'table' in s: return "t1"
        if 'col' in s: return "c1"
        if 'cond' in s: return "1=1"
        return self._gen_terminal(symbol)