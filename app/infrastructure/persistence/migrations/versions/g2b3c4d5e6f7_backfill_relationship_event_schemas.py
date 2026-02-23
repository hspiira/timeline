"""Backfill event_schema for relationship_added and relationship_removed.

Revision ID: g2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-02-18

Adds version 1 event schemas for relationship_added and relationship_removed
for every existing tenant that does not already have them (so existing tenants
can emit relationship events; new tenants get them from tenant init).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "g2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Same shape as get_relationship_event_schema_definition()
RELATIONSHIP_EVENT_SCHEMA_JSON = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Relationship Event Payload",
  "description": "Payload for relationship_added and relationship_removed events",
  "type": "object",
  "required": ["related_subject_id", "relationship_kind"],
  "properties": {
    "related_subject_id": {"type": "string", "minLength": 1},
    "relationship_kind": {"type": "string", "minLength": 1, "maxLength": 100}
  },
  "additionalProperties": true
}"""


def upgrade() -> None:
    conn = op.get_bind()
    # Get all tenant ids
    result = conn.execute(text("SELECT id FROM tenant"))
    tenant_ids = [row[0] for row in result]
    if not tenant_ids:
        return

    # For each tenant, insert relationship_added and relationship_removed schemas
    # if they don't already exist (idempotent: check by tenant_id + event_type + version).
    for tenant_id in tenant_ids:
        for event_type in ("relationship_added", "relationship_removed"):
            check = conn.execute(
                text(
                    "SELECT 1 FROM event_schema "
                    "WHERE tenant_id = :tid AND event_type = :et AND version = 1"
                ),
                {"tid": tenant_id, "et": event_type},
            ).fetchone()
            if check:
                continue
            # generate_cuid() is not available in migration; use gen_random_uuid() or a simple id.
            conn.execute(
                text(
                    "INSERT INTO event_schema (id, tenant_id, event_type, schema_definition, version, is_active, created_at, updated_at, created_by) "
                    "VALUES (gen_random_uuid()::text, :tid, :et, CAST(:schema_def AS jsonb), 1, true, now(), now(), null)"
                ),
                {
                    "tid": tenant_id,
                    "et": event_type,
                    "schema_def": RELATIONSHIP_EVENT_SCHEMA_JSON,
                },
            )


def downgrade() -> None:
    # Remove relationship event schemas (version 1 only) for all tenants
    op.execute(
        text(
            "DELETE FROM event_schema "
            "WHERE event_type IN ('relationship_added', 'relationship_removed') AND version = 1"
        )
    )
