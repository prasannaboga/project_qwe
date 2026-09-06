"""add_indexes_for_todos_pagination_and_sorting

Revision ID: b1976b3395b4
Revises: 2066bdd2fb23
Create Date: 2026-09-06 20:58:03.599355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1976b3395b4'
down_revision: Union[str, Sequence[str], None] = '2066bdd2fb23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_todos_created_at'), 'todos', ['created_at'], unique=False)
    op.create_index(op.f('ix_todos_due_at'), 'todos', ['due_at'], unique=False)
    op.create_index(op.f('ix_todos_status'), 'todos', ['status'], unique=False)
    op.create_index(op.f('ix_todos_title'), 'todos', ['title'], unique=False)
    op.create_index(op.f('ix_todos_updated_at'), 'todos', ['updated_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_todos_updated_at'), table_name='todos')
    op.drop_index(op.f('ix_todos_title'), table_name='todos')
    op.drop_index(op.f('ix_todos_status'), table_name='todos')
    op.drop_index(op.f('ix_todos_due_at'), table_name='todos')
    op.drop_index(op.f('ix_todos_created_at'), table_name='todos')
