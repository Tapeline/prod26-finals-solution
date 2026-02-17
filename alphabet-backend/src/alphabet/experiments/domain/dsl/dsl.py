from syntactix.error_formatter import format_exception
from syntactix.lexical.exceptions import LexerError
from syntactix.parser.exceptions import ParserError

from alphabet.experiments.domain.dsl.codegen import CodeGenerator
from alphabet.experiments.domain.dsl.exceptions import (
    InvalidTargetDSLExpression,
)
from alphabet.experiments.domain.dsl.lexer import TargetDSLLexer
from alphabet.experiments.domain.dsl.parser import TargetDSLParser
from alphabet.experiments.domain.dsl.runtime import CompiledExpression


def translate_dsl(dsl_string: str) -> str:
    lexer = TargetDSLLexer.make_lexer(dsl_string)
    try:
        tokens = lexer.scan()
        parser = TargetDSLParser(tokens)
        expr = parser.parse()
        codegen = CodeGenerator(expr)
        return codegen.generate()
    except (LexerError, ParserError) as exc:
        raise InvalidTargetDSLExpression(
            format_exception(exc, dsl_string, "<input>"),
        ) from exc


def compile_dsl(dsl_string: str) -> type[CompiledExpression]:
    translated = translate_dsl(dsl_string)
    rt_globals = {"CompiledExpression": CompiledExpression}
    compiled = compile(translated, "<input>", "exec")
    exec(compiled, rt_globals)  # noqa: S102
    return rt_globals["_Expr"]
