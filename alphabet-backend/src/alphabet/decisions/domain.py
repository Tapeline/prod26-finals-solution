from typing import Final, NewType, final

import mmh3

from alphabet.experiments.domain.dsl.runtime import CompiledExpression
from alphabet.experiments.domain.experiment import ConflictPolicy, Variant
from alphabet.shared.commons import entity

DecisionId = NewType("DecisionId", str)


@final
@entity
class Decision:
    id: DecisionId
    flag_key: str
    value: str
    experiment_id: str | None


@final
class CachedExperiment:
    __slots__ = (
        "active_flag_key",
        "conflict_domain",
        "conflict_policy",
        "distribution",
        "id",
        "priority",
        "targeting",
        "variants",
    )
    id: str
    targeting: type[CompiledExpression] | None
    distribution: list[tuple[str, str] | None]
    conflict_domain: str | None
    conflict_policy: ConflictPolicy | None
    priority: int | None
    active_flag_key: str

    def __init__(
        self,
        id: str,
        variants: list[Variant],
        targeting: type[CompiledExpression] | None,
        conflict_domain: str | None,
        conflict_policy: ConflictPolicy | None,
        priority: int | None,
        active_flag_key: str,
    ) -> None:
        self.id = id
        self.variants = variants
        self.targeting = targeting
        self.conflict_domain = conflict_domain
        self.conflict_policy = conflict_policy
        self.priority = priority
        self.active_flag_key = active_flag_key
        self.distribution = distribute_variants(variants)


_MAX_HASH_VAL: Final = 2**32
_TOTAL_BUCKETS: Final = 100


def distribute_variants(
    variants: list[Variant],
) -> list[tuple[str, str] | None]:
    axis: list[tuple[str, str] | None] = [None] * 100
    i = 0
    for variant in variants:
        var_tuple = (variant.name, variant.value)
        for j in range(i, i + variant.audience.value):
            axis[j] = var_tuple
        i += variant.audience.value
    return axis


def make_decision(
    flag_key: str,
    default_value: str,
    experiment_id: str,
    variant_coordinates: list[tuple[str, str] | None],
    subject_id: str,
) -> Decision:
    hashable_str = f"{flag_key}:{experiment_id}:{subject_id}"
    hashed_norm = mmh3.hash(hashable_str, signed=False) / _MAX_HASH_VAL
    bucket = round(_TOTAL_BUCKETS * hashed_norm)
    bucket = max(bucket, 0)
    if bucket >= _TOTAL_BUCKETS:
        bucket = _TOTAL_BUCKETS - 1
    chosen = variant_coordinates[bucket]
    if chosen is None:
        chosen_value = default_value
        chosen_name = "!default"
    else:
        chosen_name, chosen_value = chosen
    return Decision(
        id=DecisionId(
            f"{experiment_id}:{flag_key}:{subject_id}:{chosen_name}",
        ),
        flag_key=flag_key,
        value=chosen_value,
        experiment_id=experiment_id,
    )


@entity
@final
class ConflictResolution:
    domain: str
    experiment_id: str
    experiment_applied: bool
    policy: ConflictPolicy
