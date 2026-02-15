# Shamelessly copied from
# https://github.com/Sehat1137/litestar-dishka-faststream

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from alphabet.shared.config import PostgresConfig


def new_session_maker(
    psql_config: PostgresConfig,
) -> async_sessionmaker[AsyncSession]:
    database_uri = (
        f"postgresql+psycopg://"
        f"{psql_config.username}"
        f":{psql_config.password}"
        f"@{psql_config.host}"
        f":{psql_config.port}"
        f"/{psql_config.database}"
    )

    engine = create_async_engine(
        database_uri,
        pool_size=psql_config.pool.size,
        max_overflow=psql_config.pool.max_overflow,
        connect_args={
            "connect_timeout": psql_config.pool.timeout_s,
        },
    )
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )
