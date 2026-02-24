import re
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Final, NewType, final

from alphabet.experiments.domain.exceptions import (
    AudienceMismatch,
    CannotTransition,
    DomainCannotBeBlank,
    ExperimentFrozen,
    ExperimentNameCannotBeBlank,
    InvalidConflictConfig,
    InvalidPercentageValue,
    InvalidPriorityValue,
    InvalidRejectionDecision,
    InvalidVariantName,
    NotOneControlVariant,
    ResultCommentCannotBeBlank,
)
from alphabet.experiments.domain.flags import FlagKey
from alphabet.experiments.domain.target_rule import TargetRuleString
from alphabet.shared.commons import entity, value_object
from alphabet.shared.domain.user import UserId

ExperimentId = NewType("ExperimentId", str)


@final
@value_object
class ExperimentName:
    value: str

    def __post_init__(self) -> None:
        if self.value == "":
            raise ExperimentNameCannotBeBlank


@final
@value_object
class Percentage:
    value: int  # statement uses integers everywhere, so do I

    def __post_init__(self) -> None:
        if not (0 <= self.value <= 100):
            raise InvalidPercentageValue


@final
class ExperimentState(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    ACCEPTED = "accepted"
    STARTED = "started"
    SECURITY_HALTED = "security_halted"
    PAUSED = "paused"
    FINISHED = "finished"
    ARCHIVED = "archived"
    REJECTED = "rejected"


_VALID_TRANSITIONS: Final = MappingProxyType(
    {
        ExperimentState.DRAFT: frozenset(
            (ExperimentState.IN_REVIEW,),
        ),
        ExperimentState.IN_REVIEW: frozenset(
            (
                ExperimentState.ACCEPTED,
                ExperimentState.REJECTED,
                ExperimentState.DRAFT,
            ),
        ),
        ExperimentState.ACCEPTED: frozenset(
            (ExperimentState.STARTED,),
        ),
        ExperimentState.STARTED: frozenset(
            (
                ExperimentState.PAUSED,
                ExperimentState.FINISHED,
                ExperimentState.SECURITY_HALTED,
            ),
        ),
        ExperimentState.PAUSED: frozenset(
            (
                ExperimentState.STARTED,
                ExperimentState.FINISHED,
            ),
        ),
        ExperimentState.FINISHED: frozenset(
            (ExperimentState.ARCHIVED,),
        ),
        ExperimentState.SECURITY_HALTED: frozenset(
            (ExperimentState.FINISHED,),
        ),
        ExperimentState.ARCHIVED: frozenset(),
        ExperimentState.REJECTED: frozenset(
            (ExperimentState.DRAFT,),
        ),
    },
)


_VARIANT_NAME_RE: Final = re.compile(r"^[a-zA-Z_-]+$")


@final
@value_object
class Variant:
    name: str
    value: str
    is_control: bool
    audience: Percentage

    def __post_init__(self) -> None:
        if self.name == "":
            raise InvalidVariantName
        if not _VARIANT_NAME_RE.fullmatch(self.name):
            raise InvalidVariantName


@final
class ExperimentOutcome(StrEnum):
    ROLLOUT_WINNER = "rollout_winner"
    ROLLBACK_DEFAULT = "rollback_default"
    NO_EFFECT = "no_effect"


@final
@value_object
class ExperimentResult:
    comment: str
    outcome: ExperimentOutcome

    def __post_init__(self) -> None:
        if self.comment == "":
            raise ResultCommentCannotBeBlank


@final
@value_object
class MetricCollection:
    primary: str
    secondary: list[str]
    guarding: list[str]


@final
@value_object
class Priority:
    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise InvalidPriorityValue


@final
@value_object
class ConflictDomain:
    value: str

    def __post_init__(self) -> None:
        if self.value == "":
            raise DomainCannotBeBlank


@final
class ConflictPolicy(StrEnum):
    ONE_OR_NONE = "one_or_none"
    HIGHER_PRIORITY = "higher_priority"


@final
@entity
class Experiment:
    _id: ExperimentId
    _name: ExperimentName
    _flag_key: FlagKey
    _state: ExperimentState
    _version: int
    _audience: Percentage
    _variants: list[Variant]
    _targeting: TargetRuleString | None
    _author_id: UserId
    _created_at: datetime
    _updated_at: datetime
    _result: ExperimentResult | None
    _metrics: MetricCollection
    _priority: Priority | None
    _conflict_domain: ConflictDomain | None
    _conflict_policy: ConflictPolicy | None

    @classmethod
    def new(
        cls,
        id: ExperimentId,
        name: ExperimentName,
        flag_key: FlagKey,
        audience: Percentage,
        variants: list[Variant],
        targeting: TargetRuleString | None,
        author_id: UserId,
        created_at: datetime,
        updated_at: datetime,
        metrics: MetricCollection,
        priority: Priority | None,
        conflict_domain: ConflictDomain | None,
        conflict_policy: ConflictPolicy | None,
    ) -> "Experiment":
        if (conflict_domain is None) ^ (conflict_policy is None):
            raise InvalidConflictConfig
        _validate_audience_and_variants(audience, variants)
        return Experiment(
            _id=id,
            _name=name,
            _flag_key=flag_key,
            _state=ExperimentState.DRAFT,
            _version=1,
            _audience=audience,
            _variants=variants,
            _targeting=targeting,
            _author_id=author_id,
            _created_at=created_at,
            _updated_at=updated_at,
            _metrics=metrics,
            _priority=priority,
            _conflict_domain=conflict_domain,
            _conflict_policy=conflict_policy,
            _result=None,
        )

    def _assert_in_draft(self) -> None:
        if self._state != ExperimentState.DRAFT:
            raise ExperimentFrozen

    @property
    def id(self) -> ExperimentId:
        return self._id

    @property
    def name(self) -> ExperimentName:
        return self._name

    @name.setter
    def name(self, name: ExperimentName) -> None:
        self._assert_in_draft()
        self._name = name

    @property
    def flag_key(self) -> FlagKey:
        return self._flag_key

    @flag_key.setter
    def flag_key(self, flag_key: FlagKey) -> None:
        self._assert_in_draft()
        self._flag_key = flag_key

    @property
    def state(self) -> ExperimentState:
        return self._state

    @state.setter
    def state(self, new_state: ExperimentState) -> None:
        if new_state not in _VALID_TRANSITIONS[self._state]:
            raise CannotTransition(self._state, new_state)
        if new_state == ExperimentState.ARCHIVED:
            # a workaround, alas this is a bad design.
            # archiving implies setting an outcome
            # use archive method
            raise CannotTransition(self._state, ExperimentState.ARCHIVED)
        self._state = new_state

    @property
    def version(self) -> int:
        return self._version

    def increment_version(self) -> None:
        self._version += 1

    @property
    def audience(self) -> Percentage:
        return self._audience

    @property
    def variants(self) -> list[Variant]:
        return self._variants

    def set_new_audience_variants(
        self,
        audience: Percentage,
        variants: list[Variant],
    ) -> None:
        _validate_audience_and_variants(audience, variants)
        self._variants = variants
        self._audience = audience

    def set_new_variants(self, vairants: list[Variant]) -> None:
        _validate_audience_and_variants(self._audience, vairants)
        self._variants = vairants

    @property
    def targeting(self) -> TargetRuleString | None:
        return self._targeting

    @targeting.setter
    def targeting(self, new_targeting: TargetRuleString | None) -> None:
        self._targeting = new_targeting

    @property
    def author_id(self) -> UserId:
        return self._author_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @updated_at.setter
    def updated_at(self, updated_at: datetime) -> None:
        self._updated_at = updated_at

    @property
    def result(self) -> ExperimentResult | None:
        return self._result

    def archive(self, with_result: ExperimentResult) -> None:
        if self._state != ExperimentState.FINISHED:
            raise CannotTransition(self._state, ExperimentState.ARCHIVED)
        self._result = with_result
        self._state = ExperimentState.ARCHIVED

    @property
    def metrics(self) -> MetricCollection:
        return self._metrics

    @metrics.setter
    def metrics(self, new_metrics: MetricCollection) -> None:
        self._metrics = new_metrics

    @property
    def priority(self) -> Priority | None:
        return self._priority

    @priority.setter
    def priority(self, new_priority: Priority | None) -> None:
        self._priority = new_priority

    @property
    def conflict_domain(self) -> ConflictDomain | None:
        return self._conflict_domain

    @property
    def conflict_policy(self) -> ConflictPolicy | None:
        return self._conflict_policy

    def remove_conflict_domain(self) -> None:
        self._conflict_policy = None
        self._conflict_domain = None

    def set_conflict_domain(
        self,
        domain: ConflictDomain,
        policy: ConflictPolicy,
    ) -> None:
        self._conflict_domain = domain
        self._conflict_policy = policy


def _validate_audience_and_variants(
    audience: Percentage,
    variants: list[Variant],
) -> None:
    variant_audience_sum = sum(variant.audience.value for variant in variants)
    if variant_audience_sum != 100:
        raise AudienceMismatch
    if sum(1 for variant in variants if variant.is_control) != 1:
        raise NotOneControlVariant


@final
@entity
class Approval:
    experiment_id: ExperimentId
    approver_id: UserId


@final
class ReviewDecisionType(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@final
@entity
class ReviewDecision:
    experiment_id: ExperimentId
    rejecter_id: UserId | None
    reject_comment: str | None
    type: ReviewDecisionType = ReviewDecisionType.ACCEPTED

    def __post_init__(self) -> None:
        if self.rejecter_id:
            self.type = ReviewDecisionType.REJECTED
        if (self.rejecter_id is None) ^ (self.reject_comment is None):
            raise InvalidRejectionDecision

    @classmethod
    def rejected(
        cls,
        experiment_id: ExperimentId,
        rejecter_id: UserId | None,
        reject_comment: str | None,
    ) -> "ReviewDecision":
        return ReviewDecision(experiment_id, rejecter_id, reject_comment)

    @classmethod
    def approved(cls, experiment_id: ExperimentId) -> "ReviewDecision":
        return ReviewDecision(experiment_id, None, None)
