"""Añade frame_index opcional a session_metrics."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20250331_0002"
down_revision = "20250331_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("session_metrics", sa.Column("frame_index", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("session_metrics", "frame_index")

