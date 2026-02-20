from abc import abstractmethod
from collections.abc import Collection
from itertools import groupby
from operator import attrgetter
from typing import Protocol, assert_never, final

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
from alphabet.experiments.domain.experiment import ConflictPolicy, Experiment
from alphabet.shared.commons import interactor
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
    async def is_in_cooldown_or_set_if_needed(self, subject_id: str) -> bool:
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
    decision_data: DecisionDataStore
    flags: FlagStorage
    experiments: ExperimentStorage
    resolutions_repo: ResolutionRepository

    # TODO: reworked completely, edit ADR to match

    async def __call__(
        self,
        subject_id: str,
        subject_attrs: dict[str, str],
        flag_keys: list[str],
    ) -> dict[str, Decision | None]:
        logger.debug("making decision for %s", subject_id)
        experiments = self._get_only_running_experiments(flag_keys)
        in_cooldown = await self.decision_data.is_in_cooldown_or_set_if_needed(
            subject_id,
        )

        unassigned = set(flag_keys)
        assigned: dict[str, Decision | None] = {}
        assigned |= await self.decision_data.load_existing_decisions(
            subject_id,
            flag_keys,
            {exp.id for exp in experiments},
        )
        logger.debug("decided already for %s", str(assigned.keys()))
        unassigned.difference_update(assigned.keys())

        resolved, resolutions = self._resolve_conflicts(experiments)
        logger.debug("after resolution %s", str(resolved))
        resolved_keys_to_experiments = {
            experiment.active_flag_key: experiment for experiment in resolved
        }
        for flag in unassigned:
            experiment = resolved_keys_to_experiments.get(flag)
            if not experiment:
                logger.debug("defaulting no exp %s", flag)
                assigned[flag] = self._default_for(flag, subject_id)
            elif (
                experiment.targeting
                and not experiment.targeting(subject_attrs).run()
            ):
                logger.debug("defaulting no match %s", flag)
                assigned[flag] = self._default_for(flag, subject_id)
            elif in_cooldown:
                logger.debug("defaulting due to cooldown %s", flag)
                assigned[flag] = self._default_for(flag, subject_id)
            else:
                logger.debug("assigning %s", flag)
                assigned[flag] = self._make_decision(
                    subject_id,
                    experiment,
                )

        unassigned.difference_update(assigned.keys())
        for left_flag in unassigned:
            logger.debug("defaulting unassigned %s", left_flag)
            assigned[left_flag] = self._default_for(left_flag, subject_id)

        await self.decision_data.save_decisions(
            subject_id,
            [
                decision
                for decision in assigned.values()
                if decision and decision.experiment_id is not None
            ],
        )
        if resolutions:
            # TODO: maybe move to background
            await self.resolutions_repo.save_resolutions(resolutions)
        return assigned

    def _resolve_conflicts(
        self,
        experiments: list[CachedExperiment],
    ) -> tuple[list[CachedExperiment], list[ConflictResolution]]:
        resolutions: list[ConflictResolution] = []
        survivors: list[CachedExperiment] = []
        for domain, conflicts in groupby(
            sorted(experiments, key=attrgetter("conflict_domain")),
            attrgetter("conflict_domain"),
        ):
            if domain is None:
                survivors.extend(conflicts)
                continue
            conflicts_list = list(conflicts)
            policy = self._choose_policy(conflicts_list)
            selected = self._apply_policy(
                policy,
                domain,
                conflicts_list,
                resolutions,
            )
            if selected:
                survivors.append(selected)
        return survivors, resolutions

    def _apply_policy(
        self,
        policy: ConflictPolicy,
        domain: str,
        conflicts: list[CachedExperiment],
        resolutions_to_store: list[ConflictResolution],
    ) -> CachedExperiment | None:
        match policy:
            case ConflictPolicy.ONE_OR_NONE:
                resolutions_to_store.extend(
                    ConflictResolution(
                        domain=domain,
                        experiment_id=experiment.id,
                        experiment_applied=False,
                        policy=ConflictPolicy.ONE_OR_NONE,
                    )
                    for experiment in conflicts
                )
                return None
            case ConflictPolicy.HIGHER_PRIORITY:
                winner, *_ = sorted(
                    filter(lambda exp: exp.priority is not None, conflicts),
                    key=lambda exp: (exp.priority, hash(exp.id)),
                )
                resolutions_to_store.extend(
                    ConflictResolution(
                        domain=domain,
                        experiment_id=experiment.id,
                        experiment_applied=experiment is winner,
                        policy=ConflictPolicy.HIGHER_PRIORITY,
                    )
                    for experiment in conflicts
                )
                return winner
            case _:
                assert_never(policy)

    def _choose_policy(
        self,
        conflicting: list[CachedExperiment],
    ) -> ConflictPolicy:
        policy = None
        for experiment in conflicting:
            match experiment.conflict_policy:
                case ConflictPolicy.ONE_OR_NONE:
                    return ConflictPolicy.ONE_OR_NONE
                case ConflictPolicy.HIGHER_PRIORITY:
                    policy = ConflictPolicy.HIGHER_PRIORITY
                case None:
                    raise AssertionError("Cannot be none here")
                case _:
                    assert_never(experiment.conflict_policy)
        if policy is None:
            raise AssertionError("Cannot be none here")
        return policy

    def _make_decision(
        self,
        subject_id: str,
        experiment: CachedExperiment,
    ) -> Decision | None:
        flag_default = self.flags.get_default(experiment.active_flag_key)
        if flag_default is None:
            return None
        return make_decision(
            experiment.active_flag_key,
            flag_default,
            experiment.id,
            experiment.distribution,
            subject_id,
        )

    def _get_only_running_experiments(
        self,
        flag_keys: list[str],
    ) -> list[CachedExperiment]:
        return [
            exp
            for exp in self.experiments.get_experiments(flag_keys)
            if exp is not None
        ]

    def _default_for(self, flag_key: str, subject_id: str) -> Decision | None:
        value = self.flags.get_default(flag_key)
        if value is None:
            return None
        return Decision(
            # TODO: REFACTOR ONE MORE TIME
            # TODO: at least make decision ids uniform so
            #       I can pull out flag and exp ids on event site
            # idk, can we just leave it like that?
            DecisionId(f":{flag_key}:{subject_id}:!default-{generate_uuid()}"),
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
        flags = await self.flags.all_defaults()
        for key, default in flags:
            self.flags_cache.set_flag_default(key, default)
        logger.info("Flag cache warmed up for %s entries", len(flags))
        experiments = await self.experiments.all_running()
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
        experiment_audience=experiment.audience.value,
    )
