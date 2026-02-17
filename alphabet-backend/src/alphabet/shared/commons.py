from operator import attrgetter

from dataclasses import dataclass
from typing import dataclass_transform


@dataclass_transform(frozen_default=True)
def dto[DTO_T](cls: type[DTO_T]) -> type[DTO_T]:
    """Alias to slotted frozen dataclass."""
    return dataclass(slots=True, frozen=True)(cls)


@dataclass_transform()
def entity[Entity_T](cls: type[Entity_T]) -> type[Entity_T]:
    """Alias to slotted dataclass."""
    return dataclass(slots=True)(cls)


@dataclass_transform()
def value_object[VO_T](cls: type[VO_T]) -> type[VO_T]:
    """Alias to slotted dataclass."""
    return dataclass(slots=True, frozen=True)(cls)


@dataclass_transform(frozen_default=True)
def interactor[Interactor_T](cls: type[Interactor_T]) -> type[Interactor_T]:
    """Alias to slotted frozen dataclass."""
    return dataclass(slots=True, frozen=True)(cls)


def identity[Someting_T](something: Someting_T) -> Someting_T:
    """Classic identity function: x -> x."""
    return something


class MaybeMissing:
    """A simple sentinel value."""


MISSING = MaybeMissing()


type Maybe[T] = T | MaybeMissing


vo_coercer = attrgetter("value")
