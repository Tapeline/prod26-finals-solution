from abc import abstractmethod
from typing import Protocol

from alphabet.shared.commons import dto
from alphabet.shared.domain.user import IapId


@dto
class ExtUserIdentity:
    iap_id: IapId
    email: str


class UserIdProvider(Protocol):
    @abstractmethod
    def get_user(self) -> ExtUserIdentity | None:
        raise NotImplementedError

    @abstractmethod
    def require_user(self) -> ExtUserIdentity:
        """Get or throw UserIsAnonymous."""
        raise NotImplementedError
