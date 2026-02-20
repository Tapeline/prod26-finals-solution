from types import MappingProxyType
from typing import Final, assert_never, cast

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
from alphabet.metrics.domain.metrics import SQLFragment

_SOURCE_TO_TABLE: Final = MappingProxyType(
    {
        Source.EVENTS: "events",
        Source.DISCARDED: "discarded_events",
        Source.DUPLICATE: "duplicate_events",
    },
)
_AGG_FUNCTION_TEMPLATES: Final = MappingProxyType(
    {
        Aggregation.COUNT: "count({})",
        Aggregation.SUM: "sum({})",
        Aggregation.MIN: "min({})",
        Aggregation.MAX: "max({})",
        Aggregation.P50: "quantile(0.50)({})",
        Aggregation.P75: "quantile(0.75)({})",
        Aggregation.P90: "quantile(0.90)({})",
        Aggregation.P95: "quantile(0.95)({})",
        Aggregation.P99: "quantile(0.99)({})",
    },
)


class CodeGenerator:
    def __init__(self, expr: MetricExprNode) -> None:
        self.expr = expr

    def generate(self) -> tuple[SQLFragment, SQLFragment | None]:
        return self._gen_MetricExprNode(self.expr)

    def _gen(self, node: Node) -> str | SQLFragment:
        generator = getattr(self, f"_gen_{node.__class__.__name__}", None)
        if not generator:
            raise NotImplementedError(
                f"Generator not implemented for {type(node)}",
            )
        return generator(node)  # type: ignore[no-any-return]

    def _gen_MetricExprNode(
        self,
        node: MetricExprNode,
    ) -> tuple[SQLFragment, SQLFragment | None]:
        numerator = self._gen_ComponentNode(node.numerator)
        denominator = None
        if node.denominator is not None:
            denominator = self._gen_ComponentNode(node.denominator)
        return numerator, denominator

    def _gen_ComponentNode(self, node: ComponentNode) -> SQLFragment:
        table_name = _SOURCE_TO_TABLE[node.source]
        select_expr = self._gen_aggregation(node)
        where_expr = self._gen_component_where(node)
        return SQLFragment(
            select=select_expr,
            where=where_expr,
            table=table_name,
        )

    def _gen_aggregation(self, node: ComponentNode) -> str:
        value_sql = None
        if node.value:
            is_numeric_agg = node.aggregation != Aggregation.COUNT
            value_sql = self._gen_value_extractor(
                node.value,
                as_float=is_numeric_agg,
            )
        if node.aggregation == Aggregation.COUNT and not value_sql:
            return "count()"
        return _AGG_FUNCTION_TEMPLATES[node.aggregation].format(value_sql)

    def _gen_component_where(self, node: ComponentNode) -> str:
        parts: list[str] = []
        if node.event_type != "*":
            if node.source == Source.DISCARDED:
                parts.append(f"event_type_id = '{node.event_type}'")
            else:
                parts.append(f"event_type = '{node.event_type}'")
        if node.attribution == Attribution.ATTRIBUTED:
            parts.append("status = 'accepted'")
        elif node.attribution == Attribution.UNATTRIBUTED:
            parts.append("status != 'accepted'")
        if node.filters is not None:
            filters_sql = self._gen(node.filters)
            if filters_sql:
                parts.append(f"({filters_sql})")
        return " AND ".join(parts) if parts else "1=1"

    def _gen_value_extractor(
        self,
        node: ValueNode | SystemValueNode,
        *,
        as_float: bool = False,
    ) -> str:
        if isinstance(node, SystemValueNode):
            return self._gen_SystemValueNode(node)
        path_str = ", ".join(f"'{p}'" for p in node.path)
        if as_float:
            return f"JSONExtractFloat(attributes, {path_str})"
        return f"JSONExtractString(attributes, {path_str})"

    def _gen_SystemValueNode(self, node: SystemValueNode) -> str:
        match node.kind:
            case SystemValueKind.DELIVERY_LATENCY:
                return "dateDiff('millisecond', issued_at, received_at)"
            case _:
                assert_never(node.kind)

    def _gen_FilterOrNode(self, node: FilterOrNode) -> str:
        parts = [cast(str, self._gen(op)) for op in node.operands]
        return f"({' OR '.join(parts)})" if parts else ""

    def _gen_FilterAndNode(self, node: FilterAndNode) -> str:
        parts = [cast(str, self._gen(op)) for op in node.operands]
        return f"({' AND '.join(parts)})" if parts else ""

    def _gen_FilterPrimaryNode(self, node: FilterPrimaryNode) -> str:
        path_sql = self._gen_value_extractor(
            ValueNode(token=node.token, path=node.path),
            as_float=False,
        )
        literal_sql = self._gen(node.literal)
        if isinstance(node.literal, LiteralNullNode):
            if node.operator == FilterEquality.EQ:
                return f"{path_sql} IS NULL"
            if node.operator == FilterEquality.NE:
                return f"{path_sql} IS NOT NULL"
        op = "=" if node.operator == FilterEquality.EQ else "!="
        return f"{path_sql} {op} {literal_sql}"

    def _gen_LiteralStrNode(self, node: LiteralStrNode) -> str:
        # TODO: refactor to escape maybe?
        return f"{node.value!r}"

    def _gen_LiteralNumberNode(self, node: LiteralNumberNode) -> str:
        return f"{node.value!r}"

    def _gen_LiteralBoolNode(self, node: LiteralBoolNode) -> str:
        return "1" if node.value else "0"

    def _gen_LiteralNullNode(self, node: LiteralNullNode) -> str:
        return "NULL"
