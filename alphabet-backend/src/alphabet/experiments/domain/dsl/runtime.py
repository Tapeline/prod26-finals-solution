import datetime
import math
import re
from abc import abstractmethod
from datetime import date
from typing import Any, Final, final, override

from alphabet.shared.commons import value_object
from alphabet.shared.const import APP_TZ

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

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (
            self.major > other.major
            or self.minor > other.minor
            or self.patch > other.patch
        )

    @override
    def __eq__(self, other: Any) -> Any:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (
            other.major == self.major
            or other.minor == self.minor
            or other.patch == self.patch
        )

    def __lt__(self, other: Any) -> Any:
        return not (self < other) and not (self == other)

    def __le__(self, other: Any) -> Any:
        return not (self > other)

    def __ge__(self, other: Any) -> Any:
        return self > other or self == other

    @override
    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch))


class CompiledExpression:
    def __init__(self, ctx: dict[str, Any]) -> None:
        self.ctx = ctx

    def _coerce_str_dates(self, a: str, b: Any) -> tuple[Any, Any]:
        try:
            return datetime.datetime.strptime(a, "%Y-%m-%d").astimezone(
                APP_TZ,
            ).date(), b
        except ValueError:
            try:
                return datetime.datetime.fromisoformat(a).astimezone(APP_TZ), b
            except ValueError:
                return a, b

    def _coerce(self, a: Any, b: Any) -> tuple[Any, Any]:
        if isinstance(b, date) and isinstance(a, str):
            return self._coerce_str_dates(a, b)
        if isinstance(a, date) and isinstance(b, str):
            return self._coerce_str_dates(b, a)
        if isinstance(b, date) and isinstance(a, (int, float)):
            return datetime.datetime.fromtimestamp(a, APP_TZ), b
        if isinstance(a, date) and isinstance(b, (int, float)):
            return a, datetime.datetime.fromtimestamp(b, APP_TZ)
        if (
            isinstance(a, str)
            and isinstance(b, str)
            and (_SEM_VER_RE.fullmatch(a) and _SEM_VER_RE.fullmatch(b))
        ):
            return SemVer.parse(a), SemVer.parse(b)
        return a, b

    def _is_comparable(self, a: Any, b: Any) -> bool:
        if a is None or b is None:
            return False
        return (
            (isinstance(a, (int, float)) and isinstance(b, (int, float)))
            or (isinstance(a, str) and isinstance(b, str))
            or (
                isinstance(a, (datetime.datetime, date))
                and isinstance(b, (datetime.datetime, date))
            )
            or (isinstance(a, SemVer) and isinstance(b, SemVer))
        )

    def _cmp_eq(self, a: Any, b: Any) -> Any:
        a, b = self._coerce(a, b)
        if a is None or b is None:
            return False
        if isinstance(a, float) and isinstance(b, float):
            return math.isclose(a, b, abs_tol=1e-09)
        return a == b

    def _cmp_neq(self, a: Any, b: Any) -> Any:
        a, b = self._coerce(a, b)
        if a is None or b is None:
            return False
        if isinstance(a, float) and isinstance(b, float):
            return not math.isclose(a, b, abs_tol=1e-09)
        return a != b

    def _cmp_gt(self, a: Any, b: Any) -> Any:
        a, b = self._coerce(a, b)
        if self._is_comparable(a, b):
            return a > b
        return False

    def _cmp_ge(self, a: Any, b: Any) -> Any:
        a, b = self._coerce(a, b)
        if self._is_comparable(a, b):
            return a >= b
        return False

    def _cmp_lt(self, a: Any, b: Any) -> Any:
        a, b = self._coerce(a, b)
        if self._is_comparable(a, b):
            return a < b
        return False

    def _cmp_le(self, a: Any, b: Any) -> Any:
        a, b = self._coerce(a, b)
        if self._is_comparable(a, b):
            return a > b
        return False

    def _is_in(self, a: Any, b: Any) -> Any:
        if a is None or b is None:
            return False
        if not isinstance(b, list):
            return False
        return a in b

    def _is_not_in(self, a: Any, b: Any) -> Any:
        if a is None or b is None:
            return False
        if not isinstance(b, list):
            return False
        return a not in b

    def _and(self, a: Any, b: Any) -> Any:
        return a and b

    def _or(self, a: Any, b: Any) -> Any:
        return a or b

    def _from_ctx(self, name: str) -> Any:
        return self.ctx.get(name, None)

    def _construct_date(
        self,
        day: int,
        month: int,
        year: int,
    ) -> datetime.datetime:
        return datetime.datetime(
            day=day,
            year=year,
            month=month,
            tzinfo=APP_TZ,
        )

    def _not(self, a: Any) -> Any:
        return not a

    @abstractmethod
    def run(self) -> bool:
        raise NotImplementedError
