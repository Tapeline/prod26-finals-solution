
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
class Config:
    postgres: PostgresConfig
    logging: LoggingConfig
    is_debug: bool = True
