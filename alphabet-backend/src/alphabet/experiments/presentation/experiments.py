from collections.abc import Sequence
from datetime import datetime
from ftplib import error_reply
from operator import attrgetter
from types import MappingProxyType
from typing import Literal, Final

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, get, patch, post
from msgspec import Struct, UnsetType, UNSET

from alphabet.experiments.application.interactors.experiments import (
    CreateExperiment,
    CreateExperimentDTO,
    RejectDraft,
    SendToReview,
    UpdateExperiment,
    UpdateExperimentDTO, ApproveDraft, RestoreFromRejected, StartExperiment,
    ManageRunningExperiment, ArchiveExperiment, ReadExperimentVersion,
    ReadExperimentVersionHistory, ReadExperimentAudit, ExperimentAuditDTO,
)
from alphabet.experiments.domain.experiment import (
    ConflictDomain, ConflictPolicy,
    Experiment,
    ExperimentId, ExperimentName,
    ExperimentOutcome,
    ExperimentResult, MetricCollection,
    Percentage,
    Priority,
    ReviewDecisionType, Variant, ReviewDecision, ExperimentState,
)
from alphabet.experiments.domain.flags import FlagKey
from alphabet.experiments.domain.target_rule import TargetRuleString
from alphabet.shared.commons import (
    MISSING,
    Maybe,
    maybe_map, MaybeMissing,
)
from alphabet.shared.presentation.framework.openapi import (
    RESPONSE_FORBIDDEN, RESPONSE_NOT_AUTH_AND_FORBIDDEN,
    RESPONSE_NOT_AUTHENTICATED,
    RESPONSE_NOT_FOUND, success_spec, error_spec,
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
    metrics: MetricCollectionSchema
    targeting: str | None = None
    priority: int | None = None
    conflict_domain: str | None = None
    conflict_policy: ConflictPolicy | None = None


class UpdateExperimentRequest(Struct):
    name: str | UnsetType = UNSET
    flag_key: str | UnsetType = UNSET
    audience: int | UnsetType = UNSET
    variants: list[VariantSchema] | UnsetType = UNSET
    metrics: MetricCollectionSchema | UnsetType = UNSET
    priority: int | None | UnsetType = UNSET
    targeting: str | None | UnsetType = UNSET
    conflict_domain: str | None | UnsetType = UNSET
    conflict_policy: ConflictPolicy | None | UnsetType = UNSET


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
            targeting=maybe_map(experiment.targeting, attrgetter("value")),
            author_id=experiment.author_id,
            created_at=experiment.created_at,
            updated_at=experiment.updated_at,
            result=maybe_map(
                experiment.result, lambda r: ExperimentResultSchema(
                    comment=r.comment,
                    outcome=r.outcome,
                )
            ),
            metrics=MetricCollectionSchema(
                primary=experiment.metrics.primary,
                secondary=experiment.metrics.secondary,
                guarding=experiment.metrics.guarding,
            ),
            priority=maybe_map(experiment.priority, attrgetter("value")),
            conflict_domain=maybe_map(
                experiment.conflict_domain, attrgetter("value")
            ),
            conflict_policy=maybe_map(experiment.conflict_policy)
        )


class RejectRequest(Struct):
    comment: str


class ReviewDecisionResponse(Struct):
    experiment_id: str
    type: ReviewDecisionType
    rejecter_id: str | None
    reject_comment: str | None

    @classmethod
    def from_decision(
        cls, decision: ReviewDecision
    ) -> "ReviewDecisionResponse":
        return ReviewDecisionResponse(
            experiment_id=decision.experiment_id,
            type=decision.type,
            rejecter_id=decision.rejecter_id,
            reject_comment=decision.reject_comment,
        )


class ApprovalAcceptedResponse(Struct):
    status: Literal["waiting_for_more_votes", "accepted"]
    decision: ReviewDecisionResponse | None


class ManageRunningExperimentRequest(Struct):
    new_state: ExperimentState


class ArchiveExperimentRequest(Struct):
    outcome: ExperimentOutcome
    comment: str


class ApprovalSchema(Struct):
    experiment_id: str
    approver_id: str


class ExperimentAuditResponse(Struct):
    approvals: list[ApprovalSchema]
    decision: ReviewDecisionResponse | None

    @classmethod
    def from_dto(cls, dto: ExperimentAuditDTO) -> "ExperimentAuditResponse":
        return ExperimentAuditResponse(
            approvals=[
                ApprovalSchema(
                    experiment_id=approval.experiment_id,
                    approver_id=approval.approver_id,
                )
                for approval in dto.approvals
            ],
            decision=ReviewDecisionResponse.from_decision(dto.decision)
            if dto.decision else None,
        )


CANNOT_CHANGE_STATE: Final = MappingProxyType(
    {
        409: error_spec("Cannot change state.")
    }
)


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
                name=maybe_map(data.name, ExperimentName),
                flag_key=maybe_map(data.flag_key, FlagKey),
                audience=maybe_map(data.audience, Percentage),
                variants=maybe_map(
                    data.variants, lambda variants: [
                        Variant(
                            name=variant.name,
                            value=variant.value,
                            is_control=variant.is_control,
                            audience=Percentage(variant.audience),
                        )
                        for variant in variants
                    ]
                ),
                metrics=maybe_map(
                    data.metrics, lambda metrics: MetricCollection(
                        primary=metrics.primary,
                        secondary=metrics.secondary,
                        guarding=metrics.guarding,
                    )
                ),
                priority=maybe_map(data.priority, Priority),
                targeting=maybe_map(data.targeting, TargetRuleString),
                conflict_domain=maybe_map(
                    data.conflict_domain, ConflictDomain
                ),
                conflict_policy=maybe_map(data.conflict_policy),
            )
        )
        return ExperimentResponse.from_experiment(experiment)

    @post(
        path="/{exp_id:str}/send-to-review",
        responses={
            200: success_spec("Sent.", ExperimentResponse),
            **CANNOT_CHANGE_STATE,
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_FORBIDDEN,
        },
        status_code=200
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
        responses={
            200: success_spec("Rejected.", ReviewDecisionResponse),
            **CANNOT_CHANGE_STATE,
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_FORBIDDEN,
        },
        status_code=200
    )
    @inject
    async def reject(
        self,
        exp_id: str,
        data: RejectRequest,
        interactor: FromDishka[RejectDraft]
    ) -> ReviewDecisionResponse:
        decision = await interactor(ExperimentId(exp_id), data.comment)
        return ReviewDecisionResponse.from_decision(decision)

    @post(
        path="/{exp_id:str}/approve",
        responses={
            200: success_spec("Approval accepted.", ApprovalAcceptedResponse),
            409: error_spec("Not in review or approved already."),
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_FORBIDDEN,
        },
        status_code=200
    )
    @inject
    async def approve(
        self,
        exp_id: str,
        interactor: FromDishka[ApproveDraft]
    ) -> ApprovalAcceptedResponse:
        decision = await interactor(ExperimentId(exp_id))
        if not decision:
            return ApprovalAcceptedResponse(
                status="waiting_for_more_votes",
                decision=None
            )
        else:
            return ApprovalAcceptedResponse(
                status="accepted",
                decision=ReviewDecisionResponse.from_decision(decision)
            )

    @post(
        path="/{exp_id:str}/restore",
        responses={
            200: success_spec("Restored from rejected.", ExperimentResponse),
            **CANNOT_CHANGE_STATE,
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_FORBIDDEN,
        },
        status_code=200
    )
    @inject
    async def restore(
        self,
        exp_id: str,
        interactor: FromDishka[RestoreFromRejected]
    ) -> ExperimentResponse:
        experiment = await interactor(ExperimentId(exp_id))
        return ExperimentResponse.from_experiment(experiment)

    @post(
        path="/{exp_id:str}/start",
        responses={
            200: success_spec("Started.", ExperimentResponse),
            **CANNOT_CHANGE_STATE,
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_FORBIDDEN,
        },
        status_code=200
    )
    @inject
    async def start(
        self,
        exp_id: str,
        interactor: FromDishka[StartExperiment]
    ) -> ExperimentResponse:
        experiment = await interactor(ExperimentId(exp_id))
        return ExperimentResponse.from_experiment(experiment)

    @post(
        path="/{exp_id:str}/manage-running",
        responses={
            200: success_spec("State changed.", ExperimentResponse),
            **CANNOT_CHANGE_STATE,
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_FORBIDDEN,
        },
        status_code=200
    )
    @inject
    async def manage_running(
        self,
        exp_id: str,
        data: ManageRunningExperimentRequest,
        interactor: FromDishka[ManageRunningExperiment]
    ) -> ExperimentResponse:
        experiment = await interactor(ExperimentId(exp_id), data.new_state)
        return ExperimentResponse.from_experiment(experiment)

    @post(
        path="/{exp_id:str}/archive",
        responses={
            200: success_spec("Archived and set result.", ExperimentResponse),
            **CANNOT_CHANGE_STATE,
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_FORBIDDEN,
        },
        status_code=200
    )
    @inject
    async def archive(
        self,
        exp_id: str,
        data: ArchiveExperimentRequest,
        interactor: FromDishka[ArchiveExperiment]
    ) -> ExperimentResponse:
        experiment = await interactor(
            ExperimentId(exp_id),
            ExperimentResult(
                data.comment,
                data.outcome,
            )
        )
        return ExperimentResponse.from_experiment(experiment)

    @get(
        path="/{exp_id:str}",
        responses={
            200: success_spec("Retrieved.", ExperimentResponse),
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
        },
        status_code=200
    )
    @inject
    async def get_one_experiment(
        self,
        exp_id: str,
        interactor: FromDishka[ReadExperimentVersion],
        version: int | None = None,
    ) -> ExperimentResponse:
        experiment = await interactor(
            ExperimentId(exp_id), version if version else MISSING
        )
        return ExperimentResponse.from_experiment(experiment)

    @get(
        path="/{exp_id:str}/history",
        responses={
            200: success_spec("Retrieved.", list[ExperimentResponse]),
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
        },
        status_code=200
    )
    @inject
    async def get_history(
        self,
        exp_id: str,
        interactor: FromDishka[ReadExperimentVersionHistory],
    ) -> list[ExperimentResponse]:
        experiments = await interactor(ExperimentId(exp_id))
        return list(map(ExperimentResponse.from_experiment, experiments))

    @get(
        path="/{exp_id:str}/review-audit",
        responses={
            200: success_spec("Audit retrieved.", ExperimentAuditResponse),
            **RESPONSE_NOT_FOUND,
            **RESPONSE_NOT_AUTHENTICATED,
        },
        status_code=200
    )
    @inject
    async def get_audit(
        self,
        exp_id: str,
        interactor: FromDishka[ReadExperimentAudit]
    ) -> ExperimentAuditResponse:
        audit_dto = await interactor(ExperimentId(exp_id))
        return ExperimentAuditResponse.from_dto(audit_dto)
