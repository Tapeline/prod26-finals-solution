from abc import abstractmethod
from typing import Protocol, final

from alphabet.shared.application.idp import UserIdProvider
from alphabet.shared.domain.exceptions import AppException, NotAllowed
from alphabet.shared.domain.user import IapId, Role, User


class UserReader(Protocol):
    @abstractmethod
    async def get_by_iap_id(self, iap_id: IapId) -> User | None:
        raise NotImplementedError


class WithUserReaderAndIdP(Protocol):
    @property
    def user_reader(self) -> UserReader: ...
    @property
    def idp(self) -> UserIdProvider: ...


async def require_user_with_role(
    interactor: WithUserReaderAndIdP,
    allowed_roles: set[Role],
) -> User:
    user = await require_any_user(interactor)
    if user.role not in allowed_roles:
        raise NotAllowed
    return user


async def require_any_user(
    interactor: WithUserReaderAndIdP,
) -> User:
    identity = interactor.idp.require_user()
    user = await interactor.user_reader.get_by_iap_id(identity.iap_id)
    if not user:
        raise UserNotFound
    return user


@final
class UserNotFound(AppException):
    text = "User not found. Contact your administrator"
