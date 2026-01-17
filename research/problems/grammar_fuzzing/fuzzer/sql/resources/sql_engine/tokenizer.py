"""
SQL Tokenizer

This module handles the lexical analysis of SQL strings, converting them into
a stream of tokens for the parser to consume.
"""

from typing import List
from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    # Keywords
    CREATE = "CREATE"
    TABLE = "TABLE"
    IF = "IF"
    NOT = "NOT"
    EXISTS = "EXISTS"
    INSERT = "INSERT"
    INTO = "INTO"
    VALUES = "VALUES"
    SELECT = "SELECT"
    DISTINCT = "DISTINCT"
    ALL = "ALL"
    FROM = "FROM"
    WHERE = "WHERE"
    ORDER = "ORDER"
    BY = "BY"
    UPDATE = "UPDATE"
    SET = "SET"
    DELETE = "DELETE"
    AND = "AND"
    OR = "OR"
    ASC = "ASC"
    DESC = "DESC"
    GROUP = "GROUP"
    HAVING = "HAVING"
    LIMIT = "LIMIT"
    OFFSET = "OFFSET"
    JOIN = "JOIN"
    INNER = "INNER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    FULL = "FULL"
    OUTER = "OUTER"
    ON = "ON"
    AS = "AS"
    IN = "IN"
    BETWEEN = "BETWEEN"
    LIKE = "LIKE"
    IS = "IS"
    NULL = "NULL"
    TRUE = "TRUE"
    FALSE = "FALSE"
    PRIMARY = "PRIMARY"
    KEY = "KEY"
    UNIQUE = "UNIQUE"
    DEFAULT = "DEFAULT"
    CHECK = "CHECK"
    AUTOINCREMENT = "AUTOINCREMENT"
    
    # Data types
    INT = "INT"
    INTEGER = "INTEGER"
    TEXT = "TEXT"
    VARCHAR = "VARCHAR"
    REAL = "REAL"
    BLOB = "BLOB"
    BOOLEAN = "BOOLEAN"
    
    # Operators
    EQUALS = "="
    NOT_EQUALS1 = "<>"
    NOT_EQUALS2 = "!="
    LESS_THAN = "<"
    LESS_THAN_EQUALS = "<="
    GREATER_THAN = ">"
    GREATER_THAN_EQUALS = ">="
    
    # Functions
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    UPPER = "UPPER"
    LOWER = "LOWER"
    LENGTH = "LENGTH"
    SUBSTR = "SUBSTR"
    
    # Symbols
    ASTERISK = "*"
    PLUS = "+"
    MINUS = "-"
    DIVIDE = "/"
    MODULO = "%"
    COMMA = ","
    LPAREN = "("
    RPAREN = ")"
    DOT = "."
    SEMICOLON = ";"
    
    # Literals
    IDENTIFIER = "IDENTIFIER"
    STRING_LITERAL = "STRING_LITERAL"
    NUMBER_LITERAL = "NUMBER_LITERAL"
    
    # Special
    EOF = "EOF"


@dataclass
class Token:
    """Represents a single token in the SQL input"""
    type: TokenType
    value: str
    position: int


class Tokenizer:
    """Tokenizes SQL input into tokens."""
    
    def __init__(self, text: str):
        self.text = text
        self.position = 0
        self.tokens = []
        self._tokenize()
    
    def _tokenize(self):
        """Tokenize the input text."""
        keywords = self._build_keyword_map()
        
        i = 0
        while i < len(self.text):
            # Skip whitespace
            if self.text[i].isspace():
                i += 1
                continue
            
            # Multi-character operators
            if i < len(self.text) - 1:
                two_char = self.text[i:i+2]
                if two_char in ['<>', '!=', '<=', '>=']:
                    token_type = self._get_operator_token_type(two_char)
                    self.tokens.append(Token(token_type, two_char, i))
                    i += 2
                    continue
            
            # Single character tokens
            single_char_token = self._try_parse_single_char(self.text[i], i)
            if single_char_token:
                self.tokens.append(single_char_token)
                i += 1
                continue
            
            # String literals (quoted)
            if self.text[i] in ["'", '"']:
                token, new_i = self._parse_string_literal(i)
                self.tokens.append(token)
                i = new_i
                continue
            
            # Numbers (including decimals)
            if self.text[i].isdigit():
                token, new_i = self._parse_number_literal(i)
                self.tokens.append(token)
                i = new_i
                continue
            
            # Identifiers and keywords
            if self.text[i].isalpha() or self.text[i] == '_':
                token, new_i = self._parse_identifier_or_keyword(i, keywords)
                self.tokens.append(token)
                i = new_i
                continue
            
            # Unknown character
            raise SyntaxError(f"Unexpected character '{self.text[i]}' at position {i}")
        
        self.tokens.append(Token(TokenType.EOF, '', len(self.text)))
    
    def _build_keyword_map(self) -> dict:
        """Build mapping from keyword strings to token types"""
        return {
            'CREATE': TokenType.CREATE,
            'TABLE': TokenType.TABLE,
            'IF': TokenType.IF,
            'NOT': TokenType.NOT,
            'EXISTS': TokenType.EXISTS,
            'INSERT': TokenType.INSERT,
            'INTO': TokenType.INTO,
            'VALUES': TokenType.VALUES,
            'SELECT': TokenType.SELECT,
            'DISTINCT': TokenType.DISTINCT,
            'ALL': TokenType.ALL,
            'FROM': TokenType.FROM,
            'WHERE': TokenType.WHERE,
            'ORDER': TokenType.ORDER,
            'BY': TokenType.BY,
            'UPDATE': TokenType.UPDATE,
            'SET': TokenType.SET,
            'DELETE': TokenType.DELETE,
            'AND': TokenType.AND,
            'OR': TokenType.OR,
            'ASC': TokenType.ASC,
            'DESC': TokenType.DESC,
            'GROUP': TokenType.GROUP,
            'HAVING': TokenType.HAVING,
            'LIMIT': TokenType.LIMIT,
            'OFFSET': TokenType.OFFSET,
            'JOIN': TokenType.JOIN,
            'INNER': TokenType.INNER,
            'LEFT': TokenType.LEFT,
            'RIGHT': TokenType.RIGHT,
            'FULL': TokenType.FULL,
            'OUTER': TokenType.OUTER,
            'ON': TokenType.ON,
            'AS': TokenType.AS,
            'IN': TokenType.IN,
            'BETWEEN': TokenType.BETWEEN,
            'LIKE': TokenType.LIKE,
            'IS': TokenType.IS,
            'NULL': TokenType.NULL,
            'TRUE': TokenType.TRUE,
            'FALSE': TokenType.FALSE,
            'PRIMARY': TokenType.PRIMARY,
            'KEY': TokenType.KEY,
            'UNIQUE': TokenType.UNIQUE,
            'DEFAULT': TokenType.DEFAULT,
            'CHECK': TokenType.CHECK,
            'AUTOINCREMENT': TokenType.AUTOINCREMENT,
            'INT': TokenType.INT,
            'INTEGER': TokenType.INTEGER,
            'TEXT': TokenType.TEXT,
            'VARCHAR': TokenType.VARCHAR,
            'REAL': TokenType.REAL,
            'BLOB': TokenType.BLOB,
            'BOOLEAN': TokenType.BOOLEAN,
            'COUNT': TokenType.COUNT,
            'SUM': TokenType.SUM,
            'AVG': TokenType.AVG,
            'MIN': TokenType.MIN,
            'MAX': TokenType.MAX,
            'UPPER': TokenType.UPPER,
            'LOWER': TokenType.LOWER,
            'LENGTH': TokenType.LENGTH,
            'SUBSTR': TokenType.SUBSTR,
        }
    
    def _get_operator_token_type(self, operator: str) -> TokenType:
        """Get token type for operator"""
        mapping = {
            '<>': TokenType.NOT_EQUALS1,
            '!=': TokenType.NOT_EQUALS2,
            '<=': TokenType.LESS_THAN_EQUALS,
            '>=': TokenType.GREATER_THAN_EQUALS,
        }
        return mapping[operator]
    
    def _try_parse_single_char(self, char: str, position: int) -> Token:
        """Try to parse a single character token"""
        mapping = {
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            ',': TokenType.COMMA,
            '*': TokenType.ASTERISK,
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '/': TokenType.DIVIDE,
            '%': TokenType.MODULO,
            '.': TokenType.DOT,
            ';': TokenType.SEMICOLON,
            '=': TokenType.EQUALS,
            '<': TokenType.LESS_THAN,
            '>': TokenType.GREATER_THAN,
        }
        
        if char in mapping:
            return Token(mapping[char], char, position)
        return None
    
    def _parse_string_literal(self, start_pos: int) -> tuple[Token, int]:
        """Parse a string literal"""
        quote = self.text[start_pos]
        i = start_pos + 1
        
        while i < len(self.text) and self.text[i] != quote:
            i += 1
        
        if i >= len(self.text):
            raise SyntaxError(f"Unterminated string literal at position {start_pos}")
        
        value = self.text[start_pos + 1:i]  # Extract content without quotes
        return Token(TokenType.STRING_LITERAL, value, start_pos), i + 1
    
    def _parse_number_literal(self, start_pos: int) -> tuple[Token, int]:
        """Parse a number literal (integer or decimal)"""
        i = start_pos
        
        while i < len(self.text) and (self.text[i].isdigit() or self.text[i] == '.'):
            i += 1
        
        value = self.text[start_pos:i]
        return Token(TokenType.NUMBER_LITERAL, value, start_pos), i
    
    def _parse_identifier_or_keyword(self, start_pos: int, keywords: dict) -> tuple[Token, int]:
        """Parse an identifier or keyword"""
        i = start_pos
        
        while i < len(self.text) and (self.text[i].isalnum() or self.text[i] == '_'):
            i += 1
        
        value = self.text[start_pos:i]
        token_type = keywords.get(value.upper(), TokenType.IDENTIFIER)
        return Token(token_type, value, start_pos), i


class TokenizerError(Exception):
    """Exception raised when tokenization fails."""
    pass
