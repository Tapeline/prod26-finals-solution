from sqlalchemy import (
    Column, Boolean, ForeignKey, String, Table, Double,
    Integer, Enum, DateTime,
)

from alphabet.guardrails.domain import GuardAction
from alphabet.shared.infrastructure.sql_meta import metadata

guard_rules = Table(
    "guard_rules",
    metadata,
    Column("id", String, primary_key=True, unique=True),
    Column("experiment_id", String, ForeignKey("experiments_latest.id")),
    Column("metric_key", String),
    Column("threshold", Double),
    Column("watch_window_s", Integer),
    Column("action", Enum(GuardAction)),
    Column("is_archived", Boolean)
)

audit_log = Table(
    "audit_log",
    metadata,
    Column("id", String, primary_key=True, unique=True),
    Column("rule_id", String, ForeignKey("guard_rules.id")),
    Column("fired_at", DateTime),
    Column("experiment_id", String, ForeignKey("experiments_latest.id")),
    Column("metric_key", String),
    Column("metric_value", Double),
    Column("taken_action", Enum(GuardAction)),
)
