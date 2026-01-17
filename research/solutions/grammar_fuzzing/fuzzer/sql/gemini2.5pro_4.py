import os
import re

class Solution:
    def solve(self, resources_path: str) -> dict:
        """
        Returns a dict with the fuzzer code.
        The fuzzer is a grammar-based generator with mutations.
        The SQL grammar is read from resources and baked into the fuzzer code string.
        """
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        try:
            with open(grammar_path, "r", encoding='utf-8') as f:
                grammar_content = f.read()
        except FileNotFoundError:
            # Provide a fallback grammar if the file is missing in some edge case
            grammar_content = 'sql_statement ::= "SELECT" "1";'

        fuzzer_code = f"""
import random
import re
import string

# --- Grammar Definition (baked in) ---
SQL_GRAMMAR_TEXT = {repr(grammar_content)}

# --- Fuzzer Implementation ---

class GrammarFuzzer:
    def __init__(self, grammar_text, max_depth=8):
        self.grammar = self._parse_grammar(grammar_text)
        if not self.grammar:
            raise ValueError("Grammar could not be parsed or is empty.")
        self.root_symbol = next(iter(self.grammar))
        self.max_depth = max_depth
        
        self.keywords = set()
        non_terminals = set(self.grammar.keys())
        for productions in self.grammar.values():
            for production in productions:
                for token in production:
                    if re.match(r'^[A-Z_][A-Z0-9_]*$', token) and token not in non_terminals:
                        self.keywords.add(token)
        
        if not self.keywords:
            self.keywords.update(["SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE", "DELETE", "CREATE", "TABLE"])

    def _parse_grammar(self, grammar_text):
        grammar = {{}}
        current_rule_name = None
        current_rule_def = ""

        lines = grammar_text.splitlines()
        for line in lines:
            line = line.split('#', 1)[0].strip()
            if not line:
                continue
            
            match = re.match(r'([a-z_][a-z0-9_]*)\\s*::=', line)
            if match:
                if current_rule_name:
                    productions = [p.strip() for p in current_rule_def.split('|')]
                    grammar[current_rule_name] = [self._tokenize_production(p) for p in productions]
                
                current_rule_name = match.group(1)
                current_rule_def = line[match.end():].strip()
            else:
                current_rule_def += " " + line
        
        if current_rule_name:
            productions = [p.strip() for p in current_rule_def.split('|')]
            grammar[current_rule_name] = [self._tokenize_production(p) for p in productions]
            
        return grammar

    def _tokenize_production(self, p_str):
        if not p_str:
            return []
        return re.findall(r'"[^"]+"|[a-zA-Z_][a-zA-Z0-9_]*|\\S+', p_str)

    def generate_one(self):
        s = self._generate_symbol(self.root_symbol, 0)
        if random.random() < 0.20:
            s = self._mutate(s)
        return s.strip()

    def _generate_symbol(self, symbol, depth):
        if depth > self.max_depth or (depth > self.max_depth / 2 and random.random() < 0.2):
            return ""
        
        if symbol not in self.grammar:
            if symbol.startswith('"'):
                return symbol[1:-1]
            
            if symbol == 'IDENTIFIER': return self._generate_identifier()
            if symbol == 'STRING_LITERAL': return self._generate_string()
            if symbol == 'INTEGER_LITERAL': return self._generate_integer()
            if symbol == 'FLOAT_LITERAL': return self._generate_float()
            if symbol == 'HEX_LITERAL': return f"X'{{''.join(random.choices('0123456789abcdef', k=random.choice([2, 4, 8])))}}'"
            
            return symbol

        productions = self.grammar[symbol]
        if not productions:
            return ""

        weights = [len(p) + 1 for p in productions]
        chosen_production = random.choices(productions, weights=weights, k=1)[0]

        parts = [self._generate_symbol(part, depth + 1) for part in chosen_production]
        return " ".join(filter(None, parts))

    def _generate_identifier(self):
        r = random.random()
        if r < 0.6:
            return random.choice(['t', 't1', 'users', 'orders', 'id', 'name', 'value', 'c1'])
        elif r < 0.8:
            name = random.choice(string.ascii_lowercase + '_')
            name += ''.join(random.choices(string.ascii_lowercase + string.digits + '_', k=random.randint(0, 7)))
            return name
        else:
            return random.choice(list(self.keywords))

    def _generate_string(self):
        content_chars = string.ascii_letters + string.digits + " _-%'\\/"
        content = ''.join(random.choices(content_chars, k=random.randint(0, 10)))
        return f"'{content.replace("'", "''")}'"

    def _generate_integer(self):
        if random.random() < 0.2:
            return str(random.choice([0, 1, -1, 2147483647, -2147483648, 9223372036854775807]))
        return str(random.randint(-1000, 1000))

    def _generate_float(self):
        return f"{{random.uniform(-1e6, 1e6):.4f}}"

    def _mutate(self, sql):
        mutators = [
            self._mutate_replace_keyword,
            self._mutate_char_swap,
            self._mutate_char_insert,
            self._mutate_char_delete,
            self._mutate_add_punctuation,
        ]
        if not sql: return "';--("
        mutator = random.choice(mutators)
        return mutator(sql)

    def _mutate_replace_keyword(self, sql):
        if len(self.keywords) < 2: return sql
        k1, k2 = random.sample(list(self.keywords), 2)
        return sql.replace(k1, k2, 1)

    def _mutate_char_swap(self, sql):
        if len(sql) < 2: return sql
        i, j = random.sample(range(len(sql)), 2)
        l = list(sql)
        l[i], l[j] = l[j], l[i]
        return "".join(l)

    def _mutate_char_insert(self, sql):
        pos = random.randint(0, len(sql))
        char = random.choice("';(),`\\"--\\t\\n\\x00")
        return sql[:pos] + char + sql[pos:]

    def _mutate_char_delete(self, sql):
        if not sql: return sql
        pos = random.randint(0, len(sql)-1)
        return sql[:pos] + sql[pos+1:]

    def _mutate_add_punctuation(self, sql):
        pos = random.randint(0, len(sql))
        punc = random.choice([";", "(", ")", ",", "'", '"', "`"])
        return sql[:pos] + punc + sql[pos:]

# --- Fuzzer Entrypoint ---

FUZZER_INSTANCE = None
BATCH_SIZE = 2000

class RandomFallbackFuzzer:
    def generate_one(self):
        length = random.randint(5, 60)
        return ''.join(random.choices(string.ascii_letters + string.digits + " _'(),;=*-/", k=length))

def fuzz(parse_sql):
    global FUZZER_INSTANCE

    if FUZZER_INSTANCE is None:
        try:
            FUZZER_INSTANCE = GrammarFuzzer(SQL_GRAMMAR_TEXT)
        except Exception:
            FUZZER_INSTANCE = RandomFallbackFuzzer()

    statements = [FUZZER_INSTANCE.generate_one() for _ in range(BATCH_SIZE)]
    
    parse_sql(statements)
    
    return True
"""
        return {"code": fuzzer_code}