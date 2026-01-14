"""
SQL Engine Package

A comprehensive SQL engine that can parse SQL statements into an Abstract Syntax Tree (AST),
convert AST back to SQL strings, and execute SQL queries.

Usage:
    from sql_engine import parse_sql, ast_to_sql
    
    # Parse SQL to AST
    statements = parse_sql("SELECT * FROM users WHERE age > 25")
    
    # Convert AST back to SQL
    sql_string = ast_to_sql(statements[0])
"""

from typing import List
from .tokenizer import Tokenizer, Token, TokenType, TokenizerError
from .parser import Parser, ParseError
from .ast_nodes import SQLStatement
from .ast_nodes import *
from .ast_to_sql import ASTToSQLConverter, ast_to_sql

__version__ = "1.0.0"
__all__ = [
    # Main functions
    "parse_sql",
    "ast_to_sql",
    "execute_sql",
    
    # Core classes
    "Tokenizer",
    "Parser", 
    "ASTToSQLConverter",
    "BaseProcessor",
    "SQLiteProcessor",
    "DuckDBProcessor",
    
    # AST Node types
    "SQLStatement",
    "Expression",
    "CreateTableStatement",
    "InsertStatement", 
    "SelectStatement",
    "UpdateStatement",
    "DeleteStatement",
    "ColumnDefinition",
    "DataType",
    "ColumnConstraint",
    "PrimaryKeyConstraint",
    "UniqueConstraint",
    "NotNullConstraint",
    "DefaultConstraint",
    "CheckConstraint",
    "AutoIncrementConstraint",
    "FromClause",
    "TableReference",
    "SubqueryExpression",
    "JoinExpression",
    "WildcardExpression",
    "AliasExpression",
    "OrderByExpression",
    "BinaryExpression",
    "UnaryExpression",
    "LiteralExpression",
    "IdentifierExpression",
    "ColumnReference",
    "FunctionCallExpression",
    "InExpression",
    "BetweenExpression",
    "AssignmentExpression",
    
    # Token types
    "Token",
    "TokenType",
    
    # Exceptions
    "ParseError",
    "TokenizerError",
]


def parse_sql(sql_string: str) -> List[SQLStatement]:
    """
    Parse a SQL string into a list of AST statements.
    
    Requires semicolons between multiple statements for proper SQL syntax.
    
    Args:
        ast_node: An AST node (usually a statement)
        
    Returns:
        SQL string representation
        
    Example:
        >>> statements = parse_sql("SELECT name FROM users")
        >>> sql = ast_to_sql(statements[0])
        >>> print(sql)
        "SELECT name FROM users"
        
    Type returned:
        <class 'sql_engine.ast_nodes.SelectStatement'>
    """
    try:
        # Tokenize the SQL string
        tokenizer = Tokenizer(sql_string)
        tokens = tokenizer.tokens
        
        # Parse tokens into AST
        parser = Parser(tokens)
        statements = parser.parse()
        
        return statements
        
    except Exception as e:
        if isinstance(e, (TokenizerError, ParseError)):
            raise
        else:
            # Wrap other exceptions as ParseError
            raise ParseError(f"Failed to parse SQL: {str(e)}") from e

