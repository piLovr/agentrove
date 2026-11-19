"""merge heads: remote_control (Hub fork) and per-event notifications (upstream)

Databases that already ran a9b8c7d6e5f4 still need b9c0d1e2f3a4; this merge makes
Alembic apply it and leaves a single head.

Revision ID: c1d2e3f4a5b6
Revises: a9b8c7d6e5f4, b9c0d1e2f3a4
"""

from typing import Sequence

revision: str = "c1d2e3f4a5b6"
down_revision: str | Sequence[str] | None = ("a9b8c7d6e5f4", "b9c0d1e2f3a4")
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
