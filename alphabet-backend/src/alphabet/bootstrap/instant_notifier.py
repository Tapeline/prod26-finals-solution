from typing import final, override

from dishka import AsyncContainer

from alphabet.decisions.application import (
    SetFlagDefault,
    SetRunningExperimentOnFlag,
    cached_experiment_from_experiment,
)
from alphabet.experiments.application.interfaces import (
    ExperimentChangeNotifier,
    FlagChangeNotifier,
)
from alphabet.experiments.domain.experiment import Experiment
from alphabet.experiments.domain.flags import FlagKey
from alphabet.guardrails.application.interfaces import GuardrailNotifier
from alphabet.guardrails.domain import AuditRecord
from alphabet.notifications.application.interactors import (
    ExperimentEvent,
    GuardrailEvent,
    PublishNotification,
)
from alphabet.shared.commons import autoinit
from alphabet.subject_events.application.interfaces import (
    EventTypeCache,
    EventTypeChangeNotifier,
)
from alphabet.subject_events.domain.events import EventType


@final
@autoinit
class InstantNotifier(
    ExperimentChangeNotifier,
    FlagChangeNotifier,
    EventTypeChangeNotifier,
    GuardrailNotifier,
):
    """
    A harsh MQ mock for now that interconnects modules.

    When we'll scale, this will give way for an actual message queue.
    """

    container: AsyncContainer

    @override
    async def notify_experiment_activated(
        self,
        experiment: Experiment,
    ) -> None:
        async with self.container() as nested:
            (await nested.get(SetRunningExperimentOnFlag))(
                experiment.flag_key.value,
                cached_experiment_from_experiment(experiment),
            )

    @override
    async def notify_experiment_deactivated(
        self,
        experiment: Experiment,
    ) -> None:
        async with self.container() as nested:
            (await nested.get(SetRunningExperimentOnFlag))(
                experiment.flag_key.value,
                None,
            )

    @override
    async def notify_experiment_halted(self, experiment: Experiment) -> None:
        async with self.container() as nested:
            (await nested.get(SetRunningExperimentOnFlag))(
                experiment.flag_key.value,
                cached_experiment_from_experiment(experiment),
            )

    @override
    async def notify_flag_default_changed(
        self,
        flag_key: FlagKey,
        new_default: str,
    ) -> None:
        async with self.container() as nested:
            (await nested.get(SetFlagDefault))(
                flag_key.value,
                new_default,
            )

    @override
    async def notify_event_type_created(self, event_type: EventType) -> None:
        async with self.container() as nested:
            (await nested.get(EventTypeCache)).place_event_types([event_type])

    @override
    async def notify_experiment_state_changed(
        self,
        experiment: Experiment,
    ) -> None:
        async with self.container() as nested:
            publisher = await nested.get(PublishNotification)
            await publisher(ExperimentEvent(experiment))

    @override
    async def notify_rule_triggered(self, outcome: AuditRecord) -> None:
        async with self.container() as nested:
            publisher = await nested.get(PublishNotification)
            await publisher(GuardrailEvent(outcome))
