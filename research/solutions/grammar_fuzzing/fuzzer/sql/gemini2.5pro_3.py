import os
import re

class Solution:
    def solve(self, resources_path: str) -> dict:
        """
        Generates the Python code for a grammar-based SQL fuzzer.
        
        The process involves:
        1. Reading and parsing the SQL grammar file provided.
        2. Pre-computing helper data structures (e.g., simplest expansion rules) to
           make the runtime generator more efficient.
        3. Embedding the parsed grammar and pre-computed data directly into the
           fuzzer's source code as Python literals.
        4. Constructing the fuzzer logic, which includes:
           - A seed corpus for initial high-value targets.
           - A recursive grammar-based generator.
           - A mutation engine to explore error-handling paths.
           - The main `fuzz` function that orchestrates batch generation.
        """

        def parse_grammar_to_dict(text: str) -> dict:
            """Parses BNF-style grammar text into a dictionary."""
            grammar = {}
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '::=' not in line:
                    continue
                
                try:
                    symbol, definition = line.split('::=', 1)
                    symbol = symbol.strip()
                    
                    rules = definition.split('|')
                    productions = []
                    for rule in rules:
                        # Find all terminals ('...') and non-terminals (<...>)
                        tokens = re.findall(r"'[^']+'|<[^>]+>", rule.strip())
                        if tokens:
                            productions.append(tokens)
                    
                    if productions:
                        grammar[symbol] = productions
                except ValueError:
                    continue
            return grammar

        def precompute_simplest_rules(grammar: dict) -> dict:
            """
            For each non-terminal, finds the production rule with the fewest
            non-terminals, which is useful for terminating recursion.
            """
            simplest_rules = {}
            for symbol, productions in grammar.items():
                if not productions:
                    continue
                
                def count_non_terminals(rule):
                    return sum(1 for token in rule if token.startswith('<'))

                best_rule = min(productions, key=lambda r: (count_non_terminals(r), len(r)))
                simplest_rules[symbol] = best_rule
            return simplest_rules

        grammar_path = os.path.join(resources_path, 'sql_grammar.txt')
        try:
            with open(grammar_path, 'r', encoding='utf-8') as f:
                grammar_content = f.read()
        except FileNotFoundError:
            grammar_content = "<sql_statement> ::= 'SELECT' '1' ';'"

        parsed_grammar = parse_grammar_to_dict(grammar_content)
        simplest_rules = precompute_simplest_rules(parsed_grammar)

        fuzzer_code = f"""
import random
import sys

# Grammar-based fuzzers can be deeply recursive.
if sys.getrecursionlimit() < 2000:
    sys.setrecursionlimit(2000)

# The parsed grammar and precomputed rules are hardcoded for performance.
GRAMMAR = {parsed_grammar!r}
SIMPLEST_RULES = {simplest_rules!r}

# Global state for the fuzzer.
FUZZER_STATE = {{
    "seed_corpus_run": False,
}}

# A curated list of SQL statements to cover common and edge cases quickly.
SEED_CORPUS = [
    # Basic valid statements
    "SELECT 1;", "SELECT * FROM my_table;", "SELECT c1, c2 FROM t;",
    "INSERT INTO t (c1, c2) VALUES (1, 'hello');", "INSERT INTO t VALUES (1, 'a'), (2, 'b');",
    "UPDATE t SET c1 = 1, c2 = 'foo' WHERE c1 > 10;",
    "DELETE FROM t WHERE c1 = 1;",
    "CREATE TABLE t (c1 INT, c2 VARCHAR(20) PRIMARY KEY, c3 DECIMAL(10, 2));",
    "DROP TABLE t;", "TRUNCATE TABLE t;",
    "CREATE INDEX i ON t (c1);", "DROP INDEX i;",
    
    # Syntax variations and edge cases
    "select(1);", "SELECT `c` FROM `t`;", 'SELECT "c" FROM "t";',
    "SELECT 'hello' AS greeting, 1+2*3, (5+5)/2;",
    "SELECT * FROM t WHERE c1 IS NULL AND c2 IS NOT NULL;",
    "SELECT * FROM t WHERE c1 IN (1, 2, 3) AND c2 LIKE 'a%';", "SELECT * FROM t WHERE c1 NOT IN (1,2);",
    "SELECT * FROM t WHERE c1 BETWEEN 10 AND 20;",
    "SELECT c1, COUNT(*) FROM t GROUP BY c1 HAVING COUNT(*) > 1;",
    "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id;",
    "SELECT * FROM t1 INNER JOIN t2 USING(id);",
    "SELECT * FROM t1 LEFT JOIN t2 ON t1.id = t2.id;",
    "SELECT * FROM t1 RIGHT OUTER JOIN t2 ON t1.id = t2.id;",
    "SELECT * FROM t ORDER BY c1 ASC, c2 DESC;",
    "SELECT * FROM t LIMIT 10 OFFSET 5;",
    "SELECT * FROM t WHERE c1 IN (SELECT c1 FROM t2);",
    "SELECT CASE WHEN c1 > 0 THEN 'pos' WHEN c1 < 0 THEN 'neg' ELSE 'zero' END FROM t;",
    "SELECT CAST(c1 AS VARCHAR(50)) FROM t;",

    # Malformed / Error-handling statements
    "SELECT", "SELECT * FROM;", "INSERT INTO t VALUES (1, 2, 3) VALUES (4, 5, 6);",
    "CREATE TABLE t (c1 INT c2 VARCHAR);", "SELECT * FROM t WHERE c1 = );",
    "SELECT 'unterminated string", "SELECT 1.2.3;", "SELECT 0xFG;",
    "SELECT FROM WHERE", "", ";", ";;;", " \\t\\n ",
    "SELECT /* comment */ * FROM t;", "SELECT -- comment\\n * FROM t;",
    "SELECT 1e9999;", "SELECT " + "'a'"*1000 + ";",
    "SELECT (((((((((((1))))))))))));", "SELECT (1,2,(3,4));"
]

def generate_from_grammar(symbol, depth=0, max_depth=8):
    \"\"\"Recursively generates a string from a grammar symbol.\"\"\"
    if depth > max_depth:
        if symbol not in GRAMMAR:
            return symbol.strip("'")
        
        rule = SIMPLEST_RULES.get(symbol)
        if not rule:
            if 'expr' in symbol or 'value' in symbol: return '1'
            if 'name' in symbol or 'identifier' in symbol: return 'x'
            if 'string' in symbol: return "'s'"
            return ''
    elif symbol not in GRAMMAR:
        return symbol.strip("'")
    else:
        productions = GRAMMAR[symbol]
        if depth > max_depth / 2:
            weights = [1.0 / (len(p) + 1)**2 for p in productions]
            rule = random.choices(productions, weights=weights, k=1)[0]
        else:
            rule = random.choice(productions)

    return " ".join(generate_from_grammar(s, depth + 1, max_depth) for s in rule)

def mutate_sql(sql: str) -> str:
    \"\"\"Applies a random mutation to a SQL string to explore error paths.\"\"\"
    if not sql:
        return random.choice([';', "'", "SELECT"])

    mutation_type = random.random()
    try:
        pos = random.randrange(len(sql))
        if mutation_type < 0.4 and len(sql) > 1:
            char = random.choice(';()[],\\'"*<>=+-/\\t\\n')
            return sql[:pos] + char + sql[pos+1:]
        elif mutation_type < 0.7:
            char = random.choice(';()[],\\'"*<>=+-/\\t\\n')
            return sql[:pos] + char + sql[pos:]
        elif len(sql) > 1:
            return sql[:pos] + sql[pos+1:]
        else:
            return random.choice(';()[],\\'"*<>=+-/\\t\\n')
    except (ValueError, IndexError):
        return sql

def fuzz(parse_sql):
    \"\"\"Main fuzzing function called repeatedly by the evaluator.\"\"\"
    batch = []
    
    if not FUZZER_STATE["seed_corpus_run"]:
        batch.extend(SEED_CORPUS)
        FUZZER_STATE["seed_corpus_run"] = True

    batch_size = 1500
    start_symbol = '<sql_statement>'

    for _ in range(batch_size):
        try:
            max_d = random.randint(4, 12)
            generated_sql = generate_from_grammar(start_symbol, max_depth=max_d)
            batch.append(generated_sql)
        except RecursionError:
            batch.append("SELECT 1;")

    mutation_count = int(batch_size * 0.20)
    indices_to_mutate = random.sample(range(len(batch)), min(mutation_count, len(batch)))
    for i in indices_to_mutate:
        batch[i] = mutate_sql(batch[i])
        
    parse_sql(batch)
    
    return True
"""
        return {"code": fuzzer_code}