# Judith's Hair Room — Digital Secretary

Production-oriented MVP for a one-person hair salon. The product is intentionally designed as a **digital secretary**, not a complicated salon ERP: it keeps the calendar safe, tells Judith who is next, tracks deposits/balances, and makes her available/occupied state obvious.

## Architecture

- `frontend/` — React + Vite + TypeScript + Tailwind CSS, mobile-first UI, prepared for React Router.
- `backend/` — FastAPI + Pydantic + SQLAlchemy REST API.
- `backend/alembic/` — PostgreSQL migrations and initial salon/style seed data.
- PostgreSQL — Supabase in production. **SQLite is not supported.**
- GitHub Pages — frontend hosting initially.
- Render — backend hosting initially.

## Milestones

### Milestone 1 — Foundation
- Repository split into frontend/backend/database migration areas.
- Environment-driven configuration.
- Production PostgreSQL requirement.
- React Router dependency prepared.
- Health endpoint.

### Milestone 2 — Database
- Normalized models for settings, styles, customers, appointments, payments, blocked time, inventory, expenses and notifications.
- UUID primary keys, foreign keys, indexes, checks and timestamps.
- Alembic initial migration with salon defaults and the supplied style/pricing ranges.

### Milestone 3 — FastAPI foundation
- REST endpoints for styles, appointments, availability, customers, payments, blocked time and dashboard.
- Pydantic validation and consistent HTTP error responses.
- CORS from environment variables.

### Milestone 4 — Availability engine
- Backend is the source of truth.
- Half-open overlap rule: `requested_start < existing_end AND requested_end > existing_start`.
- Cancelled and no-show appointments do not block.
- Blocked time blocks bookings.
- Opening/closing hours, working days, minimum notice and advance-booking limits are enforced.
- PostgreSQL GiST exclusion constraint prevents overlapping blocking appointments.
- PostgreSQL advisory transaction lock serializes booking operations for the same day, protecting the availability-check/create sequence.
- Occupied slots return `409 CONFLICT` plus alternative slots.

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set DATABASE_URL to a PostgreSQL/Supabase connection string
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Health: `GET /health`

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Set `VITE_API_URL` to the FastAPI base URL. Never put Supabase service-role keys or backend secrets in `VITE_*` variables.

## Testing

Backend unit tests cover the core overlap rule, boundary behavior, duration and slot generation. PostgreSQL integration tests cover the double-booking race once `DATABASE_URL` points to a migrated PostgreSQL database.

```bash
cd backend
pytest -q
```

For the race test, run `alembic upgrade head` first.

## Deployment

### Supabase
1. Create a PostgreSQL project.
2. Copy its connection string into Render as `DATABASE_URL`.
3. Run `alembic upgrade head` against the production database before first use.

### Render
Use `render.yaml` or configure:

- Build: `pip install -r backend/requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment: `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`

### GitHub Pages
The existing Pages workflow builds `frontend/` and passes `VITE_API_URL` from the GitHub Actions repository variable of the same name.

## Security rules

- Do not commit `.env` files.
- PostgreSQL credentials remain server-side.
- Frontend may receive only public configuration such as `VITE_API_URL`.
- Owner authentication/authorization is a subsequent milestone before exposing owner-only routes publicly.

## Product roadmap

5. Customer booking flow  
6. Owner authentication + dashboard hardening  
7. Start/DONE live availability  
8. Payments  
9. Customer records  
10. Reports, inventory and expenses  
11. Notification adapters  
12. Full CI, deployment and production verification
