from typing import final

from alphabet.experiments.domain.experiment import ExperimentState
from alphabet.shared.domain.exceptions import AppException


@final
class InvalidFlagKey(AppException):
    text = "Flag key must satisfy [A-Za-z0-9_-]+"


@final
class ExperimentNameCannotBeBlank(AppException):
    text = "Experiment name cannot be blank"


@final
class InvalidFlagValue(AppException):
    text = "This flag value is not applicable to flag type"


@final
class InvalidPercentageValue(AppException):
    text = "Percentage must be between 0 and 100"


@final
class VariantNameCannotBeBlank(AppException):
    text = "Variant name cannot be blank"


@final
class ResultCommentCannotBeBlank(AppException):
    text = "Comment cannot be blank"


@final
class InvalidPriorityValue(AppException):
    text = "Priority must be no less than 0"


@final
class DomainCannotBeBlank(AppException):
    text = "Conflict domain cannot be blank"


@final
class InvalidConflictConfig(AppException):
    text = (
        "Either both conflict domain and conflict "
        "policy should be set or not"
    )


@final
class AudienceMismatch(AppException):
    text = "Variant audiences must sum up to experiment audience"


@final
class NotOneControlVariant(AppException):
    text = "Exactly one variant must be control"


@final
class ExperimentFrozen(AppException):
    text = "Experiments can be edited only in draft state"


@final
class CannotTransition(AppException):
    def __init__(
        self,
        from_state: ExperimentState,
        to_state: ExperimentState
    ) -> None:
        self.from_state = from_state
        self.to_state = to_state
        self.text = f"Cannot transition from {from_state} to {to_state}"


@final
class InvalidRejectionDecision(AppException):
    text = "If rejected, both rejecter_id and reject_comment must be set"
