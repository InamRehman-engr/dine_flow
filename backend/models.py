import json
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


def utcnow():
    return datetime.now(timezone.utc)


def new_table_access_token() -> str:
    """Opaque unguessable token used in guest QR links (not sequential table numbers)."""
    return secrets.token_urlsafe(24)


class Tenant(db.Model):
    __tablename__ = "tenants"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    reset_token = db.Column(db.String(64), nullable=True, index=True)
    reset_token_expires = db.Column(db.DateTime(timezone=True), nullable=True)
    # JSON list of {x, y} points (0–100 %) describing the floor boundary polygon
    floor_boundary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    tables = db.relationship("DiningTable", back_populates="tenant", cascade="all, delete-orphan")
    categories = db.relationship("MenuCategory", back_populates="tenant", cascade="all, delete-orphan")
    menu_items = db.relationship("MenuItem", back_populates="tenant", cascade="all, delete-orphan")
    orders = db.relationship("Order", back_populates="tenant", cascade="all, delete-orphan")

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
            "floor_boundary": self.get_floor_boundary(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DiningTable(db.Model):
    __tablename__ = "dining_tables"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "number", name="uq_tenant_table_number"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    number = db.Column(db.Integer, nullable=False)
    access_token = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        index=True,
        default=new_table_access_token,
    )
    cell_index = db.Column(db.Integer, nullable=False, default=0)  # legacy; prefer pos_x/pos_y
    pos_x = db.Column(db.Float, nullable=False, default=20.0)  # % of canvas width
    pos_y = db.Column(db.Float, nullable=False, default=20.0)  # % of canvas height
    capacity = db.Column(db.Integer, nullable=False, default=4)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="tables")

    def to_dict(self, occupancy=None, waiter_alert=False, include_token=False):
        data = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "number": self.number,
            "cell_index": self.cell_index,
            "pos_x": float(self.pos_x),
            "pos_y": float(self.pos_y),
            "capacity": self.capacity,
            "version": self.version,
            "occupancy": occupancy or "free",
            "waiter_alert": waiter_alert,
        }
        if include_token:
            data["access_token"] = self.access_token
        return data


class MenuCategory(db.Model):
    __tablename__ = "menu_categories"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="categories")
    items = db.relationship("MenuItem", back_populates="category", cascade="all, delete-orphan")

    def to_dict(self, include_items=False):
        data = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "sort_order": self.sort_order,
        }
        if include_items:
            data["items"] = [i.to_dict() for i in self.items]
        return data


class MenuItem(db.Model):
    __tablename__ = "menu_items"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    category_id = db.Column(UUID(as_uuid=True), db.ForeignKey("menu_categories.id"), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    image_url = db.Column(db.String(500), nullable=True)
    available = db.Column(db.Boolean, nullable=False, default=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="menu_items")
    category = db.relationship("MenuCategory", back_populates="items")

    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "category_id": str(self.category_id) if self.category_id else None,
            "name": self.name,
            "description": self.description,
            "price": float(self.price),
            "image_url": self.image_url,
            "available": self.available,
            "version": self.version,
        }


ORDER_STATUSES = ("pending", "preparing", "ready", "served", "cancelled")
OPEN_ORDER_STATUSES = ("pending", "preparing", "ready")

ALLOWED_TRANSITIONS = {
    "pending": {"preparing", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready": {"served", "cancelled"},
    "served": set(),
    "cancelled": set(),
}


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    table_number = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, default="pending", index=True)
    notes = db.Column(db.Text, nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    tenant = db.relationship("Tenant", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "table_number": self.table_number,
            "status": self.status,
            "notes": self.notes,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "items": [i.to_dict() for i in self.items],
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = db.Column(UUID(as_uuid=True), db.ForeignKey("orders.id"), nullable=False, index=True)
    menu_item_id = db.Column(UUID(as_uuid=True), db.ForeignKey("menu_items.id"), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    order = db.relationship("Order", back_populates="items")

    def to_dict(self):
        return {
            "id": str(self.id),
            "order_id": str(self.order_id),
            "menu_item_id": str(self.menu_item_id) if self.menu_item_id else None,
            "name": self.name,
            "unit_price": float(self.unit_price),
            "quantity": self.quantity,
            "line_total": float(self.unit_price) * self.quantity,
        }


class WaiterCall(db.Model):
    __tablename__ = "waiter_calls"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tenants.id"), nullable=False, index=True)
    table_number = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(db.String(16), nullable=False, default="open")  # open | acked
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    acked_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "table_number": self.table_number,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "acked_at": self.acked_at.isoformat() if self.acked_at else None,
        }
