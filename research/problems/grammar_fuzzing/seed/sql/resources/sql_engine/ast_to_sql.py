"""
AST to SQL Converter

This module converts AST nodes back to SQL strings.
"""

from typing import List, Union
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


class ASTToSQLConverter:
    """Converts AST nodes back to SQL strings."""
    
    def convert(self, node: Union[SQLStatement, Expression]) -> str:
        """Convert an AST node to SQL string."""
        if isinstance(node, CreateTableStatement):
            return self._convert_create_table(node)
        elif isinstance(node, InsertStatement):
            return self._convert_insert(node)
        elif isinstance(node, SelectStatement):
            return self._convert_select(node)
        elif isinstance(node, UpdateStatement):
            return self._convert_update(node)
        elif isinstance(node, DeleteStatement):
            return self._convert_delete(node)
        elif isinstance(node, Expression):
            return self._convert_expression(node)
        else:
            raise ValueError(f"Unsupported node type: {type(node)}")
    
    def _convert_create_table(self, stmt: CreateTableStatement) -> str:
        """Convert CREATE TABLE statement to SQL."""
        sql = "CREATE TABLE"
        
        if stmt.if_not_exists:
            sql += " IF NOT EXISTS"
        
        sql += f" {stmt.table_name} ("
        
        column_defs = []
        for column in stmt.columns:
            column_def = self._convert_column_definition(column)
            column_defs.append(column_def)
        
        sql += ", ".join(column_defs)
        sql += ")"
        
        return sql
    
    def _convert_column_definition(self, column: ColumnDefinition) -> str:
        """Convert column definition to SQL."""
        sql = f"{column.name} {column.data_type.value}"
        
        for constraint in column.constraints:
            sql += " " + self._convert_column_constraint(constraint)
        
        return sql
    
    def _convert_column_constraint(self, constraint: ColumnConstraint) -> str:
        """Convert column constraint to SQL."""
        if isinstance(constraint, PrimaryKeyConstraint):
            return "PRIMARY KEY"
        elif isinstance(constraint, UniqueConstraint):
            return "UNIQUE"
        elif isinstance(constraint, NotNullConstraint):
            return "NOT NULL"
        elif isinstance(constraint, DefaultConstraint):
            return f"DEFAULT {self._convert_expression(constraint.value)}"
        elif isinstance(constraint, CheckConstraint):
            return f"CHECK ({self._convert_expression(constraint.condition)})"
        elif isinstance(constraint, AutoIncrementConstraint):
            return "AUTOINCREMENT"
        else:
            raise ValueError(f"Unsupported constraint type: {type(constraint)}")
    
    def _convert_insert(self, stmt: InsertStatement) -> str:
        """Convert INSERT statement to SQL."""
        sql = f"INSERT INTO {stmt.table_name}"
        
        if stmt.columns:
            columns = ", ".join(stmt.columns)
            sql += f" ({columns})"
        
        # Handle multiple value rows
        value_rows_sql = []
        for value_row in stmt.value_rows:
            values = []
            for value in value_row:
                values.append(self._convert_expression(value))
            value_rows_sql.append(f"({', '.join(values)})")
        
        sql += f" VALUES {', '.join(value_rows_sql)}"
        
        return sql
    
    def _convert_select(self, stmt: SelectStatement) -> str:
        """Convert SELECT statement to SQL."""
        sql = "SELECT"
        
        if stmt.distinct:
            sql += " DISTINCT"
        
        if stmt.all:
            sql += " ALL"
        
        # Select list
        select_items = []
        for item in stmt.select_list:
            select_items.append(self._convert_expression(item))
        
        sql += " " + ", ".join(select_items)
        
        # FROM clause
        if stmt.from_clause:
            sql += " " + self._convert_from_clause(stmt.from_clause)
        
        # WHERE clause
        if stmt.where_clause:
            sql += f" WHERE {self._convert_expression(stmt.where_clause)}"
        
        # GROUP BY clause
        if stmt.group_by:
            group_items = []
            for item in stmt.group_by:
                group_items.append(self._convert_expression(item))
            sql += f" GROUP BY {', '.join(group_items)}"
        
        # HAVING clause
        if stmt.having_clause:
            sql += f" HAVING {self._convert_expression(stmt.having_clause)}"
        
        # ORDER BY clause
        if stmt.order_by:
            order_items = []
            for item in stmt.order_by:
                order_items.append(self._convert_expression(item))
            sql += f" ORDER BY {', '.join(order_items)}"
        
        # LIMIT clause
        if stmt.limit_clause:
            sql += f" LIMIT {self._convert_expression(stmt.limit_clause)}"
        
        # OFFSET clause
        if stmt.offset_clause:
            sql += f" OFFSET {self._convert_expression(stmt.offset_clause)}"
        
        return sql
    
    def _convert_from_clause(self, from_clause: FromClause) -> str:
        """Convert FROM clause to SQL."""
        sql = "FROM " + self._convert_table_source(from_clause.table)
        
        for join in from_clause.joins:
            sql += " " + self._convert_join(join)
        
        return sql
    
    def _convert_table_source(self, source: Union[TableReference, SubqueryExpression]) -> str:
        """Convert table source to SQL."""
        if isinstance(source, TableReference):
            sql = source.table_name
            if source.alias:
                sql += f" AS {source.alias}"
            return sql
        elif isinstance(source, SubqueryExpression):
            sql = f"({self._convert_select(source.subquery)})"
            if hasattr(source, 'alias') and source.alias:
                sql += f" AS {source.alias}"
            return sql
        else:
            raise ValueError(f"Unsupported table source type: {type(source)}")
    
    def _convert_join(self, join: JoinExpression) -> str:
        """Convert JOIN expression to SQL."""
        sql = f"{join.join_type} JOIN {self._convert_table_source(join.table)}"
        sql += f" ON {self._convert_expression(join.condition)}"
        return sql
    
    def _convert_update(self, stmt: UpdateStatement) -> str:
        """Convert UPDATE statement to SQL."""
        sql = f"UPDATE {stmt.table_name} SET "
        
        assignments = []
        for assignment in stmt.assignments:
            assignments.append(self._convert_expression(assignment))
        
        sql += ", ".join(assignments)
        
        if stmt.where_clause:
            sql += f" WHERE {self._convert_expression(stmt.where_clause)}"
        
        return sql
    
    def _convert_delete(self, stmt: DeleteStatement) -> str:
        """Convert DELETE statement to SQL."""
        sql = f"DELETE FROM {stmt.table_name}"
        
        if stmt.where_clause:
            sql += f" WHERE {self._convert_expression(stmt.where_clause)}"
        
        return sql
    
    def _convert_expression(self, expr: Expression) -> str:
        """Convert expression to SQL."""
        if isinstance(expr, LiteralExpression):
            if expr.value is None:
                return "NULL"
            elif isinstance(expr.value, str):
                # Check if it's a boolean literal
                if expr.value.upper() in ['TRUE', 'FALSE']:
                    return expr.value.upper()
                else:
                    return f"'{expr.value}'"
            else:
                return str(expr.value)
        
        elif isinstance(expr, IdentifierExpression):
            return expr.name
        
        elif isinstance(expr, ColumnReference):
            return f"{expr.table_name}.{expr.column_name}"
        
        elif isinstance(expr, BinaryExpression):
            left = self._convert_expression(expr.left)
            right = self._convert_expression(expr.right)
            return f"({left} {expr.operator} {right})"
        
        elif isinstance(expr, UnaryExpression):
            operand = self._convert_expression(expr.operand)
            if expr.operator in ["IS NULL", "IS NOT NULL"]:
                return f"{operand} {expr.operator}"
            else:
                return f"{expr.operator} {operand}"
        
        elif isinstance(expr, FunctionCallExpression):
            args = []
            for arg in expr.arguments:
                args.append(self._convert_expression(arg))
            return f"{expr.function_name}({', '.join(args)})"
        
        elif isinstance(expr, WildcardExpression):
            return "*"
        
        elif isinstance(expr, AliasExpression):
            base = self._convert_expression(expr.expression)
            return f"{base} AS {expr.alias}"
        
        elif isinstance(expr, OrderByExpression):
            base = self._convert_expression(expr.expression)
            return f"{base} {expr.direction}"
        
        elif isinstance(expr, InExpression):
            base = self._convert_expression(expr.expression)
            values = []
            for value in expr.values:
                values.append(self._convert_expression(value))
            return f"{base} IN ({', '.join(values)})"
        
        elif isinstance(expr, BetweenExpression):
            base = self._convert_expression(expr.expression)
            low = self._convert_expression(expr.low)
            high = self._convert_expression(expr.high)
            return f"{base} BETWEEN {low} AND {high}"
        
        elif isinstance(expr, ExistsExpression):
            subquery_sql = self._convert_select(expr.subquery)
            return f"EXISTS ({subquery_sql})"
        
        elif isinstance(expr, AssignmentExpression):
            value = self._convert_expression(expr.value)
            return f"{expr.column_name} = {value}"
        
        elif isinstance(expr, SubqueryExpression):
            sql = f"{self._convert_select(expr.subquery)}"
            if hasattr(expr, 'alias') and expr.alias:
                sql += f" AS {expr.alias}"
            return sql
        
        else:
            raise ValueError(f"Unsupported expression type: {type(expr)}")


def ast_to_sql(node: Union[SQLStatement, Expression]) -> str:
    """Convert an AST node to SQL string (convenience function)."""
    converter = ASTToSQLConverter()
    return converter.convert(node)
