from types import MappingProxyType

from typing import Final

from alphabet.experiments.domain.dsl.nodes import (
    BinOp, BinOpNode, LiteralBool, LiteralCollection,
    LiteralDate, LiteralNumber, LiteralStr, LiteralUndefined, NameNode,
    Node, UnaryNotNode,
)


_BIN_OP_TO_RT_NAME: Final = MappingProxyType(
    {
        BinOp.LESS: "_cmp_lt",
        BinOp.LESS_EQUAL: "_cmp_le",
        BinOp.GREATER: "_cmp_gt",
        BinOp.GREATER_EQUAL: "_cmp_ge",
        BinOp.EQ: "_cmp_eq",
        BinOp.NOT_EQ: "_cmp_neq",
        BinOp.AND: "_and",
        BinOp.OR: "_or",
        BinOp.IN: "_is_in",
        BinOp.NOT_IN: "_is_not_in",
    }
)


class CodeGenerator:
    def __init__(self, expr: Node) -> None:
        self.expr = expr

    def generate(self) -> str:
        expr_str = self._gen(self.expr)
        code = f"class _Expr(CompiledExpression):\n"
        code += "    def run(self):\n"
        code += f"        return {expr_str}\n"
        return code

    def _gen(self, node: Node) -> str:
        generator = getattr(self, f"_gen_{node.__class__.__name__}", None)
        if not generator:
            raise NotImplementedError(node)
        return str(generator(node))

    def _gen_NameNode(self, node: NameNode) -> str:
        return f"self._from_ctx({node.name!r})"

    def _gen_LiteralCollection(self, node: LiteralCollection) -> str:
        return "[" + ",".join(map(self._gen, node.items)) + "]"

    def _gen_LiteralDate(self, node: LiteralDate) -> str:
        return (f"self._construct_date("
                f"{node.value.day}, {node.value.month}, {node.value.year}"
                f")")

    def _gen_LiteralStr(self, node: LiteralStr) -> str:
        return repr(node.value)

    def _gen_LiteralNumber(self, node: LiteralNumber) -> str:
        return repr(node.value)

    def _gen_LiteralBool(self, node: LiteralBool) -> str:
        if node.value:
            return "True"
        else:
            return "False"

    def _gen_LiteralUndefined(self, node: LiteralUndefined) -> str:
        return "None"

    def _gen_UnaryNotNode(self, node: UnaryNotNode) -> str:
        return f"self._not({self._gen(node)})"

    def _gen_BinOpNode(self, node: BinOpNode) -> str:
        lhs = self._gen(node.l)
        rhs = self._gen(node.r)
        rt_name = _BIN_OP_TO_RT_NAME[node.op]
        return f"self.{rt_name}({lhs}, {rhs})"
