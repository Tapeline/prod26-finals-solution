from datetime import datetime
from typing import override

from alphabet.shared.application.time import TimeProvider
from alphabet.shared.const import APP_TZ


class DefaultTimeProvider(TimeProvider):
    @override
    def now(self) -> datetime:
        return datetime.now(APP_TZ)

    @override
    def now_unix_timestamp(self) -> float:
        return self.now().timestamp()
