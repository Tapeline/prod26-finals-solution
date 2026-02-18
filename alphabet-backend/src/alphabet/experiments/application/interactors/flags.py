from typing import final

from alphabet.experiments.application.exceptions import NoSuchFlag
from alphabet.experiments.application.interfaces import (
    FlagChangeNotifier,
    FlagRepository,
)
from alphabet.experiments.domain.flags import FeatureFlag, FlagKey, FlagType
from alphabet.shared.application.idp import UserIdProvider
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.application.time import TimeProvider
from alphabet.shared.application.transaction import TransactionManager
from alphabet.shared.application.user import (
    UserReader,
    require_any_user,
    require_user_with_role,
)
from alphabet.shared.commons import dto, interactor
from alphabet.shared.domain.user import Role


@final
@dto
class CreateFlagDTO:
    key: FlagKey
    description: str
    type: FlagType
    default: str


@final
@interactor
class CreateFlag:
    idp: UserIdProvider
    user_reader: UserReader
    flags: FlagRepository
    time_provider: TimeProvider
    tx: TransactionManager
    notifier: FlagChangeNotifier

    async def __call__(self, dto: CreateFlagDTO) -> FeatureFlag:
        async with self.tx:
            user = await require_user_with_role(
                self,
                {Role.ADMIN, Role.EXPERIMENTER},
            )
            now = self.time_provider.now()
            flag = FeatureFlag.new(
                key=dto.key,
                description=dto.description,
                type=dto.type,
                default=dto.default,
                author_id=user.id,
                created_at=now,
                updated_at=now,
            )
            await self.flags.create(flag)
        await self.notifier.notify_flag_default_changed(flag.key, flag.default)
        return flag


@final
@interactor
class UpdateFlag:
    idp: UserIdProvider
    user_reader: UserReader
    flags: FlagRepository
    time_provider: TimeProvider
    tx: TransactionManager
    notifier: FlagChangeNotifier

    async def __call__(self, key: FlagKey, new_default: str) -> FeatureFlag:
        async with self.tx:
            await require_user_with_role(
                self,
                {Role.ADMIN, Role.EXPERIMENTER},
            )
            flag = await self.flags.get_by_key(key)
            if not flag:
                raise NoSuchFlag
            flag.default = new_default
            flag.updated_at = self.time_provider.now()
            await self.flags.save(flag)
        await self.notifier.notify_flag_default_changed(key, new_default)
        return flag


@final
@interactor
class ReadFlag:
    idp: UserIdProvider
    user_reader: UserReader
    flags: FlagRepository
    tx: TransactionManager

    async def __call__(self, key: FlagKey) -> FeatureFlag:
        async with self.tx:
            await require_any_user(self)
            flag = await self.flags.get_by_key(key)
            if not flag:
                raise NoSuchFlag
            return flag


@final
@interactor
class ReadAllFlags:
    idp: UserIdProvider
    user_reader: UserReader
    flags: FlagRepository
    tx: TransactionManager

    async def __call__(self, pagination: Pagination) -> list[FeatureFlag]:
        async with self.tx:
            await require_any_user(self)
            return await self.flags.all(pagination)
