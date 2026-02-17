from datetime import date
from enum import StrEnum
from typing import final

from syntactix.parser.nodes import NodeLike

from alphabet.experiments.domain.dsl.lexer import TargetDSLToken
from alphabet.shared.commons import value_object


class Node(NodeLike[TargetDSLToken]):  # type: ignore[misc]
    token: TargetDSLToken


@final
class BinOp(StrEnum):
    LESS = "<"
    LESS_EQUAL = "<="
    GREATER = ">"
    GREATER_EQUAL = ">="
    EQ = "=="
    NOT_EQ = "!="
    AND = "and"
    OR = "or"
    IN = "in"
    NOT_IN = "not in"


@final
@value_object
class BinOpNode(Node):
    token: TargetDSLToken
    lhs: Node
    rhs: Node
    op: BinOp


@final
@value_object
class UnaryNotNode(Node):
    token: TargetDSLToken
    expr: Node


@final
@value_object
class LiteralUndefined(Node):
    token: TargetDSLToken


@final
@value_object
class LiteralBool(Node):
    token: TargetDSLToken
    value: bool


@final
@value_object
class LiteralNumber(Node):
    token: TargetDSLToken
    value: float


@final
@value_object
class LiteralStr(Node):
    token: TargetDSLToken
    value: str


@final
@value_object
class LiteralDate(Node):
    token: TargetDSLToken
    value: date


@final
@value_object
class LiteralCollection(Node):
    token: TargetDSLToken
    items: list[Node]


@final
@value_object
class NameNode(Node):
    token: TargetDSLToken
    name: str
