from collections.abc import Sequence

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, MediaType, Response, get
from litestar.plugins.prometheus import PrometheusController
from litestar.response import Template

from alphabet.decisions.application import ExperimentStorage, FlagStorage
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
