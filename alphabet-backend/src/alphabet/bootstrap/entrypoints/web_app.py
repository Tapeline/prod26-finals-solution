import asyncio
from asyncio import Task
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from dishka import AsyncContainer, make_async_container
from dishka.integrations.litestar import LitestarProvider
from dishka.integrations.litestar import setup_dishka as litestar_setup_dishka
from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.middleware import DefineMiddleware
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import (
    RapidocRenderPlugin,
    ScalarRenderPlugin,
    SwaggerRenderPlugin,
    YamlRenderPlugin,
)
from litestar.openapi.spec import Components
from litestar.template import TemplateConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.static_files.config import StaticFilesConfig
from litestar.plugins.prometheus import PrometheusConfig, PrometheusController
from structlog import getLogger

from alphabet.access.presentation.controller import AccessController
from alphabet.access.presentation.errors import access_err_handlers
from alphabet.bootstrap.config import service_config_loader
from alphabet.bootstrap.di.access import AccessDIProvider
from alphabet.bootstrap.di.decisions import DecisionsDIProvider
from alphabet.bootstrap.di.events import EventsDIProvider
from alphabet.bootstrap.di.experiments import FlagsExperimentsDIProvider
from alphabet.bootstrap.di.guardrails import GuardrailsDIProvider
from alphabet.bootstrap.di.insights import InsightsDIProvider
from alphabet.bootstrap.di.metrics import MetricsDIProvider
from alphabet.bootstrap.di.notifications import (
    NotificationsDIProvider,
    NotificationsWorkerDIProvider,
)
from alphabet.bootstrap.di.shared import (
    ClickHouseDIProvider,
    ConfigDIProvider,
    IdentityProviderDIProvider,
    MessageQueueErsatzDIProvider,
    SqlTransactionDIProvider,
    TimeDIProvider,
    ValkeyDIProvider,
)
from alphabet.bootstrap.html_server import serve_frontend
from alphabet.bootstrap.live_ready import LivenessReadinessController
from alphabet.bootstrap.logging import get_structlog_plugin_def
from alphabet.decisions.application import (
    ResolutionRepository,
    WarmUpStorages, AssignmentStore,
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
        FlagsExperimentsDIProvider(),
        MetricsDIProvider(),
        DecisionsDIProvider(),
        EventsDIProvider(),
        GuardrailsDIProvider(),
        NotificationsDIProvider(),
        NotificationsWorkerDIProvider(),
        InsightsDIProvider(),
        context={
            Config: config,
        },
    )


class CustomPrometheusController(PrometheusController):
    path = "/_internal/metrics"


def create_app() -> Litestar:
    """Bootstrap the app."""
    config = service_config_loader.load()
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
        static_files_config=[StaticFilesConfig(
            directories=["static"], path="/_static", name="static"
        )]
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
