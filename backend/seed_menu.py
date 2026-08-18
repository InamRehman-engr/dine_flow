"""Seed demo menu categories/items with Unsplash images.

Usage (inside backend container or with app context):
  python seed_menu.py
  python seed_menu.py --email inam.rehman.cowlar@gmail.com
"""

from __future__ import annotations

import argparse
import sys

from app import create_app
from extensions import db
from models import MenuCategory, MenuItem, Tenant, utcnow


SEED = [
    (
        "Starters",
        0,
        [
            (
                "Burrata & Heirloom Tomato",
                "Creamy burrata, basil oil, grilled sourdough.",
                12.50,
                "https://images.unsplash.com/photo-1608897013039-887f21d8c804?auto=format&fit=crop&w=800&q=80",
            ),
            (
                "Crispy Calamari",
                "Flash-fried squid, lemon aioli, chili flakes.",
                14.00,
                "https://images.unsplash.com/photo-1559339352-11d035aa65de?auto=format&fit=crop&w=800&q=80",
            ),
            (
                "Seasonal Soup",
                "Chef’s daily soup with warm bread.",
                8.50,
                "https://images.unsplash.com/photo-1547592166-23ac45744acd?auto=format&fit=crop&w=800&q=80",
            ),
        ],
    ),
    (
        "Mains",
        1,
        [
            (
                "Wood-fired Margherita",
                "San Marzano tomato, fresh mozzarella, basil.",
                16.00,
                "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=800&q=80",
            ),
            (
                "Grilled Salmon",
                "Charred lemon, asparagus, herb butter.",
                24.00,
                "https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=800&q=80",
            ),
            (
                "Ribeye Steak",
                "12oz grass-fed ribeye, fries, chimichurri.",
                32.00,
                "https://images.unsplash.com/photo-1600891964092-4316c288032e?auto=format&fit=crop&w=800&q=80",
            ),
            (
                "Truffle Mushroom Pasta",
                "Tagliatelle, wild mushrooms, parmesan cream.",
                19.50,
                "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?auto=format&fit=crop&w=800&q=80",
            ),
        ],
    ),
    (
        "Drinks",
        2,
        [
            (
                "Fresh Lime Cooler",
                "House-pressed lime, mint, sparkling water.",
                5.50,
                "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=800&q=80",
            ),
            (
                "Iced Cold Brew",
                "Slow-steeped coffee over ice.",
                4.75,
                "https://images.unsplash.com/photo-1517701604599-bb29b565090c?auto=format&fit=crop&w=800&q=80",
            ),
            (
                "Sparkling Yuzu Sodas",
                "Citrus fizz with a soft floral finish.",
                6.00,
                "https://images.unsplash.com/photo-1622597467836-f3285f2131b8?auto=format&fit=crop&w=800&q=80",
            ),
        ],
    ),
    (
        "Desserts",
        3,
        [
            (
                "Dark Chocolate Fondant",
                "Molten center, vanilla ice cream.",
                11.00,
                "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=800&q=80",
            ),
            (
                "Lemon Tart",
                "Crisp pastry, citrus curd, meringue.",
                9.50,
                "https://images.unsplash.com/photo-1519915028121-7d3463d20b13?auto=format&fit=crop&w=800&q=80",
            ),
        ],
    ),
]


def seed_tenant(tenant: Tenant, replace: bool = False) -> tuple[int, int]:
    existing_items = MenuItem.query.filter_by(tenant_id=tenant.id).count()
    if existing_items and not replace:
        print(f"Tenant “{tenant.name}” already has {existing_items} items. Use --replace to recreate.")
        return 0, 0

    if replace:
        MenuItem.query.filter_by(tenant_id=tenant.id).delete()
        MenuCategory.query.filter_by(tenant_id=tenant.id).delete()
        db.session.flush()

    cat_count = 0
    item_count = 0
    for cat_name, sort_order, dishes in SEED:
        cat = MenuCategory(
            tenant_id=tenant.id,
            name=cat_name,
            sort_order=sort_order,
            created_at=utcnow(),
        )
        db.session.add(cat)
        db.session.flush()
        cat_count += 1
        for name, description, price, image_url in dishes:
            db.session.add(
                MenuItem(
                    tenant_id=tenant.id,
                    category_id=cat.id,
                    name=name,
                    description=description,
                    price=price,
                    image_url=image_url,
                    available=True,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
            )
            item_count += 1

    db.session.commit()
    return cat_count, item_count


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Seed Unsplash menu demo data")
    parser.add_argument("--email", default="", help="Tenant email (default: first tenant)")
    parser.add_argument("--replace", action="store_true", help="Delete existing menu first")
    args = parser.parse_args(argv)

    app = create_app()
    with app.app_context():
        if args.email:
            tenant = Tenant.query.filter_by(email=args.email.strip().lower()).first()
        else:
            tenant = Tenant.query.order_by(Tenant.created_at.asc()).first()

        if not tenant:
            print("No tenant found. Register a restaurant first.")
            return 1

        cats, items = seed_tenant(tenant, replace=args.replace)
        if cats or items:
            print(f"Seeded {cats} categories and {items} items for “{tenant.name}” ({tenant.email}).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
