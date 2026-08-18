"""add claim number sequence

Claim numbers are issued as VC-YYYY-NNNNN and must be unique. Deriving the next
number from MAX(claim_number) races under concurrent submissions: two requests
read the same maximum and one of them fails the unique constraint. A Postgres
sequence hands out distinct values without locking.

The sequence is global rather than per-year, so numbering continues across the
year boundary instead of restarting. Only the display prefix carries the year.

Revision ID: 33ab46e0c1e8
Revises: 95d527b58ec1
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '33ab46e0c1e8'
down_revision: Union[str, None] = '95d527b58ec1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEQUENCE_NAME = "claim_number_seq"


def upgrade() -> None:
    """Create the claim number sequence."""
    op.execute(
        f"CREATE SEQUENCE IF NOT EXISTS {SEQUENCE_NAME} "
        "START WITH 1 INCREMENT BY 1 MINVALUE 1 NO MAXVALUE CACHE 1"
    )


def downgrade() -> None:
    """Drop the claim number sequence."""
    op.execute(f"DROP SEQUENCE IF EXISTS {SEQUENCE_NAME}")
