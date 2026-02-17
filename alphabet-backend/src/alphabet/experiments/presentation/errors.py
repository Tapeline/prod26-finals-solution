from types import MappingProxyType
from typing import Final

from alphabet.experiments.domain.dsl.exceptions import \
    InvalidTargetDSLExpression
from alphabet.experiments.domain.exceptions import (
    InvalidFlagKey,
    ExperimentNameCannotBeBlank,
    InvalidFlagValue,
    InvalidPercentageValue,
    VariantNameCannotBeBlank,
    ResultCommentCannotBeBlank,
    InvalidPriorityValue,
    DomainCannotBeBlank,
    InvalidConflictConfig,
    AudienceMismatch,
    NotOneControlVariant,
    ExperimentFrozen,
    CannotTransition,
    InvalidRejectionDecision,
)
from alphabet.experiments.application.exceptions import (
    NoSuchFlag,
    NoSuchExperiment,
    AlreadyApproved,
    ExperimentNotInReview,
    FlagAlreadyTaken,
)
from alphabet.shared.presentation.framework.errors import infer_code

flags_experiments_err_handlers: Final = MappingProxyType(
    {
        InvalidFlagKey: (400, infer_code),
        ExperimentNameCannotBeBlank: (400, infer_code),
        InvalidFlagValue: (400, infer_code),
        InvalidPercentageValue: (400, infer_code),
        VariantNameCannotBeBlank: (400, infer_code),
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
