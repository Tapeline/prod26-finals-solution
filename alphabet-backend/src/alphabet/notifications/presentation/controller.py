from collections.abc import Sequence
from typing import Any, assert_never

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, delete, get, patch, post
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED
from msgspec import UNSET, Struct, UnsetType

from alphabet.notifications.application.interactors import (
    CreateNotificationRule,
    CreateRuleDTO,
    DeleteNotificationRule,
    ReadAllNotificationRule,
    ReadNotificationRule,
    UpdateNotificationRule,
    UpdateRuleDTO,
)
from alphabet.notifications.domain.notifications import (
    AnyExperimentTrigger,
    ConnectionString,
    ExperimentTrigger,
    GuardrailTrigger,
    NotificationRule,
    NotificationRuleId,
    Ratelimit,
    Trigger,
    construct_trigger,
)
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


def _trigger_to_dsl(trigger: Trigger) -> str:
    match trigger:
        case AnyExperimentTrigger():
            return "experiment_lifecycle:*"
        case ExperimentTrigger(experiment_id=eid):
            return f"experiment_lifecycle:{eid}"
        case GuardrailTrigger(guardrail_id=gid):
            return f"guardrail:{gid}"
        case _:
            assert_never(trigger)


class NotificationRuleSchema(Struct):
    id: str
    trigger_dsl: str
    connection_string: str
    message_template: str
    rate_limit_seconds: int

    @classmethod
    def from_domain(cls, rule: NotificationRule) -> "NotificationRuleSchema":
        return NotificationRuleSchema(
            id=rule.id,
            trigger_dsl=_trigger_to_dsl(rule.trigger),
            connection_string=str(rule.connection),
            message_template=rule.message_template,
            rate_limit_seconds=rule.rate_limit.seconds,
        )


class CreateNotificationRuleRequest(Struct):
    trigger: str
    connection_string: str
    template: str
    rate_limit_s: int


class UpdateNotificationRuleRequest(Struct):
    trigger: str | UnsetType = UNSET
    connection_string: str | UnsetType = UNSET
    template: str | UnsetType = UNSET
    rate_limit_s: int | UnsetType = UNSET


class NotificationRulesController(Controller):
    path = "/api/v1/notification-rules"
    tags: Sequence[str] | None = ("Notifications",)
    security = security_defs

    @post(
        path="/create",
        status_code=HTTP_201_CREATED,
        responses={
            201: success_spec("Created.", NotificationRuleSchema),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
        },
    )
    @inject
    async def create_rule(
        self,
        data: CreateNotificationRuleRequest,
        interactor: FromDishka[CreateNotificationRule],
    ) -> NotificationRuleSchema:
        rule = await interactor(
            CreateRuleDTO(
                trigger=construct_trigger(data.trigger),
                connection=ConnectionString(data.connection_string),
                template=data.template,
                rate_limit=Ratelimit(data.rate_limit_s),
            )
        )
        return NotificationRuleSchema.from_domain(rule)

    @get(
        path="/",
        responses={
            200: success_spec("Retrieved list.", list[NotificationRuleSchema]),
            **RESPONSE_NOT_AUTHENTICATED,
        },
    )
    @inject
    async def list_rules(
        self,
        interactor: FromDishka[ReadAllNotificationRule],
        limit: int = 50,
        offset: int = 0,
    ) -> list[NotificationRuleSchema]:
        rules = await interactor(Pagination(limit, offset))
        return [NotificationRuleSchema.from_domain(r) for r in rules]

    @get(
        path="/{rule_id:str}",
        responses={
            200: success_spec("Retrieved.", NotificationRuleSchema),
            **RESPONSE_NOT_AUTHENTICATED,
            **RESPONSE_NOT_FOUND,
        },
    )
    @inject
    async def read_rule(
        self,
        rule_id: str,
        interactor: FromDishka[ReadNotificationRule],
    ) -> NotificationRuleSchema:
        rule = await interactor(NotificationRuleId(rule_id))
        return NotificationRuleSchema.from_domain(rule)

    @patch(
        path="/{rule_id:str}",
        responses={
            200: success_spec("Updated.", NotificationRuleSchema),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
            **RESPONSE_NOT_FOUND,
        },
    )
    @inject
    async def update_rule(
        self,
        rule_id: str,
        data: UpdateNotificationRuleRequest,
        interactor: FromDishka[UpdateNotificationRule],
    ) -> NotificationRuleSchema:
        rule = await interactor(
            NotificationRuleId(rule_id),
            UpdateRuleDTO(
                trigger=maybe_map(data.trigger, construct_trigger),
                connection=maybe_map(data.connection_string, ConnectionString),
                template=maybe_map(data.template),
                rate_limit=maybe_map(data.rate_limit_s, Ratelimit),
            ),
        )
        return NotificationRuleSchema.from_domain(rule)

    @delete(
        path="/{rule_id:str}",
        status_code=HTTP_200_OK,
        responses={
            200: success_spec("Deleted."),
            **RESPONSE_NOT_AUTH_AND_FORBIDDEN,
            **RESPONSE_NOT_FOUND,
        },
    )
    @inject
    async def delete_rule(
        self,
        rule_id: str,
        interactor: FromDishka[DeleteNotificationRule],
    ) -> None:
        await interactor(NotificationRuleId(rule_id))
