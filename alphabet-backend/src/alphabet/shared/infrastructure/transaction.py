from typing import Any, final, override

from sqlalchemy.ext.asyncio import AsyncSession

from alphabet.shared.application.transaction import TransactionManager


@final
class SqlTransactionManager(TransactionManager):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @override
    async def __aenter__(self) -> None:
        pass

    @override
    async def __aexit__(
        self,
        exc_type: type[Exception] | None,
        exc_val: Exception | None,
        exc_tb: Any | None,
    ) -> None:
        if exc_val:
            await self.session.rollback()
        else:
            await self.session.commit()
