from collections.abc import AsyncIterable

import clickhouse_connect
from clickhouse_connect.driver import AsyncClient
from dishka import (
    AnyOf,
    AsyncContainer,
    Provider,
    Scope,
    WithParents,
    from_context,
    provide,
)
from litestar import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from alphabet.bootstrap.instant_notifier import InstantNotifier
from alphabet.experiments.application.interfaces import (
    ExperimentChangeNotifier,
    FlagChangeNotifier,
)
from alphabet.guardrails.application.interfaces import GuardrailNotifier
from alphabet.shared.application.idp import UserIdProvider
from alphabet.shared.application.time import TimeProvider
from alphabet.shared.config import AppConfig, Config
from alphabet.shared.infrastructure.connection import new_session_maker
from alphabet.shared.infrastructure.time import DefaultTimeProvider
from alphabet.shared.infrastructure.transaction import SqlTransactionManager
from alphabet.shared.infrastructure.valkey_connection import (
    create_valkey_client,
)
from alphabet.shared.presentation.idp import HeaderIdP
from alphabet.subject_events.application.interfaces import (
    EventTypeChangeNotifier,
)


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

    @provide(scope=Scope.APP)
    def provide_app_config(self, config: Config) -> AppConfig:
        return config.app


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
        return DefaultTimeProvider()


class MessageQueueErsatzDIProvider(Provider):
    @provide(scope=Scope.APP)
    def provide_mq_ersatz(
        self,
        container: AsyncContainer,
    ) -> AnyOf[
        ExperimentChangeNotifier,
        FlagChangeNotifier,
        EventTypeChangeNotifier,
        GuardrailNotifier,
        InstantNotifier,
    ]:
        return InstantNotifier(container)


class ValkeyDIProvider(Provider):
    @provide(scope=Scope.APP)
    async def provide_client(self, config: Config) -> Redis:
        return await create_valkey_client(config.valkey)


class ClickHouseDIProvider(Provider):
    @provide(scope=Scope.APP)
    async def provide_client(
        self,
        config: Config,
    ) -> AsyncIterable[WithParents[AsyncClient]]:
        async with await clickhouse_connect.get_async_client(
            host=config.clickhouse.host,
            port=config.clickhouse.port,
            database=config.clickhouse.database,
            username=config.clickhouse.username,
            password=config.clickhouse.password,
        ) as client:
            yield client
