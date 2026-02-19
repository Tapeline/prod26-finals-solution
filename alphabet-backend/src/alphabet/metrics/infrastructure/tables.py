from sqlalchemy import Column, DateTime, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import JSONB

from alphabet.shared.infrastructure.sql_meta import metadata

metrics = Table(
    "metrics",
    metadata,
    Column("key", String, primary_key=True, unique=True),
    Column("expression", String),
    Column("compiled", JSONB, nullable=False),
)

reports = Table(
    "reports",
    metadata,
    Column("id", String, primary_key=True, unique=True),
    Column(
        "experiment_id",
        String,
        ForeignKey("experiments_latest.id"),
    ),
    Column("start_at", DateTime),
    Column("end_at", DateTime),
)
