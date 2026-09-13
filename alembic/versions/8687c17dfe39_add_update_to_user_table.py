"""add update to user table

Revision ID: 8687c17dfe39
Revises: 82fb702cb1ba
Create Date: 2026-09-13 04:47:46.693905

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8687c17dfe39'
down_revision: Union[str, Sequence[str], None] = '82fb702cb1ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('auth_provider', sa.String(), nullable=True))
    op.add_column('users', sa.Column('auth_provider_id', sa.String(length=64), nullable=True, index=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'auth_provider_id')
