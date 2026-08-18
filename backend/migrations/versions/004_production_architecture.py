"""Alembic migration: staff, floors, stations, modifiers, audits, soft-delete, order FK."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004_production_architecture"
down_revision = "003_table_access_tokens"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # floors
    op.create_table(
        "floors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False, server_default="Main Floor"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("boundary", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_floors_tenant_id", "floors", ["tenant_id"])

    # staff_users
    op.create_table(
        "staff_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="manager"),
        sa.Column("display_name", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "email", name="uq_staff_tenant_email"),
    )
    op.create_index("ix_staff_users_tenant_id", "staff_users", ["tenant_id"])
    op.create_index("ix_staff_users_email", "staff_users", ["email"])

    # refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("staff_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff_users.id"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_refresh_tokens_staff_user_id", "refresh_tokens", ["staff_user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    # kitchen_stations
    op.create_table(
        "kitchen_stations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_kitchen_stations_tenant_id", "kitchen_stations", ["tenant_id"])

    # dining_tables: floor_id + deleted_at
    op.add_column("dining_tables", sa.Column("floor_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("dining_tables", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_dining_tables_floor_id", "dining_tables", "floors", ["floor_id"], ["id"])
    op.create_index("ix_dining_tables_floor_id", "dining_tables", ["floor_id"])

    # menu soft-delete + station
    op.add_column("menu_categories", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("menu_items", sa.Column("station_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("menu_items", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_menu_items_station_id", "menu_items", "kitchen_stations", ["station_id"], ["id"])
    op.create_index("ix_menu_items_station_id", "menu_items", ["station_id"])

    # modifier_groups + modifiers
    op.create_table(
        "modifier_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("menu_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("menu_items.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("max_select", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_modifier_groups_tenant_id", "modifier_groups", ["tenant_id"])
    op.create_index("ix_modifier_groups_menu_item_id", "modifier_groups", ["menu_item_id"])

    op.create_table(
        "modifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("modifier_groups.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("price_delta", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_modifiers_group_id", "modifiers", ["group_id"])

    # orders: dining_table_id
    op.add_column("orders", sa.Column("dining_table_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_orders_dining_table_id", "orders", "dining_tables", ["dining_table_id"], ["id"])
    op.create_index("ix_orders_dining_table_id", "orders", ["dining_table_id"])

    # order_items: station + modifiers snapshot
    op.add_column("order_items", sa.Column("station_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("order_items", sa.Column("modifiers_json", postgresql.JSONB(), nullable=True))
    op.create_foreign_key("fk_order_items_station_id", "order_items", "kitchen_stations", ["station_id"], ["id"])

    # order_status_audits
    op.create_table(
        "order_status_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("actor_staff_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff_users.id"), nullable=True),
        sa.Column("actor_label", sa.String(64), nullable=False, server_default="guest"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_order_status_audits_order_id", "order_status_audits", ["order_id"])
    op.create_index("ix_order_status_audits_tenant_id", "order_status_audits", ["tenant_id"])

    # waiter_calls: reason, note, dining_table_id
    op.add_column("waiter_calls", sa.Column("dining_table_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("waiter_calls", sa.Column("reason", sa.String(32), nullable=False, server_default="help"))
    op.add_column("waiter_calls", sa.Column("note", sa.Text(), nullable=True))
    op.create_foreign_key("fk_waiter_calls_dining_table_id", "waiter_calls", "dining_tables", ["dining_table_id"], ["id"])
    op.create_index("ix_waiter_calls_dining_table_id", "waiter_calls", ["dining_table_id"])

    # ---- data backfill ----
    conn = op.get_bind()

    # Staff from tenants
    conn.execute(
        sa.text(
            """
            INSERT INTO staff_users (id, tenant_id, email, password_hash, role, display_name, is_active, created_at)
            SELECT gen_random_uuid(), id, email, password_hash, 'manager', name, true, created_at
            FROM tenants
            WHERE NOT EXISTS (
              SELECT 1 FROM staff_users s WHERE s.tenant_id = tenants.id AND s.email = tenants.email
            )
            """
        )
    )

    # Default floor per tenant; copy legacy boundary
    conn.execute(
        sa.text(
            """
            INSERT INTO floors (id, tenant_id, name, sort_order, boundary, created_at)
            SELECT gen_random_uuid(), id, 'Main Floor', 0, floor_boundary, created_at
            FROM tenants
            WHERE NOT EXISTS (SELECT 1 FROM floors f WHERE f.tenant_id = tenants.id AND f.deleted_at IS NULL)
            """
        )
    )

    # Assign tables to first floor of their tenant
    conn.execute(
        sa.text(
            """
            UPDATE dining_tables dt
            SET floor_id = (
              SELECT f.id FROM floors f
              WHERE f.tenant_id = dt.tenant_id AND f.deleted_at IS NULL
              ORDER BY f.sort_order, f.created_at
              LIMIT 1
            )
            WHERE dt.floor_id IS NULL
            """
        )
    )

    # Backfill order dining_table_id
    conn.execute(
        sa.text(
            """
            UPDATE orders o
            SET dining_table_id = (
              SELECT t.id FROM dining_tables t
              WHERE t.tenant_id = o.tenant_id AND t.number = o.table_number AND t.deleted_at IS NULL
              LIMIT 1
            )
            WHERE o.dining_table_id IS NULL
            """
        )
    )

    # Backfill waiter_call dining_table_id
    conn.execute(
        sa.text(
            """
            UPDATE waiter_calls w
            SET dining_table_id = (
              SELECT t.id FROM dining_tables t
              WHERE t.tenant_id = w.tenant_id AND t.number = w.table_number AND t.deleted_at IS NULL
              LIMIT 1
            )
            WHERE w.dining_table_id IS NULL
            """
        )
    )


def downgrade():
    op.drop_constraint("fk_waiter_calls_dining_table_id", "waiter_calls", type_="foreignkey")
    op.drop_index("ix_waiter_calls_dining_table_id", "waiter_calls")
    op.drop_column("waiter_calls", "note")
    op.drop_column("waiter_calls", "reason")
    op.drop_column("waiter_calls", "dining_table_id")

    op.drop_table("order_status_audits")

    op.drop_constraint("fk_order_items_station_id", "order_items", type_="foreignkey")
    op.drop_column("order_items", "modifiers_json")
    op.drop_column("order_items", "station_id")

    op.drop_constraint("fk_orders_dining_table_id", "orders", type_="foreignkey")
    op.drop_index("ix_orders_dining_table_id", "orders")
    op.drop_column("orders", "dining_table_id")

    op.drop_table("modifiers")
    op.drop_table("modifier_groups")

    op.drop_constraint("fk_menu_items_station_id", "menu_items", type_="foreignkey")
    op.drop_index("ix_menu_items_station_id", "menu_items")
    op.drop_column("menu_items", "deleted_at")
    op.drop_column("menu_items", "station_id")
    op.drop_column("menu_categories", "deleted_at")

    op.drop_constraint("fk_dining_tables_floor_id", "dining_tables", type_="foreignkey")
    op.drop_index("ix_dining_tables_floor_id", "dining_tables")
    op.drop_column("dining_tables", "deleted_at")
    op.drop_column("dining_tables", "floor_id")

    op.drop_table("kitchen_stations")
    op.drop_table("refresh_tokens")
    op.drop_table("staff_users")
    op.drop_table("floors")
