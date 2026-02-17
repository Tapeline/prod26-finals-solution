from datetime import datetime
from typing import override

from alphabet.shared.application.time import TimeProvider


class DefaultNaiveTimeProvider(TimeProvider):
    @override
    def now(self) -> datetime:
        return datetime.now()

    @override
    def now_unix_timestamp(self) -> float:
        return self.now().timestamp()
