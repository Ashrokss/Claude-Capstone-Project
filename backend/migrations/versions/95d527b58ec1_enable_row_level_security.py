"""enable row level security

Enables RLS on every application table and grants no policies.

Supabase exposes a PostgREST Data API to anyone holding the publishable key,
which is public by design. With RLS off, that key can read and write every
claim. Enabling RLS without policies denies the `anon` and `authenticated`
roles outright, which is the posture this system wants: the FastAPI backend is
the only path to claims data, and it connects as the table owner, which is not
subject to RLS.

If the frontend is ever pointed straight at PostgREST, add per-table policies
here rather than disabling RLS.

Revision ID: 95d527b58ec1
Revises: 6d674d8aaf69
Create Date: 2026-08-17 11:25:41.689669

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '95d527b58ec1'
down_revision: Union[str, None] = '6d674d8aaf69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = (
    "claims",
    "documents",
    "images",
    "assessments",
    "damage_items",
    "fraud_indicators",
    "human_decisions",
)


def upgrade() -> None:
    """Enable RLS on every application table."""
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")

    # Revoke the blanket grants Supabase hands the API roles. RLS alone is
    # enough to block reads, but removing the grants means a future policy
    # added for one role cannot accidentally widen access for another.
    for table in TABLES:
        op.execute(f"REVOKE ALL ON public.{table} FROM anon, authenticated")


def downgrade() -> None:
    """Restore the default grants and disable RLS."""
    for table in TABLES:
        op.execute(f"GRANT ALL ON public.{table} TO anon, authenticated")

    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
