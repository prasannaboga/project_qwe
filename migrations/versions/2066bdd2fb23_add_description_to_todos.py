"""add description to todos

Revision ID: 2066bdd2fb23
Revises: 9372e3b3c98f
Create Date: 2026-08-22 12:30:45.281241

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2066bdd2fb23'
down_revision: Union[str, Sequence[str], None] = '9372e3b3c98f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('description', sa.String(length=1000), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('todos', schema=None) as batch_op:
        batch_op.drop_column('description')
