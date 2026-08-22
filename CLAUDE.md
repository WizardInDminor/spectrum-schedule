# CLAUDE.md

Self-hosted schedule + developmental tracker for an autistic child. Read `SPEC.md`
before building anything; do not start a phase without explicit approval.

## Stack (fixed — do not substitute)

- **api/** — Python 3.12, FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2,
  managed with `uv`, tested with pytest.
- **web/** — Next.js App Router, TypeScript, React. **Custom CSS modules only — no
  Tailwind, no UI kits, no CSS-in-JS libraries.** Installable PWA.
- **db** — SQLite now, Postgres-swappable: no SQLite-only types, UUID PKs as
  `String(36)`, timezone-aware UTC datetimes everywhere.
- **auth** — session cookies, email + password, roles `parent` / `caregiver`. No
  third-party auth, no analytics, no telemetry — this is a child's health data on
  family-controlled infrastructure.
- **deploy** — Docker Compose (api + web + caddy). Deployment concerns stay out of
  app code.

## Architecture

Event log first. Things that happen (item completed/skipped, trial, observation,
incident, preference evidence, note) are append-only rows in `events`; fixes are
correction events (`corrects_event_id`), never UPDATE or DELETE. Schedules status,
progress, streaks, confidence, trends, reports are projections over the stream —
pure functions in `api/app/projections/`, no denormalized status columns.

## Commands

```
make dev        # run API (uvicorn :8000) + web (next :3000) together
make test       # api pytest + web typecheck
make lint       # ruff + eslint/tsc
make migrate    # alembic upgrade head
make revision m="msg"   # autogenerate an alembic revision
make install    # uv sync + npm install
```

Per-package: `cd api && uv run pytest -x`, `cd web && npm run dev`.

## Rules

- **Schema changes go through Alembic migrations.** Never edit the DB or a shipped
  migration by hand; new revision every time.
- **Every API endpoint gets a pytest test; every projection gets a unit test** with
  fixture events (projections are pure functions — test them without the DB).
- **No PII anywhere but DB values.** Child/family names never appear in code,
  fixtures, seeds, logs, or commit messages — placeholder names only ("Test Child A").
- **Custom CSS only; mobile viewport first**, desktop second. Every logging flow must
  work one-thumbed on a phone.
- **Stop and ask before adding any dependency** not already in `api/uv.lock` or
  `web/package-lock.json`.
- Events are append-only: no endpoint or migration may UPDATE/DELETE `events` rows.
- All datetimes UTC-aware; schedule dates are `Date` + the child's IANA timezone.
