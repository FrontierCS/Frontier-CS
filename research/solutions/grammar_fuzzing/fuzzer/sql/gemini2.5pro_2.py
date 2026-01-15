import os

class Solution:
    def solve(self, resources_path: str) -> dict:
        grammar_path_repr = repr(os.path.join(resources_path, 'sql_grammar.txt'))

        fuzzer_code_template = """
import random
import re
import string

class GrammarFuzzer:
    _instance = None

    def __init__(self, grammar_file_path):
        # --- Configuration ---
        self.MAX_RECURSION_DEPTH = 8
        self.BATCH_SIZE = 2000
        self.GENERATION_PHASE_CALLS = 4
        self.MUTATION_RATE = 0.5
        self.CORPUS_SIZE_LIMIT = 1500

        # --- State ---
        self.grammar = {{}}
        self.call_count = 0
        self.corpus = set()
        self.start_symbol = "<sql_statement>"
        
        self._parse_grammar(grammar_file_path)
        
        # --- Fuzzing Resources ---
        self.terminals = {{
            '<identifier>': ['t', 'c', 'users', 'products', 'orders', 't1', 'c1', 'id', 'name', 'price', 'tbl', 'col', 'a_long_identifier_name_to_test_limits'],
            '<string_literal>': ["'hello'", "'world'", "''", "'a''b'", "'%pattern%'", "'_'", "';'", "'--'", "'/* comment */'"],
            '<numeric_literal>': ['1', '0', '123', '3.14', '0.0', '-5', '1e5', '1.2e-3', '99999999999999999999', '-1.23456789E-10'],
            '<integer_literal>': ['0', '1', '10', '999', '-50', '2147483647', '-2147483648'],
            '<float_literal>': ['0.0', '1.23', '-4.56', '1e9', '2.3E-4'],
            '<boolean_literal>': ['TRUE', 'FALSE', 'UNKNOWN'],
        }}

        self.sql_keywords = [
            "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE", "SET",
            "DELETE", "CREATE", "TABLE", "DROP", "ALTER", "ADD", "COLUMN", "AND",
            "OR", "NOT", "NULL", "IS", "AS", "ON", "JOIN", "LEFT", "RIGHT", "INNER",
            "OUTER", "GROUP", "BY", "ORDER", "HAVING", "LIMIT", "OFFSET", "DISTINCT",
            "ALL", "ANY", "BETWEEN", "EXISTS", "IN", "LIKE", "PRIMARY", "KEY",
            "FOREIGN", "REFERENCES", "UNIQUE", "CHECK", "DEFAULT", "INDEX", "CAST", "CASE"
        ]
        self.special_chars = list("`~!@#$%^&*()-_=+[]{{}}|;':\\\",./<>? \\t\\n\\r")

        self.mutators = [
            self._insert_random_char,
            self._delete_random_char,
            self._replace_random_char,
            self._duplicate_substring,
            self._swap_chars,
            self._insert_keyword,
            self._bit_flip,
        ]

    @staticmethod
    def get_instance(grammar_file_path):
        if GrammarFuzzer._instance is None:
            GrammarFuzzer._instance = GrammarFuzzer(grammar_file_path)
        return GrammarFuzzer._instance

    def _parse_grammar(self, grammar_file):
        try:
            with open(grammar_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '::=' not in line:
                        continue
                    non_terminal, productions = line.split('::=', 1)
                    non_terminal = non_terminal.strip()
                    productions_list = [p.strip() for p in productions.split('|')]
                    self.grammar[non_terminal] = productions_list
        except Exception:
            self.grammar = {{
                "<sql_statement>": ["<select_statement>", "<insert_statement>", "<create_statement>"],
                "<select_statement>": ["'SELECT' '*' 'FROM' <identifier>"],
                "<insert_statement>": ["'INSERT' 'INTO' <identifier> 'VALUES' '(' <numeric_literal> ')'"],
                "<create_statement>": ["'CREATE' 'TABLE' <identifier> '(' <identifier> ')'"]
            }}

    def _generate(self, symbol, depth):
        if depth > self.MAX_RECURSION_DEPTH:
            if symbol in self.terminals: return random.choice(self.terminals[symbol])
            if symbol in self.grammar:
                for prod in sorted(self.grammar[symbol], key=lambda k: random.random()):
                    if '<' not in prod:
                         parts = re.findall(r"'[^']+'|[^\s']+", prod)
                         return " ".join([p.strip("'") for p in parts])
            return "..."

        if symbol in self.terminals:
            return random.choice(self.terminals[symbol])

        if symbol not in self.grammar:
            return symbol.strip("'")

        productions = self.grammar.get(symbol, [])
        if not productions: return symbol.strip("'")

        chosen_production = random.choice(productions)
        
        parts = re.findall(r"(<[^>]+>|'[^']+'|[^\s<>']+)", chosen_production)
        
        result = [self._generate(part, depth + 1) for part in parts]
        return " ".join(filter(None, result))

    def generate_new_inputs(self, count):
        inputs = []
        for _ in range(count):
            new_sql = self._generate(self.start_symbol, 0)
            new_sql = re.sub(r'\\s+', ' ', new_sql).strip()
            if random.random() < 0.2: new_sql += ";"
            inputs.append(new_sql)
            if len(self.corpus) < self.CORPUS_SIZE_LIMIT:
                self.corpus.add(new_sql)
        return inputs
        
    def _insert_random_char(self, s):
        if not s: return random.choice(self.special_chars)
        pos = random.randint(0, len(s))
        return s[:pos] + random.choice(self.special_chars) + s[pos:]

    def _delete_random_char(self, s):
        if len(s) < 2: return ""
        pos = random.randint(0, len(s) - 1)
        return s[:pos] + s[pos+1:]

    def _replace_random_char(self, s):
        if not s: return ""
        pos = random.randint(0, len(s) - 1)
        return s[:pos] + random.choice(self.special_chars) + s[pos+1:]
        
    def _duplicate_substring(self, s):
        if len(s) < 2: return s + s
        start = random.randint(0, len(s) - 1)
        end = random.randint(start + 1, len(s))
        substring = s[start:end]
        repeat = random.randint(2, 5)
        pos = random.randint(0, len(s))
        return s[:pos] + (substring + " ") * repeat + s[pos:]

    def _swap_chars(self, s):
        if len(s) < 2: return s
        p1, p2 = random.sample(range(len(s)), 2)
        l = list(s)
        l[p1], l[p2] = l[p2], l[p1]
        return "".join(l)
        
    def _insert_keyword(self, s):
        pos = random.randint(0, len(s)) if s else 0
        return s[:pos] + " " + random.choice(self.sql_keywords) + " " + s[pos:]

    def _bit_flip(self, s):
        if not s: return s
        pos = random.randint(0, len(s) - 1)
        char_code = ord(s[pos])
        bit = 1 << random.randint(0, 6)
        new_char_code = char_code ^ bit
        if 32 <= new_char_code <= 126:
            return s[:pos] + chr(new_char_code) + s[pos+1:]
        return s

    def mutate(self, s):
        num_mutations = random.randint(1, 3)
        for _ in range(num_mutations):
            if not s: break
            s = random.choice(self.mutators)(s)
        return s

    def run_fuzz_step(self):
        self.call_count += 1
        
        if self.call_count <= self.GENERATION_PHASE_CALLS:
            return self.generate_new_inputs(self.BATCH_SIZE)
        
        batch = []
        num_new = int(self.BATCH_SIZE * (1 - self.MUTATION_RATE))
        if num_new > 0:
            batch.extend(self.generate_new_inputs(num_new))
        
        num_mutations = self.BATCH_SIZE - num_new
        if num_mutations > 0:
            if not self.corpus:
                 batch.extend(self.generate_new_inputs(num_mutations))
            else:
                corpus_list = list(self.corpus)
                for _ in range(num_mutations):
                    seed = random.choice(corpus_list)
                    batch.append(self.mutate(seed))
        
        random.shuffle(batch)
        return batch

_fuzzer_instance = None

def fuzz(parse_sql):
    global _fuzzer_instance
    if _fuzzer_instance is None:
        grammar_path = {grammar_path_repr}
        _fuzzer_instance = GrammarFuzzer.get_instance(grammar_path)

    statements = _fuzzer_instance.run_fuzz_step()
    parse_sql(statements)
    return True
"""
        return {"code": fuzzer_code_template.format(grammar_path_repr=grammar_path_repr)}