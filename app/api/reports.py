from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models import Report
from workers.tasks import generate_report_task

router = APIRouter()


class ReportRequest(BaseModel):
    client_id: str
    report_type: str  # "monthly" | "quarterly" | "annual"
    period_start: str  # "2024-01-01"
    period_end: str    # "2024-03-31"


class ReportResponse(BaseModel):
    report_id: str
    status: str
    message: str


@router.post("/generate", response_model=ReportResponse, status_code=202)
async def generate_report(
    payload: ReportRequest,
    db: AsyncSession = Depends(get_db),
):
    report = Report(
        client_id=payload.client_id,
        report_type=payload.report_type,
        period_start=payload.period_start,
        period_end=payload.period_end,
        status="queued",
    )
    db.add(report)
    await db.flush()
    task = generate_report_task.delay(
        report_id=report.id,
        client_id=payload.client_id,
        report_type=payload.report_type,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )

    report.celery_task_id = task.id

    return ReportResponse(
        report_id=report.id,
        status="queued",
        message="Report generation started. Poll /status for updates.",
    )


@router.get("/{report_id}/status")
async def get_report_status(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report).where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status in ("queued", "started"):
        from celery.result import AsyncResult
        from workers.celery import celery_app

        task_result = AsyncResult(report.celery_task_id, app=celery_app)

        if task_result.status == "SUCCESS":
            report.status = "success"
            report.file_path = task_result.result.get("file_path")
        elif task_result.status == "FAILURE":
            report.status = "failed"

    return {
        "report_id": report.id,
        "status": report.status,
        "file_path": report.file_path,
        "client_id": report.client_id,
        "report_type": report.report_type,
    }


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report).where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status != "success":
        raise HTTPException(
            status_code=400,
            detail=f"Report is not ready yet. Current status: {report.status}"
        )

    file_path = Path(report.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=f"report_{report.client_id}_{report.report_type}.pdf",
    )

@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report).where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    await db.delete(report)