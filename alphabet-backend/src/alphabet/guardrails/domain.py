from datetime import timedelta, datetime
from enum import StrEnum
from typing import final, NewType

from alphabet.experiments.domain.experiment import ExperimentId
from alphabet.metrics.domain.metrics import MetricKey
from alphabet.shared.commons import entity

GuardRuleId = NewType("GuardRuleId", str)


@final
class GuardAction(StrEnum):
    PAUSE = "pause"
    FORCE_CONTROL = "force_control"


@entity
@final
class GuardRule:
    id: GuardRuleId
    experiment_id: ExperimentId
    metric_key: MetricKey
    threshold: float
    watch_window: timedelta
    action: GuardAction
    is_archived: bool


AuditRecordId = NewType("AuditRecordId", str)


@final
@entity
class AuditRecord:
    id: AuditRecordId
    rule_id: GuardRuleId
    fired_at: datetime
    experiment_id: ExperimentId
    metric_key: MetricKey
    metric_value: float
    taken_action: GuardAction
