from litestar import Controller, get, Response, MediaType
from dishka.integrations.litestar import inject
from dishka import FromDishka

from alphabet.decisions.application import ExperimentStorage, FlagStorage
from alphabet.subject_events.application.interfaces import EventTypeCache


class LivenessReadinessController(Controller):
    path = ""

    @get(
        "/ready",
        media_type=MediaType.TEXT
    )
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
                event_type_cache.is_ready()
            )
        ):
            return Response(
                status_code=503,
                content="not ready",
            )
        else:
            return Response(
                status_code=200,
                content="ready"
            )

    @get(
        "/health",
        media_type=MediaType.TEXT
    )
    async def health(self) -> Response[str]:
        return Response(status_code=200, content="healthy")
