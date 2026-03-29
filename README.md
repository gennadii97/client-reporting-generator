# Client Reporting Generator

Async PDF report generation service for financial clients.

## Stack

- **FastAPI** — REST API
- **Celery + Redis** — async task queue
- **Jinja2 + WeasyPrint** — HTML to PDF rendering
- **SQLAlchemy + PostgreSQL** — database
- **Docker** — containerisation

## Quick Start
```bash
docker run -d --name redis -p 6379:6379 redis:alpine
uvicorn app.main:app --reload --port 8000
celery -A workers.celery:celery_app worker --loglevel=info
```

Open http://127.0.0.1:8000/docs

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/reports/generate | Queue PDF generation |
| GET | /api/v1/reports/{id}/status | Check task status |
| GET | /health | Health check |

## How it works

1. Client sends POST request with client ID and report period
2. FastAPI returns 202 Accepted + report_id immediately
3. Celery worker picks up the task, renders Jinja2 template, converts to PDF via WeasyPrint
4. Client polls /status endpoint until status is SUCCESS
