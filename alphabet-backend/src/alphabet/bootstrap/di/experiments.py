from dishka import AnyOf, Provider, Scope, provide, provide_all

from alphabet.experiments.application.interactors.experiments import (
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
)
from alphabet.experiments.application.interactors.flags import (
    CreateFlag,
    ReadAllFlags,
    ReadFlag,
    UpdateFlag,
)
from alphabet.access.application.interfaces import UserRepository
from alphabet.access.infrastructure.repos import SqlUserRepository
from alphabet.experiments.application.interfaces import (
    FlagRepository,
    ExperimentsRepository, ReviewRepository,
)
from alphabet.experiments.infrastructure.experiments_repo import \
    SqlExperimentsRepository
from alphabet.experiments.infrastructure.flags_repo import SqlFlagRepository
from alphabet.experiments.infrastructure.reviews_repo import \
    SqlReviewRepository
from alphabet.experiments.presentation.flags import FlagResponse
from alphabet.shared.application.transaction import TransactionManager
from alphabet.shared.application.user import UserReader


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
        scope=Scope.REQUEST
    )
    experiments_repo = provide(
        SqlExperimentsRepository,
        provides=ExperimentsRepository,
        scope=Scope.REQUEST
    )
    reviews_repo = provide(
        SqlReviewRepository,
        provides=ReviewRepository,
        scope=Scope.REQUEST
    )
