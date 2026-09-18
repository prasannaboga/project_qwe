"""add priority to todos

Revision ID: 1ec5a25dec6b
Revises: b1976b3395b4
Create Date: 2026-09-18 21:11:31.532559

Risk note: This migration adds a NOT NULL 'priority' column with server_default='medium'.
All pre-existing rows will receive 'medium' as their priority at migration time.
Downgrade drops the column — data loss for any stored priority values on rollback.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ec5a25dec6b'
down_revision: Union[str, Sequence[str], None] = 'b1976b3395b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add priority column (NOT NULL, server_default='medium') and its index to todos."""
    op.add_column(
        'todos',
        sa.Column(
            'priority',
            sa.Enum(
                'urgent', 'high', 'medium', 'low',
                name='todopriority',
                native_enum=False,
                create_constraint=True,
            ),
            server_default='medium',
            nullable=False,
        ),
    )
    op.create_index(op.f('ix_todos_priority'), 'todos', ['priority'], unique=False)


def downgrade() -> None:
    """Remove priority column and its index from todos."""
    op.drop_index(op.f('ix_todos_priority'), table_name='todos')
    op.drop_column('todos', 'priority')
