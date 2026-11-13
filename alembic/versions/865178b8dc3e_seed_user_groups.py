"""seed user groups

Revision ID: 865178b8dc3e
Revises: b294d6275fb6
Create Date: 2026-11-12 12:12:30.337518

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "865178b8dc3e"
down_revision: Union[str, None] = "b294d6275fb6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("INSERT INTO user_groups (name) VALUES ('USER'), ('MODERATOR'), ('ADMIN')")


def downgrade() -> None:
    op.execute("DELETE FROM user_groups")
