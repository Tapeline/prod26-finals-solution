from datetime import datetime

from abc import abstractmethod

from typing import Protocol


class TimeProvider(Protocol):
    @abstractmethod
    def now(self) -> datetime:
        raise NotImplementedError

    @abstractmethod
    def now_unix_timestamp(self) -> int:
        raise NotImplementedError
