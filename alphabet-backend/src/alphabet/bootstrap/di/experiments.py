from dishka import Provider, Scope, provide, provide_all

from alphabet.experiments.application.interactors.experiments import (
    ApproveDraft,
    ArchiveExperiment,
    CreateExperiment,
    ManageRunningExperiment,
    ReadExperimentAudit,
    ReadExperimentVersion,
    ReadExperimentVersionHistory,
    RejectDraft,
    RestoreFromRejected,
    SendToReview,
    StartExperiment,
    UpdateExperiment,
)
from alphabet.experiments.application.interactors.flags import (
    CreateFlag,
    ReadAllFlags,
    ReadFlag,
    UpdateFlag,
)
from alphabet.experiments.application.interfaces import (
    ExperimentsRepository,
    FlagRepository,
    ReviewRepository,
)
from alphabet.experiments.infrastructure.experiments_repo import (
    SqlExperimentsRepository,
)
from alphabet.experiments.infrastructure.flags_repo import SqlFlagRepository
from alphabet.experiments.infrastructure.reviews_repo import (
    SqlReviewRepository,
)


class FlagsExperimentsDIProvider(Provider):
    interactors = provide_all(
        CreateExperiment,
        RejectDraft,
        SendToReview,
        UpdateExperiment,
        ApproveDraft,
        RestoreFromRejected,
        StartExperiment,
        ManageRunningExperiment,
        ArchiveExperiment,
        ReadExperimentVersion,
        ReadExperimentVersionHistory,
        ReadExperimentAudit,
        CreateFlag,
        ReadAllFlags,
        ReadFlag,
        UpdateFlag,
        scope=Scope.REQUEST,
    )

    flags_repo = provide(
        SqlFlagRepository,
        provides=FlagRepository,
        scope=Scope.REQUEST,
    )
    experiments_repo = provide(
        SqlExperimentsRepository,
        provides=ExperimentsRepository,
        scope=Scope.REQUEST,
    )
    reviews_repo = provide(
        SqlReviewRepository,
        provides=ReviewRepository,
        scope=Scope.REQUEST,
    )


class OnlyExperimentRepoDIProvider(Provider):
    experiments_repo = provide(
        SqlExperimentsRepository,
        provides=ExperimentsRepository,
        scope=Scope.REQUEST,
    )
