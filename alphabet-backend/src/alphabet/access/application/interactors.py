from typing import final

from structlog import getLogger

from alphabet.access.application.exceptions import (
    AlreadyActivated,
    CannotSetReviewRulesForNonExperimenter,
    EmailNotRegistered,
    NoSuchApproverGroup,
)
from alphabet.access.application.interfaces import (
    UserRepository,
)
from alphabet.access.domain import ApproverGroup
from alphabet.shared.application.idp import UserIdProvider
from alphabet.shared.application.transaction import TransactionManager
from alphabet.shared.application.user import (
    UserNotFound,
    UserReader,
    require_any_user,
    require_user_with_role,
)
from alphabet.shared.commons import dto, interactor
from alphabet.shared.domain.user import Role, User, UserId
from alphabet.shared.uuid import generate_id

logger = getLogger(__name__)


@final
@interactor
class ActivateUser:
    idp: UserIdProvider
    users: UserRepository
    user_reader: UserReader
    tx: TransactionManager

    async def __call__(self) -> User:
        async with self.tx:
            identity = self.idp.require_user()
            if await self.user_reader.get_by_iap_id(identity.iap_id):
                raise AlreadyActivated
            user = await self.users.get_by_email(identity.email)
            if not user:
                raise EmailNotRegistered
            if user.is_active:
                logger.info(
                    "Tried to activate existing user",
                    user_role=user.role,
                    user_id=user.id,
                    old_iap=user.iap_id,
                    new_iap=identity.iap_id,
                )
                raise AlreadyActivated
            logger.info(
                "Activated user",
                user_role=user.role,
                user_id=user.id,
                user_email=user.email,
                user_iap=identity.iap_id,
            )
            user.iap_id = identity.iap_id
            await self.users.save(user)
            return user


@dto
class CreateUserDTO:
    email: str
    role: Role


@final
@interactor
class CreateUser:
    idp: UserIdProvider
    user_reader: UserReader
    users: UserRepository
    tx: TransactionManager

    async def __call__(self, dto: CreateUserDTO) -> User:
        async with self.tx:
            await require_user_with_role(self, {Role.ADMIN})
            user = User(
                id=generate_id(UserId),
                iap_id=None,
                email=dto.email,
                role=dto.role,
            )
            await self.users.create(user)
            return user


@final
@dto
class UpdateUserDTO:
    new_email: str | None
    new_role: Role | None


@final
@interactor
class UpdateUser:
    idp: UserIdProvider
    user_reader: UserReader
    users: UserRepository
    tx: TransactionManager

    async def __call__(self, target: UserId, dto: UpdateUserDTO) -> User:
        async with self.tx:
            await require_user_with_role(self, {Role.ADMIN})
            user = await self.users.get_by_id(target)
            if not user:
                raise UserNotFound
            if dto.new_email:
                user.email = dto.new_email
            if dto.new_role:
                logger.info(
                    "Changed role of user", user_id=user.id,
                    old_role=user.role, new_role=dto.new_role
                )
                user.role = dto.new_role
            await self.users.save(user)
            return user


@final
@dto
class NewReviewRulesDTO:
    threshold: int
    approvers: list[UserId]


@final
@interactor
class SetReviewRules:
    idp: UserIdProvider
    user_reader: UserReader
    users: UserRepository
    tx: TransactionManager

    async def __call__(
        self,
        target: UserId,
        dto: NewReviewRulesDTO,
    ) -> ApproverGroup:
        group = ApproverGroup(dto.approvers, dto.threshold)
        # ? do we need to validate whether approver ids exist?
        async with self.tx:
            await require_user_with_role(self, {Role.ADMIN})
            user = await self.users.get_by_id(target)
            if not user:
                raise UserNotFound
            if user.role != Role.EXPERIMENTER:
                raise CannotSetReviewRulesForNonExperimenter
            await self.users.store_approver_group(target, group)
            return group


@final
@interactor
class ReadReviewRules:
    idp: UserIdProvider
    user_reader: UserReader
    users: UserRepository
    tx: TransactionManager

    async def __call__(self, target: UserId) -> ApproverGroup:
        self.idp.require_user()
        async with self.tx:
            user = await self.users.get_by_id(target)
            if not user:
                raise UserNotFound
            if user.role != Role.EXPERIMENTER:
                raise NoSuchApproverGroup
            group = await self.users.load_approver_group(target)
            if not group:
                raise NoSuchApproverGroup
            return group


@final
@interactor
class ReadUserById:
    idp: UserIdProvider
    users: UserRepository
    tx: TransactionManager

    async def __call__(self, target: UserId) -> User:
        self.idp.require_user()
        async with self.tx:
            user = await self.users.get_by_id(target)
            if not user:
                raise UserNotFound
            return user


@final
@interactor
class ReadUserByEmail:
    idp: UserIdProvider
    users: UserRepository
    tx: TransactionManager

    async def __call__(self, email: str) -> User:
        self.idp.require_user()
        async with self.tx:
            user = await self.users.get_by_email(email)
            if not user:
                raise EmailNotRegistered
            return user


@final
@interactor
class ReadMe:
    idp: UserIdProvider
    user_reader: UserReader
    tx: TransactionManager

    async def __call__(self) -> User:
        async with self.tx:
            return await require_any_user(self)
