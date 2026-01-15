import os
import json
import random
import re
import time
import itertools
from collections import defaultdict, deque
from typing import List, Dict, Set, Tuple, Optional

class Grammar:
    def __init__(self, grammar_path: str):
        self.rules = {}
        self.start_symbol = None
        self.load_grammar(grammar_path)
        
    def load_grammar(self, grammar_path: str):
        with open(grammar_path, 'r') as f:
            lines = f.readlines()
            
        current_rule = None
        productions = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if '::=' in line:
                if current_rule:
                    self.rules[current_rule] = productions
                    productions = []
                parts = line.split('::=', 1)
                current_rule = parts[0].strip()
                prod = parts[1].strip()
                if prod:
                    productions.append(prod)
            elif current_rule and line.startswith('|'):
                prod = line[1:].strip()
                if prod:
                    productions.append(prod)
            elif current_rule:
                productions.append(line)
                
        if current_rule and productions:
            self.rules[current_rule] = productions
            
        if '<select_stmt>' in self.rules:
            self.start_symbol = '<select_stmt>'
        elif '<statement>' in self.rules:
            self.start_symbol = '<statement>'
        else:
            self.start_symbol = list(self.rules.keys())[0] if self.rules else None
    
    def expand(self, symbol: str, depth: int = 0, max_depth: int = 8) -> str:
        if depth > max_depth:
            return ''
            
        if symbol not in self.rules:
            return symbol.replace('<', '').replace('>', '')
            
        productions = self.rules[symbol]
        chosen = random.choice(productions)
        
        tokens = re.findall(r'<[^>]+>|[^<\s]+', chosen)
        result = []
        
        for token in tokens:
            if token.startswith('<'):
                result.append(self.expand(token, depth + 1, max_depth))
            else:
                result.append(token)
                
        return ' '.join(result).strip()

class Solution:
    def solve(self, resources_path: str) -> dict:
        grammar_path = os.path.join(resources_path, 'sql_grammar.txt')
        
        fuzzer_code = f'''import os
import random
import re
import time
import itertools
from collections import defaultdict, deque
from typing import List, Dict, Set

class Grammar:
    def __init__(self):
        self.rules = {self._load_grammar(grammar_path)}
        self.start_symbol = {self._get_start_symbol()}
        
    def expand(self, symbol: str, depth: int = 0, max_depth: int = 8) -> str:
        if depth > max_depth:
            return ''
            
        if symbol not in self.rules:
            return symbol.replace('<', '').replace('>', '')
            
        productions = self.rules[symbol]
        if not productions:
            return ''
            
        chosen = random.choice(productions)
        tokens = re.findall(r'<[^>]+>|[^<\s]+', chosen)
        result = []
        
        for token in tokens:
            if token.startswith('<'):
                expanded = self.expand(token, depth + 1, max_depth)
                result.append(expanded if expanded else 'NULL')
            else:
                result.append(token)
                
        return ' '.join(result).strip()
    
    def generate_valid(self, count: int = 1) -> List[str]:
        results = []
        for _ in range(count):
            if self.start_symbol:
                stmt = self.expand(self.start_symbol)
                if stmt:
                    results.append(stmt)
        return results

class Mutator:
    def __init__(self):
        self.keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 
                        'ALTER', 'FROM', 'WHERE', 'GROUP', 'HAVING', 'ORDER', 'BY',
                        'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'ON', 'AS',
                        'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL',
                        'TRUE', 'FALSE', 'EXISTS', 'DISTINCT', 'UNION', 'ALL',
                        'VALUES', 'INTO', 'SET', 'TABLE', 'VIEW', 'INDEX',
                        'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'UNIQUE',
                        'CHECK', 'DEFAULT', 'CONSTRAINT', 'TRANSACTION',
                        'COMMIT', 'ROLLBACK', 'BEGIN', 'END']
        
        self.operators = ['=', '<>', '!=', '<', '>', '<=', '>=', '+', '-', '*', '/', '%']
        self.functions = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COALESCE', 'NULLIF']
        
    def mutate(self, sql: str) -> str:
        if not sql:
            return sql
            
        mutations = [
            self._insert_random,
            self._delete_random,
            self._replace_random,
            self._swap_parts,
            self._add_nested,
            self._change_operator,
            self._add_function,
            self._corrupt_syntax
        ]
        
        mutator = random.choice(mutations)
        try:
            return mutator(sql)
        except:
            return sql
    
    def _insert_random(self, sql: str) -> str:
        words = sql.split()
        if len(words) <= 1:
            return sql
            
        pos = random.randint(0, len(words))
        insert_word = random.choice(self.keywords + ['1', '0', 'NULL', "'test'", 'col'])
        words.insert(pos, insert_word)
        return ' '.join(words)
    
    def _delete_random(self, sql: str) -> str:
        words = sql.split()
        if len(words) <= 2:
            return sql
            
        pos = random.randint(0, len(words) - 1)
        words.pop(pos)
        return ' '.join(words)
    
    def _replace_random(self, sql: str) -> str:
        words = sql.split()
        if not words:
            return sql
            
        pos = random.randint(0, len(words) - 1)
        replacements = self.keywords + self.operators + ['NULL', '1', '0', "'text'"]
        words[pos] = random.choice(replacements)
        return ' '.join(words)
    
    def _swap_parts(self, sql: str) -> str:
        words = sql.split()
        if len(words) < 3:
            return sql
            
        i = random.randint(0, len(words) - 2)
        j = random.randint(i + 1, len(words) - 1)
        words[i], words[j] = words[j], words[i]
        return ' '.join(words)
    
    def _add_nested(self, sql: str) -> str:
        patterns = [
            (r'(SELECT\s+)', r'\\1(SELECT 1 FROM (SELECT 1) t) '),
            (r'(WHERE\s+)', r'\\1(EXISTS (SELECT 1)) AND '),
            (r'(=\s*)', r'= (SELECT 1) OR '),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return re.sub(pattern, replacement, sql, 1, re.IGNORECASE)
        return sql + ' AND (SELECT 1)'
    
    def _change_operator(self, sql: str) -> str:
        for op in self.operators:
            if op in sql:
                new_op = random.choice(self.operators)
                return sql.replace(op, new_op, 1)
        return sql
    
    def _add_function(self, sql: str) -> str:
        func = random.choice(self.functions)
        return func + '(' + sql + ')'
    
    def _corrupt_syntax(self, sql: str) -> str:
        corruptions = [
            lambda s: s + ';;',
            lambda s: s.replace(' ', '  '),
            lambda s: s[:len(s)//2] + ' /* ' + s[len(s)//2:] + ' */',
            lambda s: s + ' WHERE 1=0',
            lambda s: s + ' GROUP BY 1',
            lambda s: s.replace('=', '=='),
        ]
        return random.choice(corruptions)(sql)

class FuzzerState:
    def __init__(self):
        self.corpus = deque(maxlen=1000)
        self.mutation_counts = defaultdict(int)
        self.grammar = Grammar()
        self.mutator = Mutator()
        self.start_time = time.time()
        self.generation_phase = 0
        self.last_expansion_time = 0
        
        self.statement_templates = [
            "SELECT * FROM t",
            "SELECT col1, col2 FROM t WHERE cond",
            "INSERT INTO t (col1, col2) VALUES (val1, val2)",
            "UPDATE t SET col = val WHERE cond",
            "DELETE FROM t WHERE cond",
            "CREATE TABLE t (col1 INT, col2 VARCHAR(255))",
            "DROP TABLE t",
            "ALTER TABLE t ADD COLUMN col INT",
            "SELECT * FROM t1 JOIN t2 ON t1.id = t2.id",
            "SELECT * FROM t GROUP BY col HAVING agg > 0",
            "SELECT * FROM t ORDER BY col",
            "SELECT DISTINCT col FROM t",
            "SELECT * FROM t WHERE col IN (SELECT col FROM t2)",
            "SELECT * FROM t WHERE col LIKE '%pattern%'",
            "SELECT * FROM t WHERE col BETWEEN 1 AND 10",
            "SELECT COUNT(*) FROM t",
            "SELECT * FROM t WHERE col IS NULL",
            "SELECT * FROM t WHERE col IS NOT NULL",
            "BEGIN TRANSACTION; COMMIT",
            "SAVEPOINT s1; ROLLBACK TO s1",
        ]
        
        self.edge_cases = [
            "",
            ";",
            "SELECT",
            "SELECT FROM",
            "SELECT * FROM WHERE",
            "1",
            "'",
            "''''",
            "NULL",
            "SELECT NULL",
            "SELECT 1/0",
            "SELECT * FROM (SELECT 1)",
            "SELECT * FROM nonexistent",
            "INSERT INTO VALUES",
            "UPDATE SET",
            "DELETE WHERE",
            "CREATE TABLE",
            "DROP",
            "ALTER TABLE",
            "SELECT * FROM t,,,,,",
            "SELECT * FROM t WHERE 1=1",
            "SELECT * FROM t WHERE 'a'='a'",
            "SELECT * FROM t WHERE NULL=NULL",
            "SELECT * FROM t GROUP BY",
            "SELECT * FROM t ORDER BY",
            "SELECT * FROM t LIMIT -1",
            "SELECT * FROM t OFFSET -1",
            "SELECT * FROM t JOIN ON",
            "SELECT * FROM t UNION SELECT * FROM t",
            "SELECT * FROM t INTERSECT SELECT * FROM t",
            "SELECT * FROM t EXCEPT SELECT * FROM t",
            "WITH cte AS (SELECT 1) SELECT * FROM cte",
            "EXPLAIN SELECT 1",
            "PRAGMA table_info(t)",
            "VACUUM",
            "ANALYZE",
            "REINDEX",
        ]
        
        for template in self.statement_templates:
            self.corpus.append(template)
        
        for edge in self.edge_cases:
            self.corpus.append(edge)
    
    def generate_batch(self, size: int = 50) -> List[str]:
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        batch = []
        
        if elapsed < 5:
            self.generation_phase = 0
        elif elapsed < 20:
            self.generation_phase = 1
        elif elapsed < 40:
            self.generation_phase = 2
        else:
            self.generation_phase = 3
        
        if self.generation_phase == 0:
            for _ in range(size // 3):
                batch.extend(self.grammar.generate_valid(1))
            
            for _ in range(size // 3):
                if self.corpus:
                    template = random.choice(list(self.corpus))
                    batch.append(self.mutator.mutate(template))
            
            for _ in range(size // 3):
                batch.append(random.choice(self.edge_cases))
                
        elif self.generation_phase == 1:
            for _ in range(size // 2):
                batch.extend(self.grammar.generate_valid(1))
            
            for _ in range(size // 2):
                if self.corpus:
                    parent = random.choice(list(self.corpus))
                    for _ in range(3):
                        mutated = self.mutator.mutate(parent)
                        batch.append(mutated)
                        if len(batch) >= size:
                            break
                    if len(batch) >= size:
                        break
                        
        elif self.generation_phase == 2:
            for _ in range(size // 4):
                batch.extend(self.grammar.generate_valid(2))
            
            mutation_targets = list(self.corpus)
            for _ in range(size // 2):
                if mutation_targets:
                    parent = random.choice(mutation_targets)
                    for _ in range(2):
                        mutated = self.mutator.mutate(parent)
                        batch.append(mutated)
            
            for _ in range(size // 4):
                batch.append(random.choice(self.edge_cases))
                
        else:
            for _ in range(size // 3):
                if self.corpus:
                    parent = random.choice(list(self.corpus))
                    for _ in range(3):
                        mutated = self.mutator.mutate(parent)
                        mutated2 = self.mutator.mutate(mutated)
                        batch.append(mutated2)
            
            for _ in range(size // 3):
                batch.extend(self.grammar.generate_valid(1))
            
            for _ in range(size // 3):
                combinations = [
                    "SELECT * FROM t WHERE " + cond
                    for cond in ["1=1", "NULL IS NULL", "col IN (1,2,3)", "col LIKE '%'"]
                ]
                batch.extend(combinations[:2])
        
        batch = [stmt for stmt in batch if stmt is not None and stmt.strip()]
        
        if len(batch) > size:
            batch = batch[:size]
        
        for stmt in batch:
            if stmt not in self.corpus:
                self.corpus.append(stmt)
        
        return batch

# Global state
state = None

def fuzz(parse_sql):
    global state
    
    if state is None:
        state = FuzzerState()
    
    current_time = time.time()
    if current_time - state.start_time > 58:
        return False
    
    batch = state.generate_batch(100)
    
    if batch:
        parse_sql(batch)
    
    return True
'''
        return {"code": fuzzer_code}
    
    def _load_grammar(self, grammar_path: str) -> Dict:
        rules = {}
        try:
            with open(grammar_path, 'r') as f:
                lines = f.readlines()
            
            current_rule = None
            productions = []
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                if '::=' in line:
                    if current_rule and productions:
                        rules[current_rule] = productions[:]
                        productions = []
                    parts = line.split('::=', 1)
                    current_rule = parts[0].strip()
                    prod = parts[1].strip()
                    if prod:
                        productions.append(prod)
                elif current_rule and line.startswith('|'):
                    prod = line[1:].strip()
                    if prod:
                        productions.append(prod)
                elif current_rule:
                    productions.append(line)
                    
            if current_rule and productions:
                rules[current_rule] = productions[:]
                
        except Exception as e:
            rules = {
                '<select_stmt>': ['SELECT <select_list> FROM <table_ref> <where_clause> <group_clause> <order_clause>'],
                '<select_list>': ['*', '<column>', '<column>, <select_list>'],
                '<table_ref>': ['t', 't1', 't2'],
                '<where_clause>': ['', 'WHERE <condition>'],
                '<condition>': ['<column> = <value>', '<column> > <value>', '<column> IN (<value_list>)'],
                '<column>': ['col1', 'col2', 'col3'],
                '<value>': ['1', '0', 'NULL', "'test'"],
                '<value_list>': ['<value>', '<value>, <value_list>'],
                '<group_clause>': ['', 'GROUP BY <column>'],
                '<order_clause>': ['', 'ORDER BY <column>'],
            }
        
        return rules
    
    def _get_start_symbol(self) -> str:
        return '<select_stmt>'