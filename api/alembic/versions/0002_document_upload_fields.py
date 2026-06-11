"""document upload fields: size, mime, error

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "documents",
        sa.Column("mime", sa.String(length=64), nullable=False, server_default=""),
    )
    op.add_column("documents", sa.Column("error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "error")
    op.drop_column("documents", "mime")
    op.drop_column("documents", "size_bytes")
