from typing import Any, overload, override

from sqlalchemy import Row, insert, select, update
from sqlalchemy.exc import IntegrityError

from alphabet.experiments.application.exceptions import FlagKeyAlreadyExists
from alphabet.experiments.application.interfaces import (
    FlagRepository,
)
from alphabet.experiments.domain.flags import FeatureFlag, FlagKey
from alphabet.experiments.infrastructure.tables import (
    flags,
)
from alphabet.shared.application.pagination import Pagination
from alphabet.shared.domain.user import UserId
from alphabet.shared.infrastructure.transaction import SqlTransactionManager


class SqlFlagRepository(FlagRepository):
    def __init__(self, tx: SqlTransactionManager) -> None:
        self.session = tx.session

    @override
    async def get_by_key(self, key: FlagKey) -> FeatureFlag | None:
        result = await self.session.execute(
            select(flags).where(flags.c.key == key.value),
        )
        return _row_to_flag(result.first())

    @override
    async def create(self, flag: FeatureFlag) -> None:
        try:
            await self.session.execute(
                insert(flags).values(
                    key=flag.key.value,
                    description=flag.description,
                    type=flag.type,
                    default=flag.default,
                    author_id=flag.author_id,
                    created_at=flag.created_at,
                    updated_at=flag.updated_at,
                ),
            )
        except IntegrityError as exc:
            raise FlagKeyAlreadyExists from exc

    @override
    async def save(self, flag: FeatureFlag) -> None:
        await self.session.execute(
            update(flags)
            .where(flags.c.key == flag.key.value)
            .values(
                description=flag.description,
                type=flag.type,
                default=flag.default,
                author_id=flag.author_id,
                created_at=flag.created_at,
                updated_at=flag.updated_at,
            ),
        )

    @override
    async def lock_on(self, flag_key: FlagKey) -> None:
        await self.session.execute(
            select(flags)
            .where(flags.c.key == flag_key.value)
            .with_for_update(),
        )

    @override
    async def all(self, pagination: Pagination) -> list[FeatureFlag]:
        result = await self.session.execute(
            select(flags).limit(pagination.limit).offset(pagination.offset),
        )
        return list(map(_row_to_flag, result.all()))

    @override
    async def all_defaults(self) -> list[tuple[str, str]]:
        result = await self.session.execute(select(flags))
        return [(row.key, row.default) for row in result.all()]


@overload
def _row_to_flag(row: Row[Any]) -> FeatureFlag: ...
@overload
def _row_to_flag(row: None) -> None: ...


def _row_to_flag(row: Row[Any] | None) -> FeatureFlag | None:
    if not row:
        return None
    return FeatureFlag(
        _key=FlagKey(row.key),
        _description=row.description,
        _type=row.type,
        _default=row.default,
        _author_id=UserId(row.author_id),
        _created_at=row.created_at,
        _updated_at=row.updated_at,
    )
