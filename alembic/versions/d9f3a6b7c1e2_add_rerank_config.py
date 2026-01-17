"""add rerank config to datasets and app settings

Revision ID: d9f3a6b7c1e2
Revises: c7e9b4d1f8a2
Create Date: 2026-01-11 03:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d9f3a6b7c1e2"
down_revision: Union[str, None] = "c7e9b4d1f8a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("datasets", sa.Column("rerank_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("datasets", sa.Column("rerank_model", sa.String(), nullable=True))
    op.add_column("datasets", sa.Column("rerank_top_k", sa.Integer(), nullable=True))
    op.add_column("datasets", sa.Column("rerank_min_score", sa.Float(), nullable=True))
    op.add_column("app_settings", sa.Column("default_rerank_model", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("app_settings", "default_rerank_model")
    op.drop_column("datasets", "rerank_min_score")
    op.drop_column("datasets", "rerank_top_k")
    op.drop_column("datasets", "rerank_model")
    op.drop_column("datasets", "rerank_enabled")
