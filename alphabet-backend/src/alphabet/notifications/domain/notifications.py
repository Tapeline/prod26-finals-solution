import re
from datetime import datetime
from typing import final, NewType, Final, override

from alphabet.experiments.domain.experiment import ExperimentId
from alphabet.guardrails.domain import GuardRuleId
from alphabet.notifications.domain.exceptions import (
    InvalidConnectionString,
    InvalidRatelimit, InvalidTrigger,
)
from alphabet.shared.commons import entity, value_object

NotificationRuleId = NewType("NotificationRuleId", str)


@final
@value_object
class ExperimentTrigger:
    experiment_id: ExperimentId


@final
@value_object
class GuardrailTrigger:
    guardrail_id: GuardRuleId


@final
@value_object
class AnyExperimentTrigger:
    """Triggers for any experiment (* as id)."""


type Trigger = ExperimentTrigger | GuardrailTrigger | AnyExperimentTrigger


def construct_trigger(dsl: str) -> Trigger:
    match dsl.split(":", maxsplit=1):
        case ["experiment_lifecycle", "*"]:
            return AnyExperimentTrigger()
        case ["experiment_lifecycle", exp_id]:
            return ExperimentTrigger(ExperimentId(exp_id))
        case ["guardrail", guardrail_id]:
            return GuardrailTrigger(GuardRuleId(guardrail_id))
        case _:
            raise InvalidTrigger


_CONN_STRING_RE: Final = re.compile("[A-Za-z0-9_-]+://.*")

@final
class ConnectionString:
    __slots__ = ("integration", "resource")

    def __init__(self, conn_string: str) -> None:
        if not _CONN_STRING_RE.fullmatch(conn_string):
            raise InvalidConnectionString
        self.integration, self.resource = conn_string.split("://", maxsplit=1)

    @override
    def __repr__(self) -> str:
        return f"{self.integration}://{self.resource}"


@final
@value_object
class Ratelimit:
    _value: int

    def __post_init__(self) -> None:
        if self._value <= 0:
            raise InvalidRatelimit

    @property
    def seconds(self) -> int:
        return self._value


@entity
@final
class NotificationRule:
    id: NotificationRuleId
    trigger: Trigger
    connection: ConnectionString
    message_template: str
    rate_limit: Ratelimit


Fingerprint = NewType("Fingerprint", str)


@final
@entity
class PreparedNotification:
    fingerprint: Fingerprint
    rule_id: NotificationRuleId
    meta: dict[str, str]
    issued_at: datetime

