from typing import final

from alphabet.shared.domain.exceptions import AppException


@final
class NoSuchFlag(AppException):
    text = "No such flag"


@final
class NoSuchExperiment(AppException):
    text = "No such experiment"


@final
class AlreadyApproved(AppException):
    text = "Already approved"


@final
class ExperimentNotInReview(AppException):
    text = "Experiment is not in review"


@final
class FlagAlreadyTaken(AppException):
    text = "This flag is already taken by another running experiment"


@final
class FlagKeyAlreadyExists(AppException):
    text = "Flag key already exists"
