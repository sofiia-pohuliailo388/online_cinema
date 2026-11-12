"""merge conflicting migrations

Revision ID: 13e97a87d283
Revises: 865178b8dc3e, a05da154e8a8
Create Date: 2026-11-12 20:05:25.324775

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '13e97a87d283'
down_revision: Union[str, None] = ('865178b8dc3e', 'a05da154e8a8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
