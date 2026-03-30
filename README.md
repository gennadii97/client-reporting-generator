# Client Reporting Generator

Async PDF report generation service for financial clients.
Built to demonstrate production-grade Python backend skills.

## Stack

- **FastAPI** — REST API with automatic Swagger docs
- **Celery + Redis** — async task queue, non-blocking PDF generation
- **SQLAlchemy 2.0 + PostgreSQL** — async ORM with Alembic migrations
- **Jinja2 + WeasyPrint** — HTML template to PDF rendering
- **Docker Compose** — full local environment in one command
- **pytest** — async tests with in-memory SQLite

## Performance

Benchmark across 10 runs (`scripts/benchmark.py`):

| Approach | Median time |
|----------|-------------|
| Legacy synchronous | 0.63s |
| Optimized (Celery worker) | 0.08s |
| **Improvement** | **-87%** |

## Quick Start
```bash
git clone https://github.com/genn/client-reporting-generator
cd client-reporting-generator
cp .env.example .env
cd docker && docker compose up --build
```

Open http://127.0.0.1:8000/docs

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/clients/ | Create client |
| GET | /api/v1/clients/ | List clients |
| GET | /api/v1/clients/{id} | Get client |
| POST | /api/v1/reports/generate | Queue PDF generation |
| GET | /api/v1/reports/{id}/status | Check task status |
| GET | /api/v1/reports/{id}/download | Download PDF |
| GET | /health | Health check |

## How it works

1. `POST /reports/generate` — FastAPI validates input via Pydantic, saves Report to DB with status `queued`, sends task to Celery via Redis, returns `202 Accepted` immediately
2. Celery worker picks up the task, renders Jinja2 template, converts to PDF via WeasyPrint, updates file path in DB
3. `GET /reports/{id}/status` — client polls until status is `success`
4. `GET /reports/{id}/download` — client downloads the PDF file

## Project Structure
```
app/
  api/          # FastAPI routers
  core/         # config, database
  models.py     # SQLAlchemy models
workers/
  celery.py     # Celery app
  tasks.py      # PDF generation task
templates/      # Jinja2 HTML templates
docker/         # Dockerfile, compose.yml
migrations/     # Alembic migrations
scripts/        # benchmark.py
tests/          # pytest
```

## Running Tests
```bash
pip install aiosqlite
pytest tests/ -v
```

## Key Design Decisions

**Celery over FastAPI BackgroundTasks** — tasks survive server restarts, support retries (`max_retries=3`), and can be monitored. BackgroundTasks would lose tasks on crash.

**202 Accepted pattern** — report generation is async. Client gets `report_id` immediately and polls `/status`. Correct HTTP semantics for long-running operations.

**Alembic migrations** — schema changes are versioned and reversible. `alembic upgrade head` runs automatically on container start.
