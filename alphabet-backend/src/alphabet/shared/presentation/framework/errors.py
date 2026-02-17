# from https://github.com/Tapeline/Fastscaffold

from collections.abc import Callable, Mapping
from typing import Any, Final, NewType

import inflection
from litestar import Request, Response

_InferCodeType = NewType("_InferCodeType", str)
infer_code: Final = _InferCodeType("")

type StatusCode = int
type ErrorCode = str | _InferCodeType
type SimpleHandlerDef = tuple[StatusCode, ErrorCode]
type ErrorExtras = dict
type ErrorEnricher[_Exc_T: Exception] = Callable[[_Exc_T], ErrorExtras]
type EnrichedHandlerDef[_Exc_T: Exception] = tuple[
    *SimpleHandlerDef,
    ErrorEnricher[_Exc_T],
]
type HandlerDef = SimpleHandlerDef | EnrichedHandlerDef[Any]
type LitestarErrHandler = Callable[
    [Request[Any, Any, Any], Exception],
    Response[Any],
]


def _default_enricher(exc: Any) -> dict[Any, Any]:
    return {"detail": getattr(exc, "text", "No detail.")}


def _create_handler(handler_def: HandlerDef) -> LitestarErrHandler:
    enricher: ErrorEnricher[Any] = _default_enricher
    if len(handler_def) == 2:
        status, code = handler_def
    else:
        status, code, enricher = handler_def

    def handler_func(  # noqa: WPS430
        request: Request[Any, Any, Any],
        exc: Exception,
    ) -> Response[Any]:
        nonlocal code  # noqa: WPS420
        extras = enricher(exc)
        if code is infer_code:
            # refactor so it's not in runtime
            code = inflection.underscore(exc.__class__.__name__)
        return Response(
            status_code=status,
            content={
                "code": code,
                "extras": extras,
            },
        )

    return handler_func


def gen_handler_mapping(
    handler_defs: Mapping[type[Exception], HandlerDef],
) -> Mapping[type[Exception], LitestarErrHandler]:
    """Generate Litestar exc handlers from DSL."""
    return {
        exc_t: _create_handler(exc_handler)
        for exc_t, exc_handler in handler_defs.items()
    }
