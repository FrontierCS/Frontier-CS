"""
AST Node Definitions

This module contains all the Abstract Syntax Tree node definitions
used by the SQL parser.
"""

from dataclasses import dataclass
from typing import List, Optional, Union
from enum import Enum


# ===== Base AST Node =====

@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    pass


# ===== Expression AST Nodes =====

@dataclass
class Expression(ASTNode):
    """Base class for all expressions"""
    pass

@dataclass
class LiteralExpression(Expression):
    """Literal value: string, number, boolean, null"""
    value: Union[str, int, float, bool, None]

@dataclass
class IdentifierExpression(Expression):
    """Simple identifier"""
    name: str

@dataclass
class ColumnReference(Expression):
    """Column reference: [table_name.]column_name"""
    table_name: str
    column_name: str

@dataclass
class FunctionCallExpression(Expression):
    """Function call: function_name(args)"""
    function_name: str
    arguments: List[Expression]

@dataclass
class BinaryExpression(Expression):
    """Binary operation: left op right"""
    left: Expression
    operator: str
    right: Expression

@dataclass
class UnaryExpression(Expression):
    """Unary operation: op expression"""
    operator: str
    operand: Expression

@dataclass
class InExpression(Expression):
    """IN expression: expr IN (values)"""
    expression: Expression
    values: List[Expression]

@dataclass
class BetweenExpression(Expression):
    """BETWEEN expression: expr BETWEEN low AND high"""
    expression: Expression
    low: Expression
    high: Expression

@dataclass
class ExistsExpression(Expression):
    """EXISTS expression: EXISTS (subquery)"""
    subquery: 'SelectStatement'

@dataclass
class WildcardExpression(Expression):
    """Wildcard expression: *"""
    pass

@dataclass
class AliasExpression(Expression):
    """Expression with alias: expr AS alias"""
    expression: Expression
    alias: str

@dataclass
class OrderByExpression(Expression):
    """ORDER BY expression: expr [ASC|DESC]"""
    expression: Expression
    direction: str = "ASC"

@dataclass
class AssignmentExpression(Expression):
    """Assignment expression: column = value"""
    column_name: str
    value: Expression

# ===== Data Types and Constraints =====

class DataType(Enum):
    """SQL data types"""
    INT = "INT"
    INTEGER = "INTEGER"
    TEXT = "TEXT"
    VARCHAR = "VARCHAR"
    REAL = "REAL"
    BLOB = "BLOB"
    BOOLEAN = "BOOLEAN"

@dataclass
class ColumnConstraint(ASTNode):
    """Base class for column constraints"""
    pass

@dataclass
class PrimaryKeyConstraint(ColumnConstraint):
    """PRIMARY KEY constraint"""
    pass

@dataclass
class UniqueConstraint(ColumnConstraint):
    """UNIQUE constraint"""
    pass

@dataclass
class NotNullConstraint(ColumnConstraint):
    """NOT NULL constraint"""
    pass

@dataclass
class DefaultConstraint(ColumnConstraint):
    """DEFAULT constraint"""
    value: Expression

@dataclass
class CheckConstraint(ColumnConstraint):
    """CHECK constraint"""
    condition: Expression

@dataclass
class AutoIncrementConstraint(ColumnConstraint):
    """AUTOINCREMENT constraint"""
    pass

@dataclass
class ColumnDefinition(ASTNode):
    """Column definition: column_name type_name [constraints]"""
    name: str
    data_type: DataType
    constraints: List[ColumnConstraint]

    def __post_init__(self):
        if self.constraints is None:
            self.constraints = []


# ===== Table and FROM clause =====

@dataclass
class TableReference(ASTNode):
    """Direct table reference"""
    table_name: str
    alias: Optional[str] = None

@dataclass
class SubqueryExpression(Expression):
    """Subquery expression"""
    subquery: 'SelectStatement'
    alias: Optional[str] = None
    exists: bool = False  # True for EXISTS subqueries


@dataclass
class JoinExpression(ASTNode):
    """JOIN clause"""
    join_type: str  # 'INNER', 'LEFT', 'RIGHT', 'FULL', etc.
    table: Union[TableReference, SubqueryExpression]
    condition: Expression

@dataclass
class FromClause(ASTNode):
    """FROM clause with optional JOINs"""
    table: Union[TableReference, SubqueryExpression]
    joins: List[JoinExpression]

    def __post_init__(self):
        if self.joins is None:
            self.joins = []


# ===== Statement AST Nodes =====

@dataclass
class SQLStatement(ASTNode):
    """Base class for all SQL statements"""
    pass

@dataclass
class CreateTableStatement(SQLStatement):
    """CREATE TABLE statement"""
    table_name: str
    columns: List[ColumnDefinition]
    if_not_exists: bool = False

@dataclass
class InsertStatement(SQLStatement):
    """INSERT INTO statement"""
    table_name: str
    columns: List[str]  # Column names
    value_rows: List[List[Expression]]  # Multiple rows of values to insert

@dataclass
class SelectStatement(SQLStatement):
    """SELECT statement"""
    select_list: List[Expression]
    from_clause: Optional[FromClause]
    where_clause: Optional[Expression]
    group_by: List[Expression]
    having_clause: Optional[Expression]
    order_by: List[OrderByExpression]
    limit_clause: Optional[Expression]
    offset_clause: Optional[Expression]
    distinct: bool = False
    all: bool = False

    def __post_init__(self):
        if self.group_by is None:
            self.group_by = []
        if self.order_by is None:
            self.order_by = []

@dataclass
class UpdateStatement(SQLStatement):
    """UPDATE statement"""
    table_name: str
    assignments: List[AssignmentExpression]
    where_clause: Optional[Expression]

@dataclass
class DeleteStatement(SQLStatement):
    """DELETE FROM statement"""
    table_name: str
    where_clause: Optional[Expression]


# Export all classes for easy importing
__all__ = [
    # Base classes
    "ASTNode",
    "Expression",
    "SQLStatement",
    
    # Expression types
    "LiteralExpression",
    "IdentifierExpression", 
    "ColumnReference",
    "FunctionCallExpression",
    "BinaryExpression",
    "UnaryExpression",
    "InExpression",
    "BetweenExpression",
    "WildcardExpression",
    "AliasExpression",
    "OrderByExpression",
    "AssignmentExpression",
    "SubqueryExpression",
    
    # Data types and constraints
    "DataType",
    "ColumnConstraint",
    "PrimaryKeyConstraint",
    "UniqueConstraint", 
    "NotNullConstraint",
    "DefaultConstraint",
    "CheckConstraint",
    "AutoIncrementConstraint",
    "ColumnDefinition",
    
    # Table and FROM clause
    "TableReference",
    "JoinExpression",
    "FromClause",
    
    # Statements
    "CreateTableStatement",
    "InsertStatement",
    "SelectStatement", 
    "UpdateStatement",
    "DeleteStatement",
]

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    pass


# ===== Expression AST Nodes =====

@dataclass
class Expression(ASTNode):
    """Base class for all expressions"""
    pass


@dataclass
class LiteralValue(Expression):
    """Literal value: string, number, boolean, null"""
    value: str
    type: str  # 'string', 'number', 'boolean', 'null', 'special'


@dataclass
class ColumnReference(Expression):
    """Column reference: [table_name.]column_name"""
    column_name: str
    table_name: Optional[str] = None


@dataclass
class FunctionCall(Expression):
    """Function call: function_name(args)"""
    function_name: str
    args: List[Expression]
    distinct: bool = False


@dataclass
class BinaryOp(Expression):
    """Binary operation: left op right"""
    left: Expression
    operator: str
    right: Expression


@dataclass
class UnaryOp(Expression):
    """Unary operation: op expression"""
    operator: str
    expression: Expression


@dataclass
class InExpression(Expression):
    """IN expression: expr IN (values)"""
    expression: Expression
    values: List[Expression]


@dataclass
class BetweenExpression(Expression):
    """BETWEEN expression: expr BETWEEN low AND high"""
    expression: Expression
    low: Expression
    high: Expression


# ===== Column and Table Definitions =====

@dataclass
class ColumnConstraint(ASTNode):
    """Column constraint"""
    type: str  # 'primary_key', 'not_null', 'unique', 'default', 'check'
    value: Optional[Expression] = None  # For DEFAULT and CHECK constraints
    autoincrement: bool = False  # For PRIMARY KEY


@dataclass
class ColumnDef(ASTNode):
    """Column definition: column_name type_name [constraints]"""
    column_name: str
    type_name: str
    constraints: List[ColumnConstraint] = None

    def __post_init__(self):
        if self.constraints is None:
            self.constraints = []


@dataclass
class SelectItem(ASTNode):
    """SELECT list item"""
    expression: Expression
    alias: Optional[str] = None


@dataclass
class JoinClause(ASTNode):
    """JOIN clause"""
    join_type: str  # 'INNER', 'LEFT', 'RIGHT', 'FULL'
    table: 'TableSource'
    condition: Expression


@dataclass
class TableSource(ASTNode):
    """Base class for table sources in FROM clause"""
    pass


@dataclass
class TableReference(TableSource):
    """Direct table reference"""
    table_name: str
    alias: Optional[str] = None


@dataclass
class SubquerySource(TableSource):
    """Subquery as table source"""
    subquery: 'SelectStmt'
    alias: Optional[str] = None


@dataclass
class OrderItem(ASTNode):
    """ORDER BY item"""
    expression: Expression
    direction: Optional[str] = None  # "ASC" or "DESC"


@dataclass
class Assignment(ASTNode):
    """UPDATE assignment: column = expression"""
    column_name: str
    expression: Expression


# ===== Statement AST Nodes =====

@dataclass
class CreateTableStmt(ASTNode):
    """CREATE TABLE statement"""
    table_name: str
    column_defs: List[ColumnDef]
    if_not_exists: bool = False


@dataclass
class InsertStmt(ASTNode):
    """INSERT INTO statement"""
    table_name: str
    column_names: Optional[List[str]]  # None means insert into all columns
    value_rows: List[List[Expression]]  # Multiple rows of values


@dataclass
class SelectStmt(ASTNode):
    """SELECT statement"""
    distinct: Optional[str]  # None, 'DISTINCT', or 'ALL'
    select_list: List[SelectItem]
    table_source: Optional[TableSource]
    joins: List[JoinClause]
    where_clause: Optional[Expression]
    group_by: Optional[List[Expression]]
    having_clause: Optional[Expression]
    order_by: Optional[List[OrderItem]]
    limit: Optional[Expression]
    offset: Optional[Expression]

    def __post_init__(self):
        if self.joins is None:
            self.joins = []


@dataclass
class UpdateStmt(ASTNode):
    """UPDATE statement"""
    table_name: str
    assignments: List[Assignment]  # List of column = expression
    where_clause: Optional[Expression]


@dataclass
class DeleteStmt(ASTNode):
    """DELETE FROM statement"""
    table_name: str
    where_clause: Optional[Expression]


# ===== Legacy Nodes (for backward compatibility) =====

@dataclass
class Condition(ASTNode):
    """Legacy WHERE condition - kept for backward compatibility"""
    column_name: str
    operator: str
    value: str


@dataclass
class WhereClause(ASTNode):
    """Legacy WHERE clause - kept for backward compatibility"""
    conditions: List[Condition]
    logical_ops: List[str]


@dataclass
class OrderBy(ASTNode):
    """Legacy ORDER BY - kept for backward compatibility"""
    column_name: str
    direction: Optional[str] = None


# Export all node types for easy importing
__all__ = [
    'ASTNode', 'Expression', 'LiteralValue', 'ColumnReference', 'FunctionCall',
    'BinaryOp', 'UnaryOp', 'InExpression', 'BetweenExpression', 'SubqueryExpression',
    'ColumnConstraint', 'ColumnDef', 'SelectItem', 'JoinClause', 'TableSource',
    'TableReference', 'SubquerySource', 'OrderItem', 'Assignment',
    'CreateTableStmt', 'InsertStmt', 'SelectStmt', 'UpdateStmt', 'DeleteStmt',
    'Condition', 'WhereClause', 'OrderBy'
]
