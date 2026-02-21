from abc import abstractmethod
from typing import Protocol

from alphabet.experiments.domain.experiment import (
    Approval,
    Experiment,
    ExperimentId,
    ReviewDecision,
)
from alphabet.experiments.domain.flags import FeatureFlag, FlagKey
from alphabet.shared.application.pagination import Pagination


class FlagRepository(Protocol):
    @abstractmethod
    async def get_by_key(self, key: FlagKey) -> FeatureFlag | None:
        raise NotImplementedError

    @abstractmethod
    async def create(self, flag: FeatureFlag) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, flag: FeatureFlag) -> None:
        raise NotImplementedError

    @abstractmethod
    async def lock_on(self, flag_key: FlagKey) -> None:
        raise NotImplementedError

    @abstractmethod
    async def all(self, pagination: Pagination) -> list[FeatureFlag]:
        raise NotImplementedError

    @abstractmethod
    async def all_defaults(self) -> list[tuple[str, str]]:
        """Get list[tuple[flag name, default value]]."""
        raise NotImplementedError


class ExperimentsRepository(Protocol):
    @abstractmethod
    async def get_latest_by_id(
        self,
        exp_id: ExperimentId,
        *,
        lock: bool = False,
    ) -> Experiment | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id_and_version(
        self,
        exp_id: ExperimentId,
        version: int,
    ) -> Experiment | None:
        raise NotImplementedError

    @abstractmethod
    async def get_old_versions(self, exp_id: ExperimentId) -> list[Experiment]:
        raise NotImplementedError

    @abstractmethod
    async def create(self, experiment: Experiment) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, experiment: Experiment) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_active_by_flag(
        self,
        flag_key: FlagKey,
    ) -> Experiment | None:
        raise NotImplementedError

    @abstractmethod
    async def all(self, pagination: Pagination) -> list[Experiment]:
        raise NotImplementedError

    @abstractmethod
    async def all_running(self) -> list[Experiment]:
        raise NotImplementedError

    @abstractmethod
    async def all_running_and_security_halted(self) -> list[Experiment]:
        """For decide cache: STARTED + SECURITY_HALTED (usecase step 2)."""
        raise NotImplementedError


class ReviewRepository(Protocol):
    @abstractmethod
    async def all_approvals(self, exp_id: ExperimentId) -> list[Approval]:
        raise NotImplementedError

    @abstractmethod
    async def create_approval(self, approval: Approval) -> None:
        raise NotImplementedError

    @abstractmethod
    async def revoke_all_approvals(self, exp_id: ExperimentId) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save_decision(
        self,
        decision: ReviewDecision,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_decision(
        self,
        exp_id: ExperimentId,
    ) -> ReviewDecision | None:
        raise NotImplementedError


class FlagChangeNotifier(Protocol):
    @abstractmethod
    async def notify_flag_default_changed(
        self,
        flag_key: FlagKey,
        new_default: str,
    ) -> None:
        raise NotImplementedError


class ExperimentChangeNotifier(Protocol):
    @abstractmethod
    async def notify_experiment_activated(
        self,
        experiment: Experiment,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def notify_experiment_deactivated(
        self,
        experiment: Experiment,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def notify_experiment_halted(
        self,
        experiment: Experiment,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def notify_experiment_state_changed(
        self,
        experiment: Experiment,
    ) -> None:
        raise NotImplementedError
