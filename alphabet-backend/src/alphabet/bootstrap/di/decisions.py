from dishka import Provider, Scope, provide, provide_all

from alphabet.decisions.application import (
    AssignmentStore,
    DecisionDataStore,
    ExperimentStorage,
    FlagStorage,
    MakeDecision,
    ReadConflictsByDomain,
    ReadConflictsByExperiment,
    ReadDistributionOnExperiment,
    ResolutionRepository,
    SetFlagDefault,
    SetRunningExperimentOnFlag,
    WarmUpStorages,
)
from alphabet.decisions.infrastructure.assign_store import (
    ClickHouseAssignmentStore,
)
from alphabet.decisions.infrastructure.resolutions_repo import (
    ClickHouseResolutionRepository,
)
from alphabet.decisions.infrastructure.storage import (
    InMemoryExperimentStorage,
    InMemoryFlagStorage,
)
from alphabet.decisions.infrastructure.valkey import ValkeyDecisionDataStore


class DecisionsDIProvider(Provider):
    interactors = provide_all(
        MakeDecision,
        SetFlagDefault,
        SetRunningExperimentOnFlag,
        WarmUpStorages,
        ReadConflictsByExperiment,
        ReadConflictsByDomain,
        ReadDistributionOnExperiment,
        scope=Scope.REQUEST,
    )
    flag_store = provide(
        InMemoryFlagStorage,
        provides=FlagStorage,
        scope=Scope.APP,
    )
    experiment_store = provide(
        InMemoryExperimentStorage,
        provides=ExperimentStorage,
        scope=Scope.APP,
    )
    valkey = provide(
        ValkeyDecisionDataStore,
        provides=DecisionDataStore,
        scope=Scope.REQUEST,
    )
    resolutions_repo = provide(
        ClickHouseResolutionRepository,
        provides=ResolutionRepository,
        scope=Scope.APP,
    )
    assignment_store = provide(
        ClickHouseAssignmentStore,
        provides=AssignmentStore,
        scope=Scope.APP,
    )


class DecisionsCacheSyncsDIProvider(DecisionsDIProvider):
    interactors = provide_all(
        SetFlagDefault,
        SetRunningExperimentOnFlag,
        scope=Scope.REQUEST,
    )


def get_decisions_providers() -> list[Provider]:
    return [
        DecisionsDIProvider(),
        DecisionsCacheSyncsDIProvider(),
    ]
