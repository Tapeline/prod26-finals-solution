from typing import final, override

from glide import ExpirySet, ExpiryType, GlideClient

from alphabet.decisions.application import CooldownChecker
from alphabet.shared.application.time import TimeProvider
from alphabet.shared.commons import autoinit
from alphabet.shared.config import AppConfig


@final
@autoinit
class ValkeyCooldownChecker(CooldownChecker):
    client: GlideClient
    time: TimeProvider
    config: AppConfig

    @override
    async def is_in_cooldown_or_set_if_needed(self, subject_id: str) -> bool:
        in_cooldown = await self.client.get(f"cooldown:{subject_id}")
        if in_cooldown:
            return True
        last_cooldown = await self.client.get(f"last-cooldown:{subject_id}")
        if not last_cooldown:
            await self.client.set(
                f"last-cooldown:{subject_id}",
                str(int(self.time.now_unix_timestamp())),
            )
            return False
        last_cooldown_timestamp = int(last_cooldown.decode())
        now = self.time.now_unix_timestamp()
        if now - last_cooldown_timestamp >= self.config.cooldown_after_s:
            await self.client.set(
                f"last-cooldown:{subject_id}",
                str(int(now)),
            )
            await self.client.set(
                f"cooldown:{subject_id}",
                b"1",
                expiry=ExpirySet(
                    ExpiryType.SEC,
                    self.config.cooldown_for_s,
                ),
            )
            return True
        return False
