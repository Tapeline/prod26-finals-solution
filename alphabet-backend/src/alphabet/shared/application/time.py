from abc import abstractmethod
from datetime import datetime
from typing import Protocol


class TimeProvider(Protocol):
    @abstractmethod
    def now(self) -> datetime:
        raise NotImplementedError

    @abstractmethod
    def now_unix_timestamp(self) -> float:
        raise NotImplementedError
