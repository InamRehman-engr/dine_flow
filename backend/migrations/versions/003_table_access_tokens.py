"""table access tokens for QR guest links

Revision ID: 003_table_access_tokens
Revises: 002_layout_and_images
Create Date: 2026-07-14
"""

import secrets

from alembic import op
import sqlalchemy as sa

revision = "003_table_access_tokens"
down_revision = "002_layout_and_images"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dining_tables",
        sa.Column("access_token", sa.String(64), nullable=True),
    )

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM dining_tables WHERE access_token IS NULL")).fetchall()
    for (table_id,) in rows:
        token = secrets.token_urlsafe(24)
        conn.execute(
            sa.text("UPDATE dining_tables SET access_token = :token WHERE id = :id"),
            {"token": token, "id": table_id},
        )

    op.alter_column("dining_tables", "access_token", nullable=False)
    op.create_index("ix_dining_tables_access_token", "dining_tables", ["access_token"], unique=True)


def downgrade():
    op.drop_index("ix_dining_tables_access_token", table_name="dining_tables")
    op.drop_column("dining_tables", "access_token")
