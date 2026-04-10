from celery import Celery
from src.core.config import settings

celery_app = Celery(
    "nesom_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

celery_app.conf.task_routes = {
    "src.worker.tasks.send_notification": {"queue": "email"},
    "src.worker.tasks.process_device_data": {"queue": "device_data"},
    "src.worker.tasks.generate_report": {"queue": "report"},
    "report.generate_export": {"queue": "report"},
    "device.check_offline_devices": {"queue": "device_data"},
    "workorder.check_overdue_work_orders": {"queue": "default"},
}

# Periodic tasks (beat schedule)
celery_app.conf.beat_schedule = {
    "check-offline-devices-every-minute": {
        "task": "device.check_offline_devices",
        "schedule": 60.0,  # every 60 seconds
    },
    "check-overdue-work-orders-every-5-minutes": {
        "task": "workorder.check_overdue_work_orders",
        "schedule": 300.0,  # every 5 minutes
    },
}

# Ensure device tasks are included
celery_app.conf.include = ["src.worker.tasks", "src.modules.device.tasks", "src.modules.workorder.tasks", "src.modules.report.tasks"]
