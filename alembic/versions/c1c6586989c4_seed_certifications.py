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
    op.execute("""
        INSERT INTO certifications (id, name) VALUES 
        (1, 'G'),
        (2, 'PG'),
        (3, 'PG-13'),
        (4, 'R'),
        (5, 'NC-17')
        ON CONFLICT (name) DO UPDATE 
        SET id = EXCLUDED.id;
    """)

def downgrade() -> None:
    op.execute("DELETE FROM certifications WHERE id IN (1, 2, 3, 4, 5)")