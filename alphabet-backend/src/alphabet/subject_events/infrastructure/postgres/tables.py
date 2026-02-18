from sqlalchemy import (
    Column,
    String,
    Table,
    Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB

from alphabet.shared.infrastructure.sql_meta import metadata

event_types = Table(
    "event_types",
    metadata,
    Column("id", String, primary_key=True, unique=True),
    Column("name", String),
    Column("schema", JSONB),
    Column("requires_attribution", String, nullable=True),
    Column("is_archived", Boolean),
)
