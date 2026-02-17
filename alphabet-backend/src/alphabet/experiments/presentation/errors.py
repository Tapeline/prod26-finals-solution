from types import MappingProxyType
from typing import Final

from alphabet.experiments.application.exceptions import (
    AlreadyApproved,
    ExperimentNotInReview,
    FlagAlreadyTaken,
    NoSuchExperiment,
    NoSuchFlag,
)
from alphabet.experiments.domain.dsl.exceptions import (
    InvalidTargetDSLExpression,
)
from alphabet.experiments.domain.exceptions import (
    AudienceMismatch,
    CannotTransition,
    DomainCannotBeBlank,
    ExperimentFrozen,
    ExperimentNameCannotBeBlank,
    InvalidConflictConfig,
    InvalidFlagKey,
    InvalidFlagValue,
    InvalidPercentageValue,
    InvalidPriorityValue,
    InvalidRejectionDecision,
    InvalidVariantName,
    NotOneControlVariant,
    ResultCommentCannotBeBlank,
)
from alphabet.shared.presentation.framework.errors import infer_code

flags_experiments_err_handlers: Final = MappingProxyType(
    {
        InvalidFlagKey: (400, infer_code),
        ExperimentNameCannotBeBlank: (400, infer_code),
        InvalidFlagValue: (400, infer_code),
        InvalidPercentageValue: (400, infer_code),
        InvalidVariantName: (400, infer_code),
        ResultCommentCannotBeBlank: (400, infer_code),
        InvalidPriorityValue: (400, infer_code),
        DomainCannotBeBlank: (400, infer_code),
        InvalidConflictConfig: (400, infer_code),
        AudienceMismatch: (400, infer_code),
        NotOneControlVariant: (400, infer_code),
        ExperimentFrozen: (409, infer_code),
        CannotTransition: (409, infer_code),
        InvalidRejectionDecision: (400, infer_code),
        InvalidTargetDSLExpression: (400, infer_code),
        NoSuchFlag: (404, infer_code),
        NoSuchExperiment: (404, infer_code),
        AlreadyApproved: (409, infer_code),
        ExperimentNotInReview: (409, infer_code),
        FlagAlreadyTaken: (409, infer_code),
    },
)
