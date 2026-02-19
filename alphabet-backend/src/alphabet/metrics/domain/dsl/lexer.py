from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Final, final, override

from syntactix.lexical.exceptions import LexerRequireFailedError
from syntactix.lexical.lexer import LexerBase
from syntactix.lexical.token import TokenLike, TokenPos

ESCAPES: Final = MappingProxyType(
    {
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "v": "\v",
        "\\": "\\",
        '"': '"',
    },
)


@final
class MetricDSLTokenType(Enum):
    # Aggregations
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    P50 = "p50"
    P75 = "p75"
    P90 = "p90"
    P95 = "p95"
    P99 = "p99"
    COUNT = "count"

    # Sources
    DISCARDED = "discarded"
    DUPLICATE = "duplicate"

    # Attribution
    ATTRIBUTED = "attributed"
    UNATTRIBUTED = "unattributed"

    # Special values
    DELIVERY_LATENCY = "!delivery_latency"
    WILDCARD = "*"
    NULL = "null"

    # Filter keywords
    WHERE = "where"
    AND = "and"
    OR = "or"

    # Operators
    EQUAL = "=="
    NOT_EQUAL = "!="
    DOT = "."
    SLASH = "/"

    # Literals
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    NAME = "name"

    EOF = "EOF"


KEYWORDS: Final = MappingProxyType(
    {
        "sum": MetricDSLTokenType.SUM,
        "min": MetricDSLTokenType.MIN,
        "max": MetricDSLTokenType.MAX,
        "p50": MetricDSLTokenType.P50,
        "p75": MetricDSLTokenType.P75,
        "p90": MetricDSLTokenType.P90,
        "p95": MetricDSLTokenType.P95,
        "p99": MetricDSLTokenType.P99,
        "count": MetricDSLTokenType.COUNT,
        "discarded": MetricDSLTokenType.DISCARDED,
        "duplicate": MetricDSLTokenType.DUPLICATE,
        "attributed": MetricDSLTokenType.ATTRIBUTED,
        "unattributed": MetricDSLTokenType.UNATTRIBUTED,
        "where": MetricDSLTokenType.WHERE,
        "and": MetricDSLTokenType.AND,
        "or": MetricDSLTokenType.OR,
        "null": MetricDSLTokenType.NULL,
        "true": MetricDSLTokenType.BOOLEAN,
        "false": MetricDSLTokenType.BOOLEAN,
    },
)


@final
@dataclass
class MetricDSLToken(
    TokenLike[str | float | bool, str],  # type: ignore[misc]
):
    type: str
    lexeme: str
    value: str | float | bool
    pos: TokenPos

    @override
    def __repr__(self) -> str:
        return repr(self.lexeme)

    @classmethod
    def eof(cls, pos: TokenPos) -> "MetricDSLToken":
        return MetricDSLToken(MetricDSLTokenType.EOF, "EOF", "EOF", pos)


class MetricDSLLexer(
    LexerBase[MetricDSLToken, str],  # type: ignore[misc]
):
    @classmethod
    def make_lexer(cls, src: str) -> "MetricDSLLexer":
        return MetricDSLLexer(src, MetricDSLToken)

    def scan_char(self) -> None:  # noqa: C901
        ch = self.consume()
        if not ch:
            self.unexpected("EOF")
        if ch == "/":
            self.add_token(MetricDSLTokenType.SLASH)
        elif ch == ".":
            self.add_token(MetricDSLTokenType.DOT)
        elif ch == "=":
            self.require("=")
            self.add_token(MetricDSLTokenType.EQUAL)
        elif ch == "!":
            if self.match("="):
                self.add_token(MetricDSLTokenType.NOT_EQUAL)
            else:
                self.unexpected(ch)
        elif ch == ":":
            if self.match("delivery_latency"):
                self.add_token(MetricDSLTokenType.DELIVERY_LATENCY)
            else:
                self.unexpected(ch)
        elif ch == "*":
            self.add_token(MetricDSLTokenType.WILDCARD)
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
            not_at_end=True,
        )
        frac_part = None
        if self.match("."):
            if self.peek.isnumeric():
                frac_part = self.consume_while(
                    lambda: self.peek in "0123456789",
                    not_at_end=True,
                )
            else:
                # roll back, not a float number
                self.inc_pos(-1)
        if frac_part:
            value = float(f"{sign}{whole_part}.{frac_part}")
        else:
            value = float(f"{sign}{whole_part}")
        self.add_token(MetricDSLTokenType.NUMBER, value)

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
                        LexerRequireFailedError,
                        strings=ESCAPES.keys(),
                    )
                chars.append(ESCAPES[self.peek])
                escaping = False
                self.consume()
                continue
            chars.append(self.peek)
            self.consume()
        self.require('"')
        self.add_token(MetricDSLTokenType.STRING, "".join(chars))

    def scan_name_or_keyword(self) -> None:
        name = self.prev + self.consume_while(
            lambda: self.peek.isalnum() or self.peek in "-_",
            not_at_end=True,
        )
        if name in KEYWORDS:
            token_type = KEYWORDS[name]
            if token_type == MetricDSLTokenType.BOOLEAN:
                self.add_token(token_type, name == "true")
            else:
                self.add_token(token_type)
        else:
            self.add_token(MetricDSLTokenType.NAME, name)
