from collections.abc import AsyncIterable

from dishka import Provider, Scope, WithParents, from_context, provide
from litestar import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from alphabet.shared.application.idp import UserIdProvider
from alphabet.shared.application.time import TimeProvider
from alphabet.shared.config import Config
from alphabet.shared.infrastructure.connection import new_session_maker
from alphabet.shared.infrastructure.time import DefaultNaiveTimeProvider
from alphabet.shared.infrastructure.transaction import SqlTransactionManager
from alphabet.shared.presentation.idp import HeaderIdP


class IdentityProviderDIProvider(Provider):
    # IdPDIP — xD
    @provide(scope=Scope.REQUEST)
    def provide_identity(
        self,
        request: Request,  # type: ignore[type-arg]
    ) -> UserIdProvider:
        return HeaderIdP(request)


class ConfigDIProvider(Provider):
    config = from_context(Config, scope=Scope.APP)


class SqlTransactionDIProvider(Provider):
    @provide(scope=Scope.APP)
    def get_session_maker(
        self,
        config: Config,
    ) -> async_sessionmaker[AsyncSession]:
        return new_session_maker(config.postgres)

    @provide(scope=Scope.REQUEST)
    async def get_transaction(
        self,
        session_maker: async_sessionmaker[AsyncSession],
    ) -> AsyncIterable[WithParents[SqlTransactionManager]]:
        async with session_maker() as session:
            yield SqlTransactionManager(session)


class TimeDIProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_time(self) -> TimeProvider:
        return DefaultNaiveTimeProvider()
