"""
SQL Parser

This module contains the core parsing logic that converts tokens into an AST.
"""

from typing import List, Optional, Union
from .tokenizer import Token, TokenType, Tokenizer
from .ast_nodes import (
    SQLStatement, Expression, CreateTableStatement, InsertStatement, 
    SelectStatement, UpdateStatement, DeleteStatement, ColumnDefinition,
    DataType, ColumnConstraint, PrimaryKeyConstraint, UniqueConstraint,
    NotNullConstraint, DefaultConstraint, CheckConstraint, AutoIncrementConstraint,
    FromClause, TableReference, SubqueryExpression, JoinExpression,
    WildcardExpression, AliasExpression, OrderByExpression, BinaryExpression,
    UnaryExpression, LiteralExpression, IdentifierExpression, ColumnReference,
    FunctionCallExpression, InExpression, BetweenExpression, ExistsExpression,
    AssignmentExpression
)


class Parser:
    """Recursive descent parser for SQL statements."""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
    
    def parse(self) -> List[SQLStatement]:
        """Parse tokens into a list of SQL statements."""
        statements = []
        
        while not self._is_at_end():
            # Skip any leading semicolons (empty statements)
            while self._check(TokenType.SEMICOLON):
                self._advance()
                if self._is_at_end():
                    break
            
            if self._is_at_end():
                break
                
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)
                
            # Handle semicolon requirements based on mode
            if not self._is_at_end() and not self._check(TokenType.SEMICOLON):
                # Check if there's another statement coming
                if self._peek().type in [TokenType.SELECT, TokenType.INSERT, 
                                       TokenType.UPDATE, TokenType.DELETE, 
                                       TokenType.CREATE]:
                    raise SyntaxError(f"Missing semicolon before {self._peek().type} statement at position {self._peek().position}")
            
            # Optionally consume a trailing semicolon
            if self._check(TokenType.SEMICOLON):
                self._advance()
        
        return statements
    
    def _parse_statement(self) -> Optional[SQLStatement]:
        """Parse a single SQL statement."""
        if self._is_at_end():
            return None
        
        token = self._peek()
        
        if token.type == TokenType.CREATE:
            return self._parse_create_statement()
        elif token.type == TokenType.INSERT:
            return self._parse_insert_statement()
        elif token.type == TokenType.SELECT:
            return self._parse_select_statement()
        elif token.type == TokenType.UPDATE:
            return self._parse_update_statement()
        elif token.type == TokenType.DELETE:
            return self._parse_delete_statement()
        else:
            raise SyntaxError(f"Unexpected token: {token.type} at position {token.position}")
    
    def _parse_create_statement(self) -> CreateTableStatement:
        """Parse CREATE TABLE statement."""
        self._consume(TokenType.CREATE)
        self._consume(TokenType.TABLE)
        
        if_not_exists = False
        if self._check(TokenType.IF):
            self._advance()
            self._consume(TokenType.NOT)
            self._consume(TokenType.EXISTS)
            if_not_exists = True
        
        table_name = self._consume(TokenType.IDENTIFIER).value
        
        self._consume(TokenType.LPAREN)
        columns = []
        
        # Parse column definitions
        while not self._check(TokenType.RPAREN) and not self._is_at_end():
            column = self._parse_column_definition()
            columns.append(column)
            
            if self._check(TokenType.COMMA):
                self._advance()
            elif self._check(TokenType.RPAREN):
                break
            else:
                raise SyntaxError(f"Expected ',' or ')' at position {self._peek().position}")
        
        self._consume(TokenType.RPAREN)
        
        return CreateTableStatement(table_name, columns, if_not_exists)
    
    def _parse_column_definition(self) -> ColumnDefinition:
        """Parse a column definition."""
        column_name = self._consume(TokenType.IDENTIFIER).value
        data_type = self._parse_data_type()
        
        constraints = []
        while self._check_constraint_keyword():
            constraint = self._parse_column_constraint()
            constraints.append(constraint)
        
        return ColumnDefinition(column_name, data_type, constraints)
    
    def _parse_data_type(self) -> DataType:
        """Parse a data type specification."""
        token = self._advance()
        
        type_mapping = {
            TokenType.INT: DataType.INT,
            TokenType.INTEGER: DataType.INTEGER,
            TokenType.TEXT: DataType.TEXT,
            TokenType.VARCHAR: DataType.VARCHAR,
            TokenType.REAL: DataType.REAL,
            TokenType.BLOB: DataType.BLOB,
            TokenType.BOOLEAN: DataType.BOOLEAN,
        }
        
        if token.type in type_mapping:
            data_type = type_mapping[token.type]
            
            # Handle VARCHAR(n) syntax
            if token.type == TokenType.VARCHAR and self._check(TokenType.LPAREN):
                self._advance()  # consume '('
                size_token = self._consume(TokenType.NUMBER_LITERAL)
                self._consume(TokenType.RPAREN)
                return DataType.VARCHAR  # For simplicity, ignore size for now
            
            return data_type
        else:
            raise SyntaxError(f"Expected data type, got {token.type} at position {token.position}")
    
    def _check_constraint_keyword(self) -> bool:
        """Check if current token is a constraint keyword."""
        constraint_keywords = [
            TokenType.PRIMARY, TokenType.UNIQUE, TokenType.NOT,
            TokenType.DEFAULT, TokenType.CHECK, TokenType.AUTOINCREMENT
        ]
        return self._check_any(constraint_keywords)
    
    def _parse_column_constraint(self) -> ColumnConstraint:
        """Parse a column constraint."""
        if self._check(TokenType.PRIMARY):
            self._advance()
            self._consume(TokenType.KEY)
            return PrimaryKeyConstraint()
        
        if self._check(TokenType.UNIQUE):
            self._advance()
            return UniqueConstraint()
        
        if self._check(TokenType.NOT):
            self._advance()
            self._consume(TokenType.NULL)
            return NotNullConstraint()
        
        if self._check(TokenType.DEFAULT):
            self._advance()
            value = self._parse_expression()
            return DefaultConstraint(value)
        
        if self._check(TokenType.CHECK):
            self._advance()
            self._consume(TokenType.LPAREN)
            condition = self._parse_expression()
            self._consume(TokenType.RPAREN)
            return CheckConstraint(condition)
        
        if self._check(TokenType.AUTOINCREMENT):
            self._advance()
            return AutoIncrementConstraint()
        
        raise SyntaxError(f"Unknown constraint at position {self._peek().position}")
    
    def _parse_insert_statement(self) -> InsertStatement:
        """Parse INSERT statement."""
        self._consume(TokenType.INSERT)
        self._consume(TokenType.INTO)
        table_name = self._consume(TokenType.IDENTIFIER).value
        
        # Optional column list
        columns = []
        if self._check(TokenType.LPAREN):
            self._advance()
            while not self._check(TokenType.RPAREN) and not self._is_at_end():
                columns.append(self._consume(TokenType.IDENTIFIER).value)
                if self._check(TokenType.COMMA):
                    self._advance()
                elif self._check(TokenType.RPAREN):
                    break
                else:
                    raise SyntaxError(f"Expected ',' or ')' at position {self._peek().position}")
            self._consume(TokenType.RPAREN)
        
        self._consume(TokenType.VALUES)
        
        # Parse multiple value rows: VALUES (...), (...), (...)
        value_rows = []
        
        while True:
            # Parse a single value row: (value1, value2, ...)
            self._consume(TokenType.LPAREN)
            
            values = []
            while not self._check(TokenType.RPAREN) and not self._is_at_end():
                values.append(self._parse_expression())
                if self._check(TokenType.COMMA):
                    self._advance()
                elif self._check(TokenType.RPAREN):
                    break
                else:
                    raise SyntaxError(f"Expected ',' or ')' at position {self._peek().position}")
            
            self._consume(TokenType.RPAREN)
            value_rows.append(values)
            
            # Check if there's another value row
            if self._check(TokenType.COMMA):
                self._advance()
                # Continue to parse the next value row
            else:
                # No more value rows
                break
        
        return InsertStatement(table_name, columns, value_rows)
    
    def _parse_select_statement(self) -> SelectStatement:
        """Parse SELECT statement."""
        self._consume(TokenType.SELECT)
        
        # DISTINCT or ALL
        distinct = False
        all = False
        if self._check(TokenType.DISTINCT):
            self._advance()
            distinct = True
        elif self._check(TokenType.ALL):
            self._advance()
            all = True
        
        # Select list
        select_list = []
        while True:
            if self._check(TokenType.ASTERISK):
                self._advance()
                select_list.append(WildcardExpression())
            else:
                expr = self._parse_expression()
                
                # Handle AS alias
                alias = None
                if self._check(TokenType.AS):
                    self._advance()
                    alias = self._consume(TokenType.IDENTIFIER).value
                elif self._check(TokenType.IDENTIFIER):
                    # Implicit alias (no AS keyword)
                    alias = self._advance().value
                
                if alias:
                    select_list.append(AliasExpression(expr, alias))
                else:
                    select_list.append(expr)
            
            if self._check(TokenType.COMMA):
                self._advance()
            else:
                break
        
        # FROM clause
        from_clause = None
        if self._check(TokenType.FROM):
            self._advance()
            from_clause = self._parse_from_clause()
        
        # WHERE clause
        where_clause = None
        if self._check(TokenType.WHERE):
            # WHERE clause requires a FROM clause
            if from_clause is None:
                raise SyntaxError(f"WHERE clause requires FROM clause at position {self._peek().position}")
            self._advance()
            where_clause = self._parse_expression()
        
        # GROUP BY clause
        group_by = []
        if self._check(TokenType.GROUP):
            self._advance()
            self._consume(TokenType.BY)
            while True:
                group_by.append(self._parse_expression())
                if self._check(TokenType.COMMA):
                    self._advance()
                else:
                    break
        
        # HAVING clause
        having_clause = None
        if self._check(TokenType.HAVING):
            self._advance()
            having_clause = self._parse_expression()
        
        # ORDER BY clause
        order_by = []
        if self._check(TokenType.ORDER):
            self._advance()
            self._consume(TokenType.BY)
            while True:
                expr = self._parse_expression()
                direction = "ASC"
                if self._check(TokenType.ASC):
                    self._advance()
                    direction = "ASC"
                elif self._check(TokenType.DESC):
                    self._advance()
                    direction = "DESC"
                order_by.append(OrderByExpression(expr, direction))
                
                if self._check(TokenType.COMMA):
                    self._advance()
                else:
                    break
        
        # LIMIT clause
        limit_clause = None
        if self._check(TokenType.LIMIT):
            self._advance()
            limit_clause = self._parse_expression()
        
        # OFFSET clause
        offset_clause = None
        if self._check(TokenType.OFFSET):
            self._advance()
            offset_clause = self._parse_expression()
        
        return SelectStatement(
            select_list, from_clause, where_clause, group_by,
            having_clause, order_by, limit_clause, offset_clause, distinct, all
        )
    
    def _parse_from_clause(self) -> FromClause:
        """Parse FROM clause with optional JOINs."""
        # Parse the main table/subquery
        main_source = self._parse_table_source()
        joins = []
        
        # Parse JOINs
        while self._check_join_keyword():
            join = self._parse_join()
            joins.append(join)
        
        return FromClause(main_source, joins)
    
    def _parse_table_source(self) -> Union[TableReference, SubqueryExpression]:
        """Parse a table source (table name or subquery)."""
        if self._check(TokenType.LPAREN):
            # Subquery
            self._advance()
            select_stmt = self._parse_select_statement()
            self._consume(TokenType.RPAREN)
            
            # Optional alias
            alias = None
            if self._check(TokenType.AS):
                self._advance()
                alias = self._consume(TokenType.IDENTIFIER).value
            elif self._check(TokenType.IDENTIFIER):
                alias = self._advance().value
            
            return SubqueryExpression(select_stmt, alias)
        else:
            # Table name
            table_name = self._consume(TokenType.IDENTIFIER).value
            
            # Optional alias
            alias = None
            if self._check(TokenType.AS):
                self._advance()
                alias = self._consume(TokenType.IDENTIFIER).value
            elif self._check(TokenType.IDENTIFIER):
                alias = self._advance().value
            
            return TableReference(table_name, alias)
    
    def _check_join_keyword(self) -> bool:
        """Check if current token starts a JOIN clause."""
        join_keywords = [TokenType.JOIN, TokenType.INNER, TokenType.LEFT, TokenType.RIGHT, TokenType.FULL]
        return self._check_any(join_keywords)
    
    def _parse_join(self) -> JoinExpression:
        """Parse a JOIN expression."""
        join_type = "INNER"  # default
        
        if self._check(TokenType.INNER):
            self._advance()
            join_type = "INNER"
        elif self._check(TokenType.LEFT):
            self._advance()
            join_type = "LEFT"
            if self._check(TokenType.OUTER):
                self._advance()
                join_type = "LEFT OUTER"
        elif self._check(TokenType.RIGHT):
            self._advance()
            join_type = "RIGHT"
            if self._check(TokenType.OUTER):
                self._advance()
                join_type = "RIGHT OUTER"
        elif self._check(TokenType.FULL):
            self._advance()
            join_type = "FULL"
            if self._check(TokenType.OUTER):
                self._advance()
                join_type = "FULL OUTER"
        
        self._consume(TokenType.JOIN)
        
        # Parse the table to join
        table = self._parse_table_source()
        
        # Parse ON condition
        self._consume(TokenType.ON)
        condition = self._parse_expression()
        
        return JoinExpression(join_type, table, condition)
    
    def _parse_update_statement(self) -> UpdateStatement:
        """Parse UPDATE statement."""
        self._consume(TokenType.UPDATE)
        table_name = self._consume(TokenType.IDENTIFIER).value
        self._consume(TokenType.SET)
        
        assignments = []
        while True:
            column = self._consume(TokenType.IDENTIFIER).value
            self._consume(TokenType.EQUALS)
            value = self._parse_expression()
            assignments.append(AssignmentExpression(column, value))
            
            if self._check(TokenType.COMMA):
                self._advance()
            else:
                break
        
        where_clause = None
        if self._check(TokenType.WHERE):
            self._advance()
            where_clause = self._parse_expression()
        
        return UpdateStatement(table_name, assignments, where_clause)
    
    def _parse_delete_statement(self) -> DeleteStatement:
        """Parse DELETE statement."""
        self._consume(TokenType.DELETE)
        self._consume(TokenType.FROM)
        table_name = self._consume(TokenType.IDENTIFIER).value
        
        where_clause = None
        if self._check(TokenType.WHERE):
            self._advance()
            where_clause = self._parse_expression()
        
        return DeleteStatement(table_name, where_clause)
    
    def _parse_expression(self) -> Expression:
        """Parse an expression with operator precedence."""
        return self._parse_or_expression()
    
    def _parse_or_expression(self) -> Expression:
        """Parse OR expressions (lowest precedence)."""
        expr = self._parse_and_expression()
        
        while self._check(TokenType.OR):
            operator = self._advance().value
            right = self._parse_and_expression()
            expr = BinaryExpression(expr, operator, right)
        
        return expr
    
    def _parse_and_expression(self) -> Expression:
        """Parse AND expressions."""
        expr = self._parse_equality_expression()
        
        while self._check(TokenType.AND):
            operator = self._advance().value
            right = self._parse_equality_expression()
            expr = BinaryExpression(expr, operator, right)
        
        return expr
    
    def _parse_equality_expression(self) -> Expression:
        """Parse equality expressions (=, <>, !=)."""
        expr = self._parse_relational_expression()
        
        while self._check_any([TokenType.EQUALS, TokenType.NOT_EQUALS1, TokenType.NOT_EQUALS2]):
            operator = self._advance().value
            right = self._parse_relational_expression()
            expr = BinaryExpression(expr, operator, right)
        
        return expr
    
    def _parse_relational_expression(self) -> Expression:
        """Parse relational expressions (<, >, <=, >=, LIKE, IN, BETWEEN, IS)."""
        expr = self._parse_additive_expression()
        
        while True:
            if self._check_any([TokenType.LESS_THAN, TokenType.GREATER_THAN, 
                               TokenType.LESS_THAN_EQUALS, TokenType.GREATER_THAN_EQUALS]):
                operator = self._advance().value
                right = self._parse_additive_expression()
                expr = BinaryExpression(expr, operator, right)
            elif self._check(TokenType.LIKE):
                operator = self._advance().value
                right = self._parse_additive_expression()
                expr = BinaryExpression(expr, operator, right)
            elif self._check(TokenType.IN):
                self._advance()
                self._consume(TokenType.LPAREN)
                
                # Check if this is a subquery (starts with SELECT)
                if self._check(TokenType.SELECT):
                    subquery = self._parse_select_statement()
                    self._consume(TokenType.RPAREN)
                    expr = InExpression(expr, [SubqueryExpression(subquery)])
                else:
                    # Parse list of values
                    values = []
                    while not self._check(TokenType.RPAREN) and not self._is_at_end():
                        values.append(self._parse_expression())
                        if self._check(TokenType.COMMA):
                            self._advance()
                        elif self._check(TokenType.RPAREN):
                            break
                        else:
                            raise SyntaxError(f"Expected ',' or ')' at position {self._peek().position}")
                    self._consume(TokenType.RPAREN)
                    expr = InExpression(expr, values)
            elif self._check_sequence([TokenType.NOT, TokenType.IN]):
                self._advance()  # consume NOT
                self._advance()  # consume IN
                self._consume(TokenType.LPAREN)
                
                # Check if this is a subquery (starts with SELECT)
                if self._check(TokenType.SELECT):
                    subquery = self._parse_select_statement()
                    self._consume(TokenType.RPAREN)
                    expr = UnaryExpression("NOT", InExpression(expr, [SubqueryExpression(subquery)]))
                else:
                    # Parse list of values
                    values = []
                    while not self._check(TokenType.RPAREN) and not self._is_at_end():
                        values.append(self._parse_expression())
                        if self._check(TokenType.COMMA):
                            self._advance()
                        elif self._check(TokenType.RPAREN):
                            break
                        else:
                            raise SyntaxError(f"Expected ',' or ')' at position {self._peek().position}")
                    self._consume(TokenType.RPAREN)
                    expr = UnaryExpression("NOT", InExpression(expr, values))
            elif self._check(TokenType.BETWEEN):
                self._advance()
                low = self._parse_additive_expression()
                self._consume(TokenType.AND)
                high = self._parse_additive_expression()
                expr = BetweenExpression(expr, low, high)
            elif self._check(TokenType.IS):
                self._advance()
                if self._check(TokenType.NOT):
                    self._advance()
                    self._consume(TokenType.NULL)
                    expr = UnaryExpression("IS NOT NULL", expr)
                else:
                    self._consume(TokenType.NULL)
                    expr = UnaryExpression("IS NULL", expr)
            else:
                break
        
        return expr
    
    def _parse_additive_expression(self) -> Expression:
        """Parse additive expressions (+, -)."""
        expr = self._parse_multiplicative_expression()
        
        while self._check_any([TokenType.PLUS, TokenType.MINUS]):
            operator = self._advance().value
            right = self._parse_multiplicative_expression()
            expr = BinaryExpression(expr, operator, right)
        
        return expr
    
    def _parse_multiplicative_expression(self) -> Expression:
        """Parse multiplicative expressions (*, /, %)."""
        expr = self._parse_unary_expression()
        
        while self._check_any([TokenType.ASTERISK, TokenType.DIVIDE, TokenType.MODULO]):
            operator = self._advance().value
            right = self._parse_unary_expression()
            expr = BinaryExpression(expr, operator, right)
        
        return expr
    
    def _parse_unary_expression(self) -> Expression:
        """Parse unary expressions (NOT, -, +, EXISTS)."""
        if self._check(TokenType.NOT):
            operator = self._advance().value
            expr = self._parse_unary_expression()
            return UnaryExpression(operator, expr)
        
        if self._check(TokenType.EXISTS):
            self._advance()
            self._consume(TokenType.LPAREN)
            subquery = self._parse_select_statement()
            self._consume(TokenType.RPAREN)
            return ExistsExpression(subquery)
        
        if self._check_any([TokenType.PLUS, TokenType.MINUS]):
            operator = self._advance().value
            expr = self._parse_unary_expression()
            return UnaryExpression(operator, expr)
        
        return self._parse_primary_expression()
    
    def _parse_primary_expression(self) -> Expression:
        """Parse primary expressions (literals, identifiers, function calls, parentheses)."""
        if self._check(TokenType.NUMBER_LITERAL):
            token = self._advance().value
            try:
                return LiteralExpression(int(token))
            except ValueError:
                return LiteralExpression(float(token))

        if self._check(TokenType.STRING_LITERAL):
            return LiteralExpression(self._advance().value)
        
        if self._check_any([TokenType.TRUE, TokenType.FALSE]):
            return LiteralExpression(self._advance().value)
        
        if self._check(TokenType.NULL):
            self._advance()
            return LiteralExpression(None)
        
        if self._check(TokenType.LPAREN):
            self._advance()
            expr = self._parse_expression()
            self._consume(TokenType.RPAREN)
            return expr
        
        if self._check(TokenType.IDENTIFIER):
            name = self._advance().value
            
            # Check for function call
            if self._check(TokenType.LPAREN):
                self._advance()
                args = []
                while not self._check(TokenType.RPAREN) and not self._is_at_end():
                    args.append(self._parse_expression())
                    if self._check(TokenType.COMMA):
                        self._advance()
                    elif self._check(TokenType.RPAREN):
                        break
                    else:
                        raise SyntaxError(f"Expected ',' or ')' at position {self._peek().position}")
                self._consume(TokenType.RPAREN)
                return FunctionCallExpression(name, args)
            
            # Check for column reference (table.column)
            if self._check(TokenType.DOT):
                self._advance()
                column = self._consume(TokenType.IDENTIFIER).value
                return ColumnReference(column, name)
            
            # Simple identifier
            return IdentifierExpression(name)
        
        # Handle aggregate functions
        if self._check_any([TokenType.COUNT, TokenType.SUM, TokenType.AVG, TokenType.MIN, TokenType.MAX]):
            func_name = self._advance().value
            self._consume(TokenType.LPAREN)
            
            args = []
            if self._check(TokenType.ASTERISK) and func_name.upper() == "COUNT":
                self._advance()
                args.append(WildcardExpression())
            else:
                while not self._check(TokenType.RPAREN) and not self._is_at_end():
                    args.append(self._parse_expression())
                    if self._check(TokenType.COMMA):
                        self._advance()
                    elif self._check(TokenType.RPAREN):
                        break
                    else:
                        raise SyntaxError(f"Expected ',' or ')' at position {self._peek().position}")
            
            self._consume(TokenType.RPAREN)
            return FunctionCallExpression(func_name, args)
        
        # Handle string functions
        if self._check_any([TokenType.UPPER, TokenType.LOWER, TokenType.LENGTH, TokenType.SUBSTR]):
            func_name = self._advance().value
            self._consume(TokenType.LPAREN)
            
            args = []
            while not self._check(TokenType.RPAREN) and not self._is_at_end():
                args.append(self._parse_expression())
                if self._check(TokenType.COMMA):
                    self._advance()
                elif self._check(TokenType.RPAREN):
                    break
                else:
                    raise SyntaxError(f"Expected ',' or ')' at position {self._peek().position}")
            
            self._consume(TokenType.RPAREN)
            return FunctionCallExpression(func_name, args)
        
        raise SyntaxError(f"Unexpected token: {self._peek().type} at position {self._peek().position}")
    
    # Helper methods
    def _is_at_end(self) -> bool:
        """Check if we're at the end of tokens."""
        return self._peek().type == TokenType.EOF
    
    def _peek(self) -> Token:
        """Return current token without advancing."""
        return self.tokens[self.position]
    
    def _previous(self) -> Token:
        """Return previous token."""
        return self.tokens[self.position - 1]
    
    def _advance(self) -> Token:
        """Consume current token and return it."""
        if not self._is_at_end():
            self.position += 1
        return self._previous()
    
    def _check(self, token_type: TokenType) -> bool:
        """Check if current token is of given type."""
        if self._is_at_end():
            return False
        return self._peek().type == token_type
    
    def _check_any(self, token_types: List[TokenType]) -> bool:
        """Check if current token is any of the given types."""
        return any(self._check(token_type) for token_type in token_types)
    
    def _check_sequence(self, token_types: List[TokenType]) -> bool:
        """Check if the next tokens match the given sequence."""
        if self.position + len(token_types) > len(self.tokens):
            return False
        for i, token_type in enumerate(token_types):
            if self.tokens[self.position + i].type != token_type:
                return False
        return True
    
    def _match(self, *token_types: TokenType) -> bool:
        """Check if current token matches any of the types and advance if so."""
        for token_type in token_types:
            if self._check(token_type):
                self._advance()
                return True
        return False
    
    def _consume(self, token_type: TokenType) -> Token:
        """Consume token of expected type or raise error."""
        if self._check(token_type):
            return self._advance()
        
        current = self._peek()
        raise SyntaxError(f"Expected {token_type}, got {current.type} at position {current.position}")


class ParseError(Exception):
    """Exception raised when parsing fails."""
    pass
