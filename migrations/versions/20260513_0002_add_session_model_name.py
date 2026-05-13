"""add session model name

Revision ID: 20260513_0002
Revises: 20260421_0001
Create Date: 2026-05-13 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260513_0002"
down_revision = "20260421_0001"
branch_labels = None
depends_on = None


DEFAULT_MODEL = "qwen/qwen3-next-80b-a3b-instruct:free"


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "model_name",
            sa.String(length=120),
            nullable=False,
            server_default=DEFAULT_MODEL,
        ),
    )


def downgrade() -> None:
    op.drop_column("sessions", "model_name")
