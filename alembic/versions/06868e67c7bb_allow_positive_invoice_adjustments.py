"""allow positive invoice adjustments

Revision ID: 06868e67c7bb
Revises: fa12e9c34658
Create Date: 2026-10-22 12:13:45.488189

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '06868e67c7bb'
down_revision: Union[str, Sequence[str], None] = 'fa12e9c34658'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
