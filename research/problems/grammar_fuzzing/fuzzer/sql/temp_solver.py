"""
Temp solver for testing the SQL fuzzer evaluator.

This implements a simple fuzzer that generates various SQL statements.
"""


class Solution:
    def solve(self, resources_path: str) -> dict:
        """Return fuzzer code."""
        fuzzer_code = '''
import random

# Simple SQL statement templates
SELECT_TEMPLATES = [
    "SELECT * FROM {table}",
    "SELECT {col} FROM {table}",
    "SELECT {col1}, {col2} FROM {table}",
    "SELECT * FROM {table} WHERE {col} = {val}",
    "SELECT * FROM {table} WHERE {col} > {val}",
    "SELECT * FROM {table} WHERE {col} < {val}",
    "SELECT * FROM {table} WHERE {col} >= {val}",
    "SELECT * FROM {table} WHERE {col} <= {val}",
    "SELECT * FROM {table} WHERE {col} != {val}",
    "SELECT * FROM {table} WHERE {col} <> {val}",
    "SELECT * FROM {table} WHERE {col} BETWEEN {val1} AND {val2}",
    "SELECT * FROM {table} WHERE {col} IN ({val1}, {val2}, {val3})",
    "SELECT * FROM {table} WHERE {col} LIKE {pattern}",
    "SELECT * FROM {table} WHERE {col} IS NULL",
    "SELECT * FROM {table} WHERE {col} IS NOT NULL",
    "SELECT * FROM {table} WHERE {col1} = {val} AND {col2} > {val2}",
    "SELECT * FROM {table} WHERE {col1} = {val} OR {col2} > {val2}",
    "SELECT * FROM {table} WHERE NOT {col} = {val}",
    "SELECT * FROM {table} ORDER BY {col}",
    "SELECT * FROM {table} ORDER BY {col} ASC",
    "SELECT * FROM {table} ORDER BY {col} DESC",
    "SELECT * FROM {table} ORDER BY {col1}, {col2}",
    "SELECT * FROM {table} LIMIT {num}",
    "SELECT * FROM {table} LIMIT {num1} OFFSET {num2}",
    "SELECT COUNT(*) FROM {table}",
    "SELECT SUM({col}) FROM {table}",
    "SELECT AVG({col}) FROM {table}",
    "SELECT MIN({col}) FROM {table}",
    "SELECT MAX({col}) FROM {table}",
    "SELECT {col}, COUNT(*) FROM {table} GROUP BY {col}",
    "SELECT {col}, SUM({col2}) FROM {table} GROUP BY {col}",
    "SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} HAVING COUNT(*) > {val}",
    "SELECT DISTINCT {col} FROM {table}",
    "SELECT * FROM {table1} JOIN {table2} ON {table1}.{col} = {table2}.{col}",
    "SELECT * FROM {table1} LEFT JOIN {table2} ON {table1}.{col} = {table2}.{col}",
    "SELECT * FROM {table1} RIGHT JOIN {table2} ON {table1}.{col} = {table2}.{col}",
    "SELECT * FROM {table1} INNER JOIN {table2} ON {table1}.{col} = {table2}.{col}",
    "SELECT * FROM {table1}, {table2} WHERE {table1}.{col} = {table2}.{col}",
    "SELECT * FROM (SELECT * FROM {table}) AS subq",
    "SELECT * FROM {table} WHERE {col} IN (SELECT {col} FROM {table2})",
    "SELECT * FROM {table} WHERE EXISTS (SELECT 1 FROM {table2} WHERE {table2}.{col} = {table}.{col})",
    "SELECT {col} AS alias_col FROM {table} AS alias_tbl",
]

INSERT_TEMPLATES = [
    "INSERT INTO {table} VALUES ({val1})",
    "INSERT INTO {table} VALUES ({val1}, {val2})",
    "INSERT INTO {table} VALUES ({val1}, {val2}, {val3})",
    "INSERT INTO {table} ({col1}) VALUES ({val1})",
    "INSERT INTO {table} ({col1}, {col2}) VALUES ({val1}, {val2})",
    "INSERT INTO {table} ({col1}, {col2}, {col3}) VALUES ({val1}, {val2}, {val3})",
    "INSERT INTO {table} VALUES ({val1}, {val2}), ({val3}, {val4})",
]

UPDATE_TEMPLATES = [
    "UPDATE {table} SET {col} = {val}",
    "UPDATE {table} SET {col1} = {val1}, {col2} = {val2}",
    "UPDATE {table} SET {col} = {val} WHERE {col2} = {val2}",
    "UPDATE {table} SET {col} = {col} + {val}",
    "UPDATE {table} SET {col} = {val} WHERE {col2} > {val2} AND {col3} < {val3}",
]

DELETE_TEMPLATES = [
    "DELETE FROM {table}",
    "DELETE FROM {table} WHERE {col} = {val}",
    "DELETE FROM {table} WHERE {col} > {val}",
    "DELETE FROM {table} WHERE {col} IN ({val1}, {val2})",
    "DELETE FROM {table} WHERE {col} BETWEEN {val1} AND {val2}",
]

CREATE_TEMPLATES = [
    "CREATE TABLE {table} ({col} INT)",
    "CREATE TABLE {table} ({col} VARCHAR(255))",
    "CREATE TABLE {table} ({col} TEXT)",
    "CREATE TABLE {table} ({col} FLOAT)",
    "CREATE TABLE {table} ({col} BOOLEAN)",
    "CREATE TABLE {table} ({col} DATE)",
    "CREATE TABLE {table} ({col1} INT, {col2} VARCHAR(255))",
    "CREATE TABLE {table} ({col1} INT PRIMARY KEY, {col2} VARCHAR(255))",
    "CREATE TABLE {table} ({col1} INT NOT NULL, {col2} VARCHAR(255))",
    "CREATE TABLE {table} ({col1} INT UNIQUE, {col2} VARCHAR(255))",
    "CREATE TABLE {table} ({col1} INT DEFAULT 0, {col2} VARCHAR(255))",
    "CREATE TABLE {table} ({col1} INT, {col2} VARCHAR(255), PRIMARY KEY ({col1}))",
    "CREATE TABLE {table} ({col1} INT AUTO_INCREMENT, {col2} VARCHAR(255))",
    "CREATE TABLE {table} ({col1} INT CHECK ({col1} > 0))",
    "CREATE TABLE IF NOT EXISTS {table} ({col} INT)",
]

TABLES = ["users", "orders", "products", "items", "customers", "employees", "departments", "t1", "t2", "tbl"]
COLUMNS = ["id", "name", "value", "price", "quantity", "status", "created_at", "updated_at", "col1", "col2", "col3", "a", "b", "c"]
STRING_VALUES = ["'test'", "'hello'", "'world'", "'foo'", "'bar'", "'%test%'", "'test%'", "'%test'"]
INT_VALUES = ["1", "42", "100", "0", "-1", "999"]

call_count = 0

def fuzz(parse_sql):
    global call_count
    call_count += 1
    
    statements = []
    
    # Generate a batch of random statements
    for _ in range(20):
        template_type = random.choice(["select", "insert", "update", "delete", "create"])
        
        if template_type == "select":
            template = random.choice(SELECT_TEMPLATES)
        elif template_type == "insert":
            template = random.choice(INSERT_TEMPLATES)
        elif template_type == "update":
            template = random.choice(UPDATE_TEMPLATES)
        elif template_type == "delete":
            template = random.choice(DELETE_TEMPLATES)
        else:
            template = random.choice(CREATE_TEMPLATES)
        
        # Fill in the template
        stmt = template.format(
            table=random.choice(TABLES),
            table1=random.choice(TABLES),
            table2=random.choice(TABLES),
            col=random.choice(COLUMNS),
            col1=random.choice(COLUMNS),
            col2=random.choice(COLUMNS),
            col3=random.choice(COLUMNS),
            val=random.choice(INT_VALUES + STRING_VALUES),
            val1=random.choice(INT_VALUES + STRING_VALUES),
            val2=random.choice(INT_VALUES + STRING_VALUES),
            val3=random.choice(INT_VALUES + STRING_VALUES),
            val4=random.choice(INT_VALUES + STRING_VALUES),
            num=random.choice(INT_VALUES),
            num1=random.choice(["1", "10", "100"]),
            num2=random.choice(["0", "5", "10"]),
            pattern=random.choice(STRING_VALUES),
        )
        statements.append(stmt)
    
    # Execute statements through parser
    parse_sql(statements)
    
    # Stop after 100 calls to keep it quick for testing
    if call_count >= 100:
        return False
    
    return True
'''
        return {"code": fuzzer_code}


if __name__ == "__main__":
    # Quick test
    sol = Solution()
    result = sol.solve("./resources")
    print("Fuzzer code generated successfully")
    print(f"Code length: {len(result['code'])} characters")

