from datetime import date

from types import MappingProxyType

from typing import Final, cast

from syntactix.parser.parser import ParserBase

from alphabet.experiments.domain.dsl.lexer import (
    TargetDSLToken,
    TargetDSLTokenType,
)
from alphabet.experiments.domain.dsl.nodes import (
    BinOp,
    BinOpNode,
    LiteralBool, LiteralCollection,
    LiteralDate,
    LiteralNumber,
    LiteralStr,
    LiteralUndefined,
    NameNode, Node,
    UnaryNotNode,
)

_TOK_TYPE_TO_BIN_OP: Final = MappingProxyType(
    {
        TargetDSLTokenType.EQUAL: BinOp.EQ,
        TargetDSLTokenType.NOT_EQUAL: BinOp.NOT_EQ,
        TargetDSLTokenType.IN: BinOp.IN,
        TargetDSLTokenType.NOT_IN: BinOp.NOT_IN,
        TargetDSLTokenType.GREATER: BinOp.GREATER,
        TargetDSLTokenType.GREATER_EQUAL: BinOp.GREATER_EQUAL,
        TargetDSLTokenType.LESS: BinOp.LESS,
        TargetDSLTokenType.LESS_EQUAL: BinOp.LESS_EQUAL,
    }
)


class TargetDSLParser(ParserBase[TargetDSLToken, TargetDSLTokenType, Node]):
    def parse(self) -> Node:
        return self._parse_disj()

    def _parse_disj(self) -> Node:
        lhs = self._parse_conj()
        while tok := self.match(TargetDSLTokenType.OR):
            rhs = self._parse_conj()
            lhs = BinOpNode(tok, lhs, rhs, BinOp.OR)
        return lhs

    def _parse_conj(self) -> Node:
        lhs = self._parse_cmp()
        while tok := self.match(TargetDSLTokenType.AND):
            rhs = self._parse_cmp()
            lhs = BinOpNode(tok, lhs, rhs, BinOp.AND)
        return lhs

    def _parse_cmp(self) -> Node:
        lhs = self._parse_unary()
        while tok := self.match(
            TargetDSLTokenType.EQUAL,
            TargetDSLTokenType.NOT_EQUAL,
            TargetDSLTokenType.IN,
            TargetDSLTokenType.NOT_IN,
            TargetDSLTokenType.GREATER,
            TargetDSLTokenType.GREATER_EQUAL,
            TargetDSLTokenType.LESS,
            TargetDSLTokenType.LESS_EQUAL,
        ):
            rhs = self._parse_unary()
            lhs = BinOpNode(tok, lhs, rhs, _TOK_TYPE_TO_BIN_OP[tok.type])
        return lhs

    def _parse_unary(self) -> Node:
        if tok := self.match(TargetDSLTokenType.NOT):
            return UnaryNotNode(tok, self._parse_unary())
        return self._parse_primary()

    def _parse_primary(self) -> Node:
        if self.match(TargetDSLTokenType.LPAR):
            expr = self.parse()
            self.require(TargetDSLTokenType.RPAR)
            return expr
        elif tok := self.match(TargetDSLTokenType.LBRACKET):
            items = []
            if self.match(TargetDSLTokenType.RBRACKET):
                return LiteralCollection(tok, items)
            items.append(self._parse_value())
            while self.match(TargetDSLTokenType.COMMA):
                items.append(self._parse_value())
            self.require(TargetDSLTokenType.RBRACKET)
            return LiteralCollection(tok, items)
        elif tok := self.match(TargetDSLTokenType.NAME):
            return NameNode(tok, tok.value)
        else:
            return self._parse_value()

    def _parse_value(self) -> Node:
        if tok := self.match(TargetDSLTokenType.DATE):
            return LiteralDate(tok, cast(date, tok.value))
        elif tok := self.match(TargetDSLTokenType.NUMBER):
            return LiteralNumber(tok, cast(float, tok.value))
        elif tok := self.match(TargetDSLTokenType.STRING):
            return LiteralStr(tok, cast(str, tok.value))
        elif tok := self.match(TargetDSLTokenType.UNDEFINED):
            return LiteralUndefined(tok)
        elif tok := self.match(TargetDSLTokenType.TRUE):
            return LiteralBool(tok, value=True)
        elif tok := self.match(TargetDSLTokenType.FALSE):
            return LiteralBool(tok, value=False)
        else:
            if self.not_at_end:
                self.unexpected(self.peek)
            else:
                self.unexpected(TargetDSLToken.eof(self.pos))
