from enum import StrEnum
from typing import NewType, final

from alphabet.shared.commons import entity

IapId = NewType("IapId", str)
UserId = NewType("UserId", str)


@final
class Role(StrEnum):
    ADMIN = "admin"
    EXPERIMENTER = "experimenter"
    APPROVER = "approver"
    VIEWER = "viewer"


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
