from typing import final

from alphabet.shared.commons import dto


@final
@dto
class PostgresPoolConfig:
    size: int = 25
    max_overflow: int = 15
    timeout_s: int = 5


@final
@dto
class PostgresConfig:
    username: str
    password: str
    host: str
    port: int
    pool: PostgresPoolConfig
    database: str = "alphabet"


@final
@dto
class LoggingConfig:
    use_json: bool = False


@final
@dto
class ValkeyConfig:
    host: str
    port: int
    username: str = "default"
    password: str | None = None
    database_id: int | None = None


@final
@dto
class ClickHouseConfig:
    host: str
    port: int = 8123
    username: str = "default"
    password: str = ""
    database: str = "default"


@final
@dto
class AppConfig:
    cooldown_experiment_threshold: int = 10
    cooldown_for_s: int = 60 * 60 * 24
    store_stickiness_for_s: int = 60 * 60 * 24 * 7 * 2
    event_deduplication_ttl_s: int = 60 * 60 * 24 * 7 + 1


@final
@dto
class WorkersConfig:
    attribution_interval_s: int = 60
    guardrail_interval_s: int = 60
    notification_interval_s: int = 15


@final
@dto
class EventBufferConfig:
    size: int = 2000
    force_flush_interval_s: int = 5


@final
@dto
class SmtpConfig:
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""
    sender_email: str = ""
    subject: str = "Alphabet Platform Notification"
    use_tls: bool = True

    @property
    def is_set_up(self) -> bool:
        return not (not self.host or not self.port or not self.sender_email)


@final
@dto
class TelegramConfig:
    token: str = ""

    @property
    def is_set_up(self) -> bool:
        return self.token != ""


@final
@dto
class NotificationChannelsConfig:
    smtp: SmtpConfig
    telegram: TelegramConfig


@final
@dto
class ConflictBufferConfig:
    size: int = 2000
    force_flush_interval_s: int = 5


@final
@dto
class AssignmentBufferConfig:
    size: int = 2000
    force_flush_interval_s: int = 5


@dto
class Config:
    postgres: PostgresConfig
    logging: LoggingConfig
    valkey: ValkeyConfig
    clickhouse: ClickHouseConfig
    app: AppConfig
    workers: WorkersConfig
    event_buffer: EventBufferConfig
    notifications: NotificationChannelsConfig
    conflict_buffer: ConflictBufferConfig
    assignment_buffer: AssignmentBufferConfig
    is_debug: bool = True
