from abc import abstractmethod
from typing import Protocol

from alphabet.access.domain import ApproverGroup
from alphabet.shared.domain.user import User, UserId


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
