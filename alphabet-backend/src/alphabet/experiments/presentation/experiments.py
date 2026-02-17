from collections.abc import Callable, Sequence

from adaptix import P
from adaptix.conversion import get_converter, link, coercer
from typing import Any, overload

from datetime import datetime

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, get, patch, post, put
from msgspec import Struct

from alphabet.experiments.application.interactors.experiments import (
    CreateExperiment,
    CreateExperimentDTO,
    RejectDraft,
    SendToReview,
    UpdateExperiment,
    UpdateExperimentDTO,
)
from alphabet.experiments.domain.experiment import (
    ConflictDomain, ConflictPolicy,
    Experiment,
    ExperimentId, ExperimentName,
    ExperimentOutcome,
    ExperimentResult, MetricCollection,
    Percentage,
    Priority,
    ReviewDecisionType, Variant,
)
from alphabet.experiments.domain.flags import FeatureFlag, FlagKey, FlagType
from alphabet.experiments.domain.target_rule import TargetRuleString
from alphabet.experiments.presentation.flags import FlagResponse
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.commons import (
    MISSING,
    Maybe,
    MaybeMissing,
    identity,
    vo_coercer,
)
from alphabet.shared.domain.user import UserId
from alphabet.shared.presentation.framework.openapi import (
    RESPONSE_BAD_REQUEST,
    RESPONSE_FORBIDDEN, RESPONSE_NOT_AUTH_AND_FORBIDDEN,
    RESPONSE_NOT_AUTHENTICATED,
    RESPONSE_NOT_FOUND, error_spec,
    success_spec,
)
from alphabet.shared.presentation.openapi import security_defs


class VariantSchema(Struct):
    name: str
    value: str
    is_control: bool
    audience: int


class MetricCollectionSchema(Struct):
    primary: str
    secondary: list[str]
    guarding: list[str]


class ExperimentResultSchema(Struct):
    comment: str
    outcome: ExperimentOutcome


class CreateExperimentRequest(Struct):
    name: str
    flag_key: str
    audience: int
    variants: list[VariantSchema]
    targeting: str | None
    metrics: MetricCollectionSchema
    priority: int | None
    conflict_domain: str | None
    conflict_policy: ConflictPolicy | None


class UpdateExperimentRequest(Struct):
    name: Maybe[str] = MISSING
    flag_key: Maybe[str] = MISSING
    audience: Maybe[int] = MISSING
    variants: Maybe[list[VariantSchema]] = MISSING
    metrics: Maybe[MetricCollectionSchema] = MISSING
    priority: Maybe[int | None] = MISSING
    targeting: Maybe[str | None] = MISSING
    conflict_domain: Maybe[str | None] = MISSING
    conflict_policy: Maybe[ConflictPolicy | None] = MISSING


class ExperimentResponse(Struct):
    id: str
    name: str
    flag_key: str
    state: str
    version: int
    audience: int
    variants: list[VariantSchema]
    targeting: str | None
    author_id: str
    created_at: datetime
    updated_at: datetime
    result: ExperimentResultSchema | None
    metrics: MetricCollectionSchema
    priority: int | None
    conflict_domain: str | None
    conflict_policy: ConflictPolicy | None

    @classmethod
    def from_experiment(cls, experiment: Experiment) -> "ExperimentResponse":
        return ExperimentResponse(
            id=experiment.id,
            name=experiment.name.value,
            flag_key=experiment.flag_key.value,
            state=experiment.state,
            version=experiment.version,
            audience=experiment.audience.value,
            variants=[
                VariantSchema(
                    name=variant.name,
                    value=variant.value,
                    is_control=variant.is_control,
                    audience=variant.audience.value,
                )
                for variant in experiment.variants
            ],
            targeting=experiment.targeting.value
            if experiment.targeting else None,
            author_id=experiment.author_id,
            created_at=experiment.created_at,
            updated_at=experiment.updated_at,
            result=ExperimentResultSchema(
                comment=experiment.result.comment,
                outcome=experiment.result.outcome,
            ),
            metrics=MetricCollectionSchema(
                primary=experiment.metrics.primary,
                secondary=experiment.metrics.secondary,
                guarding=experiment.metrics.guarding,
            ),
            priority=experiment.priority.value,
            conflict_domain=experiment.conflict_domain.value
            if experiment.conflict_domain else None,
            conflict_policy=experiment.conflict_policy
            if experiment.conflict_policy else None,
        )


class RejectRequest(Struct):
    comment: str


class ReviewDecisionResponse(Struct):
    experiment_id: str
    type: ReviewDecisionType
    rejecter_id: str | None
    reject_comment: str | None


class ExperimentsController(Controller):
    path = "/api/v1/experiments"
    tags: Sequence[str] | None = ("Experiments",)
    security = security_defs

    @post(
        path="/create",
        responses={
            201: success_spec("Created.", ExperimentResponse),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
        },
    )
    @inject
    async def create_experiment(
        self,
        data: CreateExperimentRequest,
        interactor: FromDishka[CreateExperiment],
    ) -> ExperimentResponse:
        experiment = await interactor(
            CreateExperimentDTO(
                name=ExperimentName(data.name),
                flag_key=FlagKey(data.flag_key),
                audience=Percentage(data.audience),
                variants=[
                    Variant(
                        name=variant.name,
                        value=variant.value,
                        is_control=variant.is_control,
                        audience=Percentage(variant.audience),
                    )
                    for variant in data.variants
                ],
                targeting=TargetRuleString(data.targeting)
                if data.targeting else None,
                metrics=MetricCollection(
                    primary=data.metrics.primary,
                    secondary=data.metrics.secondary,
                    guarding=data.metrics.guarding,
                ),
                priority=Priority(data.priority) if data.priority else None,
                conflict_domain=ConflictDomain(data.conflict_domain)
                if data.conflict_domain else None,
                conflict_policy=data.conflict_policy,
            )
        )
        return ExperimentResponse.from_experiment(experiment)

    @patch(
        path="/{exp_id:str}",
        responses={
            200: success_spec("Updated.", ExperimentResponse),
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_FORBIDDEN,
        },
    )
    @inject
    async def update_experiment(
        self,
        exp_id: str,
        data: UpdateExperimentRequest,
        interactor: FromDishka[UpdateExperiment],
    ) -> ExperimentResponse:
        experiment = await interactor(
            ExperimentId(exp_id),
            UpdateExperimentDTO(
                name=_if_present(data.name, ExperimentName),
                flag_key=_if_present(data.flag_key, FlagKey),
                audience=_if_present(data.audience, Percentage),
                variants=_if_present(
                    data.variants, lambda variants: [
                        Variant(
                            name=variant.name,
                            value=variant.value,
                            is_control=variant.is_control,
                            audience=Percentage(variant.audience),
                        )
                        for variant in data.variants
                    ]
                ),
                metrics=_if_present(
                    data.metrics, lambda metrics: MetricCollection(
                        primary=data.metrics.primary,
                        secondary=data.metrics.secondary,
                        guarding=data.metrics.guarding,
                    )
                ),
                priority=_if_present(data.priority, Percentage),
                targeting=_if_present(data.targeting, TargetRuleString),
                conflict_domain=_if_present(
                    data.conflict_domain, ConflictDomain
                ),
                conflict_policy=data.conflict_policy,
            )
        )
        return ExperimentResponse.from_experiment(experiment)

    @post(
        path="/{exp_id:str}/send-to-review",
        responses={

        }
    )
    @inject
    async def send_to_review(
        self,
        exp_id: str,
        interactor: FromDishka[SendToReview]
    ) -> ExperimentResponse:
        experiment = await interactor(ExperimentId(exp_id))
        return ExperimentResponse.from_experiment(experiment)

    @post(
        path="/{exp_id:str}/reject",
    )
    @inject
    async def reject(
        self,
        exp_id: str,
        data: RejectRequest,
        interactor: FromDishka[RejectDraft]
    ) -> ExperimentResponse:


@overload
def _if_present(x: None, f: Any) -> None: ...


@overload
def _if_present(x: MaybeMissing, f: Any) -> MaybeMissing: ...


@overload
def _if_present[T, R](x: T, f: Callable[[T], R]) -> R: ...


def _if_present(x, f):
    return x if x is MISSING or x is None else f(x)
