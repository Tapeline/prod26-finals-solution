from abc import abstractmethod
from typing import Protocol

from alphabet.experiments.domain.experiment import ExperimentId
from alphabet.guardrails.domain import AuditRecord, GuardRule, GuardRuleId
from alphabet.shared.application.pagination import Pagination


class GuardRuleRepository(Protocol):
    @abstractmethod
    async def create(self, rule: GuardRule) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, rule: GuardRule) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, rule_id: GuardRuleId) -> GuardRule | None:
        raise NotImplementedError

    @abstractmethod
    async def for_experiment(
        self,
        experiment_id: ExperimentId,
    ) -> list[GuardRule]:
        raise NotImplementedError

    @abstractmethod
    async def for_experiments(
        self,
        experiment_ids: list[ExperimentId],
    ) -> list[GuardRule]:
        raise NotImplementedError


class AuditLog(Protocol):
    @abstractmethod
    async def write(self, record: AuditRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    async def query_for_experiment(
        self,
        exp_id: ExperimentId,
        pagination: Pagination,
    ) -> list[AuditRecord]:
        raise NotImplementedError

    @abstractmethod
    async def query_for_rule(
        self,
        rule_id: GuardRuleId,
        pagination: Pagination,
    ) -> list[AuditRecord]:
        raise NotImplementedError
