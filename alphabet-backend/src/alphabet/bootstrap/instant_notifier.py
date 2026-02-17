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
from alphabet.shared.commons import autoinit


@final
@autoinit
class InstantNotifier(ExperimentChangeNotifier, FlagChangeNotifier):
    """When we'll scale, this will give way for an actual message queue."""

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
