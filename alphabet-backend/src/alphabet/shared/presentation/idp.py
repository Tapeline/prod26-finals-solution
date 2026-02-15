from typing import override

import litestar

from alphabet.shared.application.idp import ExtUserIdentity, UserIdProvider
from alphabet.shared.domain.exceptions import NotAuthenticated
from alphabet.shared.domain.user import IapId


class HeaderIdP(UserIdProvider):
    def __init__(
        self,
        request: litestar.Request,  # type: ignore[type-arg]
    ) -> None:
        self.request = request

    @override
    def get_user(self) -> ExtUserIdentity | None:
        user_iap_id = self.request.headers.get("x-user-id")
        user_email = self.request.headers.get("x-user-email")
        if user_iap_id and user_email:
            return ExtUserIdentity(IapId(user_iap_id), user_email)
        return None

    @override
    def require_user(self) -> ExtUserIdentity:
        maybe_user = self.get_user()
        if not maybe_user:
            raise NotAuthenticated
        return maybe_user
