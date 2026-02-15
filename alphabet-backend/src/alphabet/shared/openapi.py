from collections.abc import Sequence
from typing import Final

from litestar.openapi.spec import SecurityScheme

security_components: Final = {
    "iap_user_id": SecurityScheme(
        type="apiKey",
        name="X-User-Id",
        security_scheme_in="header",
    ),
    "iap_user_email": SecurityScheme(
        type="apiKey",
        name="X-User-Email",
        security_scheme_in="header",
    ),
}

security_defs: Final[  # noqa: WPS234
    Sequence[dict[str, list[str]]] | None
] = ({"iap_user_id": [], "iap_user_email": []},)
