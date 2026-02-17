from collections.abc import Sequence

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, post
from msgspec import Struct

from alphabet.decisions.application import MakeDecision


class GetFlagsRequest(Struct):
    subject_id: str
    attributes: dict[str, str]
    flags: list[str]


class DecisionSchema(Struct):
    id: str
    value: str
    experiment_id: str | None


class GetFlagsResponse(Struct):
    flags: dict[str, DecisionSchema]


class DecisionsController(Controller):
    path = "/api/v1/decisions"
    tags: Sequence[str] | None = ("Decisions",)

    @post(
        path="/get-flags",
    )
    @inject
    async def get_flags(
        self,
        data: GetFlagsRequest,
        interactor: FromDishka[MakeDecision],
    ) -> GetFlagsResponse:
        decisions = await interactor(
            data.subject_id,
            data.attributes,
            data.flags,
        )
        return GetFlagsResponse(
            {
                decision.flag_key: DecisionSchema(
                    id=decision.id,
                    value=decision.value,
                    experiment_id=decision.experiment_id,
                )
                for decision in decisions
            },
        )
