from enum import StrEnum
from typing import final

from syntactix.parser.nodes import NodeLike

from alphabet.metrics.domain.dsl.lexer import MetricDSLToken
from alphabet.shared.commons import value_object


class Node(NodeLike[MetricDSLToken]):  # type: ignore[misc]
    token: MetricDSLToken


@final
class Aggregation(StrEnum):
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    P50 = "p50"
    P75 = "p75"
    P90 = "p90"
    P95 = "p95"
    P99 = "p99"
    COUNT = "count"


@final
class Source(StrEnum):
    EVENTS = "events"
    DISCARDED = "discarded"
    DUPLICATE = "duplicate"


@final
class Attribution(StrEnum):
    ALL = "all"
    ATTRIBUTED = "attributed"
    UNATTRIBUTED = "unattributed"


@final
@value_object
class LiteralStrNode(Node):
    token: MetricDSLToken
    value: str


@final
@value_object
class LiteralNumberNode(Node):
    token: MetricDSLToken
    value: float


@final
@value_object
class LiteralBoolNode(Node):
    token: MetricDSLToken
    value: bool


@final
@value_object
class LiteralNullNode(Node):
    token: MetricDSLToken


@final
class FilterEquality(StrEnum):
    EQ = "eq"
    NE = "ne"


@final
@value_object
class FilterPrimaryNode(Node):
    token: MetricDSLToken
    path: list[str]
    operator: FilterEquality
    literal: LiteralStrNode | LiteralNumberNode | LiteralBoolNode | LiteralNullNode


@final
@value_object
class FilterAndNode(Node):
    token: MetricDSLToken
    operands: list[FilterPrimaryNode]


@final
@value_object
class FilterOrNode(Node):
    token: MetricDSLToken
    operands: list[FilterAndNode]


@final
@value_object
class ValueNode(Node):
    token: MetricDSLToken
    path: list[str]


@final
class SystemValueKind(StrEnum):
    DELIVERY_LATENCY = "delivery_latency"


@final
@value_object
class SystemValueNode(Node):
    token: MetricDSLToken
    kind: SystemValueKind


# Component references value (user or system) and filters
@final
@value_object
class ComponentNode(Node):
    token: MetricDSLToken
    aggregation: Aggregation
    event_type: str
    value: ValueNode | SystemValueNode | None
    filters: FilterOrNode | None
    source: Source = Source.EVENTS
    attribution: Attribution = Attribution.ALL


@final
@value_object
class MetricExprNode(Node):
    token: MetricDSLToken
    numerator: ComponentNode
    denominator: ComponentNode | None
