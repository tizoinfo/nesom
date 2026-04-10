"""Business logic for Spare Part management module."""
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import AppException
from .models import SparePart, SparePartCategory
from .schemas import ALLOWED_STATUS_TRANSITIONS


# ── Code generation ───────────────────────────────────────────────────────────

async def generate_spare_part_code(db: AsyncSession, category_id: str) -> str:
    """Generate a unique spare part code: SP-{category_code}-{sequence}.

    The sequence is a zero-padded 3-digit number derived from the count of
    existing spare parts in the same category + 1.
    """
    category = await get_category(db, category_id)

    # Count existing spare parts in this category to derive next sequence
    count_result = await db.execute(
        select(func.count()).select_from(
            select(SparePart).where(SparePart.category_id == category_id).subquery()
        )
    )
    count = count_result.scalar_one()
    sequence = count + 1

    code = f"SP-{category.category_code}-{sequence:03d}"

    # Ensure uniqueness (handle edge cases from deletions)
    while True:
        existing = await db.execute(
            select(SparePart).where(SparePart.spare_part_code == code)
        )
        if not existing.scalar_one_or_none():
            break
        sequence += 1
        code = f"SP-{category.category_code}-{sequence:03d}"

    return code


# ── Category helpers ──────────────────────────────────────────────────────────

async def get_category(db: AsyncSession, category_id: str) -> SparePartCategory:
    result = await db.execute(
        select(SparePartCategory).where(SparePartCategory.id == category_id)
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise AppException(status_code=404, message="备件分类不存在")
    return cat


async def list_categories(db: AsyncSession) -> List[SparePartCategory]:
    result = await db.execute(
        select(SparePartCategory).order_by(SparePartCategory.sort_order)
    )
    return list(result.scalars().all())


# ── Spare Part CRUD ───────────────────────────────────────────────────────────

async def list_spare_parts(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    category_id: Optional[str] = None,
    status: Optional[str] = None,
    brand: Optional[str] = None,
    keyword: Optional[str] = None,
    low_stock_only: bool = False,
    abc_classification: Optional[str] = None,
) -> Tuple[List[SparePart], int]:
    stmt = select(SparePart)

    if category_id:
        stmt = stmt.where(SparePart.category_id == category_id)
    if status:
        stmt = stmt.where(SparePart.status == status)
    if brand:
        stmt = stmt.where(SparePart.brand == brand)
    if abc_classification:
        stmt = stmt.where(SparePart.abc_classification == abc_classification)
    if keyword:
        stmt = stmt.where(
            or_(
                SparePart.spare_part_name.ilike(f"%{keyword}%"),
                SparePart.specification.ilike(f"%{keyword}%"),
                SparePart.model.ilike(f"%{keyword}%"),
                SparePart.spare_part_code.ilike(f"%{keyword}%"),
            )
        )
    if low_stock_only:
        stmt = stmt.where(
            SparePart.safety_stock_level.isnot(None),
            SparePart.available_stock < SparePart.safety_stock_level,
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = (
        stmt.options(selectinload(SparePart.category))
        .offset(offset)
        .limit(page_size)
        .order_by(SparePart.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_spare_part(db: AsyncSession, spare_part_id: str) -> SparePart:
    result = await db.execute(
        select(SparePart)
        .where(SparePart.id == spare_part_id)
        .options(selectinload(SparePart.category))
    )
    sp = result.scalar_one_or_none()
    if not sp:
        raise AppException(status_code=404, message="备件不存在")
    return sp


async def create_spare_part(
    db: AsyncSession,
    spare_part_name: str,
    category_id: str,
    specification: str,
    **kwargs,
) -> SparePart:
    # Validate category exists
    await get_category(db, category_id)

    # Auto-generate spare part code
    code = await generate_spare_part_code(db, category_id)

    sp = SparePart(
        id=str(uuid.uuid4()),
        spare_part_code=code,
        spare_part_name=spare_part_name,
        category_id=category_id,
        specification=specification,
        **kwargs,
    )
    db.add(sp)
    await db.commit()
    await db.refresh(sp)
    return sp


async def update_spare_part(
    db: AsyncSession,
    spare_part_id: str,
    **kwargs,
) -> SparePart:
    sp = await get_spare_part(db, spare_part_id)

    # Validate status transition if status is being changed
    new_status = kwargs.get("status")
    if new_status and new_status != sp.status:
        allowed = ALLOWED_STATUS_TRANSITIONS.get(sp.status, set())
        if new_status not in allowed:
            raise AppException(
                status_code=422,
                message=f"不允许从 {sp.status} 转换到 {new_status}",
            )

    for key, value in kwargs.items():
        if value is not None:
            setattr(sp, key, value)

    await db.commit()
    await db.refresh(sp)
    return sp


async def delete_spare_part(db: AsyncSession, spare_part_id: str) -> None:
    sp = await get_spare_part(db, spare_part_id)

    # Cannot delete if there is stock
    if sp.current_stock and float(sp.current_stock) > 0:
        raise AppException(status_code=409, message="备件有库存，无法删除")

    await db.delete(sp)
    await db.commit()
