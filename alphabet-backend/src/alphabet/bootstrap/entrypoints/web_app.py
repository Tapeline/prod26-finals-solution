import asyncio
import logging
from asyncio import Task
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import uvicorn
from asgi_monitor.logging.uvicorn import build_uvicorn_log_config
from dishka import AsyncContainer, make_async_container
from dishka.integrations.litestar import LitestarProvider
from dishka.integrations.litestar import setup_dishka as litestar_setup_dishka
from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.middleware import DefineMiddleware
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import (
    RapidocRenderPlugin,
    ScalarRenderPlugin,
    SwaggerRenderPlugin,
    YamlRenderPlugin,
)
from litestar.openapi.spec import Components, ExternalDocumentation
from litestar.plugins.prometheus import PrometheusConfig
from litestar.static_files.config import StaticFilesConfig
from litestar.template import TemplateConfig
from structlog import getLogger

from alphabet.access.presentation.controller import (
    AccessController,
    internal_create_new_user,
)
from alphabet.access.presentation.errors import access_err_handlers
from alphabet.bootstrap.config import service_config_loader
from alphabet.bootstrap.di.access import AccessDIProvider
from alphabet.bootstrap.di.decisions import get_decisions_providers
from alphabet.bootstrap.di.events import EventsDIProvider
from alphabet.bootstrap.di.experiments import get_experiments_providers
from alphabet.bootstrap.di.guardrails import get_guardrails_providers
from alphabet.bootstrap.di.insights import InsightsDIProvider
from alphabet.bootstrap.di.metrics import get_metrics_providers
from alphabet.bootstrap.di.notifications import get_notifications_providers
from alphabet.bootstrap.di.shared import (
    ClickHouseDIProvider,
    ConfigDIProvider,
    IdentityProviderDIProvider,
    MessageQueueErsatzDIProvider,
    SqlTransactionDIProvider,
    TimeDIProvider,
    ValkeyDIProvider,
)
from alphabet.bootstrap.logging import get_structlog_plugin_def
from alphabet.bootstrap.service_endpoints import (
    CustomPrometheusController,
    LivenessReadinessController,
    serve_frontend,
)
from alphabet.decisions.application import (
    AssignmentStore,
    ResolutionRepository,
    WarmUpStorages,
)
from alphabet.decisions.presentation import DecisionsController
from alphabet.experiments.presentation.errors import (
    flags_experiments_err_handlers,
)
from alphabet.experiments.presentation.experiments import ExperimentsController
from alphabet.experiments.presentation.flags import FlagsController
from alphabet.guardrails.presentation.controller import GuardRulesController
from alphabet.guardrails.presentation.errors import guardrail_err_handlers
from alphabet.insights.presentation import InsightsController
from alphabet.metrics.presentation.errors import metrics_err_handlers
from alphabet.metrics.presentation.metrics import MetricsController
from alphabet.metrics.presentation.reports import ReportsController
from alphabet.notifications.presentation.controller import (
    NotificationRulesController,
)
from alphabet.notifications.presentation.errors import (
    notification_err_handlers,
)
from alphabet.shared.config import Config
from alphabet.shared.domain.exceptions import NotAuthenticated
from alphabet.shared.presentation.framework.errors import (
    gen_handler_mapping,
    infer_code,
)
from alphabet.shared.presentation.framework.middlewares import (
    RequestIdMiddleware,
)
from alphabet.shared.presentation.openapi import security_components
from alphabet.subject_events.application.interactors import WarmUpEventTypes
from alphabet.subject_events.application.interfaces import EventStore
from alphabet.subject_events.presentation.controller import EventsController
from alphabet.subject_events.presentation.errors import (
    subject_events_err_handlers,
)

logger = getLogger(__name__)

tasks: list[Task[Any]] = []


def _create_container(config: Config) -> AsyncContainer:
    return make_async_container(
        MessageQueueErsatzDIProvider(),
        LitestarProvider(),
        ConfigDIProvider(),
        SqlTransactionDIProvider(),
        IdentityProviderDIProvider(),
        TimeDIProvider(),
        ValkeyDIProvider(),
        ClickHouseDIProvider(),
        AccessDIProvider(),
        *get_decisions_providers(),
        EventsDIProvider(),
        *get_experiments_providers(),
        *get_guardrails_providers(),
        InsightsDIProvider(),
        *get_metrics_providers(),
        *get_notifications_providers(),
        context={
            Config: config,
        },
    )


def create_app(config: Config) -> Litestar:
    """Bootstrap the app."""
    logger.info("Bootstrapping the application")
    container = _create_container(config)

    prometheus_config = PrometheusConfig(
        app_name="alphabet",
        group_path=True,
        exclude=["/_internal/metrics"],
    )
    litestar_app = Litestar(
        debug=config.is_debug,
        route_handlers=[
            AccessController,
            FlagsController,
            ExperimentsController,
            DecisionsController,
            EventsController,
            MetricsController,
            ReportsController,
            GuardRulesController,
            NotificationRulesController,
            InsightsController,
            LivenessReadinessController,
            CustomPrometheusController,
            internal_create_new_user,
            serve_frontend,
        ],
        middleware=[
            prometheus_config.middleware,
            DefineMiddleware(RequestIdMiddleware),
        ],
        exception_handlers=gen_handler_mapping(  # type: ignore[arg-type]
            {
                **access_err_handlers,  # type: ignore[dict-item]
                **flags_experiments_err_handlers,
                **subject_events_err_handlers,  # type: ignore[dict-item]
                **metrics_err_handlers,
                **guardrail_err_handlers,  # type: ignore[dict-item]
                **notification_err_handlers,  # type: ignore[dict-item]
                NotAuthenticated: (401, infer_code),
            },
        ),
        openapi_config=OpenAPIConfig(
            title="Alphabet",
            description="A/B testing platform API",
            version="0.1.0",
            render_plugins=[
                SwaggerRenderPlugin(),
                RapidocRenderPlugin(),
                ScalarRenderPlugin(),
                YamlRenderPlugin(),
            ],
            path="/docs",
            components=Components(
                security_schemes=security_components,  # type: ignore[arg-type]
            ),
            external_docs=ExternalDocumentation(
                url="https://yt-redstone-mail-e7ec37.pages.prodcontest.com/",
                description="Developer's documentation",
            ),
        ),
        cors_config=CORSConfig(allow_origins=["*"]),
        plugins=[
            get_structlog_plugin_def(use_json=config.logging.use_json),
        ],
        on_startup=[
            warmup_decision_caches(container),
            warmup_event_types(container),
            start_event_store_periodic_flush(container),
            start_resolution_repo_periodic_flush(container),
            start_assignment_repo_periodic_flush(container),
        ],
        template_config=TemplateConfig(
            directory=Path("templates"),
            engine=JinjaTemplateEngine,
        ),
        static_files_config=[
            StaticFilesConfig(
                directories=["static"],
                path="/_static",
                name="static",
            ),
        ],
    )
    litestar_setup_dishka(container, litestar_app)
    logger.info("All good to go")
    return litestar_app


def warmup_decision_caches(
    container: AsyncContainer,
) -> Callable[[], Coroutine[Any, Any, None]]:
    async def warmup() -> None:
        async with container() as nested:
            interactor = await nested.get(WarmUpStorages)
            await interactor()

    return warmup


def warmup_event_types(
    container: AsyncContainer,
) -> Callable[[], Coroutine[Any, Any, None]]:
    async def warmup() -> None:
        async with container() as nested:
            interactor = await nested.get(WarmUpEventTypes)
            await interactor()

    return warmup


def start_event_store_periodic_flush(
    container: AsyncContainer,
) -> Callable[[], Coroutine[Any, Any, None]]:
    async def start() -> None:
        async with container() as nested:
            store = await nested.get(EventStore)
            tasks.append(asyncio.create_task(store.periodic_flush_routine()))

    return start


def start_resolution_repo_periodic_flush(
    container: AsyncContainer,
) -> Callable[[], Coroutine[Any, Any, None]]:
    async def start() -> None:
        async with container() as nested:
            store = await nested.get(ResolutionRepository)
            tasks.append(asyncio.create_task(store.periodic_flush_routine()))

    return start


def start_assignment_repo_periodic_flush(
    container: AsyncContainer,
) -> Callable[[], Coroutine[Any, Any, None]]:
    async def start() -> None:
        async with container() as nested:
            store = await nested.get(AssignmentStore)
            tasks.append(asyncio.create_task(store.periodic_flush_routine()))

    return start


def main() -> None:
    config = service_config_loader.load()
    if config.logging.use_json:
        log_config = build_uvicorn_log_config(
            level=logging.INFO,
            json_format=True,
            include_trace=False,
        )
    else:
        log_config = uvicorn.config.LOGGING_CONFIG
    app = create_app(config)
    uvicorn.run(
        app=app,
        host=config.server.host,
        port=config.server.port,
        log_config=log_config,
    )


if __name__ == "__main__":
    main()
