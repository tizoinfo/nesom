"""Inventory alert service – low stock and near-expiry warnings."""
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SparePart
from .inventory_models import InventorySnapshot


# ── Alert data structures ─────────────────────────────────────────────────────

def _low_stock_alert(sp: SparePart) -> dict:
    """Build a low-stock alert dict for a spare part."""
    current = float(sp.available_stock)
    safety = float(sp.safety_stock_level) if sp.safety_stock_level else 0
    min_level = float(sp.min_stock_level) if sp.min_stock_level else 0

    severity = "warning"
    threshold = safety
    if min_level and current < min_level:
        severity = "error"
        threshold = min_level

    suggested_qty = max(safety * 2 - current, 0)
    return {
        "alert_type": "low_stock",
        "severity": severity,
        "spare_part_id": sp.id,
        "spare_part_code": sp.spare_part_code,
        "spare_part_name": sp.spare_part_name,
        "current_stock": current,
        "threshold": threshold,
        "difference": current - threshold,
        "alert_message": f"可用库存({current})低于安全库存({threshold})",
        "suggested_action": f"建议采购 {suggested_qty:.0f} 件" if suggested_qty > 0 else "关注库存变化",
        "alert_time": datetime.utcnow().isoformat(),
    }


def _near_expiry_alert(snap: InventorySnapshot, spare_part_name: str, spare_part_code: str) -> dict:
    """Build a near-expiry alert dict for an inventory snapshot."""
    days_remaining = (snap.expiry_date - date.today()).days
    qty = float(snap.quantity)
    value = qty * float(snap.unit_price)

    if days_remaining <= 30:
        severity = "critical"
        action = "立即使用或退货"
    elif days_remaining <= 90:
        severity = "warning"
        action = "优先使用"
    else:
        severity = "info"
        action = "计划使用"

    return {
        "alert_type": "near_expiry",
        "severity": severity,
        "spare_part_id": snap.spare_part_id,
        "spare_part_code": spare_part_code,
        "spare_part_name": spare_part_name,
        "batch_no": snap.batch_no,
        "expiry_date": snap.expiry_date.isoformat() if snap.expiry_date else None,
        "days_remaining": days_remaining,
        "quantity": qty,
        "total_value": value,
        "alert_message": f"批次 {snap.batch_no or 'N/A'} 将在 {days_remaining} 天后过期",
        "suggested_action": action,
        "alert_time": datetime.utcnow().isoformat(),
    }


# ── Query functions ───────────────────────────────────────────────────────────

async def get_low_stock_alerts(db: AsyncSession) -> List[dict]:
    """Return spare parts whose available_stock < safety_stock_level."""
    stmt = select(SparePart).where(
        SparePart.safety_stock_level.isnot(None),
        SparePart.available_stock < SparePart.safety_stock_level,
        SparePart.status == "active",
    )
    result = await db.execute(stmt)
    parts = result.scalars().all()
    return [_low_stock_alert(sp) for sp in parts]


async def get_near_expiry_alerts(
    db: AsyncSession,
    threshold_days: int = 180,
) -> List[dict]:
    """Return inventory snapshots expiring within *threshold_days*."""
    cutoff = date.today() + timedelta(days=threshold_days)
    stmt = select(InventorySnapshot).where(
        InventorySnapshot.expiry_date.isnot(None),
        InventorySnapshot.expiry_date <= cutoff,
        InventorySnapshot.quantity > 0,
    ).order_by(InventorySnapshot.expiry_date.asc())

    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    alerts: List[dict] = []
    # We need spare part names – batch-fetch them
    sp_ids = {s.spare_part_id for s in snapshots}
    sp_map: dict = {}
    if sp_ids:
        sp_result = await db.execute(select(SparePart).where(SparePart.id.in_(sp_ids)))
        for sp in sp_result.scalars().all():
            sp_map[sp.id] = sp

    for snap in snapshots:
        sp = sp_map.get(snap.spare_part_id)
        name = sp.spare_part_name if sp else "未知"
        code = sp.spare_part_code if sp else "未知"
        alerts.append(_near_expiry_alert(snap, name, code))

    return alerts


async def get_all_alerts(
    db: AsyncSession,
    alert_type: Optional[str] = None,
    severity: Optional[str] = None,
) -> List[dict]:
    """Aggregate low-stock and near-expiry alerts with optional filters."""
    alerts: List[dict] = []

    if alert_type is None or alert_type == "low_stock":
        alerts.extend(await get_low_stock_alerts(db))

    if alert_type is None or alert_type == "near_expiry":
        alerts.extend(await get_near_expiry_alerts(db))

    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]

    return alerts
