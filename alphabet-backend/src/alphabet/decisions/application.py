from abc import abstractmethod
from collections.abc import Collection
from datetime import datetime
from itertools import groupby
from operator import attrgetter
from typing import Protocol, cast, final

import mmh3
from structlog import getLogger

from alphabet.decisions.domain import (
    CachedExperiment,
    ConflictResolution,
    Decision,
    DecisionId,
    make_decision,
)
from alphabet.experiments.application.interfaces import (
    ExperimentsRepository,
    FlagRepository,
)
from alphabet.experiments.domain.dsl.dsl import compile_dsl
from alphabet.experiments.domain.experiment import (
    ConflictDomain,
    ConflictPolicy,
    Experiment,
    ExperimentId,
    ExperimentState,
)
from alphabet.shared.application.idp import UserIdProvider
from alphabet.shared.application.time import TimeProvider
from alphabet.shared.application.user import UserReader, require_any_user
from alphabet.shared.commons import dto, interactor
from alphabet.shared.uuid import generate_uuid

logger = getLogger(__name__)


class FlagStorage(Protocol):
    @abstractmethod
    def get_default(self, flag_key: str) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def set_flag_default(self, flag_key: str, value: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_ready(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def mark_ready(self) -> None:
        raise NotImplementedError


class DecisionDataStore(Protocol):
    @abstractmethod
    async def is_in_cooldown(self, subject_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def save_decisions(
        self,
        subject_id: str,
        decisions: Collection[Decision],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def load_existing_decisions(
        self,
        subject_id: str,
        flag_keys: list[str],
        experiment_ids: set[str],
    ) -> dict[str, Decision]:
        raise NotImplementedError

    @abstractmethod
    async def record_experiment_assignments(
        self,
        subject_id: str,
        count: int,
    ) -> None:
        raise NotImplementedError


class ExperimentStorage(Protocol):
    @abstractmethod
    def get_experiments(
        self,
        flag_keys: list[str],
    ) -> list[CachedExperiment | None]:
        raise NotImplementedError

    @abstractmethod
    def set_on_flag(
        self,
        flag_key: str,
        experiment: CachedExperiment | None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_ready(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def mark_ready(self) -> None:
        raise NotImplementedError


class ResolutionRepository(Protocol):
    @abstractmethod
    async def save_resolutions(
        self,
        resolutions: list[ConflictResolution],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def count_conflicts_by_domain(
        self,
        domain: ConflictDomain,
    ) -> dict[ExperimentId, int]:
        raise NotImplementedError

    @abstractmethod
    async def count_conflicts_by_experiment(
        self,
        experiment_id: ExperimentId,
    ) -> tuple[dict[ConflictPolicy, int], dict[ConflictPolicy, int]]:
        """Returns wins/losses in conflicts."""
        raise NotImplementedError

    @abstractmethod
    async def periodic_flush_routine(self) -> None:
        raise NotImplementedError


class AssignmentStore(Protocol):
    @abstractmethod
    async def get_variant_distribution(
        self,
        experiment_id: str
    ) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    async def periodic_flush_routine(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save_assignments(
        self,
        decisions: list[Decision],
        decided_at: datetime,
        subject_id: str,
    ) -> None:
        raise NotImplementedError


@final
@interactor
class MakeDecision:
    decision_data: DecisionDataStore
    flags: FlagStorage
    experiments: ExperimentStorage
    resolutions_repo: ResolutionRepository
    assignment_store: AssignmentStore
    time: TimeProvider

    async def __call__(  # noqa: C901
        self,
        subject_id: str,
        subject_attrs: dict[str, str],
        flag_keys: list[str],
    ) -> dict[str, Decision | None]:
        # active + security halted
        experiments = self._get_experiments_for_flags(flag_keys)

        assigned: dict[str, Decision | None] = {}
        assigned |= await self.decision_data.load_existing_decisions(
            subject_id,
            flag_keys,
            {exp.id for exp in experiments},
        )
        unassigned = set(flag_keys) - set(assigned.keys())
        logger.debug("decided already for %s", list(assigned.keys()))

        in_cooldown = await self.decision_data.is_in_cooldown(subject_id)
        if in_cooldown:
            for flag in unassigned:
                assigned[flag] = self._default_for(flag, subject_id)
            return assigned

        resolved, resolutions = self._resolve_conflicts(experiments)
        resolved_by_flag = {exp.active_flag_key: exp for exp in resolved}

        new_decision_count = 0
        for flag in list(unassigned):
            exp = resolved_by_flag.get(flag)
            if not exp:
                assigned[flag] = self._default_for(flag, subject_id)
                unassigned.discard(flag)
                continue
            if exp.targeting and not exp.targeting(subject_attrs).run():
                assigned[flag] = self._default_for(flag, subject_id)
                unassigned.discard(flag)
                continue
            decision = self._assign_variant(
                subject_id,
                exp,
                flag,
            )
            if decision:
                assigned[flag] = decision
                unassigned.discard(flag)
                new_decision_count += 1

        for flag in unassigned:
            assigned[flag] = self._default_for(flag, subject_id)

        new_decisions = [
            d for d in assigned.values() if d and d.experiment_id is not None
        ]
        if new_decisions:
            await self.decision_data.save_decisions(subject_id, new_decisions)
            await self.assignment_store.save_assignments(
                new_decisions, self.time.now(), subject_id
            )
        if resolutions:
            await self.resolutions_repo.save_resolutions(resolutions)

        if new_decision_count > 0:
            await self.decision_data.record_experiment_assignments(
                subject_id,
                new_decision_count,
            )

        return assigned

    def _assign_variant(
        self,
        subject_id: str,
        experiment: CachedExperiment,
        flag_key: str,
    ) -> Decision | None:
        flag_default = self.flags.get_default(flag_key)
        if flag_default is None:
            logger.warning(
                "Requested unknown flag",
                subject=subject_id,
                flag=flag_key,
            )
            return None
        if experiment.is_security_halted:
            control = next(
                (v for v in experiment.variants if v.is_control),
                experiment.variants[0],
            )
            return Decision(
                DecisionId(
                    f"{experiment.id}:{flag_key}:{subject_id}:{control.name}",
                ),
                flag_key=flag_key,
                variant_id=control.name,
                value=control.value,
                experiment_id=experiment.id,
            )
        return make_decision(
            flag_key,
            flag_default,
            experiment.id,
            experiment.distribution,
            subject_id,
        )

    def _resolve_conflicts(
        self,
        experiments: list[CachedExperiment],
    ) -> tuple[list[CachedExperiment], list[ConflictResolution]]:
        resolutions: list[ConflictResolution] = []
        survivors: list[CachedExperiment] = []

        def _domain_key(exp: CachedExperiment) -> tuple[int, str]:
            d = exp.conflict_domain
            return (0 if d is None else 1, d or "")

        for domain, group in groupby(
            sorted(experiments, key=_domain_key),
            attrgetter("conflict_domain"),
        ):
            if domain is None:
                survivors.extend(group)
                continue
            conflicts = list(group)
            if len(conflicts) == 1:
                survivors.append(conflicts[0])
                continue
            policy = self._choose_policy(conflicts)
            selected = self._apply_policy(
                policy,
                domain,
                conflicts,
                resolutions,
            )
            if selected:
                survivors.append(selected)
        return survivors, resolutions

    def _choose_policy(
        self,
        conflicts: list[CachedExperiment],
    ) -> ConflictPolicy:
        for exp in conflicts:
            if exp.conflict_policy == ConflictPolicy.ONE_OR_NONE:
                return ConflictPolicy.ONE_OR_NONE
        return ConflictPolicy.HIGHER_PRIORITY

    def _apply_policy(
        self,
        policy: ConflictPolicy,
        domain: str,
        conflicts: list[CachedExperiment],
        out: list[ConflictResolution],
    ) -> CachedExperiment | None:
        if policy == ConflictPolicy.ONE_OR_NONE:
            out.extend(
                ConflictResolution(
                    domain=domain,
                    experiment_id=exp.id,
                    experiment_applied=False,
                    policy=ConflictPolicy.ONE_OR_NONE,
                )
                    for exp in conflicts
            )
            return None
        with_priority = [exp for exp in conflicts if exp.priority is not None]
        if not with_priority:
            return None

        winner = min(
            with_priority,
            key=lambda exp: (
                exp.priority,
                -mmh3.hash(f"{domain}:{exp.id}", signed=False)  # tie-breaker
            )
        )
        out.extend(
            ConflictResolution(
                domain=domain,
                experiment_id=exp.id,
                experiment_applied=(exp is winner),
                policy=ConflictPolicy.HIGHER_PRIORITY,
            )
                for exp in conflicts
        )
        return winner

    def _get_experiments_for_flags(
        self,
        flag_keys: list[str],
    ) -> list[CachedExperiment]:
        return [
            exp
            for exp in self.experiments.get_experiments(flag_keys)
            if exp is not None
        ]

    def _default_for(
        self,
        flag_key: str,
        subject_id: str,
    ) -> Decision | None:
        value = self.flags.get_default(flag_key)
        if value is None:
            return None
        return Decision(
            DecisionId(f":{flag_key}:{subject_id}:!default-{generate_uuid()}"),
            flag_key=flag_key,
            value=value,
            experiment_id=None,
            variant_id="!default",
        )


@final
@interactor
class SetFlagDefault:
    flags: FlagStorage

    def __call__(self, flag_key: str, default: str) -> None:
        self.flags.set_flag_default(flag_key, default)


@final
@interactor
class SetRunningExperimentOnFlag:
    experiments: ExperimentStorage

    def __call__(
        self,
        flag_key: str,
        experiment: CachedExperiment | None,
    ) -> None:
        self.experiments.set_on_flag(flag_key, experiment)


@final
@interactor
class WarmUpStorages:
    flags: FlagRepository
    experiments: ExperimentsRepository
    flags_cache: FlagStorage
    experiments_cache: ExperimentStorage

    async def __call__(self) -> None:
        logger.info("Warming up decision cache")
        flags = await self.flags.all_defaults()
        for key, default in flags:
            self.flags_cache.set_flag_default(key, default)
        logger.info("Flag cache warmed up for %s entries", len(flags))
        experiments = await self.experiments.all_running_and_security_halted()
        for experiment in experiments:
            self.experiments_cache.set_on_flag(
                experiment.flag_key.value,
                cached_experiment_from_experiment(experiment),
            )
        logger.info(
            "Experiment cache warmed up for %s entries",
            len(experiments),
        )
        self.experiments_cache.mark_ready()
        self.flags_cache.mark_ready()
        logger.info("Decision cache ready")


def cached_experiment_from_experiment(
    experiment: Experiment,
) -> CachedExperiment:
    return CachedExperiment(
        id=experiment.id,
        variants=experiment.variants,
        targeting=compile_dsl(experiment.targeting.value)
        if experiment.targeting
        else None,
        conflict_domain=experiment.conflict_domain.value
        if experiment.conflict_domain
        else None,
        conflict_policy=experiment.conflict_policy,
        priority=experiment.priority.value if experiment.priority else None,
        active_flag_key=experiment.flag_key.value,
        experiment_audience=experiment.audience.value,
        is_security_halted=(
            experiment.state == ExperimentState.SECURITY_HALTED
        ),
    )


@final
@interactor
class ReadConflictsByDomain:
    idp: UserIdProvider
    user_reader: UserReader
    resolutions: ResolutionRepository

    async def __call__(
        self,
        domain: ConflictDomain,
    ) -> dict[ExperimentId, int]:
        await require_any_user(self)
        return await self.resolutions.count_conflicts_by_domain(domain)


@final
@dto
class ExperimentConflictsDTO:
    wins: dict[ConflictPolicy, int]
    losses: dict[ConflictPolicy, int]


@final
@interactor
class ReadConflictsByExperiment:
    idp: UserIdProvider
    user_reader: UserReader
    resolutions: ResolutionRepository

    async def __call__(
        self,
        experiment_id: ExperimentId,
    ) -> ExperimentConflictsDTO:
        await require_any_user(self)
        wins, losses = await self.resolutions.count_conflicts_by_experiment(
            experiment_id,
        )
        return ExperimentConflictsDTO(
            wins=wins,
            losses=losses,
        )


@final
@interactor
class ReadDistributionOnExperiment:
    idp: UserIdProvider
    user_reader: UserReader
    assignments: AssignmentStore

    async def __call__(self, experiment_id: ExperimentId) -> dict[str, int]:
        await require_any_user(self)
        return await self.assignments.get_variant_distribution(experiment_id)
