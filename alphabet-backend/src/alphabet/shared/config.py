from alphabet.shared.commons import dto


@dto
class PostgresPoolConfig:
    size: int = 25
    max_overflow: int = 15
    timeout_s: int = 5


@dto
class PostgresConfig:
    username: str
    password: str
    host: str
    port: int
    pool: PostgresPoolConfig
    database: str = "alphabet"


@dto
class LoggingConfig:
    use_json: bool = False


@dto
class ValkeyConfig:
    host: str
    port: int
    username: str = "default"
    password: str | None = None
    database_id: int | None = None


@dto
class ClickHouseConfig:
    host: str
    port: int = 8123
    username: str = "default"
    password: str = ""
    database: str = "default"


@dto
class AppConfig:
    cooldown_after_s: int = 60 * 60 * 24
    cooldown_for_s: int = 60 * 60 * 24
    store_stickiness_for_s: int = 60 * 60 * 24 * 7 * 2
    event_deduplication_ttl_s: int = 60 * 60 * 24 * 7 + 1


@dto
class WorkersConfig:
    attribution_interval_s: int = 60
    guardrail_interval_s: int = 60


@dto
class EventBufferConfig:
    size: int = 2000
    force_flush_interval_s: int = 60


@dto
class Config:
    postgres: PostgresConfig
    logging: LoggingConfig
    valkey: ValkeyConfig
    clickhouse: ClickHouseConfig
    app: AppConfig
    workers: WorkersConfig
    event_buffer: EventBufferConfig
    is_debug: bool = True
