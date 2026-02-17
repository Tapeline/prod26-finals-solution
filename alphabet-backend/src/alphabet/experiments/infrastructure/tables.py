from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import JSONB

from alphabet.experiments.domain.experiment import (
    ConflictPolicy,
    ExperimentOutcome,
    ExperimentState,
)
from alphabet.experiments.domain.flags import FlagType
from alphabet.shared.infrastructure.sql_meta import metadata

flags = Table(
    "flags",
    metadata,
    Column("key", String, primary_key=True, unique=True),
    Column("description", String),
    Column("type", Enum(FlagType)),
    Column("default", String),
    Column("author_id", String, ForeignKey("users.id")),
    Column("created_at", DateTime),
    Column("updated_at", DateTime),
)


def create_experiment_columns() -> tuple[Column[Any], ...]:
    return (
        Column("name", String),
        Column("flag_key", String, ForeignKey("flags.key")),
        Column("state", Enum(ExperimentState)),
        Column("version", Integer),
        Column("audience", Integer),
        Column("variants", JSONB),
        Column("targeting", String, nullable=True),
        Column("author_id", String, ForeignKey("users.id")),
        Column("created_at", DateTime),
        Column("updated_at", DateTime),
        Column("result_comment", String, nullable=True),
        Column("result_outcome", Enum(ExperimentOutcome), nullable=True),
        Column("metrics", JSONB),
        Column("priority", Integer, nullable=True),
        Column("conflict_domain", String, nullable=True),
        Column("conflict_policy", Enum(ConflictPolicy), nullable=True),
    )


experiments_latest = Table(
    "experiments_latest",
    metadata,
    Column("id", String, primary_key=True, unique=True),
    *create_experiment_columns(),
)

Index("exp_latest_flag_key_index", experiments_latest.c.flag_key)

experiments_history = Table(
    "experiments_history",
    metadata,
    Column("id", String),
    *create_experiment_columns(),
)

approvals = Table(
    "approvals",
    metadata,
    Column("experiment_id", String, ForeignKey("experiments_latest.id")),
    Column("approver_id", String, ForeignKey("users.id")),
)

review_decisions = Table(
    "review_decisions",
    metadata,
    Column(
        "experiment_id",
        String,
        ForeignKey("experiments_latest.id"),
        unique=True,
    ),
    Column("rejecter_id", String, ForeignKey("users.id"), nullable=True),
    Column("reject_comment", String, nullable=True),
)
