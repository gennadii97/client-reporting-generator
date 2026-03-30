from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import reports,clients
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.app_name}")
    yield
    print("Shutting down")


app = FastAPI(
    title=settings.app_name,
    description="Generate PDF reports for financial clients",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(clients.router, prefix="/api/v1/clients", tags=["clients"])



@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.app_name}