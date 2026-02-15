import uuid
from typing import Final, override

import structlog
from litestar.enums import ScopeType
from litestar.middleware import AbstractMiddleware
from litestar.types import Receive, Scope, Send

logger = structlog.getLogger(__name__)

_ENRICHED_METHODS: Final = frozenset(
    ("GET", "POST", "PATCH", "PUT", "DELETE"),
)


class RequestIdMiddleware(AbstractMiddleware):
    """Adds UUID for each request."""

    @override
    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != ScopeType.HTTP:
            await self.app(scope, receive, send)
            return
        if scope["method"] not in _ENRICHED_METHODS:
            await self.app(scope, receive, send)
            return
        uid = str(uuid.uuid4())
        with structlog.contextvars.bound_contextvars(request_id=uid):
            await self.app(scope, receive, send)
