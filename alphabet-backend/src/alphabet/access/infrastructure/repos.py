from collections.abc import Sequence
from typing import Any, override

from sqlalchemy import Row, delete, insert, select, update
from sqlalchemy.exc import IntegrityError

from alphabet.access.application.exceptions import EmailAlreadyRegistered
from alphabet.access.application.interfaces import UserRepository
from alphabet.access.domain import ApproverGroup
from alphabet.access.infrastructure.tables import approvers, users
from alphabet.shared.domain.user import IapId, User, UserId
from alphabet.shared.infrastructure.transaction import SqlTransactionManager


class SqlUserRepository(UserRepository):
    def __init__(self, tx: SqlTransactionManager) -> None:
        self.session = tx.session

    @override
    async def get_by_id(self, user_id: UserId) -> User | None:
        result = await self.session.execute(
            select(users).where(users.c.id == user_id),
        )
        return _row_to_user(result.first())

    @override
    async def create(self, user: User) -> None:
        try:
            await self.session.execute(
                insert(users).values(
                    id=user.id,
                    email=user.email,
                    iap_id=user.iap_id,
                    role=user.role,
                ),
            )
        except IntegrityError as exc:
            raise EmailAlreadyRegistered from exc

    @override
    async def save(self, user: User) -> None:
        await self.session.execute(
            update(users)
            .where(users.c.id == user.id)
            .values(
                email=user.email,
                iap_id=user.iap_id,
                role=user.role,
            ),
        )

    @override
    async def get_by_iap_id(self, iap_id: IapId) -> User | None:
        result = await self.session.execute(
            select(users).where(users.c.iap_id == iap_id),
        )
        return _row_to_user(result.first())

    @override
    async def load_approver_group(
        self,
        user_id: UserId,
    ) -> ApproverGroup | None:
        result = await self.session.execute(
            select(users).where(users.c.id == user_id),
        )
        row = result.first()
        if not row:
            return None
        if not row.approver_threshold:
            return None
        result = await self.session.execute(
            select(approvers).where(approvers.c.experimenter_id == user_id),
        )
        return _rows_to_approver_group(result.all(), row.approver_threshold)

    @override
    async def store_approver_group(
        self,
        user_id: UserId,
        approver_group: ApproverGroup,
    ) -> None:
        await self.session.execute(
            update(users)
            .where(users.c.id == user_id)
            .values(approver_threshold=approver_group.threshold),
        )
        await self.session.execute(
            delete(approvers).where(approvers.c.experimenter_id == user_id),
        )
        for approver_id in approver_group.approvers:
            # ? can't we batch-insert this?
            await self.session.execute(
                insert(approvers).values(
                    experimenter_id=user_id,
                    approver_id=approver_id,
                ),
            )

    @override
    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(users).where(users.c.email == email),
        )
        return _row_to_user(result.first())


def _row_to_user(row: Row[Any] | None) -> User | None:
    if not row:
        return None
    return User(
        id=UserId(row.id),
        email=row.email,
        iap_id=IapId(row.iap_id),
        role=row.role,
    )


def _rows_to_approver_group(
    rows: Sequence[Row[Any]] | None,
    approver_threshold: int,
) -> ApproverGroup | None:
    if not rows:
        return None
    return ApproverGroup(
        approvers=[UserId(row.approver_id) for row in rows],
        threshold=approver_threshold,
    )
