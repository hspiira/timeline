"""add full-text search_vector to subject and event

Revision ID: s6t7u8v9w0x1
Revises: p4q5r6s7t8u9
Create Date: 2025-02-15

Adds tsvector columns and triggers for full-text search on subject
(display_name, external_ref, attributes) and event (event_type, payload).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "s6t7u8v9w0x1"
down_revision: Union[str, Sequence[str], None] = "p4q5r6s7t8u9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Subject: search_vector from display_name, external_ref, attributes::text
    op.add_column(
        "subject",
        sa.Column("search_vector", sa.dialects.postgresql.TSVECTOR(), nullable=True),
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION subject_search_vector_fn()
        RETURNS trigger AS $$
        BEGIN
          NEW.search_vector := to_tsvector('english',
            coalesce(NEW.display_name, '') || ' ' || coalesce(NEW.external_ref, '')
            || ' ' || coalesce(NEW.attributes::text, ''));
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER subject_search_vector_trigger
        BEFORE INSERT OR UPDATE ON subject
        FOR EACH ROW EXECUTE FUNCTION subject_search_vector_fn()
        """
    )
    op.execute(
        """
        UPDATE subject SET search_vector = to_tsvector('english',
          coalesce(display_name, '') || ' ' || coalesce(external_ref, '') || ' '
          || coalesce(attributes::text, ''))
        WHERE search_vector IS NULL
        """
    )
    op.create_index(
        "ix_subject_search_vector",
        "subject",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )

    # Event: search_vector from event_type, payload::text (payload is JSONB)
    op.add_column(
        "event",
        sa.Column("search_vector", sa.dialects.postgresql.TSVECTOR(), nullable=True),
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION event_search_vector_fn()
        RETURNS trigger AS $$
        BEGIN
          NEW.search_vector := to_tsvector('english',
            coalesce(NEW.event_type, '') || ' ' || coalesce(NEW.payload::text, ''));
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER event_search_vector_trigger
        BEFORE INSERT OR UPDATE ON event
        FOR EACH ROW EXECUTE FUNCTION event_search_vector_fn()
        """
    )
    op.execute(
        """
        UPDATE event SET search_vector = to_tsvector('english',
          coalesce(event_type, '') || ' ' || coalesce(payload::text, ''))
        WHERE search_vector IS NULL
        """
    )
    op.create_index(
        "ix_event_search_vector",
        "event",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_search_vector", table_name="event", postgresql_using="gin"
    )
    op.execute("DROP TRIGGER IF EXISTS event_search_vector_trigger ON event")
    op.execute("DROP FUNCTION IF EXISTS event_search_vector_fn()")
    op.drop_column("event", "search_vector")

    op.drop_index(
        "ix_subject_search_vector", table_name="subject", postgresql_using="gin"
    )
    op.execute("DROP TRIGGER IF EXISTS subject_search_vector_trigger ON subject")
    op.execute("DROP FUNCTION IF EXISTS subject_search_vector_fn()")
    op.drop_column("subject", "search_vector")
