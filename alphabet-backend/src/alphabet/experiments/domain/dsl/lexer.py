from datetime import date, datetime

from syntactix.lexical.exceptions import LexerRequireFailedError
from types import MappingProxyType

from typing import Final, final

from dataclasses import dataclass
from enum import Enum

from syntactix.lexical.lexer import LexerBase
from syntactix.lexical.token import TokenLike, TokenPos


ESCAPES: Final = MappingProxyType({
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
    "\\": "\\",
    '"': '"',
})


@final
class TargetDSLTokenType(Enum):
    NUMBER = "number"
    NAME = "name"
    STRING = "string"
    DATE = "date"
    UNDEFINED = "undefined"
    TRUE = "true"
    FALSE = "false"

    LPAR = "("
    RPAR = ")"
    LBRACKET = "["
    RBRACKET = "]"
    COMMA = ","

    OR = "OR"
    AND = "AND"
    IN = "IN"
    NOT_IN = "NOT IN"
    GREATER = ">"
    LESS = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "=="
    NOT_EQUAL = "!="
    NOT = "NOT"

    EOF = "EOF"


KEYWORDS: Final = MappingProxyType({
    "NOT": TargetDSLTokenType.NOT,
    "AND": TargetDSLTokenType.AND,
    "OR": TargetDSLTokenType.OR,
    "IN": TargetDSLTokenType.IN,
    "NOT IN": TargetDSLTokenType.NOT_IN,
    "true": TargetDSLTokenType.TRUE,
    "false": TargetDSLTokenType.FALSE,
    "undefined": TargetDSLTokenType.UNDEFINED,
})


@final
@dataclass
class TargetDSLToken(TokenLike[str | float, TargetDSLTokenType]):
    type: TargetDSLTokenType
    lexeme: str
    value: str | float | date
    pos: TokenPos

    def __repr__(self) -> str:
        return repr(self.lexeme)

    @classmethod
    def eof(cls, pos: TokenPos) -> "TargetDSLToken":
        return TargetDSLToken(TargetDSLTokenType.EOF, "EOF", "EOF", pos)


class TargetDSLLexer(LexerBase[TargetDSLToken, TargetDSLTokenType]):
    @classmethod
    def make_lexer(cls, src: str) -> "TargetDSLLexer":
        return TargetDSLLexer(src, TargetDSLToken)

    def scan_char(self) -> None:
        ch = self.consume()
        if not ch:
            self.unexpected("EOF")
        if ch in "()[],":
            self.add_token(TargetDSLTokenType(ch))
        elif ch == ">":
            if self.match("="):
                self.add_token(TargetDSLTokenType.GREATER_EQUAL)
            else:
                self.add_token(TargetDSLTokenType.GREATER)
        elif ch == "<":
            if self.match("="):
                self.add_token(TargetDSLTokenType.LESS_EQUAL)
            else:
                self.add_token(TargetDSLTokenType.LESS)
        elif ch == "=":
            self.require("=")
            self.add_token(TargetDSLTokenType.EQUAL)
        elif ch == "!":
            self.require("=")
            self.add_token(TargetDSLTokenType.NOT_EQUAL)
        elif ch == '"':
            self.scan_string()
        elif ch.isnumeric() or ch == "-":
            self.inc_pos(-1)
            self.scan_number()
        elif ch in " \t":
            self.reset_start()
        elif ch in "\r\n":
            self.mark_next_line()
            self.reset_start()
        elif ch.isalpha() or ch == "_":
            self.scan_name_or_keyword()
        else:
            self.unexpected(ch)

    def scan_number(self) -> None:
        sign = self.match("-") or ""
        whole_part = self.consume_while(
            lambda: self.peek in "0123456789",
            not_at_end=True
        )
        if not sign and len(whole_part) == 4 and self.match("-"):
            # this is a date
            whole_part += "-"
            whole_part += self.require(list("0123456789"))
            whole_part += self.require(list("0123456789"))
            whole_part += self.require("-")
            whole_part += self.require(list("0123456789"))
            whole_part += self.require(list("0123456789"))
            try:
                parsed_dt = datetime.strptime(whole_part, "%Y-%m-%d")
            except ValueError:
                self.unexpected(whole_part)
            self.add_token(TargetDSLTokenType.DATE, parsed_dt.date())
            return
        frac_part = None
        if self.match("."):
            if self.peek.isnumeric():
                frac_part = self.consume_while(
                    lambda: self.peek in "0123456789",
                    not_at_end=True
                )
            else:
                # roll back, not a float number
                self.inc_pos(-1)
        if frac_part:
            value = float(f"{sign}{whole_part}.{frac_part}")
        else:
            value = float(f"{sign}{whole_part}")
        self.add_token(TargetDSLTokenType.NUMBER, value)

    def scan_string(self) -> None:
        escaping = False
        chars = []
        while self.peek and (self.peek not in '"\n\r' or escaping):
            if self.peek == "\\" and not escaping:
                escaping = True
                self.consume()
                continue
            if escaping:
                if self.peek not in ESCAPES:
                    self.error(
                        LexerRequireFailedError, strings=ESCAPES.keys()
                    )
                chars.append(ESCAPES[self.peek])
                escaping = False
                self.consume()
                continue
            chars.append(self.peek)
            self.consume()
        self.require('"')
        self.add_token(TargetDSLTokenType.STRING, "".join(chars))

    def scan_name_or_keyword(self) -> None:
        name = self.prev + self.consume_while(
            lambda: self.peek.isalpha() or self.peek in "-_",
            not_at_end=True
        )
        if name == "NOT":
            if self.match(" IN"):
                self.add_token(TargetDSLTokenType.NOT_IN)
                return
        if name in KEYWORDS:
            self.add_token(KEYWORDS[name])
        else:
            self.add_token(TargetDSLTokenType.NAME, name)
