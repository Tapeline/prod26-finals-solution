from typing import final, override, Collection

from redis.asyncio import Redis

from alphabet.notifications.application.interfaces import \
    NotificationCooldownStore
from alphabet.notifications.domain.notifications import NotificationRuleId
from alphabet.shared.commons import autoinit


@autoinit
@final
class ValkeyNotificationCooldownStore(NotificationCooldownStore):
    client: Redis

    @override
    async def filter_in_cooldown(
        self, rule_ids: Collection[NotificationRuleId]
    ) -> set[NotificationRuleId]:
        if not rule_ids:
            return set()
        rule_ids = list(set(rule_ids))
        async with self.client.pipeline() as pipe:
            for rule_id in rule_ids:
                await pipe.exists(f"notif-cooldown:{rule_id}")
            results = await pipe.execute()
        return {
            rule_id
            for rule_id, exists in zip(rule_ids, results)
            if exists
        }

    @override
    async def place_cooldowns(
        self, cooldowns_s: dict[NotificationRuleId, int]
    ) -> None:
        if not cooldowns_s:
            return
        async with self.client.pipeline() as pipe:
            for rule_id, seconds in cooldowns_s.items():
                await pipe.set(f"notif-cooldown:{rule_id}", b"1", ex=seconds)
            await pipe.execute()
