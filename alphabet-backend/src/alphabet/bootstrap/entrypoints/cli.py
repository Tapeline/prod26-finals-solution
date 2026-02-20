import asyncio
import sys
from typing import override

import click
from dishka import (
    AsyncContainer,
    Provider,
    Scope,
    make_async_container,
    provide,
)

from alphabet.access.application.interactors import CreateUser, CreateUserDTO
from alphabet.access.application.interfaces import (
    UserRepository,
)
from alphabet.access.domain import ApproverGroup
from alphabet.access.infrastructure.repos import SqlUserRepository
from alphabet.bootstrap.config import service_config_loader
from alphabet.bootstrap.di.access import AccessDIProvider
from alphabet.bootstrap.di.shared import (
    ConfigDIProvider,
    SqlTransactionDIProvider,
)
from alphabet.shared.application.idp import ExtUserIdentity, UserIdProvider
from alphabet.shared.application.user import UserReader
from alphabet.shared.config import Config
from alphabet.shared.domain.user import IapId, Role, User, UserId
from alphabet.shared.infrastructure.transaction import SqlTransactionManager

cli_user = User(
    id=UserId("cli"),
    email="cli@localhost",
    iap_id=IapId("cli"),
    role=Role.ADMIN,
)


class CLIUserRepository(UserRepository, UserReader):
    def __init__(self, tx: SqlTransactionManager) -> None:
        self.sql_repo = SqlUserRepository(tx)

    @override
    async def get_by_id(self, user_id: UserId) -> User | None:
        if user_id == "cli":
            return cli_user
        return await self.sql_repo.get_by_id(user_id)

    @override
    async def get_by_iap_id(self, iap_id: IapId) -> User | None:
        if iap_id == "cli":
            return cli_user
        return await self.sql_repo.get_by_iap_id(iap_id)

    @override
    async def create(self, user: User) -> None:
        if user is not cli_user:
            await self.sql_repo.create(user)

    @override
    async def save(self, user: User) -> None:
        if user is not cli_user:
            await self.sql_repo.save(user)

    @override
    async def load_approver_group(
        self,
        user_id: UserId,
    ) -> ApproverGroup | None:
        if user_id == "cli":
            return None
        return await self.sql_repo.load_approver_group(user_id)

    @override
    async def store_approver_group(
        self,
        user_id: UserId,
        approver_group: ApproverGroup,
    ) -> None:
        if user_id != "cli":
            await self.sql_repo.store_approver_group(user_id, approver_group)

    @override
    async def get_by_email(self, email: str) -> User | None:
        if email == "cli@localhost":
            return cli_user
        return await self.sql_repo.get_by_email(email)


class CLIIdProvider(UserIdProvider):
    @override
    def get_user(self) -> ExtUserIdentity | None:
        return self.require_user()

    @override
    def require_user(self) -> ExtUserIdentity:
        return ExtUserIdentity(
            iap_id=IapId("cli"),
            email="cli@localhost",
        )


class CLIProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_identity(self) -> UserIdProvider:
        return CLIIdProvider()

    cli_user_repo = provide(
        CLIUserRepository,
        provides=UserRepository,
        scope=Scope.REQUEST,
        override=True,
    )


def _create_container(config: Config) -> AsyncContainer:
    return make_async_container(
        ConfigDIProvider(),
        SqlTransactionDIProvider(),
        AccessDIProvider(),
        CLIProvider(),
        context={
            Config: config,
        },
    )


@click.group()
def cli() -> None: ...


@cli.command()
@click.argument(
    "role",
    type=click.Choice(
        ["admin", "experimenter", "approver", "viewer"],
        case_sensitive=False,
    ),
    required=True,
)
@click.argument("email")
def create_user(email: str, role: str) -> None:
    role = {
        "admin": Role.ADMIN,
        "experimenter": Role.EXPERIMENTER,
        "approver": Role.APPROVER,
        "viewer": Role.VIEWER,
    }[role]
    asyncio.run(create_user_seq(email, role))


async def create_user_seq(email: str, role: Role) -> None:
    click.echo("Инициализация зависимостей")
    config = service_config_loader.load()
    container = _create_container(config)
    async with container() as request_container:
        interactor = await request_container.get(CreateUser)
        click.echo("Создание пользователя")
        user = await interactor(CreateUserDTO(email, role))
        click.secho("Пользователь создан:", fg="green")
        click.echo(f"Id:    {user.id}")
        click.echo(f"Email: {user.email}")
        click.echo(f"Роль:  {user.role}")
        click.echo(
            "Для активации, войдите в IAP и перейдите по ссылке:\n"
            "http://localhost:8080/api/v1/accounts/activate",
        )


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    cli()


if __name__ == "__main__":
    main()
