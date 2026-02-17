from typing import override

from alphabet.decisions.application import ExperimentStorage, FlagStorage
from alphabet.decisions.domain import CachedExperiment


class InMemoryFlagStorage(FlagStorage):
    def __init__(self) -> None:
        self._defaults: dict[str, str] = {}
        self._ready = False

    @override
    def get_default(self, flag_key: str) -> str | None:
        return self._defaults.get(flag_key, None)

    @override
    def set_flag_default(self, flag_key: str, value: str) -> None:
        self._defaults[flag_key] = value

    @override
    def is_ready(self) -> bool:
        return self._ready

    @override
    def mark_ready(self) -> None:
        self._ready = True


class InMemoryExperimentStorage(ExperimentStorage):
    def __init__(self) -> None:
        self._exp: dict[str, CachedExperiment] = {}
        self._ready = False

    @override
    def get_experiments(
        self,
        flag_keys: list[str],
    ) -> list[CachedExperiment | None]:
        return [self._exp.get(key, None) for key in flag_keys]

    @override
    def set_on_flag(
        self,
        flag_key: str,
        experiment: CachedExperiment | None,
    ) -> None:
        if experiment is None:
            self._exp.pop(flag_key, None)
        else:
            self._exp[flag_key] = experiment

    @override
    def is_ready(self) -> bool:
        return self._ready

    @override
    def mark_ready(self) -> None:
        self._ready = True
