from collections.abc import Sequence
from pathlib import Path

from clickhouse_connect.driver import AsyncClient
from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, MediaType, Response, get, post
from litestar.plugins.prometheus import PrometheusController
from litestar.response import Template
from redis.asyncio import Redis
from sqlalchemy import text
from msgspec import Struct

from alphabet.access.application.interfaces import UserRepository
from alphabet.access.infrastructure.repos import SqlUserRepository
from alphabet.access.presentation.controller import UserResponse
from alphabet.decisions.application import (
    ExperimentStorage,
    FlagStorage,
    WarmUpStorages,
)
from alphabet.shared.domain.user import IapId, Role, User, UserId
from alphabet.shared.infrastructure.transaction import SqlTransactionManager
from alphabet.subject_events.application.interactors import WarmUpEventTypes
from alphabet.subject_events.application.interfaces import EventTypeCache


@get("/", include_in_schema=False)
async def serve_frontend() -> Template:
    """Serves the frontend!"""
    return Template(
        template_name="index.html",
    )


class CustomPrometheusController(PrometheusController):
    path = "/_internal/metrics"
    tags: Sequence[str] | None = ("Internal service",)


class LivenessReadinessController(Controller):
    path = ""
    tags: Sequence[str] | None = ("Internal service",)

    @get("/ready", media_type=MediaType.TEXT)
    @inject
    async def is_ready(
        self,
        experiment_cache: FromDishka[ExperimentStorage],
        flag_cache: FromDishka[FlagStorage],
        event_type_cache: FromDishka[EventTypeCache],
    ) -> Response[str]:
        if not all(
            (
                experiment_cache.is_ready(),
                flag_cache.is_ready(),
                event_type_cache.is_ready(),
            ),
        ):
            return Response(
                status_code=503,
                content="not ready",
            )
        return Response(status_code=200, content="ready")

    @get("/health", media_type=MediaType.TEXT)
    async def health(self) -> Response[str]:
        return Response(status_code=200, content="healthy")


class TestNewUserRequest(Struct):
    id: str
    email: str
    role: Role
    iap_id: str | None


# This is wrong in so many ways, but is so convenient for testing :)

class TestDataManagerController(Controller):
    path = "/_internal/data"

    @post("/clear")
    @inject
    async def clear_data(
        self,
        click: FromDishka[AsyncClient],
        redis: FromDishka[Redis],
        tx: FromDishka[SqlTransactionManager],
        event_cache: FromDishka[EventTypeCache],
        flag_cache: FromDishka[FlagStorage],
        experiment_cache: FromDishka[ExperimentStorage],
    ) -> str:
        await click.command("TRUNCATE TABLE events")
        await click.command("TRUNCATE TABLE discarded_events")
        await click.command("TRUNCATE TABLE duplicate_events")
        await click.command("TRUNCATE TABLE conflict_resolutions")
        await click.command("TRUNCATE TABLE variant_assignments")
        await redis.flushdb()
        async with tx:
            await tx.session.execute(
                text("DELETE FROM prepared_notifications"),
            )
            await tx.session.execute(text("DELETE FROM notification_rules"))
            await tx.session.execute(text("DELETE FROM audit_log"))
            await tx.session.execute(text("DELETE FROM guard_rules"))
            await tx.session.execute(text("DELETE FROM reports"))
            await tx.session.execute(text("DELETE FROM metrics"))
            await tx.session.execute(text("DELETE FROM event_types"))
            await tx.session.execute(text("DELETE FROM review_decisions"))
            await tx.session.execute(text("DELETE FROM approvals"))
            await tx.session.execute(text("DELETE FROM experiments_latest"))
            await tx.session.execute(text("DELETE FROM experiments_history"))
            await tx.session.execute(text("DELETE FROM flags"))
            await tx.session.execute(text("DELETE FROM assigned_approvers"))
            await tx.session.execute(text("DELETE FROM users"))
            await tx.session.commit()
        event_cache.clear()
        experiment_cache.clear()
        flag_cache.clear()
        return "cleared"

    @post("/seed")
    @inject
    async def seed_test_data(
        self,
        tx: FromDishka[SqlTransactionManager],
        event_cache: FromDishka[EventTypeCache],
        warmup_events: FromDishka[WarmUpEventTypes],
        warmup_storages: FromDishka[WarmUpStorages],
        flag_cache: FromDishka[FlagStorage],
        experiment_cache: FromDishka[ExperimentStorage],
    ) -> str:
        async with tx:
            await tx.session.execute(
                text(Path("src/test_data.sql").read_text()),
            )
            await tx.session.commit()
        event_cache.clear()
        flag_cache.clear()
        experiment_cache.clear()
        await warmup_events()
        await warmup_storages()
        return "seeded"

    @post("new-user")
    @inject
    async def new_user(
        self,
        tx: FromDishka[SqlTransactionManager],
        repo: FromDishka[UserRepository],
        data: TestNewUserRequest
    ) -> UserResponse:
        user = User(
            id=UserId(data.id),
            email=data.email,
            role=data.role,
            iap_id=IapId(data.iap_id) if data.iap_id else None,
        )
        async with tx:
            await repo.create(user)
        return UserResponse.from_user(user)
