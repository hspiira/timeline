"""Let the set-password link work before the person has signed in.

Revision ID: h6i7j8k9l0m1
Revises: g5h6i7j8k9l0
Create Date: 2026-08-11

Setting an initial password happens before anyone is authenticated, so there is no
tenant context. ``password_set_token`` is behind row-level security (its policy
reaches the tenant through ``app_user``), so an ordinary lookup finds nothing and the
endpoint reports "Invalid or expired link" for a perfectly good link. That blocked
onboarding an organisation's first administrator entirely.

Same remedy as ``signin_organisations``: one SECURITY DEFINER function, doing one
thing. It takes the SHA-256 hash of the token — never the token itself — claims it
atomically, and returns the membership and organisation it belongs to. The caller
then sets the tenant context and continues through the normal tenant-scoped path.

Claiming is a single UPDATE with a RETURNING clause, so two simultaneous redemptions
cannot both succeed: the token is one-time by construction, not by check-then-write.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "h6i7j8k9l0m1"
down_revision: str | Sequence[str] | None = "g5h6i7j8k9l0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CREATE_FN = """
CREATE OR REPLACE FUNCTION public.redeem_password_set_token(p_token_hash text)
RETURNS TABLE (user_id text, tenant_id text)
LANGUAGE sql
VOLATILE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $fn$
    WITH claimed AS (
        UPDATE password_set_token
        SET used_at = now()
        WHERE token_hash = p_token_hash
          AND used_at IS NULL
          AND expires_at > now()
        RETURNING password_set_token.user_id
    )
    SELECT u.id::text, u.tenant_id::text
    FROM claimed c
    JOIN app_user u ON u.id = c.user_id
$fn$;
"""

_GRANT = """
DO $$
BEGIN
    EXECUTE 'REVOKE ALL ON FUNCTION public.redeem_password_set_token(text) FROM PUBLIC';
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'timeline_app') THEN
        EXECUTE 'GRANT EXECUTE ON FUNCTION public.redeem_password_set_token(text) TO timeline_app';
    END IF;
END $$;
"""


def upgrade() -> None:
    """Create redeem_password_set_token and grant it to the application role if present."""
    op.execute(_CREATE_FN)
    op.execute(_GRANT)


def downgrade() -> None:
    """Drop redeem_password_set_token."""
    op.execute("DROP FUNCTION IF EXISTS public.redeem_password_set_token(text)")
