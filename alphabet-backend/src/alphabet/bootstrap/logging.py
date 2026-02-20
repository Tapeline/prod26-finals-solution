# from https://github.com/Tapeline/Fastscaffold

import logging

import structlog
from litestar.logging import StructLoggingConfig
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin

shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.StackInfoRenderer(),
    structlog.processors.add_log_level,
    structlog.dev.set_exc_info,
]


def setup_processors(
    *,
    use_json: bool = False,
) -> list[structlog.types.Processor]:
    if use_json:
        return [
            *shared_processors,  # type: ignore[list-item]
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    return [
        *shared_processors,  # type: ignore[list-item]
        structlog.processors.TimeStamper(
            fmt="%Y-%m-%d %H:%M:%S",
            utc=False,
        ),
        structlog.dev.ConsoleRenderer(),
    ]


def configure_structlog(*, use_json: bool = False) -> None:
    structlog.configure(
        processors=setup_processors(use_json=use_json),
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


def get_structlog_plugin_def(*, use_json: bool = False) -> StructlogPlugin:
    return StructlogPlugin(
        StructlogConfig(
            StructLoggingConfig(
                processors=setup_processors(use_json=use_json),
                logger_factory=structlog.PrintLoggerFactory(),
            ),
        ),
    )
