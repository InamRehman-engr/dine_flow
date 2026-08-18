# DineFlow

Local-first multi-tenant QR table ordering, kitchen display, and waiter-call system. Served from your PC behind **Nginx**, exposed publicly via **ngrok**.

## Architecture

```text
Internet → ngrok → localhost:3080 → Nginx
                                  ├─ /           → Vue SPA (static)
                                  ├─ /api/       → Flask + Gunicorn (eventlet)
                                  └─ /socket.io/ → Flask-SocketIO
                                                    └─ PostgreSQL
```

## Quick start

1. Copy env and set your ngrok base URL (used for QR codes):

```bash
cp .env.example .env
# Set PUBLIC_BASE_URL=https://YOUR-SUBDOMAIN.ngrok-free.app
```

2. Start stack:

```bash
docker compose up --build
```

3. Tunnel port 3080:

```bash
ngrok http 3080
```

Point `PUBLIC_BASE_URL` at that https URL, then recreate the backend so QR export picks it up:

```bash
docker compose up -d --force-recreate backend
```

4. Open the app (local or ngrok URL) → **Register** a restaurant → **Create layout** (draw room boundary, drag tables) → Done downloads QR PDF → on a kitchen PC sign in as **Kitchen** with the same credentials.

## MVP scope

| Included | Not included |
| --- | --- |
| Tenant register / login / session / forgot-password | Online payments / POS replacement |
| Sign-in as Admin or Kitchen (same account, shared DB) | Separate staff user accounts |
| Freeform floor boundary + draggable tables + QR PDF | Cashier dashboard |
| Menu CRUD with image URLs + card-style customer menu | Email SMTP (reset token returned in API for local MVP) |
| Orders: pending → preparing → ready → served / cancelled | |
| Multiple open orders per table; free = no open tickets | |
| Waiter call + admin acknowledge | |
| Alembic migrations on startup | |

## Order lifecycle

```text
Customer submits cart → pending
Kitchen starts        → preparing
Kitchen plates        → ready
Served / cleared      → served   (table becomes free when no pending/preparing/ready remain)
Any open step         → cancelled (optional)
```

Optimistic concurrency: status updates send `version`; stale updates return `409`.

## Key URLs

- Admin: `/login` (choose Admin) → `/admin`, `/admin/menu`
- Kitchen: `/login` (choose Kitchen) → `/kitchen`
- Customer QR: `/menu?t=<opaque-table-token>` (not forgeable by changing table numbers)

## Secrets

All secrets live in `.env` (see `.env.example`). Do not commit real production passwords.
