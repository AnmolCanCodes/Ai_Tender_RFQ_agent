"""create initial tables

Revision ID: 5a21727cf748
Revises: 
Create Date: 2026-10-06 13:19:46.502917

"""
from typing import Sequence, Union

from alembic import op

from app.core.database import Base


# revision identifiers, used by Alembic.
revision: str = '5a21727cf748'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the application's initial schema if it does not already exist."""
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    """Drop the initial schema."""
    Base.metadata.drop_all(bind=op.get_bind())
