from types import MappingProxyType
from typing import Final, assert_never, cast

from syntactix.parser.parser import ParserBase

from alphabet.metrics.domain.dsl.lexer import (
    MetricDSLToken,
    MetricDSLTokenType,
)
from alphabet.metrics.domain.dsl.nodes import (
    Aggregation,
    Attribution,
    ComponentNode,
    FilterAndNode,
    FilterEquality,
    FilterOrNode,
    FilterPrimaryNode,
    LiteralBoolNode,
    LiteralNullNode,
    LiteralNumberNode,
    LiteralStrNode,
    MetricExprNode,
    Node,
    Source,
    SystemValueKind,
    SystemValueNode,
    ValueNode,
)

_AGG_TOKEN_TO_AGG: Final = MappingProxyType(
    {
        MetricDSLTokenType.SUM: Aggregation.SUM,
        MetricDSLTokenType.MIN: Aggregation.MIN,
        MetricDSLTokenType.MAX: Aggregation.MAX,
        MetricDSLTokenType.P50: Aggregation.P50,
        MetricDSLTokenType.P75: Aggregation.P75,
        MetricDSLTokenType.P90: Aggregation.P90,
        MetricDSLTokenType.P95: Aggregation.P95,
        MetricDSLTokenType.P99: Aggregation.P99,
        MetricDSLTokenType.COUNT: Aggregation.COUNT,
    },
)


class MetricDSLParser(
    ParserBase[MetricDSLToken, MetricDSLTokenType, Node],  # type: ignore[misc]
):
    def parse(self) -> MetricExprNode:
        numerator = self._parse_component()
        if self.match(MetricDSLTokenType.SLASH):
            denominator = self._parse_component()
            return MetricExprNode(
                numerator.token,
                numerator,
                denominator,
            )
        return MetricExprNode(numerator.token, numerator, None)

    def _parse_component(self) -> ComponentNode:
        agg_token = self.require(
            MetricDSLTokenType.SUM,
            MetricDSLTokenType.MIN,
            MetricDSLTokenType.MAX,
            MetricDSLTokenType.P50,
            MetricDSLTokenType.P75,
            MetricDSLTokenType.P90,
            MetricDSLTokenType.P95,
            MetricDSLTokenType.P99,
            MetricDSLTokenType.COUNT,
        )
        aggregation = _AGG_TOKEN_TO_AGG[agg_token.type]

        source: Source = Source.EVENTS
        if self.match(MetricDSLTokenType.DISCARDED):
            source = Source.DISCARDED
        elif self.match(MetricDSLTokenType.DUPLICATE):
            source = Source.DUPLICATE

        attribution: Attribution = Attribution.ALL
        if self.match(MetricDSLTokenType.ATTRIBUTED):
            attribution = Attribution.ATTRIBUTED
        elif self.match(MetricDSLTokenType.UNATTRIBUTED):
            attribution = Attribution.UNATTRIBUTED

        event_type_token = self.require(
            MetricDSLTokenType.NAME,
            MetricDSLTokenType.WILDCARD,
        )
        event_type = (
            "*"
            if event_type_token.type == MetricDSLTokenType.WILDCARD
            else cast(str, event_type_token.value)
        )

        value: ValueNode | SystemValueNode | None = None
        if aggregation != Aggregation.COUNT:
            value = self._parse_value()

        filters: FilterOrNode | None = None
        if self.match(MetricDSLTokenType.WHERE):
            filters = self._parse_filter_or()

        return ComponentNode(
            agg_token,
            aggregation,
            event_type,
            value,
            filters,
            source=source or Source.EVENTS,
            attribution=attribution or Attribution.ALL,
        )

    def _parse_value(self) -> ValueNode | SystemValueNode:
        token = self.peek
        if self.match(MetricDSLTokenType.DELIVERY_LATENCY):
            return SystemValueNode(token, SystemValueKind.DELIVERY_LATENCY)
        path = self._parse_path()
        return ValueNode(token, path)

    def _parse_path(self) -> list[str]:
        name_token = self.require(MetricDSLTokenType.NAME)
        path = [cast(str, name_token.value)]
        while self.match(MetricDSLTokenType.DOT):
            next_name = self.require(MetricDSLTokenType.NAME)
            path.append(cast(str, next_name.value))
        return path

    def _parse_filter_or(self) -> FilterOrNode:
        token = self.peek
        operands = [self._parse_filter_and()]
        while self.match(MetricDSLTokenType.OR):
            operands.append(self._parse_filter_and())
        return FilterOrNode(token, operands)

    def _parse_filter_and(self) -> FilterAndNode:
        token = self.peek
        operands = [self._parse_filter_primary()]
        while self.match(MetricDSLTokenType.AND):
            operands.append(self._parse_filter_primary())
        return FilterAndNode(token, operands)

    def _parse_filter_primary(self) -> FilterPrimaryNode:
        path = self._parse_path()
        token = self.require(
            MetricDSLTokenType.EQUAL,
            MetricDSLTokenType.NOT_EQUAL,
        )
        literal = self._parse_literal()
        match token.type:
            case MetricDSLTokenType.EQUAL:
                op = FilterEquality.EQ
            case MetricDSLTokenType.NOT_EQUAL:
                op = FilterEquality.NE
            case _:
                assert_never(token.type)
        return FilterPrimaryNode(token.type, path, op, literal)

    def _parse_literal(
        self,
    ) -> (
        LiteralStrNode | LiteralNumberNode | LiteralBoolNode | LiteralNullNode
    ):
        token = self.peek
        if tok := self.match(MetricDSLTokenType.STRING):
            return LiteralStrNode(token, cast(str, tok.value))
        if tok := self.match(MetricDSLTokenType.NUMBER):
            return LiteralNumberNode(token, cast(float, tok.value))
        if tok := self.match(MetricDSLTokenType.BOOLEAN):
            return LiteralBoolNode(token, cast(bool, tok.value))
        if self.match(MetricDSLTokenType.NULL):
            return LiteralNullNode(token)
        self.unexpected(self.peek)
        raise AssertionError("cannot go here")
