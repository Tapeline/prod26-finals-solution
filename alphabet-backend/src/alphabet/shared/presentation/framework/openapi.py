from types import MappingProxyType
from typing import Any, Final

from litestar.openapi import ResponseSpec
from msgspec import Struct


class CommonErrorSchema(Struct):
    """Used for all errors."""

    code: str
    extra: dict[str, Any] | None = None


def success_spec[Response_T](
    description: str,
    container: type[Response_T] | None = None,
) -> ResponseSpec:
    """Return response spec with success and data."""
    return ResponseSpec(
        description=description,
        data_container=container,
    )


def error_spec(description: str) -> ResponseSpec:
    """Return response spec with error schema."""
    return ResponseSpec(
        description=description,
        data_container=CommonErrorSchema,
        generate_examples=False,
        examples=[],
    )


RESPONSE_BAD_REQUEST: Final = MappingProxyType(
    {400: error_spec("Bad values supplied, check docs.")},
)
RESPONSE_NOT_AUTHENTICATED: Final = MappingProxyType(
    {401: error_spec("Not authenticated.")},
)
RESPONSE_FORBIDDEN: Final = MappingProxyType(
    {403: error_spec("Forbidden.")},
)
RESPONSE_NOT_FOUND: Final = MappingProxyType(
    {404: error_spec("Not found.")},
)
RESPONSE_NOT_AUTH_AND_FORBIDDEN: Final = MappingProxyType(
    {**RESPONSE_NOT_AUTHENTICATED, **RESPONSE_FORBIDDEN},
)
