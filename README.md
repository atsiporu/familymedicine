# Practice Portal

A LAN-only portal of internal tools for the family medicine practice. It runs on the practice
server beside CureMD (it does not replace it), and its AI tools use local models through Ollama,
so nothing leaves the machine.

> **No real patient data in development.** Use synthetic or masked data only. See `CLAUDE.md`.

## Tools

| Tool | What it does |
|---|---|
| Quick Links | CureMD, payer portals, labs and reference sites, managed in the admin |
| AI Assistant | Chat with a local LLM, with streaming replies, a model picker, and a queue for the single GPU |

## Setup (development)

Requirements: Python 3.14, [uv](https://docs.astral.sh/uv/), PostgreSQL, and Ollama running locally.

```bash
# PostgreSQL (once)
sudo apt install -y postgresql postgresql-16-pgvector
sudo -u postgres createuser -s $USER
createdb portal_dev

# App
cp .env.example .env          # DEBUG=true for development
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py seed_links      # optional starter links
uv run uvicorn portal.asgi:application --reload
```

Open http://localhost:8000, sign in, and assign staff to a role (group) in **Admin → Users**.

## Roles

| Role | Access |
|---|---|
| admin | everything below, plus managing links and viewing the audit log and AI request log |
| provider, front_desk, billing | Quick Links, AI Assistant |

Roles are Django groups, synced on every `migrate`. Syncing only adds permissions, so grants
made in the admin are kept. Give IT administrators `is_staff` so they can reach the admin site.

## Architecture

- **Modular monolith.** Each tool is a Django app in `apps/` that registers itself with
  `apps/core/registry.py`. The dashboard and nav are built from the registry, filtered by permission.
- **Audit log** (`apps/core/audit.py`): sign-ins, sign-outs and failed sign-ins are recorded
  automatically. It is append-only in the admin.
- **AI gateway** (`apps/ai/gateway.py`): the only path to Ollama. It queues GPU work
  (`AI_MAX_CONCURRENT`), enforces `AI_ALLOWED_MODELS`, and logs each request's metadata
  (who, model, tokens, timing). Prompt and response text are **not stored** unless `AI_STORE_CONTENT=true`.
- Sessions expire after `SESSION_IDLE_SECONDS` of inactivity (default 30 minutes).

## Checks

```bash
uv run pytest
uv run mypy .
uv run ruff check . && uv run ruff format --check .
```

## Production notes (to do)

- Run uvicorn with **one worker** (the GPU queue is per process) behind Caddy for HTTPS on the LAN.
- `DEBUG=false`, a real `SECRET_KEY`, `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` set to the LAN hostname.
- `uv run python manage.py collectstatic`.
- Separate production database, nightly encrypted backups off the machine, full-disk encryption.
