import re
from datetime import datetime
from enum import StrEnum
from typing import Final, final

from alphabet.experiments.domain.exceptions import (
    InvalidFlagKey,
    InvalidFlagValue,
)
from alphabet.shared.commons import entity, value_object
from alphabet.shared.domain.user import UserId

_FLAG_KEY_RE: Final = re.compile("[A-Za-z0-9_-]+")


@value_object
class FlagKey:
    value: str

    def __post_init__(self) -> None:
        if not _FLAG_KEY_RE.fullmatch(self.value):
            raise InvalidFlagKey


@final
class FlagType(StrEnum):
    BOOLEAN = "boolean"
    NUMBER = "number"
    STRING = "string"


@entity
class FeatureFlag:
    _key: FlagKey
    _description: str
    _type: FlagType
    _default: str
    _author_id: UserId
    _created_at: datetime
    _updated_at: datetime

    @classmethod
    def new(
        cls,
        key: FlagKey,
        description: str,
        type: FlagType,
        default: str,
        author_id: UserId,
        created_at: datetime,
        updated_at: datetime,
    ) -> "FeatureFlag":
        flag = FeatureFlag(
            key,
            description,
            type,
            default,
            author_id,
            created_at,
            updated_at,
        )
        flag.validate_type_value(default)
        return flag

    @property
    def key(self) -> FlagKey:
        return self._key

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, description: str) -> None:
        self._description = description

    @property
    def type(self) -> FlagType:
        return self._type

    @property
    def default(self) -> str:
        return self._default

    @default.setter
    def default(self, value: str) -> None:
        self.validate_type_value(value)
        self._default = value

    @property
    def author_id(self) -> UserId:
        return self._author_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @updated_at.setter
    def updated_at(self, updated_at: datetime) -> None:
        self._updated_at = updated_at

    def validate_type_value(self, value: str) -> None:
        if self._type == FlagType.BOOLEAN:
            if value not in {"true", "false"}:
                raise InvalidFlagValue
        elif self._type == FlagType.NUMBER:
            try:
                float(value)
            except ValueError:
                raise InvalidFlagValue from None
        elif self._type == FlagType.STRING:
            # no validation for strings
            return
        else:
            raise ValueError("Unknown flag type", self._type)
