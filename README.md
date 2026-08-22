# Spectrum Schedule

Self-hosted daily schedule and developmental tracker for a family of an autistic
child. Visual routines with first–then sequencing and transition warnings; IEP goal
trials, preferences, observations, and ABC incidents recorded as an append-only event
log with trend and report projections on top.

- **Spec:** [SPEC.md](SPEC.md) — read before building.
- **Conventions:** [CLAUDE.md](CLAUDE.md)
- **Layout:** `api/` (FastAPI + SQLAlchemy + Alembic, via `uv`) · `web/` (Next.js,
  custom CSS, PWA) · `docs/` · `docker-compose.yml`

## Quick start

```sh
make install   # uv sync + npm install
make dev       # API on :8000, web on :3000
make test
make lint
```

Deployment is Docker Compose (api + web + Caddy) on a home server behind Tailscale or
Cloudflare Tunnel. No third-party auth, analytics, or telemetry — the data never
leaves infrastructure the family controls.
