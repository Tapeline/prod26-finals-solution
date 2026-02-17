from typing import Any, override

from sqlalchemy import Row, delete, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from alphabet.experiments.application.interfaces import ReviewRepository
from alphabet.experiments.domain.experiment import (
    Approval,
    ExperimentId,
    ReviewDecision,
)
from alphabet.experiments.infrastructure.tables import (
    approvals,
    review_decisions,
)
from alphabet.shared.domain.user import UserId
from alphabet.shared.infrastructure.transaction import SqlTransactionManager


class SqlReviewRepository(ReviewRepository):
    def __init__(self, tx: SqlTransactionManager) -> None:
        self.session = tx.session

    @override
    async def all_approvals(self, exp_id: ExperimentId) -> list[Approval]:
        result = await self.session.execute(
            select(approvals).where(approvals.c.experiment_id == exp_id),
        )
        return list(map(_row_to_approval, result.all()))

    @override
    async def create_approval(self, approval: Approval) -> None:
        await self.session.execute(
            insert(approvals).values(
                experiment_id=approval.experiment_id,
                approver_id=approval.approver_id,
            ),
        )

    @override
    async def revoke_all_approvals(self, exp_id: ExperimentId) -> None:
        await self.session.execute(
            delete(approvals).where(approvals.c.experiment_id == exp_id),
        )

    @override
    async def save_decision(self, decision: ReviewDecision) -> None:
        stmt = pg_insert(review_decisions).values(
            experiment_id=decision.experiment_id,
            rejecter_id=decision.rejecter_id,
            reject_comment=decision.reject_comment,
        )
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=["experiment_id"],
                set_={
                    "rejecter_id": stmt.excluded.rejecter_id,
                    "reject_comment": stmt.excluded.reject_comment,
                },
            ),
        )

    @override
    async def get_decision(
        self,
        exp_id: ExperimentId,
    ) -> ReviewDecision | None:
        result = await self.session.execute(
            select(review_decisions).where(
                review_decisions.c.experiment_id == exp_id,
            ),
        )
        return _row_to_decision(result.first())


def _row_to_decision(row: Row[Any] | None) -> ReviewDecision | None:
    if not row:
        return None
    return ReviewDecision(
        experiment_id=ExperimentId(row.experiment_id),
        rejecter_id=UserId(row.rejecter_id),
        reject_comment=row.reject_comment,
    )


def _row_to_approval(row: Row[Any]) -> Approval:
    return Approval(
        experiment_id=ExperimentId(row.experiment_id),
        approver_id=UserId(row.approver_id),
    )
