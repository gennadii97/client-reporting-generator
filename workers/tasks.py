from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.core.config import settings
from workers.celery import celery_app


@celery_app.task(bind=True, name="generate_report")
def generate_report_task(
    self,
    report_id: str,
    client_id: str,
    report_type: str,
    period_start: str,
    period_end: str,
):
    try:
        self.update_state(state="STARTED", meta={"progress": 10})

        report_data = {
            "client_id": client_id,
            "report_type": report_type,
            "period_start": period_start,
            "period_end": period_end,
            "report_id": report_id,
            "portfolio_value": 1_250_000.00,
            "return_pct": 12.4,
            "holdings": [
                {"ticker": "SBER", "weight": 0.25, "value": 312_500},
                {"ticker": "LKOH", "weight": 0.20, "value": 250_000},
                {"ticker": "GMKN", "weight": 0.15, "value": 187_500},
            ],
        }

        self.update_state(state="STARTED", meta={"progress": 40})

        templates_dir = Path(__file__).parent.parent / "templates"
        env = Environment(loader=FileSystemLoader(str(templates_dir)))
        template = env.get_template("report.html")
        html_content = template.render(**report_data)

        self.update_state(state="STARTED", meta={"progress": 70})

        output_dir = Path(settings.reports_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{report_id}.pdf"

        HTML(string=html_content).write_pdf(str(output_path))

        self.update_state(state="STARTED", meta={"progress": 100})

        return {"status": "success", "file_path": str(output_path)}

    except Exception as exc:
        raise self.retry(exc=exc, countdown=5, max_retries=3)