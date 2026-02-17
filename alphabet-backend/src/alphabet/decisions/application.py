from abc import abstractmethod
from itertools import groupby
from logging import getLogger
from typing import Protocol, final

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
from alphabet.experiments.domain.experiment import ConflictPolicy, Experiment
from alphabet.shared.commons import interactor

logger = getLogger(__name__)


class FlagStorage(Protocol):
    @abstractmethod
    def get_default(self, flag_key: str) -> str:
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


class CooldownChecker(Protocol):
    @abstractmethod
    async def is_in_cooldown_or_set_if_needed(self, subject_id: str) -> bool:
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


@final
@interactor
class MakeDecision:
    cooldowns: CooldownChecker
    flags: FlagStorage
    experiments: ExperimentStorage
    resolutions_repo: ResolutionRepository

    async def __call__(
        self,
        subject_id: str,
        subject_attrs: dict[str, str],
        flag_keys: list[str],
    ) -> list[Decision]:
        # TODO: what to do if flag is missing?
        if await self.cooldowns.is_in_cooldown_or_set_if_needed(subject_id):
            return [
                self._default_for(flag_key, subject_id)
                for flag_key in flag_keys
            ]
        experiments = (
            exp
            for exp in self.experiments.get_experiments(flag_keys)
            if exp is not None
        )
        applied: list[CachedExperiment] = []
        affected_flags: set[str] = set()
        resolutions: list[ConflictResolution] = []
        for domain, conflicting in groupby(
            experiments,
            lambda e: e.conflict_domain,
        ):
            if domain is None:
                continue
            conflict: list[CachedExperiment] = list(conflicting)
            if any(
                exp.conflict_policy == ConflictPolicy.ONE_OR_NONE
                for exp in conflict
            ):
                resolutions.extend(
                    ConflictResolution(
                        domain=domain,
                        experiment_id=exp.id,
                        experiment_applied=False,
                        policy=ConflictPolicy.ONE_OR_NONE,
                    )
                    for exp in conflict
                )
                continue
            conflict.sort(key=lambda e: (e.priority, hash(e.id)))
            if len(conflict) > 1:
                resolutions.extend(
                    ConflictResolution(
                        domain=domain,
                        experiment_id=exp.id,
                        experiment_applied=i == 0,
                        policy=ConflictPolicy.ONE_OR_NONE,
                    )
                    for i, exp in enumerate(conflict)
                )
            if (
                conflict[0].targeting is None
                or conflict[0].targeting(subject_attrs).run()
            ):
                affected_flags.add(conflict[0].active_flag_key)
                applied.append(conflict[0])
        decisions = [
            make_decision(
                exp.active_flag_key,
                self.flags.get_default(exp.active_flag_key),
                exp.id,
                exp.distribution,
                subject_id,
            )
            for exp in applied
        ] + [
            self._default_for(flag_key, subject_id)
            for flag_key in flag_keys
            if flag_key not in affected_flags
        ]
        if resolutions:
            await self.resolutions_repo.save_resolutions(resolutions)
        return decisions

    def _default_for(self, flag_key: str, subject_id: str) -> Decision:
        value = self.flags.get_default(flag_key)
        return Decision(
            DecisionId(f"{flag_key}:{subject_id}:!default"),
            flag_key=flag_key,
            value=value,
            experiment_id=None,
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
        for key, default in await self.flags.all_defaults():
            self.flags_cache.set_flag_default(key, default)
        logger.info("Flag cache warmed up")
        for experiment in await self.experiments.all_running():
            self.experiments_cache.set_on_flag(
                experiment.flag_key.value,
                cached_experiment_from_experiment(experiment),
            )
        logger.info("Experiment cache warmed up")
        self.experiments_cache.mark_ready()
        self.flags_cache.mark_ready()
        logger.info("Decision cache is ready")


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
    )
