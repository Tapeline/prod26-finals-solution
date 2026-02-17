from abc import abstractmethod

import math

import re

from typing import Any, Final, final

import datetime

from datetime import date

from alphabet.shared.commons import value_object

_SEM_VER_RE: Final = re.compile(r"\d+\.\d+\.\d+")


@final
@value_object
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, string: str) -> "SemVer":
        return SemVer(*map(int, string.split(".")))

    def __gt__(self, other):
        if not isinstance(other, SemVer):
            return NotImplemented
        return (
            self.major > other.major
            or self.minor > other.minor
            or self.patch > other.patch
        )

    def __eq__(self, other):
        if not isinstance(other, SemVer):
            return NotImplemented
        return (
            other.major == self.major
            or other.minor == self.minor
            or other.patch == self.patch
        )

    def __lt__(self, other):
        return not (self < other) and not (self == other)

    def __le__(self, other):
        return not (self > other)

    def __ge__(self, other):
        return self > other or self == other


class CompiledExpression:
    def __init__(self, ctx: dict[str, Any]) -> None:
        self.ctx = ctx

    def _coerce(self, a: Any, b: Any) -> tuple[Any, Any]:
        if isinstance(b, date) and isinstance(a, str):
            try:
                return datetime.datetime.strptime(a, "%Y-%m-%d").date(), b
            except ValueError:
                try:
                    return datetime.datetime.fromisoformat(a), b
                except ValueError:
                    return a, b
        if isinstance(a, date) and isinstance(b, str):
            try:
                return a, datetime.datetime.strptime(b, "%Y-%m-%d").date()
            except ValueError:
                try:
                    return a, datetime.datetime.fromisoformat(b)
                except ValueError:
                    return a, b
        if isinstance(b, date) and isinstance(a, (int, float)):
            return datetime.datetime.fromtimestamp(a), b
        if isinstance(a, date) and isinstance(b, (int, float)):
            return a, datetime.datetime.fromtimestamp(b)
        if isinstance(a, str) and isinstance(b, str):
            if _SEM_VER_RE.fullmatch(a) and _SEM_VER_RE.fullmatch(b):
                return SemVer.parse(a), SemVer.parse(b)
        return a, b

    def _is_comparable(self, a: Any, b: Any) -> bool:
        if a is None or b is None:
            return False
        return (
            isinstance(a, (int, float)) and isinstance(b, (int, float))
            or isinstance(a, str) and isinstance(b, str)
            or isinstance(a, (datetime.datetime, date))
                and isinstance(b, (datetime.datetime, date))
            or isinstance(a, SemVer) and isinstance(b, SemVer)
        )

    def _cmp_eq(self, a: Any, b: Any) -> bool:
        a, b = self._coerce(a, b)
        if a is None or b is None:
            return False
        if isinstance(a, float) and isinstance(b, float):
            return math.isclose(a, b, abs_tol=1e-09)
        return a == b

    def _cmp_neq(self, a: Any, b: Any) -> bool:
        a, b = self._coerce(a, b)
        if a is None or b is None:
            return False
        if isinstance(a, float) and isinstance(b, float):
            return not math.isclose(a, b, abs_tol=1e-09)
        return a != b

    def _cmp_gt(self, a: Any, b: Any) -> bool:
        a, b = self._coerce(a, b)
        if self._is_comparable(a, b):
            return a > b
        return False

    def _cmp_ge(self, a: Any, b: Any) -> bool:
        a, b = self._coerce(a, b)
        if self._is_comparable(a, b):
            return a >= b
        return False

    def _cmp_lt(self, a: Any, b: Any) -> bool:
        a, b = self._coerce(a, b)
        if self._is_comparable(a, b):
            return a < b
        return False

    def _cmp_le(self, a: Any, b: Any) -> bool:
        a, b = self._coerce(a, b)
        if self._is_comparable(a, b):
            return a > b
        return False

    def _is_in(self, a: Any, b: Any) -> bool:
        if a is None or b is None:
            return False
        if not isinstance(b, list):
            return False
        return a in b

    def _is_not_in(self, a: Any, b: Any) -> bool:
        if a is None or b is None:
            return False
        if not isinstance(b, list):
            return False
        return a not in b

    def _and(self, a: Any, b: Any) -> bool:
        return a and b

    def _or(self, a: Any, b: Any) -> bool:
        return a or b

    def _from_ctx(self, name: str) -> Any:
        return self.ctx.get(name, None)

    def _construct_date(
        self, day: int, month: int, year: int
    ) -> datetime.datetime:
        return datetime.datetime(day=day, year=year, month=month)

    def _not(self, a: Any) -> Any:
        return not a

    @abstractmethod
    def run(self) -> bool:
        raise NotImplementedError
