# from https://github.com/Tapeline/Fastscaffold

from collections.abc import Callable
from dataclasses import dataclass
from operator import attrgetter
from typing import Any, dataclass_transform, overload

from msgspec import UNSET, UnsetType


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


@dataclass_transform(eq_default=False)
def autoinit[Something_T](cls: type[Something_T]) -> type[Something_T]:
    """Alias to dataclass with only init."""
    return dataclass(
        init=True,
        repr=False,
        eq=False,
        order=False,
        slots=False,
        frozen=False,
        match_args=False,
    )(cls)


def identity[Someting_T](something: Someting_T) -> Someting_T:
    """Classic identity function: x -> x."""
    return something


class MaybeMissing:
    """A simple sentinel value."""


MISSING = MaybeMissing()

type Maybe[T] = T | MaybeMissing

vo_coercer = attrgetter("value")


@overload
def maybe_map(x: UnsetType, f: Any = identity) -> MaybeMissing: ...


@overload
def maybe_map(x: None, f: Any = identity) -> None: ...


@overload
def maybe_map(x: MaybeMissing, f: Any = identity) -> MaybeMissing: ...


@overload
def maybe_map[T, R](
    x: T,
    f: Callable[[T], R] = identity,  # type: ignore[assignment]
) -> R: ...


def maybe_map[T, R](
    x: Any,
    f: Callable[[T], R] = identity,  # type: ignore[assignment]
) -> Any:
    if x is UNSET:
        return MISSING
    return x if x is MISSING or x is None else f(x)
