from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.api import auth 
from app.api import clients, reports
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name}")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    description="Generate PDF reports for financial clients",
    version="0.1.0",
    lifespan=lifespan,
)

# Подключаем limiter к приложению.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# Когда лимит превышен — возвращаем 429 Too Many Requests.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clients.router, prefix="/api/v1/clients", tags=["clients"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.app_name}