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
from litestar.plugins.prometheus import PrometheusConfig, PrometheusController
from structlog import getLogger

from alphabet.access.presentation.controller import AccessController
from alphabet.access.presentation.errors import access_err_handlers
from alphabet.bootstrap.config import service_config_loader
from alphabet.bootstrap.di.access import AccessDIProvider
from alphabet.bootstrap.di.shared import (
    ConfigDIProvider,
    IdentityProviderDIProvider,
    SqlTransactionDIProvider,
)
from alphabet.bootstrap.logging import get_structlog_plugin_def
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

logger = getLogger(__name__)


def _create_container(config: Config) -> AsyncContainer:
    return make_async_container(
        LitestarProvider(),
        ConfigDIProvider(),
        SqlTransactionDIProvider(),
        IdentityProviderDIProvider(),
        AccessDIProvider(),
        context={
            Config: config,
        },
    )


def create_app() -> Litestar:
    """Bootstrap the app."""
    config = service_config_loader.load()
    logger.info("Bootstrapping the application")
    container = _create_container(config)

    prometheus_config = PrometheusConfig(
        app_name="alphabet",
        group_path=True,
        exclude=["/metrics"],
    )

    litestar_app = Litestar(
        debug=config.is_debug,
        route_handlers=[
            AccessController,
            PrometheusController,
        ],
        middleware=[
            DefineMiddleware(RequestIdMiddleware),
            prometheus_config.middleware,
        ],
        exception_handlers=gen_handler_mapping(  # type: ignore[arg-type]
            {
                **access_err_handlers,  # type: ignore[dict-item]
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
    )
    litestar_setup_dishka(container, litestar_app)
    logger.info("All good to go")
    return litestar_app
