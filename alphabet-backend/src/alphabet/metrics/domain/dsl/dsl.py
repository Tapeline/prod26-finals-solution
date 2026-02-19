from syntactix.error_formatter import format_exception
from syntactix.lexical.exceptions import LexerError
from syntactix.parser.exceptions import ParserError

from alphabet.metrics.infrastructure.codegen import CodeGenerator
from alphabet.metrics.domain.metrics import SQLFragment
from alphabet.metrics.domain.dsl.exceptions import InvalidMetricDSLExpression
from alphabet.metrics.domain.dsl.lexer import MetricDSLLexer
from alphabet.metrics.domain.dsl.parser import MetricDSLParser


def compile_metric_dsl(dsl_string: str) -> tuple[SQLFragment, SQLFragment | None]:
    lexer = MetricDSLLexer.make_lexer(dsl_string)
    try:
        tokens = lexer.scan()
        parser = MetricDSLParser(tokens)
        expr = parser.parse()
        codegen = CodeGenerator(expr)
        return codegen.generate()
    except (LexerError, ParserError) as exc:
        raise InvalidMetricDSLExpression(
            format_exception(exc, dsl_string, "<input>"),
        ) from exc
