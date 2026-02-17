from typing import override

from alphabet.decisions.application import ResolutionRepository
from alphabet.decisions.domain import ConflictResolution


class ClickHouseResolutionRepository(ResolutionRepository):
    @override
    async def save_resolutions(
        self,
        resolutions: list[ConflictResolution],
    ) -> None:
        pass
