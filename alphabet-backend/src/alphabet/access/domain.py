from typing import final

from alphabet.shared.commons import value_object
from alphabet.shared.domain.exceptions import AppException
from alphabet.shared.domain.user import UserId


class InvalidThreshold(AppException):
    text = "Threshold must be greater than 1 and less than approver count"


@final
@value_object
class ApproverGroup:
    approvers: list[UserId]
    threshold: int

    def __post_init__(self) -> None:
        if self.threshold < 1:
            raise InvalidThreshold
        if self.threshold > len(self.approvers):
            raise InvalidThreshold
