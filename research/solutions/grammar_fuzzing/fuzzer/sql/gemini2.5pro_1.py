import os
import re

class Solution:
    def solve(self, resources_path: str) -> dict:
        """
        Generates and returns the Python code for a SQL parser fuzzer.

        The strategy is a hybrid approach:
        1.  **Grammar Parsing**: The `solve` method pre-parses the provided SQL grammar
            and embeds it directly into the fuzzer code. This avoids file I/O during
            the time-critical fuzzing loop.
        2.  **Staged Fuzzing**: The fuzzer operates in stages to maximize coverage
            efficiently.
            -   **Stage 0 (Bootstrap)**: On the first call, a curated list of high-quality
                `INITIAL_SEEDS` is executed. This quickly covers the most common parser
                paths and provides a solid base corpus for mutation.
            -   **Stage 1 (Generation)**: The next phase focuses heavily on the grammar-based
                generator to produce a large volume of syntactically plausible SQL statements,
                exploring the valid input space.
            -   **Stage 2 (Mutation)**: The fuzzer then switches to mutating the existing
                corpus. This is highly effective at discovering edge cases and triggering
                error-handling logic, which is crucial for branch coverage.
            -   **Stage 3 (Mixed)**: For the remainder of the time, a mixed strategy is
                employed, combining grammar generation, mutation, and a small amount of
                random garbage generation to stress the tokenizer.
        3.  **Efficiency**: A large batch size (2000) is used for each call to `parse_sql`
            to minimize overhead and maximize the efficiency bonus.
        4.  **State Management**: A simple global state object persists the corpus and
            fuzzing progress across multiple calls to the `fuzz` function.
        """

        def parse_grammar_file(path: str) -> dict:
            """
            Parses a BNF-style grammar file into a dictionary representation.
            Assumes a simple format: `<non_terminal> ::= rule1 | rule2 ...`
            where each rule is a space-separated list of symbols.
            """
            grammar = {}
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '::=' not in line:
                            continue
                        
                        non_terminal, definition = line.split('::=', 1)
                        non_terminal = non_terminal.strip()
                        
                        alternatives = [alt.strip() for alt in definition.split('|')]
                        
                        rules = []
                        for alt in alternatives:
                            symbols = alt.split()
                            rules.append(symbols)

                        if non_terminal not in grammar:
                            grammar[non_terminal] = []
                        grammar[non_terminal].extend(rules)
            except IOError:
                # Provide a minimal fallback grammar if the file is not found.
                return {'<sql_statement>': [['SELECT', '1']]}
            return grammar

        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        parsed_grammar = parse_grammar_file(grammar_path)
        grammar_string = repr(parsed_grammar)

        fuzzer_code_string = f'''
import random
import sys
import re

# --- Embedded Grammar ---
# The grammar is parsed once by the solve() method and embedded here for efficiency.
# This avoids file I/O during the fuzzing loop.
PARSED_GRAMMAR = {grammar_string}

# --- Fuzzer State ---
# A simple class to hold state that persists across multiple calls to fuzz().
# This is managed as a global instance.
class FuzzerState:
    def __init__(self):
        self.call_count = 0
        self.corpus = set()
        self.init_done = False

state = FuzzerState()

# --- Initial Seed Corpus ---
# A curated list of SQL statements to kickstart fuzzing. This helps to quickly
# cover common code paths and provides a good base for mutation.
INITIAL_SEEDS = [
    # Basic DML
    "SELECT * FROM t1;",
    "SELECT c1, c2 FROM t1 WHERE c1 > 10;",
    "INSERT INTO t1 VALUES (1, 'a'), (2, 'b');",
    "UPDATE t1 SET c2 = 'c' WHERE c1 = 1;",
    "DELETE FROM t1 WHERE c1 = 2;",
    "SELECT 1;", "SELECT 1, 2;",
    
    # DDL
    "CREATE TABLE t1 (c1 INT, c2 VARCHAR(255));",
    "DROP TABLE t1;",
    "ALTER TABLE t1 ADD COLUMN c3 REAL;",
    "CREATE VIEW v1 AS SELECT c1 FROM t1;",
    "DROP VIEW v1;",
    "TRUNCATE TABLE t1;",
    
    # Complex Queries
    "SELECT COUNT(*) FROM t1 GROUP BY c1 HAVING COUNT(*) > 1;",
    "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id;",
    "SELECT * FROM t1 LEFT JOIN t2 ON t1.id = t2.id WHERE t2.id IS NULL;",
    "SELECT * FROM t1 ORDER BY c1 DESC, c2 ASC LIMIT 10 OFFSET 5;",
    "WITH cte AS (SELECT c1 FROM t1) SELECT * FROM cte;",
    
    # Expressions and Functions
    "SELECT 1 + 2 * 3, 'hello' || ' ' || 'world', ABS(-5);",
    "SELECT CASE WHEN c1 > 0 THEN 'pos' WHEN c1 < 0 THEN 'neg' ELSE 'zero' END FROM t1;",
    "SELECT * FROM t1 WHERE c1 IN (1, 2, 3) AND c2 LIKE 'a%';",
    "SELECT * FROM t1 WHERE c1 BETWEEN 10 AND 20;",
    "SELECT * FROM t1 WHERE c1 IS NOT NULL;",

    # Edge Cases & Malformed SQL
    "",                          # Empty string
    ";",                         # Just a semicolon
    "SELECT",                    # Incomplete statement
    "SELECT * FRM t1;",          # Typo
    "SELECT 1 / 0;",             # Division by zero (expression level)
    "CREATE TABLE t1(c1 INT c2 INT);", # Missing comma
    "INSERT INTO t1 (c1) VALUES (1, 2);", # Mismatched columns/values
    "SELECT 'unterminated string",
    "/* unterminated comment",
    "SELECT " + "a" * 1000 + ";", # Long identifier
    " " * 1000,                  # Lots of whitespace
    "\\n\\t \\r",                   # Various whitespace
]

# --- Grammar-based Generator ---
# This class generates SQL statements by recursively expanding grammar rules.
class GrammarGenerator:
    def __init__(self, grammar):
        self.grammar = grammar
        self.max_depth = 12
    
    def generate(self, symbol='<sql_statement>', depth=0):
        if depth > self.max_depth:
            return ""

        if symbol not in self.grammar:
            return symbol + " "

        rules = self.grammar.get(symbol)
        if not rules:
            return ""

        if depth > 5 and random.random() < 0.3:
            rule = min(rules, key=len)
        else:
            rule = random.choice(rules)

        # Handle optional clauses (represented by empty rules)
        if any(not r for r in rules) and random.random() < 0.15:
             return ""

        return "".join(self.generate(s, depth + 1) for s in rule).strip()

# --- Mutation Engine ---
# This class takes existing SQL statements and applies small changes to them
# to explore nearby code paths and trigger error handling logic.
class Mutator:
    def __init__(self):
        self.mutations = [
            self._delete_random_char,
            self._insert_random_char,
            self._transpose_chars,
            self._replace_char,
            self._change_number,
            self._change_keyword,
        ]
        self.keywords = [
            'SELECT', 'FROM', 'WHERE', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET',
            'DELETE', 'CREATE', 'TABLE', 'DROP', 'ALTER', 'VIEW', 'JOIN', 'ON', 'GROUP', 'BY',
            'ORDER', 'LIMIT', 'OFFSET', 'HAVING', 'AS', 'AND', 'OR', 'NOT', 'NULL', 'IS'
        ]
        self.chars_to_insert = "(),;*'-10/ \\t\\n"

    def mutate(self, s):
        if not s:
            return random.choice(self.chars_to_insert)
        
        num_mutations = random.randint(1, 2)
        for _ in range(num_mutations):
            if not s: break
            mutator_func = random.choice(self.mutations)
            s = mutator_func(s)
        return s

    def _delete_random_char(self, s):
        pos = random.randint(0, len(s) - 1)
        return s[:pos] + s[pos+1:]

    def _insert_random_char(self, s):
        pos = random.randint(0, len(s))
        return s[:pos] + random.choice(self.chars_to_insert) + s[pos:]

    def _transpose_chars(self, s):
        if len(s) < 2: return s
        pos = random.randint(0, len(s) - 2)
        return s[:pos] + s[pos+1] + s[pos] + s[pos+2:]

    def _replace_char(self, s):
        pos = random.randint(0, len(s) - 1)
        return s[:pos] + random.choice(self.chars_to_insert) + s[pos+1:]
        
    def _change_number(self, s):
        return re.sub(r'\\d+', lambda m: str(random.choice([0, 1, -1, 100, int(m.group(0))+1])), s, count=1)

    def _change_keyword(self, s):
        tokens = re.split(r'([ ,();\\t\\n])', s)
        kws_indices = [i for i, t in enumerate(tokens) if t.upper() in self.keywords]
        if kws_indices:
            idx_to_change = random.choice(kws_indices)
            tokens[idx_to_change] = random.choice(self.keywords)
        return "".join(tokens)


# --- Fuzzer Main Logic ---
generator = GrammarGenerator(PARSED_GRAMMAR)
mutator = Mutator()
if '<sql_statement>' not in PARSED_GRAMMAR:
    PARSED_GRAMMAR['<sql_statement>'] = [['SELECT', '1']]

def fuzz(parse_sql):
    global state
    
    if not state.init_done:
        state.corpus.update(INITIAL_SEEDS)
        parse_sql(list(state.corpus))
        state.init_done = True
        state.call_count += 1
        return True

    batch_size = 2000
    batch = []
    
    stage = state.call_count // 15

    if stage == 0: # Calls 1-15: Focus on grammar-based generation
        for _ in range(batch_size):
            start_symbol = random.choice(['<sql_statement>', '<select_statement>', '<insert_statement>', '<create_table_statement>'])
            gen_sql = generator.generate(start_symbol if start_symbol in PARSED_GRAMMAR else '<sql_statement>')
            batch.append(gen_sql)
            if 0 < len(gen_sql) < 200 and len(state.corpus) < 10000:
                state.corpus.add(gen_sql)

    elif stage == 1: # Calls 16-30: Focus on mutation
        corpus_list = list(state.corpus)
        if not corpus_list: corpus_list = INITIAL_SEEDS
        for _ in range(batch_size):
            seed = random.choice(corpus_list)
            batch.append(mutator.mutate(seed))
    
    else: # Calls 31+: Mixed strategy
        corpus_list = list(state.corpus)
        if not corpus_list: corpus_list = INITIAL_SEEDS
        
        num_grammar = int(batch_size * 0.60)
        num_mutation = int(batch_size * 0.38)
        
        for _ in range(num_grammar):
            start_symbol = random.choice(list(PARSED_GRAMMAR.keys()))
            batch.append(generator.generate(start_symbol))
        
        for _ in range(num_mutation):
            seed = random.choice(corpus_list)
            batch.append(mutator.mutate(seed))
            
        for _ in range(batch_size - num_grammar - num_mutation):
            length = random.randint(1, 40)
            batch.append("".join(random.choice("(),;*'-10/ \\t\\n`\\"") for _ in range(length)))

    parse_sql(batch)
    state.call_count += 1

    return True
'''
        return {"code": fuzzer_code_string}