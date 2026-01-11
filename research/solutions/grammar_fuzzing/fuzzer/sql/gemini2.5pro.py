import os
import re

class Solution:
    """
    Implements the fuzzer solution for the SQL Parser Fuzzing problem.
    This solution uses a grammar-based generative approach combined with mutation-based
    fuzzing to maximize code coverage of the target SQL parser.
    """
    def solve(self, resources_path: str) -> dict:
        """
        Reads the SQL grammar from the provided resources path and injects it into
        a self-contained fuzzer script string.

        Args:
            resources_path: Path to the directory containing `sql_grammar.txt`.

        Returns:
            A dictionary containing the fuzzer code as a single string.
        """
        grammar_path = os.path.join(resources_path, 'sql_grammar.txt')
        try:
            with open(grammar_path, 'r', encoding='utf-8') as f:
                grammar_content = f.read()
        except FileNotFoundError:
            # Provide a minimal fallback grammar if the file is missing
            grammar_content = """
<sql_statement> ::= <select_statement> | <insert_statement>
<select_statement> ::= 'SELECT' <select_list> 'FROM' <identifier>
<insert_statement> ::= 'INSERT' 'INTO' <identifier> 'VALUES' '(' <literal_list> ')'
<select_list> ::= '*' | <identifier>
<literal_list> ::= <integer_literal> | <string_literal>
"""

        # This is the fuzzer implementation as a self-contained Python script string.
        # The SQL grammar read from resources_path will be embedded into this string.
        fuzzer_code = """
import random
import string
import re
import time

# --- State (global variables) ---
# These variables persist across multiple calls to the fuzz() function.
GRAMMAR = None
NON_TERMINALS = None
START_TIME = None
TIME_BUDGET = 58  # seconds, leave a small safety margin for teardown.
GENERATOR = None

# --- Grammar Parsing ---
def _parse_grammar(grammar_content):
    """
    Parses a BNF-style grammar text into a dictionary representation.
    This parser is designed to be robust against multi-line rule definitions.
    """
    grammar = {}
    # Use regex to split the grammar text by rule definitions (<symbol> ::=).
    # The capturing group ensures the rule name is kept as a delimiter.
    rule_declarations = re.split(r'(<[^>]+>\\s*::=)', grammar_content)
    
    if len(rule_declarations) < 2:
        return {}  # No rules found

    # The split results in a list like ['', '<rule1>::=', 'body1', '<rule2>::=', 'body2', ...].
    # We iterate over the pairs of [rule_name, rule_body].
    for i in range(1, len(rule_declarations), 2):
        name_part = rule_declarations[i]
        rules_part = rule_declarations[i+1]
        
        name = name_part.replace('::=', '').strip()
        
        rules = []
        # Each rule body can have alternatives separated by '|'.
        for rule_str in rules_part.split('|'):
            rule_str = rule_str.strip()
            if not rule_str:
                continue
            # Tokenize the rule into terminals (quoted), non-terminals (bracketed), and keywords.
            symbols = re.findall(r"'[^']+'|<[^>]+>|[^\\s]+", rule_str)
            symbols = [s.strip() for s in symbols if s.strip()]
            if symbols:
                rules.append(symbols)
        
        if rules:
            grammar[name] = rules
    return grammar

# --- Primitive Value Generators ---
# These functions generate random values for terminal types like identifiers and literals.
def _generate_identifier():
    # Mix in keywords to test parsing of reserved words in identifier contexts.
    keywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE', 'INTEGER', 'VARCHAR', 'TEXT', 'PRIMARY', 'KEY', 'AND', 'OR', 'NOT', 'NULL', 'AS', 'ORDER', 'BY', 'ASC', 'DESC', 'LIMIT', 'OFFSET', 'JOIN', 'ON', 'GROUP', 'HAVING', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX']
    if random.random() < 0.1:
        return random.choice(keywords)
    length = random.randint(1, 20)
    first_char = random.choice(string.ascii_letters)
    rest_chars = ''.join(random.choice(string.ascii_letters + string.digits + '_') for _ in range(length - 1))
    return first_char + rest_chars

def _generate_integer_literal():
    # Include common edge cases.
    if random.random() < 0.2:
        return random.choice(['0', '1', '-1', str(2**31-1), str(-(2**31)), '99999999999999999999'])
    return str(random.randint(-1000, 10000))

def _generate_string_literal():
    length = random.randint(0, 40)
    chars = string.ascii_letters + string.digits + " _-!@#$%^&*(){}[];:/?,.<>"
    content = ''.join(random.choice(chars) for _ in range(length))
    if random.random() < 0.2:
        content = content.replace("'", "''") # SQL standard for quote escaping
    if random.random() < 0.1:
        content += random.choice(["\\\\n", "\\\\t", "\\'"]) # C-style escapes
    return f"'{content}'"

# --- Grammar-based Generator ---
class FuzzerGenerator:
    """
    Generates test cases by recursively expanding a grammar.
    """
    def __init__(self, grammar):
        self.grammar = grammar
        self.non_terminals = list(grammar.keys())

    def _expand(self, symbol, depth, max_depth):
        # Stop recursion if depth limit is reached to prevent infinite loops.
        if depth > max_depth:
            # At max depth, try to return a simple terminal if possible.
            if symbol == '<identifier>': return _generate_identifier()
            if symbol == '<integer_literal>': return _generate_integer_literal()
            if symbol == '<string_literal>': return _generate_string_literal()
            return ""

        # Handle special literal-generating non-terminals.
        if symbol == '<identifier>': return _generate_identifier()
        if symbol == '<integer_literal>': return _generate_integer_literal()
        if symbol == '<string_literal>': return _generate_string_literal()
        if symbol == '<boolean_literal>': return random.choice(['TRUE', 'FALSE'])
        
        if symbol not in self.grammar:
            return symbol.strip("'") # It's a terminal (keyword or operator).

        rules = self.grammar[symbol]
        # Bias towards simpler rules (fewer symbols) to generate a mix of statement complexities.
        rule_weights = [1.0 / (len(r) + 1) for r in rules]
        chosen_rule = random.choices(rules, weights=rule_weights, k=1)[0]
        
        # With a small probability, introduce grammar-level mutations to create invalid syntax.
        if random.random() < 0.05:
            mutation_type = random.random()
            if mutation_type < 0.5 and len(chosen_rule) > 1: # Drop a symbol
                chosen_rule = chosen_rule[:-1]
            elif mutation_type < 0.8 and self.non_terminals: # Substitute with another rule
                bad_symbol = random.choice(self.non_terminals)
                if bad_symbol in self.grammar:
                    chosen_rule = random.choice(self.grammar[bad_symbol])
        
        parts = [self._expand(s, depth + 1, max_depth) for s in chosen_rule]
        return " ".join(filter(None, parts))

    def generate(self, start_symbol='<sql_statement>', max_depth=None):
        if max_depth is None:
            max_depth = random.randint(6, 15)
        return self._expand(start_symbol, 0, max_depth)

# --- Fuzzer Main Logic ---
INITIAL_SEEDS = [
    # A list of valid, invalid, and edge-case SQL statements to kickstart fuzzing.
    "SELECT * FROM t;", "SELECT c1, c2 FROM t1 WHERE c1 > 10;",
    "INSERT INTO t2 VALUES (1, 'hello', 2.5);", "UPDATE t3 SET c2 = 'world' WHERE c1 = 1;",
    "DELETE FROM t4 WHERE c1 < 0;", "CREATE TABLE t5 (c1 INTEGER, c2 VARCHAR(255) PRIMARY KEY);",
    "SELECT COUNT(*) FROM t1 GROUP BY c2 HAVING COUNT(*) > 1;",
    "SELECT t1.c1, t2.c2 FROM t1 JOIN t2 ON t1.id = t2.t1_id;",
    "SELECT * FROM t1 ORDER BY c1 ASC, c2 DESC LIMIT 10 OFFSET 5;",
    "SELECT * FROM t WHERE c1 IS NULL AND c2 IS NOT NULL;",
    "SELECT CASE WHEN a=1 THEN 'one' WHEN a=2 THEN 'two' ELSE 'other' END FROM t;",
    "SELECT 1, 'a', 1.5, true, false, null;", "SELECT", "SELECT * FROM;",
    "INSERT INTO t VALUES (1, 2, 3", ";", "", "/* comment */ SELECT--another comment\\n* FROM t;",
    "SELECT 'string with '''' quote' FROM t;", "SELECT 1e-5, .5, 5. FROM t;",
]

INTERESTING_FRAGMENTS = [
    # A pool of tokens and fragments known to trigger edge cases.
    "'", "\"", "`", ";", "--", "/*", "*/", "(", ")", "[", "]", "{", "}",
    "OR 1=1", "AND 1=1", "UNION ALL SELECT", "NULL", "0", "-1", "1.0e100", "%", "_", "%s%n%d",
]

def _mutate(sql):
    """Applies random mutations to a given SQL string."""
    if not sql: return random.choice(INTERESTING_FRAGMENTS)
    
    num_mutations = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1], k=1)[0]
    for _ in range(num_mutations):
        if not sql: break
        pos = random.randint(0, len(sql))
        mutation_type = random.random()
        
        if mutation_type < 0.4: # Insert an interesting fragment
            sql = sql[:pos] + random.choice(INTERESTING_FRAGMENTS) + sql[pos:]
        elif mutation_type < 0.7 and len(sql) > 1: # Delete a chunk of characters
            del_len = min(random.randint(1, 4), len(sql) - pos)
            sql = sql[:pos] + sql[pos + del_len:]
        elif mutation_type < 0.9 and len(sql) > 0: # Replace a character
            pos = random.randint(0, len(sql)-1)
            sql = sql[:pos] + random.choice(string.printable) + sql[pos+1:]
    return sql

def fuzz(parse_sql):
    """
    Main fuzzing loop, called repeatedly by the evaluator.
    """
    global GRAMMAR, NON_TERMINALS, START_TIME, GENERATOR

    # --- One-time initialization on the first call ---
    if START_TIME is None:
        START_TIME = time.time()
        
    if GENERATOR is None:
        # The grammar content is injected here by the Solution.solve method.
        GRAMMAR_CONTENT = \"\"\"
{grammar_content}
\"\"\"
        GRAMMAR = _parse_grammar(GRAMMAR_CONTENT)
        if not GRAMMAR: # Fallback if grammar is empty or parsing fails
            GRAMMAR = {{'<sql_statement>': [['SELECT', '<expr>', 'FROM', '<identifier>']], '<expr>': [['<identifier>'], ['*']]}}
        
        NON_TERMINALS = list(GRAMMAR.keys())
        GENERATOR = FuzzerGenerator(GRAMMAR)
        # Run initial seeds to get a baseline coverage quickly.
        parse_sql(INITIAL_SEEDS)

    # --- Time Budget Check ---
    if time.time() - START_TIME > TIME_BUDGET:
        return False  # Stop fuzzing

    # --- Test Case Generation ---
    # Generate large batches to reduce the overhead of `parse_sql` calls and improve the efficiency score.
    batch_size = 700
    statements = []
    
    # Use a mix of generation strategies to create a diverse set of inputs.
    for _ in range(batch_size):
        r = random.random()
        
        if r < 0.1: # Strategy 1: Mutate a known-good or interesting seed.
            statements.append(_mutate(random.choice(INITIAL_SEEDS)))
        elif r < 0.65: # Strategy 2: Generate a full, mostly-valid statement from the grammar root.
            statements.append(GENERATOR.generate(start_symbol='<sql_statement>'))
        elif r < 0.85 and NON_TERMINALS: # Strategy 3: Generate a SQL fragment from a random grammar rule.
            start_node = random.choice(NON_TERMINALS)
            statements.append(GENERATOR.generate(start_symbol=start_node, max_depth=random.randint(3, 8)))
        else: # Strategy 4: Generate a valid statement and then apply mutations to it.
            base_stmt = GENERATOR.generate(start_symbol='<sql_statement>')
            statements.append(_mutate(base_stmt))
            
    # --- Execute Batch ---
    parse_sql(statements)

    return True  # Continue fuzzing
"""
        # Embed the actual grammar content into the fuzzer code string.
        final_code = fuzzer_code.format(grammar_content=grammar_content)
        
        return {"code": final_code}