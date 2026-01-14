import os
import random
import string
import time
import json
from collections import defaultdict, deque
from typing import List, Dict, Set, Optional, Tuple
import hashlib

class Solution:
    def solve(self, resources_path: str) -> dict:
        fuzzer_code = self._generate_fuzzer_code(resources_path)
        return {"code": fuzzer_code}
    
    def _generate_fuzzer_code(self, resources_path: str) -> str:
        return '''
import random
import string
import time
from collections import defaultdict, deque
import hashlib
import re

# Global state for coverage-guided fuzzing
class FuzzerState:
    def __init__(self):
        self.start_time = time.time()
        self.time_budget = 60.0
        self.statement_counter = 0
        self.unique_statements = set()
        self.coverage_guidance = {}
        self.mutation_corpus = []
        self.grammar_corpus = []
        self.last_coverage_hash = ""
        self.stuck_counter = 0
        self.phase = "exploration"  # exploration, exploitation, mutation
        self.phase_start_time = 0
        self.coverage_progress = deque(maxlen=10)
        
        # Grammar patterns from observed successful statements
        self.success_patterns = []
        self.failed_patterns = []
        
        # Performance tracking
        self.batch_sizes = [100, 50, 25, 10]
        self.current_batch_idx = 0
        
        # Edge case database
        self.edge_cases = self._init_edge_cases()
    
    def _init_edge_cases(self):
        return {
            'keywords': ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'JOIN', 
                        'LEFT', 'RIGHT', 'INNER', 'OUTER', 'GROUP BY', 'ORDER BY', 'HAVING',
                        'UNION', 'INTERSECT', 'EXCEPT', 'WITH', 'CASE', 'WHEN', 'THEN', 'END',
                        'NULL', 'NOT NULL', 'DEFAULT', 'PRIMARY KEY', 'FOREIGN KEY', 'REFERENCES',
                        'CREATE', 'DROP', 'ALTER', 'TABLE', 'INDEX', 'VIEW', 'TRIGGER'],
            'operators': ['=', '!=', '<>', '<', '>', '<=', '>=', 'LIKE', 'IN', 'BETWEEN', 'IS', 'IS NOT',
                         'AND', 'OR', 'NOT', 'EXISTS', 'ALL', 'ANY', 'SOME'],
            'functions': ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COALESCE', 'NULLIF', 'CAST',
                         'UPPER', 'LOWER', 'SUBSTR', 'TRIM', 'LENGTH', 'ROUND', 'ABS',
                         'CURRENT_DATE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP'],
            'data_types': ['INTEGER', 'VARCHAR', 'CHAR', 'TEXT', 'BOOLEAN', 'DATE', 'TIME',
                          'TIMESTAMP', 'DECIMAL', 'FLOAT', 'DOUBLE', 'BLOB', 'CLOB'],
            'constraints': ['PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK', 'DEFAULT', 'NOT NULL']
        }
    
    def should_continue(self):
        elapsed = time.time() - self.start_time
        return elapsed < self.time_budget - 0.5  # Leave margin for cleanup
    
    def update_coverage_guidance(self, statements, success_flags):
        # Simulate coverage feedback by tracking which statement patterns
        # lead to unique execution paths (approximated by statement structure)
        for stmt, success in zip(statements, success_flags):
            if not stmt:
                continue
                
            # Extract pattern from statement
            pattern = self._extract_pattern(stmt)
            pattern_hash = hashlib.md5(pattern.encode()).hexdigest()[:8]
            
            if success:
                if pattern_hash not in self.coverage_guidance:
                    self.coverage_guidance[pattern_hash] = {
                        'pattern': pattern,
                        'count': 1,
                        'success_count': 1,
                        'last_used': time.time()
                    }
                    self.success_patterns.append(pattern)
                else:
                    self.coverage_guidance[pattern_hash]['count'] += 1
                    self.coverage_guidance[pattern_hash]['success_count'] += 1
                    self.coverage_guidance[pattern_hash]['last_used'] = time.time()
                    
                if pattern not in self.mutation_corpus:
                    self.mutation_corpus.append(pattern)
            else:
                if pattern_hash in self.coverage_guidance:
                    self.coverage_guidance[pattern_hash]['count'] += 1
                self.failed_patterns.append(pattern)
    
    def _extract_pattern(self, statement):
        # Extract a simplified pattern from SQL statement
        # Remove literals, identifiers, keep structure
        stmt = statement.upper()
        
        # Replace string literals
        stmt = re.sub(r"'[^']*'", "'STRING'", stmt)
        
        # Replace numbers
        stmt = re.sub(r'\b\d+\b', 'NUMBER', stmt)
        
        # Replace identifiers
        stmt = re.sub(r'\b[A-Z_][A-Z0-9_]*\b', lambda m: 'IDENT' if m.group(0) not in 
                     self.edge_cases['keywords'] + self.edge_cases['functions'] else m.group(0), stmt)
        
        return stmt
    
    def get_batch_size(self):
        # Dynamic batch sizing based on phase and progress
        if self.phase == "exploration":
            return self.batch_sizes[min(self.current_batch_idx, len(self.batch_sizes)-1)]
        elif self.phase == "exploitation":
            return max(10, self.batch_sizes[-1])
        else:  # mutation
            return 20
    
    def transition_phase(self):
        elapsed = time.time() - self.phase_start_time
        current_hash = hashlib.md5(str(sorted(self.coverage_guidance.keys())).encode()).hexdigest()
        
        if elapsed > 5 and current_hash == self.last_coverage_hash:
            self.stuck_counter += 1
        else:
            self.stuck_counter = max(0, self.stuck_counter - 1)
        
        self.last_coverage_hash = current_hash
        
        if self.stuck_counter >= 3:
            self.phase = "mutation"
            self.phase_start_time = time.time()
            self.stuck_counter = 0
        elif elapsed > 15:
            if self.phase == "exploration":
                self.phase = "exploitation"
            elif self.phase == "exploitation":
                self.phase = "exploration"
            elif self.phase == "mutation":
                self.phase = "exploration"
            self.phase_start_time = time.time()

# Main fuzzer function
state = FuzzerState()

def generate_random_identifier():
    prefixes = ['tbl', 'col', 'idx', 'v', 'x', 'y', 'z', 'a', 'b', 'c']
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=3))
    return random.choice(prefixes) + '_' + suffix

def generate_random_value():
    types = [
        lambda: str(random.randint(1, 1000)),
        lambda: "'" + ''.join(random.choices(string.ascii_letters, k=random.randint(1, 10))) + "'",
        lambda: "NULL",
        lambda: "TRUE",
        lambda: "FALSE",
        lambda: f"{random.uniform(1.0, 1000.0):.2f}",
        lambda: f"CURRENT_TIMESTAMP",
        lambda: f"'{random.randint(1900, 2100)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}'"
    ]
    return random.choice(types)()

def generate_select_statement():
    templates = [
        "SELECT * FROM {table}",
        "SELECT {columns} FROM {table}",
        "SELECT {columns} FROM {table} WHERE {condition}",
        "SELECT {columns} FROM {table} WHERE {condition} ORDER BY {order}",
        "SELECT {columns} FROM {table} WHERE {condition} GROUP BY {group} HAVING {having}",
        "SELECT {columns} FROM {table1} JOIN {table2} ON {join_condition}",
        "SELECT DISTINCT {columns} FROM {table}",
        "SELECT {columns}, COUNT(*) FROM {table} GROUP BY {columns}",
        "SELECT * FROM {table} LIMIT {limit}",
        "SELECT {columns} FROM {table} WHERE {column} IN ({values})",
        "SELECT {columns} FROM {table} WHERE {column} BETWEEN {value1} AND {value2}",
        "SELECT {columns} FROM {table} WHERE {column} LIKE '{pattern}'",
        "SELECT {columns} FROM {table} WHERE EXISTS (SELECT 1 FROM {table2} WHERE {condition})",
        "WITH {cte} AS (SELECT {columns} FROM {table}) SELECT * FROM {cte}",
        "SELECT CASE WHEN {condition} THEN {value1} ELSE {value2} END FROM {table}"
    ]
    
    table = generate_random_identifier()
    table2 = generate_random_identifier()
    columns = []
    for _ in range(random.randint(1, 4)):
        columns.append(generate_random_identifier())
    
    column_exprs = []
    for col in columns:
        if random.random() > 0.7:
            func = random.choice(['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'UPPER', 'LOWER'])
            column_exprs.append(f"{func}({col})")
        else:
            column_exprs.append(col)
    
    condition_parts = []
    for _ in range(random.randint(1, 3)):
        op = random.choice(['=', '!=', '<', '>', '<=', '>=', 'LIKE', 'IN', 'IS NULL', 'IS NOT NULL'])
        if op == 'IN':
            values = ', '.join([generate_random_value() for _ in range(random.randint(1, 3))])
            condition_parts.append(f"{random.choice(columns)} {op} ({values})")
        elif 'NULL' in op:
            condition_parts.append(f"{random.choice(columns)} {op}")
        else:
            condition_parts.append(f"{random.choice(columns)} {op} {generate_random_value()}")
    
    condition = ' AND '.join(condition_parts)
    join_condition = f"{table}.{random.choice(columns)} = {table2}.{generate_random_identifier()}"
    
    template = random.choice(templates)
    return template.format(
        table=table,
        table1=table,
        table2=table2,
        columns=', '.join(column_exprs),
        condition=condition,
        order=random.choice(columns) if columns else '1',
        group=', '.join(random.sample(columns, min(len(columns), 2))) if columns else '1',
        having=condition,
        join_condition=join_condition,
        limit=str(random.randint(1, 100)),
        column=random.choice(columns) if columns else 'col1',
        values=', '.join([generate_random_value() for _ in range(random.randint(1, 3))]),
        value1=generate_random_value(),
        value2=generate_random_value(),
        pattern='%' + ''.join(random.choices(string.ascii_letters, k=3)) + '%',
        cte='cte_' + generate_random_identifier()
    )

def generate_insert_statement():
    templates = [
        "INSERT INTO {table} VALUES ({values})",
        "INSERT INTO {table} ({columns}) VALUES ({values})",
        "INSERT INTO {table} SELECT {columns} FROM {source_table}",
        "INSERT INTO {table} ({columns}) SELECT {columns} FROM {source_table} WHERE {condition}"
    ]
    
    table = generate_random_identifier()
    source_table = generate_random_identifier()
    columns = [generate_random_identifier() for _ in range(random.randint(1, 5))]
    values = [generate_random_value() for _ in range(random.randint(1, 5))]
    
    template = random.choice(templates)
    return template.format(
        table=table,
        source_table=source_table,
        columns=', '.join(columns),
        values=', '.join(values),
        condition=f"{random.choice(columns)} = {generate_random_value()}" if columns else "1=1"
    )

def generate_update_statement():
    table = generate_random_identifier()
    columns = [generate_random_identifier() for _ in range(random.randint(1, 4))]
    
    set_clauses = []
    for col in random.sample(columns, min(len(columns), 2)):
        set_clauses.append(f"{col} = {generate_random_value()}")
    
    condition_parts = []
    for _ in range(random.randint(1, 2)):
        condition_parts.append(f"{random.choice(columns)} = {generate_random_value()}")
    
    return f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {' AND '.join(condition_parts)}"

def generate_delete_statement():
    table = generate_random_identifier()
    columns = [generate_random_identifier() for _ in range(random.randint(1, 3))]
    
    condition_parts = []
    for _ in range(random.randint(1, 2)):
        condition_parts.append(f"{random.choice(columns)} = {generate_random_value()}")
    
    if random.random() > 0.5:
        return f"DELETE FROM {table} WHERE {' AND '.join(condition_parts)}"
    else:
        return f"DELETE FROM {table}"

def generate_create_statement():
    templates = [
        "CREATE TABLE {table} ({columns})",
        "CREATE INDEX {index} ON {table} ({columns})",
        "CREATE VIEW {view} AS SELECT {columns} FROM {table}",
        "CREATE TEMPORARY TABLE {table} ({columns})",
        "CREATE TABLE IF NOT EXISTS {table} ({columns})"
    ]
    
    table = generate_random_identifier()
    index = 'idx_' + generate_random_identifier()
    view = 'vw_' + generate_random_identifier()
    
    column_defs = []
    for i in range(random.randint(1, 6)):
        col_name = generate_random_identifier()
        data_type = random.choice(['INTEGER', 'VARCHAR(50)', 'TEXT', 'BOOLEAN', 'DATE', 'TIMESTAMP', 'DECIMAL(10,2)'])
        constraints = []
        if random.random() > 0.7:
            constraints.append('PRIMARY KEY')
        if random.random() > 0.7:
            constraints.append('NOT NULL')
        if random.random() > 0.8:
            constraints.append(f'DEFAULT {generate_random_value()}')
        
        column_defs.append(f"{col_name} {data_type} {' '.join(constraints)}".strip())
    
    template = random.choice(templates)
    return template.format(
        table=table,
        index=index,
        view=view,
        columns=', '.join(column_defs)
    )

def generate_drop_statement():
    types = ['TABLE', 'INDEX', 'VIEW', 'TRIGGER']
    obj_type = random.choice(types)
    name = generate_random_identifier()
    
    if random.random() > 0.5:
        return f"DROP {obj_type} IF EXISTS {name}"
    else:
        return f"DROP {obj_type} {name}"

def generate_alter_statement():
    table = generate_random_identifier()
    column = generate_random_identifier()
    
    actions = [
        f"ADD COLUMN {column} {random.choice(['INTEGER', 'VARCHAR(50)', 'TEXT'])}",
        f"DROP COLUMN {column}",
        f"ALTER COLUMN {column} SET DATA TYPE {random.choice(['VARCHAR(100)', 'DECIMAL(10,2)'])}",
        f"ADD CONSTRAINT pk_{table} PRIMARY KEY ({column})",
        f"DROP CONSTRAINT pk_{table}"
    ]
    
    return f"ALTER TABLE {table} {random.choice(actions)}"

def generate_union_statement():
    select1 = generate_select_statement()
    select2 = generate_select_statement()
    
    union_types = ['UNION', 'UNION ALL', 'INTERSECT', 'EXCEPT']
    return f"({select1}) {random.choice(union_types)} ({select2})"

def generate_subquery_statement():
    templates = [
        "SELECT * FROM ({subquery}) AS sub",
        "SELECT * FROM {table} WHERE {column} IN ({subquery})",
        "SELECT * FROM {table} WHERE {column} = ({subquery})",
        "SELECT * FROM {table} WHERE EXISTS ({subquery})",
        "SELECT ({subquery}) FROM {table}"
    ]
    
    table = generate_random_identifier()
    column = generate_random_identifier()
    subquery = generate_select_statement()
    
    template = random.choice(templates)
    return template.format(
        table=table,
        column=column,
        subquery=subquery
    )

def generate_edge_case_statement():
    edge_cases = [
        # Empty queries and minimal forms
        "",
        ";",
        "SELECT",
        "SELECT 1",
        "SELECT NULL",
        "SELECT 1 + 1",
        
        # Weird whitespace
        "  SELECT  \n  *  \n  FROM  \n  t  ",
        "SELECT/*comment*/1",
        "SELECT--comment\n1",
        
        # Strange identifiers
        "SELECT `column`",
        'SELECT "column"',
        "SELECT [column]",
        "SELECT * FROM `table`",
        
        # Extreme values
        "SELECT 999999999999999999999999999999",
        "SELECT 0.000000000000000000000000000001",
        "SELECT 'very long string' || ' continued' || ' even more'",
        
        # Special characters
        "SELECT 'string with \\'quotes\\''",
        "SELECT 'string with \\nnewline'",
        "SELECT 'string with \\ttab'",
        
        # Invalid but interesting
        "SELECT * FROM WHERE",
        "SELECT * GROUP BY",
        "INSERT INTO VALUES",
        "UPDATE SET",
        
        # Nested parentheses
        "SELECT (((1)))",
        "SELECT * FROM (((t)))",
        
        # Mixed case and weird casing
        "sElEcT * FrOm TaBlE",
        "Select * From Table",
        
        # Multiple statements
        "SELECT 1; SELECT 2; SELECT 3",
        "CREATE TABLE t (a INT); INSERT INTO t VALUES (1); SELECT * FROM t",
        
        # Window functions if supported
        "SELECT ROW_NUMBER() OVER () FROM t",
        "SELECT RANK() OVER (ORDER BY col) FROM t",
        
        # Cast expressions
        "SELECT CAST(1 AS VARCHAR)",
        "SELECT 1::INTEGER",
        
        # Case expressions
        "SELECT CASE 1 WHEN 1 THEN 'one' WHEN 2 THEN 'two' ELSE 'other' END",
        "SELECT CASE WHEN 1=1 THEN 'true' ELSE 'false' END",
        
        # Coalesce and nullif
        "SELECT COALESCE(NULL, 1, 2)",
        "SELECT NULLIF(1, 1)",
        
        # Mathematical expressions
        "SELECT 1 + 2 * 3 / 4 - 5",
        "SELECT POWER(2, 10)",
        "SELECT ABS(-1), CEIL(1.1), FLOOR(1.9), ROUND(1.555, 2)",
        
        # String functions
        "SELECT CONCAT('a', 'b', 'c')",
        "SELECT SUBSTR('abcdef', 2, 3)",
        "SELECT TRIM('  abc  ')",
        "SELECT REPLACE('abc', 'b', 'x')",
        
        # Date functions
        "SELECT CURRENT_DATE + INTERVAL '1' DAY",
        "SELECT EXTRACT(YEAR FROM CURRENT_DATE)",
        
        # Aggregates with filters
        "SELECT SUM(col) FILTER (WHERE col > 0) FROM t",
        
        # Lateral joins
        "SELECT * FROM t, LATERAL (SELECT * FROM u WHERE u.id = t.id)",
        
        # Recursive CTEs
        "WITH RECURSIVE cte AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM cte WHERE n < 10) SELECT * FROM cte",
        
        # JSON if supported
        "SELECT JSON_EXTRACT('{\"a\":1}', '$.a')",
        "SELECT JSON_ARRAY(1, 2, 3)",
        
        # Arrays
        "SELECT ARRAY[1, 2, 3]",
        "SELECT UNNEST(ARRAY[1, 2, 3])",
        
        # Pivot/unpivot
        "SELECT * FROM t PIVOT (SUM(val) FOR cat IN ('A', 'B', 'C'))",
        
        # Sample/tablesample
        "SELECT * FROM t TABLESAMPLE BERNOULLI (10)",
        
        # Explain/analyze
        "EXPLAIN SELECT * FROM t",
        "EXPLAIN ANALYZE SELECT * FROM t",
        
        # Transaction commands
        "BEGIN",
        "COMMIT",
        "ROLLBACK",
        "SAVEPOINT s1",
        
        # Vacuum/analyze
        "VACUUM",
        "ANALYZE t",
        
        # Privileges
        "GRANT SELECT ON t TO user",
        "REVOKE INSERT ON t FROM user",
        
        # Constraints
        "ALTER TABLE t ADD CONSTRAINT CHECK (col > 0)",
        "ALTER TABLE t ADD CONSTRAINT UNIQUE (col1, col2)",
        
        # Index with options
        "CREATE INDEX idx ON t (col) INCLUDE (col2) WHERE col IS NOT NULL",
        
        # Full text search
        "SELECT * FROM t WHERE to_tsvector('english', col) @@ to_tsquery('english', 'word')",
        
        # Geometric types
        "SELECT POINT(0, 0)",
        "SELECT LINE(POINT(0,0), POINT(1,1))",
        
        # Network types
        "SELECT '192.168.1.1'::INET",
        "SELECT '01:23:45:67:89:ab'::MACADDR",
        
        # Range types
        "SELECT '[1,10]'::int4range",
        "SELECT INTERVAL '1 day'",
        
        # Money type
        "SELECT '$123.45'::MONEY",
        
        # UUID
        "SELECT 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'::UUID",
        
        # XML
        "SELECT XMLPARSE(DOCUMENT '<root><a>1</a></root>')",
        
        # Regular expressions
        "SELECT * FROM t WHERE col ~ '^[A-Z]+$'",
        "SELECT REGEXP_REPLACE(col, '\\d+', 'X') FROM t",
        
        # Soundex/metaphone
        "SELECT SOUNDEX('hello')",
        "SELECT METAPHONE('hello', 4)",
        
        # Triggers
        "CREATE TRIGGER trig AFTER INSERT ON t FOR EACH ROW EXECUTE FUNCTION func()",
        
        # Sequences
        "CREATE SEQUENCE seq",
        "SELECT nextval('seq')",
        
        # Domains
        "CREATE DOMAIN email AS VARCHAR(255) CHECK (VALUE ~ '@')",
        
        # Composite types
        "CREATE TYPE point AS (x FLOAT, y FLOAT)",
        
        # Enums
        "CREATE TYPE mood AS ENUM ('sad', 'ok', 'happy')",
        
        # Partitions
        "CREATE TABLE t PARTITION OF parent FOR VALUES IN (1, 2, 3)",
        
        # Inheritance
        "CREATE TABLE child () INHERITS (parent)",
        
        # Rules
        "CREATE RULE rule AS ON INSERT TO t DO INSTEAD NOTHING",
        
        # Prepared statements
        "PREPARE stmt AS SELECT * FROM t WHERE id = $1",
        "EXECUTE stmt(1)",
        
        # Cursors
        "DECLARE cur CURSOR FOR SELECT * FROM t",
        "FETCH NEXT FROM cur",
        
        # Copy
        "COPY t FROM '/path/to/file.csv'",
        
        # Notify/listen
        "NOTIFY channel, 'message'",
        "LISTEN channel",
        
        # Set commands
        "SET search_path TO public",
        "SET TIME ZONE 'UTC'",
        
        # Show commands
        "SHOW ALL",
        "SHOW search_path",
        
        # Reset
        "RESET search_path",
        
        # Discard
        "DISCARD ALL",
        
        # Checkpoint
        "CHECKPOINT",
        
        # Reindex
        "REINDEX TABLE t",
        
        # Cluster
        "CLUSTER t USING idx",
        
        # Refresh materialized view
        "REFRESH MATERIALIZED VIEW v",
        
        # Lock table
        "LOCK TABLE t IN EXCLUSIVE MODE",
        
        # Comment
        "COMMENT ON TABLE t IS 'table comment'",
        
        # Security label
        "SECURITY LABEL FOR 'selinux' ON TABLE t IS 'system_u:object_r:sepgsql_table_t:s0'",
        
        # Event trigger
        "CREATE EVENT TRIGGER trig ON ddl_command_start EXECUTE FUNCTION func()",
        
        # Publication/subscription
        "CREATE PUBLICATION pub FOR TABLE t",
        "CREATE SUBSCRIPTION sub CONNECTION 'dbname=db' PUBLICATION pub",
        
        # Collation
        "CREATE COLLATION case_insensitive FROM \"C\"",
        
        # Conversion
        "CREATE CONVERSION conv FOR 'LATIN1' TO 'UTF8' FROM func",
        
        # Operator
        "CREATE OPERATOR + (PROCEDURE = func, LEFTARG = integer, RIGHTARG = integer)",
        
        # Operator class/family
        "CREATE OPERATOR CLASS opclass FOR TYPE int4 USING btree",
        "CREATE OPERATOR FAMILY opfam USING btree",
        
        # Text search
        "CREATE TEXT SEARCH CONFIGURATION cfg (PARSER = default)",
        "CREATE TEXT SEARCH DICTIONARY dict (TEMPLATE = simple)",
        
        # Foreign data wrapper
        "CREATE FOREIGN DATA WRAPPER fdw",
        "CREATE SERVER srv FOREIGN DATA WRAPPER fdw",
        "CREATE FOREIGN TABLE ft () SERVER srv",
        
        # User mapping
        "CREATE USER MAPPING FOR user SERVER srv",
        
        # Extension
        "CREATE EXTENSION hstore",
        
        # Language
        "CREATE LANGUAGE plpgsql",
        
        # Procedure
        "CREATE PROCEDURE proc() AS $$ BEGIN NULL; END; $$ LANGUAGE plpgsql",
        
        # Function with various options
        "CREATE FUNCTION func() RETURNS int AS $$ SELECT 1 $$ LANGUAGE sql",
        "CREATE FUNCTION func() RETURNS SETOF int AS $$ SELECT 1 $$ LANGUAGE sql",
        "CREATE FUNCTION func() RETURNS TABLE (a int, b text) AS $$ SELECT 1, 'x' $$ LANGUAGE sql",
        "CREATE FUNCTION func() RETURNS int LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$ SELECT 1 $$",
        
        # Aggregate
        "CREATE AGGREGATE agg (BASETYPE = int4, SFUNC = func, STYPE = int)",
        
        # Cast
        "CREATE CAST (int AS text) WITH FUNCTION int_to_text",
        
        # Transform
        "CREATE TRANSFORM FOR int LANGUAGE plpythonu (FROM SQL WITH FUNCTION func)",
        
        # Access method
        "CREATE ACCESS METHOD am TYPE TABLE HANDLER func",
        
        # Tablespace
        "CREATE TABLESPACE ts LOCATION '/path'",
        
        # Role
        "CREATE ROLE role",
        "GRANT role TO user",
        
        # Group
        "CREATE GROUP group",
        
        # User
        "CREATE USER user",
        
        # Schema
        "CREATE SCHEMA schema",
        
        # Database
        "CREATE DATABASE db",
        
        # Tablesample method
        "CREATE TABLESAMPLE METHOD method",
        
        # Statistical functions
        "SELECT CORR(x, y), REGR_SLOPE(y, x), STDDEV(x), VARIANCE(x) FROM t",
        
        # Window functions with frame
        "SELECT SUM(col) OVER (ORDER BY col ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) FROM t",
        "SELECT FIRST_VALUE(col) OVER (ORDER BY col RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) FROM t",
        
        # Grouping sets
        "SELECT col1, col2, SUM(val) FROM t GROUP BY GROUPING SETS ((col1), (col2), ())",
        "SELECT col1, col2, SUM(val) FROM t GROUP BY CUBE (col1, col2)",
        "SELECT col1, col2, SUM(val) FROM t GROUP BY ROLLUP (col1, col2)",
        
        # Distinct on
        "SELECT DISTINCT ON (col1) col1, col2 FROM t ORDER BY col1, col2",
        
        # Returning
        "INSERT INTO t VALUES (1) RETURNING *",
        "UPDATE t SET col = 1 RETURNING col",
        "DELETE FROM t RETURNING *",
        
        # Upsert
        "INSERT INTO t VALUES (1) ON CONFLICT (id) DO UPDATE SET col = EXCLUDED.col",
        "INSERT INTO t VALUES (1) ON CONFLICT DO NOTHING",
        
        # Overlaps operator
        "SELECT (DATE '2001-02-16', DATE '2001-12-21') OVERLAPS (DATE '2001-10-30', DATE '2002-10-30')",
        
        # XML functions
        "SELECT XMLELEMENT(NAME root, XMLATTRIBUTES(1 AS id), XMLELEMENT(NAME child, 'value'))",
        "SELECT XMLFOREST(col1, col2)",
        
        # JSON functions
        "SELECT JSON_BUILD_OBJECT('a', 1, 'b', TRUE)",
        "SELECT JSON_OBJECT('{a, 1, b, 2}')",
        "SELECT JSON_ARRAY_ELEMENTS('[1,2,3]')",
        "SELECT JSON_TYPEOF('1')",
        
        # Hstore
        "SELECT 'a=>1,b=>2'::hstore",
        "SELECT hstore('a', '1')",
        
        # Ltree
        "SELECT 'Top.Science'::ltree",
        
        # PostGIS if available
        "SELECT ST_MakePoint(0, 0)",
        "SELECT ST_Area(ST_MakePolygon(ST_MakeLine(ARRAY[ST_MakePoint(0,0), ST_MakePoint(1,0), ST_MakePoint(1,1), ST_MakePoint(0,1), ST_MakePoint(0,0)])))",
        
        # Cryptography
        "SELECT MD5('hello')",
        "SELECT SHA256('hello')",
        "SELECT ENCODE('hello'::bytea, 'base64')",
        
        # Compression
        "SELECT COMPRESS('hello')",
        "SELECT UNCOMPRESS(COMPRESS('hello'))",
        
        # Full SQL standard reserved words
        "SELECT ALL, AND, ANY, ARRAY, AS, ASYMMETRIC, AUTHORIZATION, BETWEEN, BOTH, CASE, CAST, CHECK, COLLATE, "
        "COLUMN, CONSTRAINT, CREATE, CROSS, CURRENT_CATALOG, CURRENT_DATE, CURRENT_ROLE, CURRENT_SCHEMA, "
        "CURRENT_TIME, CURRENT_TIMESTAMP, CURRENT_USER, DEFAULT, DEFERRABLE, DESC, DISTINCT, DO, ELSE, END, "
        "EXCEPT, FALSE, FETCH, FOR, FOREIGN, FREEZE, FROM, FULL, GRANT, GROUP, HAVING, ILIKE, IN, INITIALLY, "
        "INNER, INTERSECT, INTO, IS, ISNULL, JOIN, LEADING, LEFT, LIKE, LIMIT, LOCALTIME, LOCALTIMESTAMP, "
        "NATURAL, NOT, NOTNULL, NULL, OFF, OFFSET, ON, ONLY, OR, ORDER, OUTER, OVERLAPS, PLACING, PRIMARY, "
        "REFERENCES, RETURNING, RIGHT, SELECT, SESSION_USER, SIMILAR, SOME, SYMMETRIC, TABLE, THEN, TO, "
        "TRAILING, TRUE, UNION, UNIQUE, USER, USING, VARIADIC, VERBOSE, WHEN, WHERE, WINDOW, WITH",
        
        # Non-standard but common
        "SELECT AUTO_INCREMENT, BINARY, BLOB, CHANGE, DATABASES, DEC, DELAYED, DESCRIBE, DUAL, ENCLOSED, "
        "ENGINES, ESCAPED, FIELDS, FLOAT4, FLOAT8, FORCE, FULLTEXT, GENERATED, IGNORE, INDEX, INFILE, INT1, "
        "INT2, INT3, INT4, INT8, KEYS, KILL, LINES, LOAD, LOCK, LONG, LOW_PRIORITY, MEDIUMINT, MODIFY, "
        "NO_WRITE_TO_BINLOG, OPTIMIZE, OPTIONALLY, OUT_FILE, PROCEDURE, PURGE, READ, REFERENCES, REGEXP, "
        "RENAME, REPEAT, REPLACE, REQUIRE, RESTRICT, RLIKE, SCHEMAS, SEPARATOR, SHOW, SQL_BIG_RESULT, "
        "SQL_CALC_FOUND_ROWS, SQL_SMALL_RESULT, SSL, STARTING, STRAIGHT_JOIN, TERMINATED, TINYINT, "
        "UNSIGNED, USAGE, USE, VARCHARACTER, VARYING, WRITE, XOR, YEAR_MONTH, ZEROFILL",
        
        # Edge case: really long identifier
        f"SELECT * FROM {'x' * 100}",
        
        # Edge case: many columns
        "SELECT " + ", ".join([f"col{i}" for i in range(1, 51)]) + " FROM t",
        
        # Edge case: deeply nested
        "SELECT " + "(".join([str(i) for i in range(1, 51)]) + ")" * 49,
        
        # Edge case: Unicode
        "SELECT 'café', 'caf\\u00e9', '🎉', '👨‍👩‍👧‍👦', '𐌀𐌁𐌂'",
        
        # Edge case: SQL injection patterns
        "SELECT * FROM t WHERE id = '1' OR '1' = '1'",
        "SELECT * FROM t WHERE id = '1'; DROP TABLE t; --",
        "SELECT * FROM t WHERE id = 1 UNION SELECT password FROM users",
        
        # Edge case: weird numbers
        "SELECT 0xDEADBEEF, 0b1010, 1e100, 1e-100, nan(), infinity()",
        
        # Edge case: time zones
        "SELECT TIMESTAMP WITH TIME ZONE '2001-02-16 20:38:40-05'",
        "SELECT TIMESTAMP WITHOUT TIME ZONE '2001-02-16 20:38:40'",
        
        # Edge case: intervals with all parts
        "SELECT INTERVAL '1 year 2 months 3 days 4 hours 5 minutes 6 seconds'",
        
        # Edge case: mixed character sets
        "SELECT _utf8'hello', _latin1'world', N'unicode'",
        
        # Edge case: national character
        "SELECT N'text', NATIONAL 'text'",
        
        # Edge case: hex string
        "SELECT X'4D7953514C', 0x4D7953514C",
        
        # Edge case: bit string
        "SELECT B'1010', b'1010'",
        
        # Edge case: money
        "SELECT $100.50, €100.50, £100.50, ¥100.50",
        
        # Edge case: scientific notation
        "SELECT 1.23e45, -9.87e-65",
        
        # Edge case: octal
        "SELECT 0755, 0o755",
        
        # Edge case: binary
        "SELECT 0b1101",
        
        # Edge case: IPv6
        "SELECT '::1', '2001:0db8:85a3:0000:0000:8a2e:0370:7334'",
        
        # Edge case: MAC address
        "SELECT '08:00:2b:01:02:03', '08-00-2b-01-02-03', '08002b:010203', '08002b-010203'",
        
        # Edge case: geometric box
        "SELECT BOX '((0,0),(1,1))'",
        
        # Edge case: circle
        "SELECT CIRCLE '((0,0),10)'",
        
        # Edge case: path
        "SELECT PATH '((0,0),(1,1),(2,0))'",
        
        # Edge case: polygon
        "SELECT POLYGON '((0,0),(0,1),(1,1),(1,0))'",
        
        # Edge case: line
        "SELECT LINE '((0,0),(1,1))'",
        
        # Edge case: line segment
        "SELECT LSEG '((0,0),(1,1))'",
        
        # Edge case: point
        "SELECT POINT '(0,0)'",
        
        # Edge case: cidr
        "SELECT '192.168.100.128/25'::CIDR",
        
        # Edge case: inet with netmask
        "SELECT '192.168.1.0/24'::INET",
        
        # Edge case: tsvector
        "SELECT 'a fat cat sat on a mat and ate a fat rat'::tsvector",
        
        # Edge case: tsquery
        "SELECT 'fat & rat'::tsquery",
        
        # Edge case: txid_snapshot
        "SELECT '10:20:10,14,15'::txid_snapshot",
        
        # Edge case: uuid with all forms
        "SELECT 'A0EEBC99-9C0B-4EF8-BB6D-6BB9BD380A11'::uuid",
        "SELECT 'a0eebc999c0b4ef8bb6d6bb9bd380a11'::uuid",
        "SELECT '{a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11}'::uuid",
        "SELECT 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'::uuid",
        
        # Edge case: xml with all options
        "SELECT XML '<foo>bar</foo>'",
        "SELECT XMLDOCUMENT '<?xml version=\"1.0\"?><foo>bar</foo>'",
        "SELECT XMLPARSE(CONTENT '<foo>bar</foo>')",
        "SELECT XMLPARSE(DOCUMENT '<?xml version=\"1.0\"?><foo>bar</foo>')",
        
        # Edge case: json with all forms
        "SELECT JSON '{\"a\":1}'",
        "SELECT JSON '[1,2,3]'",
        "SELECT JSON '"hello"'",
        "SELECT JSON 'null'",
        "SELECT JSON 'true'",
        "SELECT JSON 'false'",
        "SELECT JSON '123.45'",
        
        # Edge case: jsonb
        "SELECT JSONB '{\"a\":1}'",
        
        # Edge case: array with all dimensions
        "SELECT ARRAY[[1,2],[3,4]]",
        "SELECT ARRAY[ARRAY[1,2],ARRAY[3,4]]",
        "SELECT '{{1,2},{3,4}}'::int[][]",
        
        # Edge case: composite with nesting
        "SELECT ROW(1, ROW(2, 3), ARRAY[4,5])",
        
        # Edge case: domain with check
        "CREATE DOMAIN posint AS int CHECK (VALUE > 0)",
        "SELECT 1::posint",
        
        # Edge case: range with all bounds
        "SELECT '[1,10]'::int4range",
        "SELECT '(1,10]'::int4range",
        "SELECT '[1,10)'::int4range",
        "SELECT '(1,10)'::int4range",
        "SELECT 'empty'::int4range",
        
        # Edge case: multirange
        "SELECT '{[1,5], [10,15]}'::int4multirange",
        
        # Edge case: pg_lsn
        "SELECT '0/0'::pg_lsn",
        "SELECT 'FFFFFFFF/FFFFFFFF'::pg_lsn",
        
        # Edge case: tid
        "SELECT '(0,1)'::tid",
        
        # Edge case: xid8
        "SELECT '123'::xid8",
        
        # Edge case: pg_snapshot
        "SELECT '10:20:10,14,15'::pg_snapshot",
        
        # Edge case: pg_node_tree
        "SELECT '(a b)'::pg_node_tree",
        
        # Edge case: aclitem
        "SELECT 'user=r/user'::aclitem",
        
        # Edge case: regproc
        "SELECT 'now'::regproc",
        
        # Edge case: regprocedure
        "SELECT 'now()'::regprocedure",
        
        # Edge case: regoper
        "SELECT '+'::regoper",
        
        # Edge case: regoperator
        "SELECT '+(integer,integer)'::regoperator",
        
        # Edge case: regclass
        "SELECT 'pg_class'::regclass",
        
        # Edge case: regtype
        "SELECT 'integer'::regtype",
        
        # Edge case: regrole
        "SELECT 'postgres'::regrole",
        
        # Edge case: regnamespace
        "SELECT 'pg_catalog'::regnamespace",
        
        # Edge case: regconfig
        "SELECT 'english'::regconfig",
        
        # Edge case: regdictionary
        "SELECT 'simple'::regdictionary",
        
        # Edge case: pg_ddl_command
        "SELECT 'CREATE TABLE t (a int)'::pg_ddl_command",
        
        # Edge case: tablefunc crosstab
        "SELECT * FROM crosstab('SELECT rowid, attribute, value FROM ct') AS ct(row_name text, category_1 text, category_2 text)",
        
        # Edge case: dblink
        "SELECT * FROM dblink('dbname=postgres', 'SELECT 1') AS t(a int)",
        
        # Edge case: postgres_fdw
        "SELECT * FROM foreign_table",
        
        # Edge case: file_fdw
        "SELECT * FROM file_table",
        
        # Edge case: pg_prewarm
        "SELECT pg_prewarm('t')",
        
        # Edge case: pg_buffercache
        "SELECT * FROM pg_buffercache",
        
        # Edge case: pg_stat_statements
        "SELECT * FROM pg_stat_statements",
        
        # Edge case: auto_explain
        "LOAD 'auto_explain'",
        
        # Edge case: pageinspect
        "SELECT * FROM page_header(get_raw_page('t', 0))",
        
        # Edge case: pgstattuple
        "SELECT * FROM pgstattuple('t')",
        
        # Edge case: pg_freespacemap
        "SELECT * FROM pg_freespace('t')",
        
        # Edge case: pg_visibility
        "SELECT * FROM pg_visibility('t')",
        
        # Edge case: pg_walinspect
        "SELECT * FROM pg_get_wal_records(NULL, NULL)",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts
        "SELECT * FROM pg_prepared_xacts",
        
        # Edge case: pg_prepared_statements
        "SELECT * FROM pg_prepared_statements",
        
        # Edge case: pg_seclabels
        "SELECT * FROM pg_seclabels",
        
        # Edge case: pg_settings
        "SELECT * FROM pg_settings",
        
        # Edge case: pg_file_settings
        "SELECT * FROM pg_file_settings",
        
        # Edge case: pg_hba_file_rules
        "SELECT * FROM pg_hba_file_rules",
        
        # Edge case: pg_timezone_abbrevs
        "SELECT * FROM pg_timezone_abbrevs",
        
        # Edge case: pg_timezone_names
        "SELECT * FROM pg_timezone_names",
        
        # Edge case: pg_config
        "SELECT * FROM pg_config",
        
        # Edge case: pg_shmem_allocations
        "SELECT * FROM pg_shmem_allocations",
        
        # Edge case: pg_backend_memory_contexts
        "SELECT * FROM pg_backend_memory_contexts",
        
        # Edge case: pg_stat_kcache
        "SELECT * FROM pg_stat_kcache",
        
        # Edge case: pg_stat_statements_info
        "SELECT * FROM pg_stat_statements_info",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription_stats
        "SELECT * FROM pg_stat_subscription_stats",
        
        # Edge case: pg_stat_recovery_prefetch
        "SELECT * FROM pg_stat_recovery_prefetch",
        
        # Edge case: pg_stat_io
        "SELECT * FROM pg_stat_io",
        
        # Edge case: pg_stat_slru
        "SELECT * FROM pg_stat_slru",
        
        # Edge case: pg_stat_archiver
        "SELECT * FROM pg_stat_archiver",
        
        # Edge case: pg_stat_bgwriter
        "SELECT * FROM pg_stat_bgwriter",
        
        # Edge case: pg_stat_wal
        "SELECT * FROM pg_stat_wal",
        
        # Edge case: pg_stat_database
        "SELECT * FROM pg_stat_database",
        
        # Edge case: pg_stat_database_conflicts
        "SELECT * FROM pg_stat_database_conflicts",
        
        # Edge case: pg_stat_user_functions
        "SELECT * FROM pg_stat_user_functions",
        
        # Edge case: pg_stat_xact_user_functions
        "SELECT * FROM pg_stat_xact_user_functions",
        
        # Edge case: pg_stat_user_tables
        "SELECT * FROM pg_stat_user_tables",
        
        # Edge case: pg_stat_xact_user_tables
        "SELECT * FROM pg_stat_xact_user_tables",
        
        # Edge case: pg_statio_user_tables
        "SELECT * FROM pg_statio_user_tables",
        
        # Edge case: pg_stat_user_indexes
        "SELECT * FROM pg_stat_user_indexes",
        
        # Edge case: pg_statio_user_indexes
        "SELECT * FROM pg_statio_user_indexes",
        
        # Edge case: pg_statio_user_sequences
        "SELECT * FROM pg_statio_user_sequences",
        
        # Edge case: pg_stat_user_sequences
        "SELECT * FROM pg_stat_user_sequences",
        
        # Edge case: pg_stat_activity
        "SELECT * FROM pg_stat_activity",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_stat_subscription
        "SELECT * FROM pg_stat_subscription",
        
        # Edge case: pg_stat_ssl
        "SELECT * FROM pg_stat_ssl",
        
        # Edge case: pg_stat_gssapi
        "SELECT * FROM pg_stat_gssapi",
        
        # Edge case: pg_stat_progress_vacuum
        "SELECT * FROM pg_stat_progress_vacuum",
        
        # Edge case: pg_stat_progress_cluster
        "SELECT * FROM pg_stat_progress_cluster",
        
        # Edge case: pg_stat_progress_create_index
        "SELECT * FROM pg_stat_progress_create_index",
        
        # Edge case: pg_stat_progress_analyze
        "SELECT * FROM pg_stat_progress_analyze",
        
        # Edge case: pg_stat_progress_basebackup
        "SELECT * FROM pg_stat_progress_basebackup",
        
        # Edge case: pg_stat_progress_copy
        "SELECT * FROM pg_stat_progress_copy",
        
        # Edge case: pg_user_mappings
        "SELECT * FROM pg_user_mappings",
        
        # Edge case: pg_replication_slots
        "SELECT * FROM pg_replication_slots",
        
        # Edge case: pg_stat_replication
        "SELECT * FROM pg_stat_replication",
        
        # Edge case: pg_stat_wal_receiver
        "SELECT * FROM pg_stat_wal_receiver",
        
        # Edge case: pg_subscription_rel
        "SELECT * FROM pg_subscription_rel",
        
        # Edge case: pg_publication_tables
        "SELECT * FROM pg_publication_tables",
        
        # Edge case: pg_locks
        "SELECT * FROM pg_locks",
        
        # Edge case: pg_prepared_xacts