from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB

from alphabet.shared.infrastructure.sql_meta import metadata

notification_rules = Table(
    "notification_rules",
    metadata,
    Column("id", String, primary_key=True, unique=True),
    Column("trigger_type", String, nullable=False, index=True),
    Column("trigger_resource", String, nullable=False),
    Column("connection_string", String, nullable=False),
    Column("message_template", Text, nullable=False),
    Column("rate_limit_s", Integer, nullable=False),
)

prepared_notifications = Table(
    "prepared_notifications",
    metadata,
    Column("fingerprint", String, primary_key=True, unique=True),
    Column("rule_id", String, nullable=False, index=True),
    Column("meta", JSONB, nullable=False),
    Column("issued_at", DateTime(timezone=True), nullable=False),
)
