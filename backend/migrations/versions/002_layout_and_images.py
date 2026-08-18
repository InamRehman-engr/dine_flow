"""floor layout positions and menu images

Revision ID: 002_layout_and_images
Revises: 001_initial
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa

revision = "002_layout_and_images"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tenants",
        sa.Column("floor_boundary", sa.Text(), nullable=True),
    )
    op.add_column(
        "dining_tables",
        sa.Column("pos_x", sa.Float(), nullable=False, server_default="20"),
    )
    op.add_column(
        "dining_tables",
        sa.Column("pos_y", sa.Float(), nullable=False, server_default="20"),
    )
    op.add_column(
        "menu_items",
        sa.Column("image_url", sa.String(500), nullable=True),
    )


def downgrade():
    op.drop_column("menu_items", "image_url")
    op.drop_column("dining_tables", "pos_y")
    op.drop_column("dining_tables", "pos_x")
    op.drop_column("tenants", "floor_boundary")
