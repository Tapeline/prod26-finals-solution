from collections.abc import Sequence

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, post, get
from msgspec import Struct

from alphabet.decisions.application import (
    MakeDecision,
    ReadConflictsByExperiment, ReadConflictsByDomain,
)
from alphabet.experiments.domain.experiment import (
    ConflictPolicy,
    ExperimentId, ConflictDomain,
)
from alphabet.shared.presentation.framework.openapi import (
    success_spec,
    RESPONSE_NOT_AUTHENTICATED,
)
from alphabet.shared.presentation.openapi import security_defs


class GetFlagsRequest(Struct):
    subject_id: str
    attributes: dict[str, str]
    flags: list[str]


class DecisionSchema(Struct):
    id: str
    value: str
    experiment_id: str | None


class GetFlagsResponse(Struct):
    flags: dict[str, DecisionSchema | None]


class ConflictsByExperimentResponse(Struct):
    wins: dict[ConflictPolicy, int]
    losses: dict[ConflictPolicy, int]


class ConflictsByDomainResponse(Struct):
    total: int
    per_experiment: dict[ExperimentId, int]


class DecisionsController(Controller):
    path = "/api/v1/decisions"
    tags: Sequence[str] | None = ("Decisions",)

    @post(
        path="/get-flags",
        status_code=200,
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
                key: DecisionSchema(
                    id=decision.id,
                    value=decision.value,
                    experiment_id=decision.experiment_id,
                )
                if decision
                else None
                for key, decision in decisions.items()
            },
        )

    @get(
        "/conflicts/by-experiment/{exp_id:str}",
        responses={
            200: success_spec("Retrieved.", ConflictsByExperimentResponse),
            **RESPONSE_NOT_AUTHENTICATED,
        },
        security=security_defs
    )
    @inject
    async def get_conflicts_by_experiment(
        self, exp_id: str,
        interactor: FromDishka[ReadConflictsByExperiment],
    ) -> ConflictsByExperimentResponse:
        dto = await interactor(ExperimentId(exp_id))
        return ConflictsByExperimentResponse(
            wins=dto.wins,
            losses=dto.losses,
        )

    @get(
        "/conflicts/by-domain/{domain:str}",
        responses={
            200: success_spec("Retrieved.", ConflictsByDomainResponse),
            **RESPONSE_NOT_AUTHENTICATED,
        },
        security=security_defs
    )
    @inject
    async def get_conflicts_by_domain(
        self, domain: str,
        interactor: FromDishka[ReadConflictsByDomain]
    ) -> ConflictsByDomainResponse:
        per_experiment = await interactor(ConflictDomain(domain))
        return ConflictsByDomainResponse(
            total=sum(per_experiment.values()),
            per_experiment=per_experiment
        )
