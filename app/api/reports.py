from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from workers.tasks import generate_report_task

router = APIRouter()


class ReportRequest(BaseModel):
    client_id: UUID
    report_type: str  # "monthly" | "quarterly" | "annual"
    period_start: str  # "2024-01-01"
    period_end: str    # "2024-03-31"


class ReportResponse(BaseModel):
    report_id: UUID
    status: str
    message: str


@router.post("/generate", response_model=ReportResponse, status_code=202)
async def generate_report(
    payload: ReportRequest,
    db: AsyncSession = Depends(get_db),
):
    report_id = uuid4()

    generate_report_task.delay(
        report_id=str(report_id),
        client_id=str(payload.client_id),
        report_type=payload.report_type,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )

    return ReportResponse(
        report_id=report_id,
        status="queued",
        message="Report generation started. Poll /status for updates.",
    )


@router.get("/{report_id}/status")
async def get_report_status(report_id: UUID):
    from celery.result import AsyncResult
    from workers.celery import celery_app

    result = AsyncResult(str(report_id), app=celery_app)

    return {
        "report_id": report_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }