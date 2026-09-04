# Judith's Hair Room — Digital Secretary

A mobile-first salon booking and operations platform for a one-person hairdressing business.

## Stack
- Frontend: React + Vite + TypeScript + Tailwind CSS
- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Database: Supabase PostgreSQL
- Initial deployment: GitHub Pages (frontend) + Render (API)

## Core workflow
1. Customer chooses a style and agrees the final price.
2. The system calculates a 50% Orange Money deposit.
3. Availability is checked against appointments and blocked time in PostgreSQL.
4. Confirmed bookings immediately occupy the slot.
5. Judith can tap **START** when work begins and **DONE** when it finishes.
6. Early completion immediately releases the remaining time.

## Development
See `frontend/README.md` and `backend/README.md` for local setup.
