"""add unique constraint to tenant name

Revision ID: a1b2c3d4e5f6
Revises: 85fe3dccc734
Create Date: 2026-01-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '85fe3dccc734'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add unique constraint to tenant name
    op.create_unique_constraint('uq_tenant_name', 'tenants', ['name'])


def downgrade() -> None:
    # Remove unique constraint
    op.drop_constraint('uq_tenant_name', 'tenants', type_='unique')
