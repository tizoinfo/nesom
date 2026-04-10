"""Celery periodic tasks for device monitoring."""
import asyncio
import logging
from datetime import datetime

from src.worker.celery_app import celery_app
from src.database.session import AsyncSessionLocal
from . import service as device_service

logger = logging.getLogger(__name__)


@celery_app.task(name="device.check_offline_devices")
def check_offline_devices_task():
    """Periodic task: mark devices as offline if heartbeat > 5 minutes old."""
    async def _run():
        async with AsyncSessionLocal() as db:
            offline_devices = await device_service.check_offline_devices(db)
            if offline_devices:
                logger.info(
                    "Marked %d device(s) as offline: %s",
                    len(offline_devices),
                    [d.device_code for d in offline_devices],
                )
            return len(offline_devices)

    return asyncio.run(_run())
