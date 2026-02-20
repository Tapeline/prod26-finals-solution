from collections.abc import Sequence
from datetime import datetime, timedelta

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, get, patch, post
from msgspec import UNSET, Struct, UnsetType

from alphabet.experiments.domain.experiment import ExperimentId
from alphabet.guardrails.application.interactors import (
    ArchiveRule,
    CreateRule,
    CreateRuleDTO,
    ReadAuditForExperiment,
    ReadAuditForGuardRule,
    ReadRule,
    ReadRulesForExperiment,
    UpdateRule,
    UpdateRuleDTO,
)
from alphabet.guardrails.domain import (
    AuditRecord,
    GuardAction,
    GuardRule,
    GuardRuleId,
)
from alphabet.metrics.domain.metrics import MetricKey
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.commons import maybe_map
from alphabet.shared.presentation.framework.openapi import (
    RESPONSE_FORBIDDEN,
    RESPONSE_NOT_AUTH_AND_FORBIDDEN,
    RESPONSE_NOT_AUTHENTICATED,
    RESPONSE_NOT_FOUND,
    error_spec,
    success_spec,
)
from alphabet.shared.presentation.openapi import security_defs


class GuardRuleSchema(Struct):
    id: str
    experiment_id: str
    metric_key: str
    threshold: float
    watch_window_s: int
    action: GuardAction
    is_archived: bool

    @classmethod
    def from_rule(cls, rule: GuardRule) -> "GuardRuleSchema":
        return GuardRuleSchema(
            id=rule.id,
            experiment_id=rule.experiment_id,
            metric_key=rule.metric_key.value,
            threshold=rule.threshold,
            watch_window_s=int(rule.watch_window.total_seconds()),
            action=rule.action,
            is_archived=rule.is_archived,
        )


class AuditRecordSchema(Struct):
    id: str
    rule_id: str
    fired_at: datetime
    experiment_id: str
    metric_key: str
    metric_value: float
    taken_action: GuardAction

    @classmethod
    def from_record(cls, record: AuditRecord) -> "AuditRecordSchema":
        return AuditRecordSchema(
            id=record.id,
            experiment_id=record.experiment_id,
            metric_key=record.metric_key.value,
            rule_id=record.rule_id,
            fired_at=record.fired_at,
            metric_value=record.metric_value,
            taken_action=record.taken_action,
        )


class CreateGuardRuleRequest(Struct):
    experiment_id: str
    metric_key: str
    threshold: float
    watch_window_s: int
    action: GuardAction


class UpdateGuardRuleRequest(Struct):
    threshold: float | UnsetType = UNSET
    watch_window_s: int | UnsetType = UNSET
    action: GuardAction | UnsetType = UNSET


class GuardRulesController(Controller):
    path = "/api/v1/guardrails"
    tags: Sequence[str] | None = ("Guardrails",)
    security = security_defs

    @post(
        path="/for-experiment/{exp_id:str}/create",
        responses={
            201: success_spec("Created.", GuardRuleSchema),
            409: error_spec("Already exists."),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
        },
    )
    @inject
    async def create_rule(
        self,
        exp_id: str,
        data: CreateGuardRuleRequest,
        interactor: FromDishka[CreateRule],
    ) -> GuardRuleSchema:
        rule = await interactor(
            ExperimentId(exp_id),
            CreateRuleDTO(
                metric_key=MetricKey(data.metric_key),
                threshold=data.threshold,
                watch_window=timedelta(seconds=data.watch_window_s),
                action=data.action,
            ),
        )
        return GuardRuleSchema.from_rule(rule)

    @get(
        path="/for-experiment/{exp_id:str}",
        responses={
            200: success_spec("Retrieved.", list[GuardRuleSchema]),
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_FORBIDDEN,
        },
    )
    @inject
    async def list_rules_for_experiment(
        self,
        exp_id: str,
        interactor: FromDishka[ReadRulesForExperiment],
    ) -> list[GuardRuleSchema]:
        rules = await interactor(ExperimentId(exp_id))
        return list(map(GuardRuleSchema.from_rule, rules))

    @patch(
        path="/{rule_id:str}",
        responses={
            200: success_spec("Updated.", GuardRuleSchema),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
            **RESPONSE_NOT_FOUND,
        },
    )
    @inject
    async def update_rule(
        self,
        rule_key: str,
        interactor: FromDishka[UpdateRule],
        data: UpdateGuardRuleRequest,
    ) -> GuardRuleSchema:
        rule = await interactor(
            GuardRuleId(rule_key),
            UpdateRuleDTO(
                threshold=maybe_map(data.threshold),
                watch_window=maybe_map(
                    data.watch_window_s, lambda s: timedelta(seconds=s),
                ),
                action=maybe_map(data.action),
            ),
        )
        return GuardRuleSchema.from_rule(rule)

    @get(
        path="/{rule_id:str}",
        responses={
            200: success_spec("Retrieved.", GuardRuleSchema),
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_NOT_FOUND,
        },
    )
    @inject
    async def read_rule(
        self,
        rule_id: str,
        interactor: FromDishka[ReadRule],
    ) -> GuardRuleSchema:
        rule = await interactor(GuardRuleId(rule_id))
        return GuardRuleSchema.from_rule(rule)

    @post(
        path="/{rule_id:str}/archive",
        responses={
            200: success_spec("Archived.", GuardRuleSchema),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
            **RESPONSE_NOT_FOUND,
        },
        status_code=200,
    )
    @inject
    async def archive_rule(
        self,
        rule_key: str,
        interactor: FromDishka[ArchiveRule],
    ) -> GuardRuleSchema:
        rule = await interactor(GuardRuleId(rule_key))
        return GuardRuleSchema.from_rule(rule)

    @get(
        path="/{rule_id:str}/log",
        responses={
            200: success_spec("Retrieved.", list[AuditRecordSchema]),
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_NOT_FOUND,
        },
    )
    @inject
    async def read_audit_log_for_rule(
        self,
        rule_id: str,
        interactor: FromDishka[ReadAuditForGuardRule],
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditRecordSchema]:
        records = await interactor(
            GuardRuleId(rule_id), Pagination(limit, offset),
        )
        return list(map(AuditRecordSchema.from_record, records))

    @get(
        path="/for-experiment/{exp_id:str}/log",
        responses={
            200: success_spec("Retrieved.", list[AuditRecordSchema]),
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_NOT_FOUND,
        },
    )
    @inject
    async def read_audit_log_for_experiment(
        self,
        exp_id: str,
        interactor: FromDishka[ReadAuditForExperiment],
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditRecordSchema]:
        records = await interactor(
            ExperimentId(exp_id), Pagination(limit, offset),
        )
        return list(map(AuditRecordSchema.from_record, records))
