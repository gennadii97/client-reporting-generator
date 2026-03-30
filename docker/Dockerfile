FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir fastapi uvicorn[standard] pydantic pydantic-settings \
    sqlalchemy alembic asyncpg celery redis jinja2 weasyprint \
    python-multipart greenlet psycopg2-binary pytest pytest-asyncio httpx ruff mypy

COPY . .

RUN mkdir -p /tmp/reports