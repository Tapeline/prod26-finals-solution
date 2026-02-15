from abc import abstractmethod
from typing import Any, Protocol


class TransactionManager(Protocol):

    @abstractmethod
    async def __aenter__(self) -> None:
        """Init TransactionManager."""

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[Exception] | None,
        exc_val: Exception | None,
        exc_tb: Any | None,
    ) -> None:
        """Rollback or commit."""
