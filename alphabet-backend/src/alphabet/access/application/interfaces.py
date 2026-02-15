from abc import abstractmethod
from typing import Protocol

from alphabet.access.domain import ApproverGroup, IapId, User, UserId
from alphabet.shared.commons import dto


class UserRepository(Protocol):
    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def create(self, user: User) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, user: User) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_iap_id(self, iap_id: IapId) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def load_approver_group(
        self,
        user_id: UserId,
    ) -> ApproverGroup | None:
        raise NotImplementedError

    @abstractmethod
    async def store_approver_group(
        self,
        user_id: UserId,
        approver_group: ApproverGroup,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        raise NotImplementedError


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
