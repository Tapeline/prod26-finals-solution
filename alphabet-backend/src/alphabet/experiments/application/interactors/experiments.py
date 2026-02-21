from operator import attrgetter
from typing import cast, final

from alphabet.access.application.interfaces import UserRepository
from alphabet.experiments.application.exceptions import (
    AlreadyApproved,
    ExperimentNotInReview,
    FlagAlreadyTaken,
    NoSuchExperiment,
    NoSuchFlag,
)
from alphabet.experiments.application.interfaces import (
    ExperimentChangeNotifier,
    ExperimentsRepository,
    FlagRepository,
    ReviewRepository,
)
from alphabet.experiments.domain.exceptions import (
    CannotTransition,
    InvalidConflictConfig,
)
from alphabet.experiments.domain.experiment import (
    Approval,
    ConflictDomain,
    ConflictPolicy,
    Experiment,
    ExperimentId,
    ExperimentName,
    ExperimentResult,
    ExperimentState,
    MetricCollection,
    Percentage,
    Priority,
    ReviewDecision,
    Variant,
)
from alphabet.experiments.domain.flags import FlagKey
from alphabet.experiments.domain.target_rule import TargetRuleString
from alphabet.shared.application.idp import UserIdProvider
from alphabet.shared.application.time import TimeProvider
from alphabet.shared.application.transaction import TransactionManager
from alphabet.shared.application.user import (
    UserReader,
    require_any_user,
    require_user_with_role,
)
from alphabet.shared.commons import (
    MISSING,
    Maybe,
    dto,
    interactor,
)
from alphabet.shared.domain.exceptions import NotAllowed
from alphabet.shared.domain.user import Role
from alphabet.shared.uuid import generate_id


@final
@dto
class CreateExperimentDTO:
    name: ExperimentName
    flag_key: FlagKey
    audience: Percentage
    variants: list[Variant]
    targeting: TargetRuleString | None
    metrics: MetricCollection
    priority: Priority | None
    conflict_domain: ConflictDomain | None
    conflict_policy: ConflictPolicy | None


@final
@interactor
class CreateExperiment:
    idp: UserIdProvider
    user_reader: UserReader
    flags: FlagRepository
    experiments: ExperimentsRepository
    time_provider: TimeProvider
    tx: TransactionManager

    async def __call__(self, dto: CreateExperimentDTO) -> Experiment:
        if dto.targeting:
            dto.targeting.validate()
        async with self.tx:
            user = await require_user_with_role(
                self,
                {Role.ADMIN, Role.EXPERIMENTER},
            )
            exp_flag = await self.flags.get_by_key(dto.flag_key)
            if not exp_flag:
                raise NoSuchFlag
            now = self.time_provider.now()
            experiment = Experiment.new(
                id=generate_id(ExperimentId),
                name=dto.name,
                flag_key=dto.flag_key,
                audience=dto.audience,
                variants=dto.variants,
                targeting=dto.targeting,
                metrics=dto.metrics,
                priority=dto.priority,
                conflict_domain=dto.conflict_domain,
                conflict_policy=dto.conflict_policy,
                author_id=user.id,
                created_at=now,
                updated_at=now,
            )
            await self.experiments.create(experiment)
            return experiment


@final
@dto
class UpdateExperimentDTO:
    name: Maybe[ExperimentName]
    flag_key: Maybe[FlagKey]
    audience: Maybe[Percentage]
    variants: Maybe[list[Variant]]
    metrics: Maybe[MetricCollection]
    priority: Maybe[Priority | None]
    targeting: Maybe[TargetRuleString | None]
    conflict_domain: Maybe[ConflictDomain | None]
    conflict_policy: Maybe[ConflictPolicy | None]


@final
@interactor
class UpdateExperiment:
    idp: UserIdProvider
    user_reader: UserReader
    flags: FlagRepository
    time_provider: TimeProvider
    tx: TransactionManager
    experiments: ExperimentsRepository

    # TODO: refactor later
    async def __call__(  # noqa: C901
        self,
        exp_id: ExperimentId,
        dto: UpdateExperimentDTO,
    ) -> Experiment:
        if dto.targeting is not MISSING and dto.targeting is not None:
            cast(TargetRuleString, dto.targeting).validate()
        async with self.tx:
            await require_user_with_role(
                self,
                {Role.ADMIN, Role.EXPERIMENTER},
            )
            experiment = await self.experiments.get_latest_by_id(exp_id)
            if not experiment:
                raise NoSuchExperiment
            if dto.flag_key is not MISSING:
                flag = await self.flags.get_by_key(cast(FlagKey, dto.flag_key))
                if not flag:
                    raise NoSuchFlag
                experiment.flag_key = cast(FlagKey, dto.flag_key)
            if dto.metrics is not MISSING:
                experiment.metrics = cast(MetricCollection, dto.metrics)
            if dto.priority is not MISSING:
                experiment.priority = cast(Priority | None, dto.priority)
            if dto.targeting is not MISSING:
                experiment.targeting = cast(
                    TargetRuleString | None,
                    dto.targeting,
                )
            if dto.name is not MISSING:
                experiment.name = cast(ExperimentName, dto.name)
            if dto.conflict_domain is None and dto.conflict_policy is None:
                experiment.remove_conflict_domain()
            elif (
                dto.conflict_domain is not MISSING
                and dto.conflict_policy is not MISSING
            ):
                experiment.set_conflict_domain(
                    cast(ConflictDomain, dto.conflict_domain),
                    cast(ConflictPolicy, dto.conflict_policy),
                )
            if (dto.conflict_policy is MISSING) ^ (
                dto.conflict_policy is MISSING
            ):
                raise InvalidConflictConfig
            if dto.variants is not MISSING:
                if dto.audience is not MISSING:
                    experiment.set_new_audience_variants(
                        cast(Percentage, dto.audience),
                        cast(list[Variant], dto.variants),
                    )
                else:
                    experiment.set_new_variants(
                        cast(list[Variant], dto.variants),
                    )
            experiment.updated_at = self.time_provider.now()
            experiment.increment_version()
            await self.experiments.save(experiment)
            return experiment


@final
@interactor
class SendToReview:
    idp: UserIdProvider
    user_reader: UserReader
    time_provider: TimeProvider
    tx: TransactionManager
    experiments: ExperimentsRepository
    reviews: ReviewRepository
    notifier: ExperimentChangeNotifier

    async def __call__(self, exp_id: ExperimentId) -> Experiment:
        async with self.tx:
            await require_user_with_role(
                self,
                {Role.ADMIN, Role.EXPERIMENTER},
            )
            experiment = await self.experiments.get_latest_by_id(exp_id)
            if not experiment:
                raise NoSuchExperiment
            experiment.state = ExperimentState.IN_REVIEW
            await self.reviews.revoke_all_approvals(experiment.id)
            await self.experiments.save(experiment)
            await self.notifier.notify_experiment_state_changed(experiment)
            return experiment


@final
@interactor
class RestoreFromRejected:
    idp: UserIdProvider
    user_reader: UserReader
    time_provider: TimeProvider
    tx: TransactionManager
    experiments: ExperimentsRepository
    notifier: ExperimentChangeNotifier

    async def __call__(self, exp_id: ExperimentId) -> Experiment:
        async with self.tx:
            await require_user_with_role(
                self,
                {Role.ADMIN, Role.EXPERIMENTER},
            )
            experiment = await self.experiments.get_latest_by_id(exp_id)
            if not experiment:
                raise NoSuchExperiment
            experiment.state = ExperimentState.DRAFT
            await self.experiments.save(experiment)
            await self.notifier.notify_experiment_state_changed(experiment)
            return experiment


@final
@interactor
class RejectDraft:
    idp: UserIdProvider
    user_reader: UserReader
    users: UserRepository
    time_provider: TimeProvider
    tx: TransactionManager
    experiments: ExperimentsRepository
    reviews: ReviewRepository
    notifier: ExperimentChangeNotifier

    async def __call__(
        self,
        exp_id: ExperimentId,
        comment: str,
    ) -> ReviewDecision:
        async with self.tx:
            approver = await require_user_with_role(
                self,
                {Role.ADMIN, Role.APPROVER},
            )
            experiment = await self.experiments.get_latest_by_id(
                exp_id,
                lock=True,
            )
            if not experiment:
                raise NoSuchExperiment
            if experiment.state != ExperimentState.IN_REVIEW:
                raise ExperimentNotInReview
            approver_group = await self.users.load_approver_group(
                experiment.author_id,
            )
            if (not approver_group and approver.role == Role.ADMIN) or (
                approver_group and approver.id in approver_group.approvers
            ):
                rejecter_id = approver.id
            else:
                raise NotAllowed
            experiment.updated_at = self.time_provider.now()
            experiment.state = ExperimentState.REJECTED
            decision = ReviewDecision.rejected(
                experiment_id=experiment.id,
                rejecter_id=rejecter_id,
                reject_comment=comment,
            )
            await self.reviews.save_decision(decision)
            await self.experiments.save(experiment)
            await self.notifier.notify_experiment_state_changed(experiment)
            return decision


@final
@interactor
class ApproveDraft:
    idp: UserIdProvider
    user_reader: UserReader
    users: UserRepository
    time_provider: TimeProvider
    tx: TransactionManager
    experiments: ExperimentsRepository
    reviews: ReviewRepository
    notifier: ExperimentChangeNotifier

    async def __call__(
        self,
        exp_id: ExperimentId,
    ) -> ReviewDecision | None:
        async with self.tx:
            approver = await require_user_with_role(
                self,
                {Role.ADMIN, Role.APPROVER},
            )
            experiment = await self.experiments.get_latest_by_id(
                exp_id,
                lock=True,
            )
            if not experiment:
                raise NoSuchExperiment
            if experiment.state != ExperimentState.IN_REVIEW:
                raise ExperimentNotInReview
            approver_group = await self.users.load_approver_group(
                experiment.author_id,
            )
            approvals = await self.reviews.all_approvals(experiment.id)
            if approver.id in map(attrgetter("approver_id"), approvals):
                raise AlreadyApproved
            decision: ReviewDecision | None = None
            if not approver_group and approver.role == Role.ADMIN:
                await self.reviews.create_approval(
                    Approval(experiment.id, approver.id),
                )
                decision = await self._accept(experiment)
            elif approver_group and approver.id in approver_group.approvers:
                await self.reviews.create_approval(
                    Approval(experiment.id, approver.id),
                )
                if len(approvals) + 1 >= approver_group.threshold:
                    decision = await self._accept(experiment)
            else:
                raise NotAllowed
            await self.experiments.save(experiment)
            if decision:
                await self.notifier.notify_experiment_state_changed(experiment)
            return decision

    async def _accept(
        self,
        experiment: Experiment,
    ) -> ReviewDecision:
        experiment.state = ExperimentState.ACCEPTED
        experiment.updated_at = self.time_provider.now()
        decision = ReviewDecision.approved(experiment.id)
        await self.reviews.save_decision(decision)
        # send a notification
        return decision


@final
@interactor
class StartExperiment:
    idp: UserIdProvider
    user_reader: UserReader
    time_provider: TimeProvider
    tx: TransactionManager
    flags: FlagRepository
    experiments: ExperimentsRepository
    notifier: ExperimentChangeNotifier

    async def __call__(self, exp_id: ExperimentId) -> Experiment:
        async with self.tx:
            await require_user_with_role(self, {Role.EXPERIMENTER})
            experiment = await self.experiments.get_latest_by_id(exp_id)
            if not experiment:
                raise NoSuchExperiment
            if experiment.state != ExperimentState.ACCEPTED:
                raise CannotTransition(
                    experiment.state,
                    ExperimentState.STARTED,
                )
            await self.flags.lock_on(experiment.flag_key)
            if await self.experiments.get_active_by_flag(experiment.flag_key):
                raise FlagAlreadyTaken
            experiment.state = ExperimentState.STARTED
            experiment.updated_at = self.time_provider.now()
            await self.experiments.save(experiment)
        await self.notifier.notify_experiment_activated(experiment)
        await self.notifier.notify_experiment_state_changed(experiment)
        return experiment


@final
@interactor
class ManageRunningExperiment:
    idp: UserIdProvider
    user_reader: UserReader
    tx: TransactionManager
    experiments: ExperimentsRepository
    time_provider: TimeProvider
    notifier: ExperimentChangeNotifier

    async def __call__(
        self,
        exp_id: ExperimentId,
        new_state: ExperimentState,
    ) -> Experiment:
        async with self.tx:
            await require_user_with_role(self, {Role.EXPERIMENTER})
            experiment = await self.experiments.get_latest_by_id(exp_id)
            if not experiment:
                raise NoSuchExperiment
            experiment.state = new_state
            experiment.updated_at = self.time_provider.now()
            await self.experiments.save(experiment)
        if new_state == ExperimentState.STARTED:
            await self.notifier.notify_experiment_activated(experiment)
        else:
            await self.notifier.notify_experiment_deactivated(experiment)
        await self.notifier.notify_experiment_state_changed(experiment)
        return experiment


@final
@interactor
class ArchiveExperiment:
    idp: UserIdProvider
    user_reader: UserReader
    tx: TransactionManager
    experiments: ExperimentsRepository
    time_provider: TimeProvider
    notifier: ExperimentChangeNotifier

    async def __call__(
        self,
        exp_id: ExperimentId,
        result: ExperimentResult,
    ) -> Experiment:
        async with self.tx:
            await require_user_with_role(self, {Role.EXPERIMENTER})
            experiment = await self.experiments.get_latest_by_id(exp_id)
            if not experiment:
                raise NoSuchExperiment
            experiment.updated_at = self.time_provider.now()
            experiment.archive(result)
            await self.experiments.save(experiment)
            await self.notifier.notify_experiment_state_changed(experiment)
            return experiment


@final
@interactor
class ReadExperimentVersion:
    idp: UserIdProvider
    user_reader: UserReader
    tx: TransactionManager
    experiments: ExperimentsRepository

    async def __call__(
        self,
        exp_id: ExperimentId,
        version: Maybe[int],
    ) -> Experiment:
        async with self.tx:
            await require_any_user(self)
            if version is MISSING:
                experiment = await self.experiments.get_latest_by_id(exp_id)
            else:
                experiment = await self.experiments.get_by_id_and_version(
                    exp_id,
                    cast(int, version),
                )
            if not experiment:
                raise NoSuchExperiment
            return experiment


@final
@interactor
class ReadExperimentVersionHistory:
    idp: UserIdProvider
    user_reader: UserReader
    tx: TransactionManager
    experiments: ExperimentsRepository

    async def __call__(
        self,
        exp_id: ExperimentId,
    ) -> list[Experiment]:
        async with self.tx:
            await require_any_user(self)
            return await self.experiments.get_old_versions(exp_id)


@final
@dto
class ExperimentAuditDTO:
    approvals: list[Approval]
    decision: ReviewDecision | None


@final
@interactor
class ReadExperimentAudit:
    idp: UserIdProvider
    user_reader: UserReader
    tx: TransactionManager
    experiments: ExperimentsRepository
    reviews: ReviewRepository

    async def __call__(
        self,
        exp_id: ExperimentId,
    ) -> ExperimentAuditDTO:
        async with self.tx:
            await require_any_user(self)
            if not await self.experiments.get_latest_by_id(exp_id):
                raise NoSuchExperiment
            approvals = await self.reviews.all_approvals(exp_id)
            decision = await self.reviews.get_decision(exp_id)
            return ExperimentAuditDTO(approvals, decision)
