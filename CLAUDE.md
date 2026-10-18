# Family Medicine Practice Portal

A LAN-only web portal of internal tools for a family medicine practice. It runs on the practice's
own machine, beside the CureMD EMR (it does not replace it). Some tools use local LLMs served by Ollama.

## HARD RULE: no patient data, ever

- **Never read, open, query, print, copy or commit real patient data (PHI)**: not from the
  production database, CureMD exports, logs, uploads, backups, screenshots or any other file.
- Work only with **synthetic or masked/anonymized data**. Seed data, fixtures and test data
  must be obviously fake (e.g. `Test Patient`, `555-01xx` phone numbers, `example.com` emails).
- Never connect to the production database. Development uses its own database (`portal_dev`).
- If a file or command output looks like it might contain real patient data, stop, don't read
  further, and ask the user.
- Code must not log prompt/response text or patient identifiers to application logs.
  The AI gateway stores request metadata only unless `AI_STORE_CONTENT` is explicitly enabled.

## Stack

- Python 3.14, managed with `uv`
- Django (ASGI, served by uvicorn), with Django templates and a little vanilla JS (HTMX when needed)
- PostgreSQL (+ pgvector later)
- Ollama running natively on localhost:11434 (do not containerize it, since it needs the AMD GPU)
- Type checking: mypy strict + django-stubs. Lint/format: ruff. Tests: pytest + pytest-django.

## Layout

Modular monolith. Each tool is a Django app under `apps/` and registers itself with the tool
registry (`apps/core/registry.py`) in its `AppConfig.ready()`. The dashboard builds its menu
from those registrations, filtered by the user's permissions.

- `portal/`: settings, urls, asgi
- `apps/core/`: custom User, roles (Django groups), audit log, dashboard, tool registry
- `apps/ai/`: Ollama gateway (single-GPU queue, request audit, model listing, streaming)
- `apps/links/`: quick links / CureMD launcher
- `apps/chat/`: AI chat tool

## Commands

```bash
uv sync                                  # install deps
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run uvicorn portal.asgi:application --reload   # dev server on :8000
uv run pytest
uv run mypy .
uv run ruff check . && uv run ruff format .
```

## Conventions

- Fully annotated code; mypy strict must pass.
- Pydantic models at external boundaries (Ollama responses, future CureMD imports).
- Record security-relevant actions with `apps.core.audit.record(...)`.
- No external CDNs or telemetry: vendor static assets into the repo.
