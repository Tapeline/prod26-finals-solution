from redis.asyncio import Redis

from alphabet.shared.config import ValkeyConfig


async def create_valkey_client(valkey_config: ValkeyConfig) -> Redis:
    return Redis(
        host=valkey_config.host,
        port=valkey_config.port,
        username=valkey_config.username,
        password=valkey_config.password,
        db=valkey_config.database_id or 0,
    )
