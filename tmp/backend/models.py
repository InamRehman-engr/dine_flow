import json
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import JSONB, UUID
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


def new_table_access_token() -> str:
    """Opaque unguessable token used in guest QR links (not sequential table numbers)."""
    return secrets.token_urlsafe(24)


STAFF_ROLES = ("manager", "kitchen")
WAITER_REASONS = ("water", "bill", "help", "other")

ORDER_STATUSES = ("pending", "preparing", "ready", "served", "cancelled")
OPEN_ORDER_STATUSES = ("pending", "preparing", "ready")

ALLOWED_TRANSITIONS = {
    "pending": {"preparing", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready": {"served", "cancelled"},
    "served": set(),
    "cancelled": set(),
}


class Tenant(db.Model):
    __tablename__ = "tenants"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    reset_token = db.Column(db.String(64), nullable=True, index=True)
    reset_token_expires = db.Column(db.DateTime(timezone=True), nullable=True)
    # Legacy — migrated to floors.boundary; kept for backwards-compatible reads
    floor_boundary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    tables = db.relationship("DiningTable", back_populates="tenant", cascade="all, delete-orphan")
    floors = db.relationship("Floor", back_populates="tenant", cascade="all, delete-orphan")
    staff_users = db.relationship("StaffUser", back_populates="tenant", cascade="all, delete-orphan")
    categories = db.relationship("MenuCategory", back_populates="tenant", cascade="all, delete-orphan")
    menu_items = db.relationship("MenuItem", back_populates="tenant", cascade="all, delete-orphan")
    orders = db.relationship("Order", back_populates="tenant", cascade="all, delete-orphan")
    stations = db.relationship("KitchenStation", back_populates="tenant", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_floor_boundary(self):
        if not self.floor_boundary:
            return []
        try:
            data = json.loads(self.floor_boundary)
            return data if isinstance(data, list) else []
        except (TypeError, ValueError, json.JSONDecodeError):
            return []

    def set_floor_boundary(self, points):
        if not points:
            self.floor_boundary = None
        else:
            self.floor_boundary = json.dumps(points)

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StaffUser(db.Model):
    __tablename__ = "staff_users"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "email", name="uq_staff_tenant_email"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="manager")
    display_name = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="staff_users")
    refresh_tokens = db.relationship("RefreshToken", back_populates="staff_user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "email": self.email,
            "role": self.role,
            "display_name": self.display_name,
            "is_active": self.is_active,
        }


class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("staff_users.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    staff_user = db.relationship("StaffUser", back_populates="refresh_tokens")


class Floor(db.Model):
    __tablename__ = "floors"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False, default="Main Floor")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    boundary = db.Column(db.Text, nullable=True)  # JSON list of {x,y}
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="floors")
    tables = db.relationship("DiningTable", back_populates="floor")

    def get_boundary(self):
        if not self.boundary:
            return []
        try:
            data = json.loads(self.boundary)
            return data if isinstance(data, list) else []
        except (TypeError, ValueError, json.JSONDecodeError):
            return []

    def set_boundary(self, points):
        if not points:
            self.boundary = None
        else:
            self.boundary = json.dumps(points)

    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "sort_order": self.sort_order,
            "boundary": self.get_boundary(),
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class DiningTable(db.Model):
    __tablename__ = "dining_tables"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "number", name="uq_tenant_table_number"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    floor_id = db.Column(UUID(as_uuid=True), db.ForeignKey("floors.id"), nullable=True, index=True)
    number = db.Column(db.Integer, nullable=False)
    access_token = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        index=True,
        default=new_table_access_token,
    )
    cell_index = db.Column(db.Integer, nullable=False, default=0)
    pos_x = db.Column(db.Float, nullable=False, default=20.0)
    pos_y = db.Column(db.Float, nullable=False, default=20.0)
    capacity = db.Column(db.Integer, nullable=False, default=4)
    version = db.Column(db.Integer, nullable=False, default=1)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="tables")
    floor = db.relationship("Floor", back_populates="tables")
    orders = db.relationship("Order", back_populates="dining_table")

    def to_dict(self, occupancy=None, waiter_alert=False, include_token=False, open_ticket_count=0):
        data = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "floor_id": str(self.floor_id) if self.floor_id else None,
            "number": self.number,
            "cell_index": self.cell_index,
            "pos_x": float(self.pos_x),
            "pos_y": float(self.pos_y),
            "capacity": self.capacity,
            "version": self.version,
            "occupancy": occupancy or "free",
            "waiter_alert": waiter_alert,
            "open_ticket_count": open_ticket_count,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
        if include_token:
            data["access_token"] = self.access_token
        return data


class KitchenStation(db.Model):
    __tablename__ = "kitchen_stations"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="stations")
    items = db.relationship("MenuItem", back_populates="station")

    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "sort_order": self.sort_order,
        }


class MenuCategory(db.Model):
    __tablename__ = "menu_categories"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="categories")
    items = db.relationship("MenuItem", back_populates="category")

    def to_dict(self, include_items=False):
        data = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "sort_order": self.sort_order,
        }
        if include_items:
            data["items"] = [i.to_dict() for i in self.items if not i.deleted_at]
        return data


class MenuItem(db.Model):
    __tablename__ = "menu_items"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    category_id = db.Column(UUID(as_uuid=True), db.ForeignKey("menu_categories.id"), nullable=True, index=True)
    station_id = db.Column(UUID(as_uuid=True), db.ForeignKey("kitchen_stations.id"), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    image_url = db.Column(db.String(500), nullable=True)
    available = db.Column(db.Boolean, nullable=False, default=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="menu_items")
    category = db.relationship("MenuCategory", back_populates="items")
    station = db.relationship("KitchenStation", back_populates="items")
    modifier_groups = db.relationship(
        "ModifierGroup",
        back_populates="menu_item",
        cascade="all, delete-orphan",
        order_by="ModifierGroup.sort_order",
    )

    def to_dict(self, include_modifiers=False):
        data = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "category_id": str(self.category_id) if self.category_id else None,
            "station_id": str(self.station_id) if self.station_id else None,
            "name": self.name,
            "description": self.description,
            "price": float(self.price),
            "image_url": self.image_url,
            "available": self.available,
            "version": self.version,
        }
        if include_modifiers:
            data["modifier_groups"] = [g.to_dict() for g in self.modifier_groups if not g.deleted_at]
        return data


class ModifierGroup(db.Model):
    __tablename__ = "modifier_groups"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    menu_item_id = db.Column(UUID(as_uuid=True), db.ForeignKey("menu_items.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    required = db.Column(db.Boolean, nullable=False, default=False)
    max_select = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    menu_item = db.relationship("MenuItem", back_populates="modifier_groups")
    modifiers = db.relationship(
        "Modifier",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="Modifier.sort_order",
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "menu_item_id": str(self.menu_item_id),
            "name": self.name,
            "required": self.required,
            "max_select": self.max_select,
            "sort_order": self.sort_order,
            "modifiers": [m.to_dict() for m in self.modifiers if not m.deleted_at],
        }


class Modifier(db.Model):
    __tablename__ = "modifiers"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = db.Column(UUID(as_uuid=True), db.ForeignKey("modifier_groups.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    price_delta = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    group = db.relationship("ModifierGroup", back_populates="modifiers")

    def to_dict(self):
        return {
            "id": str(self.id),
            "group_id": str(self.group_id),
            "name": self.name,
            "price_delta": float(self.price_delta),
            "sort_order": self.sort_order,
        }


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    dining_table_id = db.Column(UUID(as_uuid=True), db.ForeignKey("dining_tables.id"), nullable=True, index=True)
    table_number = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, default="pending", index=True)
    notes = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="orders")
    dining_table = db.relationship("DiningTable", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    audits = db.relationship("OrderStatusAudit", back_populates="order", cascade="all, delete-orphan")

    def to_dict(self, include_audits=False):
        station_ids = set()
        for item in self.items:
            if item.station_id:
                station_ids.add(str(item.station_id))
        data = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "dining_table_id": str(self.dining_table_id) if self.dining_table_id else None,
            "table_number": self.table_number,
            "status": self.status,
            "notes": self.notes,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "items": [i.to_dict() for i in self.items],
            "station_ids": list(station_ids),
        }
        if include_audits:
            data["audits"] = [a.to_dict() for a in sorted(self.audits, key=lambda x: x.created_at)]
        return data


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = db.Column(UUID(as_uuid=True), db.ForeignKey("orders.id"), nullable=False, index=True)
    menu_item_id = db.Column(UUID(as_uuid=True), db.ForeignKey("menu_items.id"), nullable=True)
    station_id = db.Column(UUID(as_uuid=True), db.ForeignKey("kitchen_stations.id"), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    modifiers_json = db.Column(JSONB, nullable=True)  # [{name, price_delta}]

    order = db.relationship("Order", back_populates="items")

    def to_dict(self):
        mods = self.modifiers_json or []
        return {
            "id": str(self.id),
            "order_id": str(self.order_id),
            "menu_item_id": str(self.menu_item_id) if self.menu_item_id else None,
            "station_id": str(self.station_id) if self.station_id else None,
            "name": self.name,
            "unit_price": float(self.unit_price),
            "quantity": self.quantity,
            "modifiers": mods,
            "line_total": float(self.unit_price) * self.quantity,
        }


class OrderStatusAudit(db.Model):
    __tablename__ = "order_status_audits"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = db.Column(UUID(as_uuid=True), db.ForeignKey("orders.id"), nullable=False, index=True)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    from_status = db.Column(db.String(32), nullable=True)
    to_status = db.Column(db.String(32), nullable=False)
    actor_staff_id = db.Column(UUID(as_uuid=True), db.ForeignKey("staff_users.id"), nullable=True)
    actor_label = db.Column(db.String(64), nullable=False, default="guest")
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    order = db.relationship("Order", back_populates="audits")

    def to_dict(self):
        return {
            "id": str(self.id),
            "order_id": str(self.order_id),
            "from_status": self.from_status,
            "to_status": self.to_status,
            "actor_staff_id": str(self.actor_staff_id) if self.actor_staff_id else None,
            "actor_label": self.actor_label,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WaiterCall(db.Model):
    __tablename__ = "waiter_calls"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    dining_table_id = db.Column(UUID(as_uuid=True), db.ForeignKey("dining_tables.id"), nullable=True, index=True)
    table_number = db.Column(db.Integer, nullable=False, index=True)
    reason = db.Column(db.String(32), nullable=False, default="help")
    note = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(16), nullable=False, default="open")  # open | acked
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    acked_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "dining_table_id": str(self.dining_table_id) if self.dining_table_id else None,
            "table_number": self.table_number,
            "reason": self.reason,
            "note": self.note,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "acked_at": self.acked_at.isoformat() if self.acked_at else None,
        }
