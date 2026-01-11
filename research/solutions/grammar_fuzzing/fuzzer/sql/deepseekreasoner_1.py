import os
import random
import time
import re
from typing import List, Dict, Set, Tuple, Optional, Any
import math
import json

class Solution:
    def solve(self, resources_path: str) -> dict:
        # Read and parse the grammar
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        with open(grammar_path, 'r') as f:
            grammar_content = f.read()
        
        # Parse the grammar into a structured format
        grammar = self._parse_grammar(grammar_content)
        
        # Generate fuzzer code
        fuzzer_code = self._generate_fuzzer_code(grammar)
        
        return {"code": fuzzer_code}
    
    def _parse_grammar(self, content: str) -> Dict[str, List[List[str]]]:
        """Parse BNF-style grammar into structured format."""
        grammar = {}
        lines = content.strip().split('\n')
        
        current_nt = None
        current_rules = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if '::=' in line:
                if current_nt is not None:
                    grammar[current_nt] = current_rules
                parts = line.split('::=', 1)
                current_nt = parts[0].strip()
                current_rules = [self._parse_rule(parts[1].strip())]
            elif '|' in line:
                current_rules.append(self._parse_rule(line[1:].strip()))
            else:
                # Continuation of previous rule
                if current_rules:
                    current_rules[-1].extend(self._parse_rule(line))
        
        if current_nt is not None:
            grammar[current_nt] = current_rules
            
        return grammar
    
    def _parse_rule(self, rule_str: str) -> List[str]:
        """Parse a single grammar rule into tokens."""
        tokens = []
        current = []
        in_angle = False
        in_quote = False
        quote_char = None
        
        for char in rule_str:
            if char == '<' and not in_quote:
                if current:
                    tokens.append(''.join(current))
                    current = []
                in_angle = True
                current.append(char)
            elif char == '>' and in_angle and not in_quote:
                current.append(char)
                tokens.append(''.join(current))
                current = []
                in_angle = False
            elif char in ('\'', '"') and not in_angle:
                if in_quote and char == quote_char:
                    current.append(char)
                    tokens.append(''.join(current))
                    current = []
                    in_quote = False
                    quote_char = None
                elif not in_quote:
                    if current:
                        tokens.append(''.join(current))
                    current = [char]
                    in_quote = True
                    quote_char = char
                else:
                    current.append(char)
            elif char == ' ' and not in_angle and not in_quote:
                if current:
                    tokens.append(''.join(current))
                    current = []
            else:
                current.append(char)
        
        if current:
            tokens.append(''.join(current))
            
        # Filter out empty tokens and spaces
        return [t for t in tokens if t and t != ' ']
    
    def _generate_fuzzer_code(self, grammar: Dict) -> str:
        """Generate the complete fuzzer code with the parsed grammar embedded."""
        
        # Create a JSON-serializable version of the grammar
        grammar_json = json.dumps(grammar)
        
        fuzzer_code = f'''
import random
import time
import json
import math
from typing import List, Set, Dict, Tuple, Optional, Any
import re
import sys
import itertools

class SQLFuzzer:
    def __init__(self):
        # Load grammar from embedded JSON
        self.grammar = json.loads('{grammar_json}')
        
        # Track seen statements to avoid duplicates
        self.seen_statements = set()
        
        # Coverage feedback simulation (we track what we've generated)
        self.generated_patterns = set()
        
        # Initialize with seed statements
        self.seed_statements = [
            "SELECT 1",
            "SELECT * FROM t",
            "INSERT INTO t VALUES (1)",
            "UPDATE t SET a = 1",
            "DELETE FROM t",
            "CREATE TABLE t (id INT)",
            "DROP TABLE t",
            "SELECT a, b FROM t1 JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t WHERE x > 10",
            "SELECT COUNT(*) FROM t GROUP BY category",
        ]
        
        # Mutation operators
        self.mutators = [
            self._mutate_keyword,
            self._mutate_identifier,
            self._mutate_literal,
            self._mutate_add_clause,
            self._mutate_remove_clause,
            self._mutate_shuffle_clauses,
        ]
        
        # Weighted distribution for generation strategies
        self.strategy_weights = [0.3, 0.3, 0.2, 0.2]  # grammar, mutation, combination, seed
        
        # Statement complexity levels
        self.complexity_levels = [1, 2, 3, 4, 5]
        self.current_complexity = 1
        self.complexity_progress = 0
        
        # Performance tracking
        self.start_time = None
        self.statement_count = 0
        self.batch_size = 50
        self.max_statements = 10000
        
        # Terminal expansions cache
        self.terminal_cache = {{
            '<identifier>': ['id', 'name', 'value', 't', 't1', 't2', 'users', 'orders', 'products'],
            '<table_name>': ['users', 'orders', 'products', 'customers', 'items', 't', 't1', 't2'],
            '<column_name>': ['id', 'name', 'value', 'price', 'quantity', 'status', 'created_at'],
            '<number>': ['0', '1', '10', '100', '999', '-1', '3.14', 'NULL'],
            '<string_literal>': ["'test'", "'hello'", "'world'", "''", "'a'", "'longer string'"],
            '<operator>': ['=', '>', '<', '>=', '<=', '<>', '!=', 'LIKE', 'IN'],
            '<data_type>': ['INT', 'VARCHAR(255)', 'TEXT', 'BOOLEAN', 'DATE', 'TIMESTAMP'],
        }}
    
    def expand_symbol(self, symbol: str, depth: int = 0, max_depth: int = 5) -> str:
        """Recursively expand a grammar symbol."""
        if depth >= max_depth:
            # Return a simple terminal if we've gone too deep
            if symbol in self.terminal_cache:
                return random.choice(self.terminal_cache[symbol])
            return symbol.strip('<>')
        
        # Check if it's a terminal
        if not symbol.startswith('<'):
            return symbol
        
        # Check terminal cache first
        if symbol in self.terminal_cache:
            return random.choice(self.terminal_cache[symbol])
        
        # Non-terminal - expand using grammar rules
        if symbol in self.grammar:
            rules = self.grammar[symbol]
            if rules:
                chosen_rule = random.choice(rules)
                parts = []
                for part in chosen_rule:
                    if part.startswith('<') and part.endswith('>'):
                        parts.append(self.expand_symbol(part, depth + 1, max_depth))
                    else:
                        parts.append(part)
                return ' '.join(parts)
        
        # Fallback - return symbol without brackets
        return symbol.strip('<>')
    
    def generate_from_grammar(self, complexity: int = 3) -> str:
        """Generate a SQL statement using the grammar."""
        max_depth = min(complexity + 2, 8)
        
        # Start with statement symbol
        start_symbols = ['<statement>', '<select_statement>', '<insert_statement>', 
                        '<update_statement>', '<delete_statement>', '<create_statement>']
        
        start = random.choice(start_symbols)
        statement = self.expand_symbol(start, max_depth=max_depth)
        
        # Clean up extra spaces
        statement = re.sub(r'\\s+', ' ', statement).strip()
        
        # Ensure it ends with semicolon
        if not statement.endswith(';'):
            statement += ';'
            
        return statement
    
    def generate_mutation(self, base_statement: str) -> str:
        """Create a mutated version of a base statement."""
        if not base_statement or random.random() < 0.1:
            return self.generate_from_grammar(2)
        
        mutator = random.choice(self.mutators)
        try:
            return mutator(base_statement)
        except:
            return base_statement
    
    def _mutate_keyword(self, stmt: str) -> str:
        """Replace a SQL keyword with another."""
        keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 
                   'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'OUTER JOIN',
                   'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER',
                   'AND', 'OR', 'NOT', 'NULL', 'DISTINCT', 'LIMIT', 'OFFSET']
        
        words = stmt.split()
        if not words:
            return stmt
        
        # Find keyword positions
        keyword_positions = [i for i, w in enumerate(words) 
                           if w.upper() in keywords and random.random() < 0.3]
        
        if keyword_positions:
            pos = random.choice(keyword_positions)
            new_keyword = random.choice(keywords)
            words[pos] = new_keyword
        
        return ' '.join(words)
    
    def _mutate_identifier(self, stmt: str) -> str:
        """Replace an identifier with another."""
        identifiers = ['t', 't1', 't2', 'users', 'orders', 'products', 'customers',
                      'id', 'name', 'value', 'price', 'quantity', 'status']
        
        # Simple word-based replacement
        words = re.split(r'(\\s+|[,;()])', stmt)
        for i, word in enumerate(words):
            if word.strip() and word.upper() not in ['SELECT', 'FROM', 'WHERE', 'INSERT', 
                                                    'UPDATE', 'DELETE', 'CREATE', 'DROP']:
                if random.random() < 0.2:
                    words[i] = random.choice(identifiers)
        
        return ''.join(words)
    
    def _mutate_literal(self, stmt: str) -> str:
        """Replace a literal value."""
        # Find numbers and strings
        def replace_match(match):
            if random.random() < 0.5:
                if match.group().isdigit():
                    return str(random.choice([0, 1, 10, 100, 999, -1, 3.14]))
                elif match.group().startswith("'") and match.group().endswith("'"):
                    return random.choice(["'test'", "'hello'", "'world'", "''", "'x'"])
            return match.group()
        
        # Pattern for numbers and quoted strings
        pattern = r'\\b\\d+\\b|\\'[^\\']*\\''
        return re.sub(pattern, replace_match, stmt)
    
    def _mutate_add_clause(self, stmt: str) -> str:
        """Add a random clause to the statement."""
        clauses = [
            ' WHERE 1=1',
            ' GROUP BY id',
            ' ORDER BY name',
            ' LIMIT 10',
            ' OFFSET 0',
            ' HAVING COUNT(*) > 0',
            ' AND status = 1',
            ' OR deleted = 0',
        ]
        
        if random.random() < 0.7:
            # Add at end before semicolon
            if stmt.endswith(';'):
                stmt = stmt[:-1] + random.choice(clauses) + ';'
            else:
                stmt += random.choice(clauses)
        
        return stmt
    
    def _mutate_remove_clause(self, stmt: str) -> str:
        """Remove a random clause from the statement."""
        # Simple implementation - remove last few words
        words = stmt.split()
        if len(words) > 3:
            remove_count = random.randint(1, min(3, len(words) - 2))
            words = words[:-remove_count]
            return ' '.join(words) + ';'
        return stmt
    
    def _mutate_shuffle_clauses(self, stmt: str) -> str:
        """Shuffle parts of the statement."""
        # Split by common SQL keywords
        parts = re.split(r'(\\s+(?:WHERE|GROUP BY|ORDER BY|HAVING|LIMIT|OFFSET)\\s+)', stmt, flags=re.IGNORECASE)
        
        if len(parts) > 3:
            # Keep SELECT ... FROM part, shuffle the rest
            main_part = parts[0]
            clauses = parts[1:]
            
            # Group clauses with their keywords
            clause_pairs = []
            i = 0
            while i < len(clauses):
                if i + 1 < len(clauses):
                    clause_pairs.append(clauses[i] + clauses[i + 1])
                    i += 2
                else:
                    clause_pairs.append(clauses[i])
                    i += 1
            
            random.shuffle(clause_pairs)
            return main_part + ''.join(clause_pairs)
        
        return stmt
    
    def generate_combination(self, stmt1: str, stmt2: str) -> str:
        """Combine parts of two statements."""
        # Extract clauses from each
        clauses1 = re.findall(r'(SELECT.*?)(?=(?:WHERE|GROUP BY|ORDER BY|HAVING|LIMIT|OFFSET|;))', stmt1 + ';', re.IGNORECASE | re.DOTALL)
        clauses2 = re.findall(r'(SELECT.*?)(?=(?:WHERE|GROUP BY|ORDER BY|HAVING|LIMIT|OFFSET|;))', stmt2 + ';', re.IGNORECASE | re.DOTALL)
        
        if clauses1 and clauses2:
            # Take SELECT part from first, add random clause from second
            result = clauses1[0]
            if random.random() < 0.7 and len(clauses2[0].split()) > 3:
                # Find a clause in second statement
                second_clauses = re.split(r'(?:WHERE|GROUP BY|ORDER BY|HAVING|LIMIT|OFFSET)', clauses2[0], flags=re.IGNORECASE)
                if len(second_clauses) > 1:
                    clause_keyword = re.search(r'(WHERE|GROUP BY|ORDER BY|HAVING|LIMIT|OFFSET)', clauses2[0][len(second_clauses[0]):], re.IGNORECASE)
                    if clause_keyword:
                        result += ' ' + clause_keyword.group() + second_clauses[1]
            
            return result + ';'
        
        return stmt1 if random.random() < 0.5 else stmt2
    
    def generate_batch(self, batch_size: int) -> List[str]:
        """Generate a batch of diverse SQL statements."""
        statements = []
        
        while len(statements) < batch_size:
            strategy = random.choices(
                ['grammar', 'mutation', 'combination', 'seed'],
                weights=self.strategy_weights,
                k=1
            )[0]
            
            if strategy == 'grammar':
                stmt = self.generate_from_grammar(self.current_complexity)
                
            elif strategy == 'mutation' and self.seen_statements:
                base = random.choice(list(self.seen_statements))
                stmt = self.generate_mutation(base)
                
            elif strategy == 'combination' and len(self.seen_statements) >= 2:
                base1, base2 = random.sample(list(self.seen_statements), 2)
                stmt = self.generate_combination(base1, base2)
                
            else:  # seed or fallback
                stmt = random.choice(self.seed_statements)
            
            # Ensure uniqueness
            if stmt not in self.seen_statements and len(stmt) < 1000:  # Avoid overly long statements
                self.seen_statements.add(stmt)
                statements.append(stmt)
                
                # Track pattern for diversity
                pattern = re.sub(r'\\b\\d+\\b', '#', re.sub(r"\\'[^\\']*\\'", "'#'", stmt))
                self.generated_patterns.add(pattern)
        
        # Adjust strategy weights based on diversity
        diversity = len(self.generated_patterns) / max(1, len(self.seen_statements))
        if diversity < 0.3:
            # Increase grammar generation for more diversity
            self.strategy_weights = [0.4, 0.3, 0.2, 0.1]
        elif diversity > 0.7:
            # Good diversity, focus on mutation
            self.strategy_weights = [0.2, 0.5, 0.2, 0.1]
        
        # Gradually increase complexity
        self.complexity_progress += 1
        if self.complexity_progress % 50 == 0 and self.current_complexity < 5:
            self.current_complexity += 1
        
        return statements
    
    def fuzz(self, parse_sql):
        """
        Main fuzzing function called by evaluator.
        """
        if self.start_time is None:
            self.start_time = time.time()
        
        elapsed = time.time() - self.start_time
        
        # Check if we should stop
        if elapsed >= 58:  # Stop slightly before time limit
            return False
        
        # Generate batch of statements
        batch = self.generate_batch(self.batch_size)
        self.statement_count += len(batch)
        
        # Parse the batch
        parse_sql(batch)
        
        # Adaptive batch sizing
        if elapsed < 10:
            self.batch_size = 30
        elif elapsed < 30:
            self.batch_size = 50
        elif elapsed < 50:
            self.batch_size = 70
        else:
            self.batch_size = 100  # Larger batches towards the end
        
        # Continue fuzzing
        return True

# Global fuzzer instance
_fuzzer = SQLFuzzer()

def fuzz(parse_sql):
    """
    Fuzzer entry point called by evaluator.
    """
    return _fuzzer.fuzz(parse_sql)
'''
        return fuzzer_code