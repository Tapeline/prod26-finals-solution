from glide import (
    GlideClient,
    GlideClientConfiguration,
    NodeAddress,
    ServerCredentials,
)

from alphabet.shared.config import ValkeyConfig


async def create_valkey_client(valkey_config: ValkeyConfig) -> GlideClient:
    config = GlideClientConfiguration(
        [NodeAddress(valkey_config.host, valkey_config.port)],
        credentials=ServerCredentials(
            valkey_config.password,
            valkey_config.username,
        ),
        database_id=valkey_config.database_id,
    )
    return await GlideClient.create(config)
