"""seed_certifications

Revision ID: c1c6586989c4
Revises: d87dec9aae84
Create Date: 2026-11-15 14:45:08.745853

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1c6586989c4'
down_revision: Union[str, None] = 'd87dec9aae84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    certifications_table = sa.table(
        'certifications',
        sa.column('id', sa.Integer()),
        sa.column('name', sa.String())
    )

    op.bulk_insert(
        certifications_table,
        [
            {"id": 1, "name": "G"},
            {"id": 2, "name": "PG"},
            {"id": 3, "name": "PG-13"},
            {"id": 4, "name": "R"},
            {"id": 5, "name": "NC-17"},
        ]
    )


def downgrade() -> None:
    op.execute("DELETE FROM certifications WHERE name IN ('G', 'PG', 'PG-13', 'R', 'NC-17')")
