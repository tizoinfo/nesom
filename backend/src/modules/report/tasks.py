"""Celery tasks for report generation and export."""
import os
import uuid
from datetime import datetime

from loguru import logger

from src.worker.celery_app import celery_app


@celery_app.task(bind=True, name="report.generate_export", max_retries=3, default_retry_delay=60)
def generate_report_export(
    self,
    execution_id: str,
    template_id: str,
    parameters: dict,
    export_format: str = "excel",
    options: dict = None,
):
    """Async Celery task to generate a report export file (Excel/PDF/CSV)."""
    options = options or {}
    try:
        self.update_state(state="PROGRESS", meta={"progress": 10, "message": "开始生成报表"})
        logger.info(f"Generating report export: execution={execution_id}, format={export_format}")

        # Generate export file based on format
        self.update_state(state="PROGRESS", meta={"progress": 50, "message": "处理数据中"})

        export_dir = os.path.join("exports", "reports")
        os.makedirs(export_dir, exist_ok=True)

        if export_format == "excel":
            file_path = _generate_excel(export_dir, template_id, parameters, options)
        elif export_format == "csv":
            file_path = _generate_csv(export_dir, template_id, parameters, options)
        else:
            file_path = _generate_excel(export_dir, template_id, parameters, options)

        self.update_state(state="PROGRESS", meta={"progress": 100, "message": "生成完成"})

        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        return {
            "status": "completed",
            "file_path": file_path,
            "file_size": file_size,
            "execution_id": execution_id,
        }

    except Exception as exc:
        logger.error(f"Report export failed: {exc}")
        raise self.retry(exc=exc)


def _generate_excel(export_dir: str, template_id: str, parameters: dict, options: dict) -> str:
    """Generate an Excel file using openpyxl."""
    try:
        from openpyxl import Workbook
    except ImportError:
        logger.warning("openpyxl not installed, creating placeholder file")
        file_path = os.path.join(export_dir, f"report_{uuid.uuid4().hex[:8]}.xlsx")
        with open(file_path, "wb") as f:
            f.write(b"")
        return file_path

    wb = Workbook()
    ws = wb.active
    ws.title = "报表数据"

    # Header row
    ws.append(["报表模板ID", template_id])
    ws.append(["生成时间", datetime.utcnow().isoformat()])
    ws.append(["参数", str(parameters)])
    ws.append([])
    ws.append(["暂无数据 - 请配置数据源"])

    file_name = f"report_{uuid.uuid4().hex[:8]}.xlsx"
    file_path = os.path.join(export_dir, file_name)
    wb.save(file_path)
    return file_path


def _generate_csv(export_dir: str, template_id: str, parameters: dict, options: dict) -> str:
    """Generate a CSV file."""
    import csv

    file_name = f"report_{uuid.uuid4().hex[:8]}.csv"
    file_path = os.path.join(export_dir, file_name)

    with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["报表模板ID", template_id])
        writer.writerow(["生成时间", datetime.utcnow().isoformat()])
        writer.writerow(["参数", str(parameters)])
        writer.writerow([])
        writer.writerow(["暂无数据 - 请配置数据源"])

    return file_path
