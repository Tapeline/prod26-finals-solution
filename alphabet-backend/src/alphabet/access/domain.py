from enum import StrEnum
from typing import NewType, final

from alphabet.shared.commons import entity, value_object
from alphabet.shared.exceptions import AppException

IapId = NewType("IapId", str)
UserId = NewType("UserId", str)


@final
class Role(StrEnum):
    ADMIN = "admin"
    EXPERIMENTER = "experimenter"
    APPROVER = "approver"
    VIEWER = "viewer"


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


@final
@entity
class User:
    id: UserId
    iap_id: IapId | None
    email: str
    role: Role

    @property
    def is_active(self) -> bool:
        return self.iap_id is not None
