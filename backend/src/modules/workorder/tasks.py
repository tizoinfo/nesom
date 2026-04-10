"""Celery periodic tasks for work order management."""
import asyncio
import logging

from src.worker.celery_app import celery_app
from src.database.session import AsyncSessionLocal
from . import service as wo_service

logger = logging.getLogger(__name__)


@celery_app.task(name="workorder.check_overdue_work_orders")
def check_overdue_work_orders_task():
    """Periodic task: check for overdue work orders and escalate priority."""
    async def _run():
        async with AsyncSessionLocal() as db:
            escalated = await wo_service.check_overdue_work_orders(db)
            if escalated:
                logger.info(
                    "Escalated %d overdue work order(s): %s",
                    len(escalated),
                    [wo.work_order_no for wo in escalated],
                )
            return len(escalated)

    return asyncio.run(_run())
