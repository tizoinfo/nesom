from loguru import logger
from .celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def send_notification(self, to: str, subject: str, content: str):
    try:
        logger.info(f"Sending notification to {to}: {subject}")
        return {"status": "success", "to": to}
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def process_device_data(self, device_id: str, data: dict):
    try:
        logger.info(f"Processing data for device {device_id}")
        return {"status": "success", "device_id": device_id}
    except Exception as e:
        logger.error(f"Failed to process device data: {e}")
        raise self.retry(exc=e, countdown=30)


@celery_app.task(bind=True)
def generate_report(self, report_id: str, params: dict):
    try:
        logger.info(f"Generating report {report_id}")
        return {"status": "success", "report_id": report_id}
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise self.retry(exc=e, countdown=60)
