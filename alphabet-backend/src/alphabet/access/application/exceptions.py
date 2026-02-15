from typing import final

from alphabet.shared.domain.exceptions import AppException


@final
class EmailAlreadyRegistered(AppException):
    text = "Your email is already registered. Contact your administrator"


@final
class UserIsAnonymous(AppException):
    text = "User is not logged in"


@final
class UserNotFound(AppException):
    text = "User not found. Contact your administrator"


@final
class EmailNotRegistered(AppException):
    text = "Your email is not registered. Contact your administrator"


@final
class AlreadyActivated(AppException):
    text = "User is already activated"


@final
class CannotSetReviewRulesForNonExperimenter(AppException):
    text = "Review rules (approver group) can exist only for experimenters"


@final
class NoSuchApproverGroup(AppException):
    text = "Approver group not set for this user"
