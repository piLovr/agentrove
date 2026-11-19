"""add chats.remote_control (Hub fork)

Revision ID: a9b8c7d6e5f4
Revises: b9c0d1e2f3a4
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a9b8c7d6e5f4"
down_revision: str | None = "b9c0d1e2f3a4"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Default on, including for existing chats.
    op.add_column(
        "chats",
        sa.Column(
            "remote_control", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )


def downgrade() -> None:
    op.drop_column("chats", "remote_control")
