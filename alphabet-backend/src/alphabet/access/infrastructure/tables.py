from sqlalchemy import Column, Enum, ForeignKey, Index, Integer, String, Table

from alphabet.shared.domain.user import Role
from alphabet.shared.infrastructure.sql_meta import metadata

users = Table(
    "users",
    metadata,
    Column("id", String, primary_key=True, unique=True),
    Column("email", String, unique=True),
    Column("iap_id", String, nullable=True),
    Column("role", Enum(Role)),
    Column("approver_threshold", Integer, nullable=True),
)

Index("iap_id_index", users.c.iap_id)

approvers = Table(
    "assigned_approvers",
    metadata,
    Column("experimenter_id", String, ForeignKey("users.id"), nullable=False),
    Column("approver_id", String, ForeignKey("users.id"), nullable=False),
)
