"""FastAPI router for Spare Part management module."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.shared.schemas import ok, PaginatedData
from . import service
from .schemas import (
    SparePartCategoryRead,
    SparePartCreate,
    SparePartDetail,
    SparePartRead,
    SparePartUpdate,
)

router = APIRouter()


# ── Categories ────────────────────────────────────────────────────────────────

@router.get("/spare-part-categories", summary="获取备件分类列表")
async def list_categories(db: AsyncSession = Depends(get_db)):
    categories = await service.list_categories(db)
    return ok(
        data=[SparePartCategoryRead.model_validate(c) for c in categories],
        message="成功",
    )


# ── Spare Parts ───────────────────────────────────────────────────────────────

@router.get("/spare-parts", summary="获取备件列表")
async def list_spare_parts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    low_stock_only: bool = Query(False),
    abc_classification: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    parts, total = await service.list_spare_parts(
        db,
        page=page,
        page_size=page_size,
        category_id=category_id,
        status=status,
        brand=brand,
        keyword=keyword,
        low_stock_only=low_stock_only,
        abc_classification=abc_classification,
    )
    items = [SparePartRead.model_validate(p) for p in parts]
    paginated = PaginatedData(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return ok(data=paginated, message="成功")


@router.get("/spare-parts/{spare_part_id}", summary="获取备件详情")
async def get_spare_part(spare_part_id: str, db: AsyncSession = Depends(get_db)):
    sp = await service.get_spare_part(db, spare_part_id)
    return ok(data=SparePartDetail.model_validate(sp), message="成功")


@router.post("/spare-parts", summary="创建备件", status_code=201)
async def create_spare_part(body: SparePartCreate, db: AsyncSession = Depends(get_db)):
    sp = await service.create_spare_part(
        db,
        spare_part_name=body.spare_part_name,
        category_id=body.category_id,
        specification=body.specification,
        model=body.model,
        brand=body.brand,
        unit=body.unit,
        unit_weight=body.unit_weight,
        unit_volume=body.unit_volume,
        attributes=body.attributes,
        description=body.description,
        technical_parameters=body.technical_parameters,
        applicable_devices=body.applicable_devices,
        is_consumable=body.is_consumable,
        is_controlled=body.is_controlled,
        has_serial_number=body.has_serial_number,
        shelf_life_months=body.shelf_life_months,
        procurement_lead_time=body.procurement_lead_time,
        min_order_quantity=body.min_order_quantity,
        economic_order_quantity=body.economic_order_quantity,
        standard_cost=body.standard_cost,
        min_stock_level=body.min_stock_level,
        max_stock_level=body.max_stock_level,
        safety_stock_level=body.safety_stock_level,
        abc_classification=body.abc_classification,
    )
    return ok(
        data={
            "id": sp.id,
            "spare_part_code": sp.spare_part_code,
            "created_at": sp.created_at.isoformat() if sp.created_at else None,
        },
        message="备件创建成功",
    )


@router.patch("/spare-parts/{spare_part_id}", summary="更新备件")
async def update_spare_part(
    spare_part_id: str,
    body: SparePartUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = body.model_dump(exclude_none=True)
    sp = await service.update_spare_part(db, spare_part_id, **update_data)
    return ok(
        data={
            "id": sp.id,
            "updated_at": sp.updated_at.isoformat() if sp.updated_at else None,
        },
        message="备件更新成功",
    )


@router.delete("/spare-parts/{spare_part_id}", summary="删除备件")
async def delete_spare_part(spare_part_id: str, db: AsyncSession = Depends(get_db)):
    await service.delete_spare_part(db, spare_part_id)
    return ok(message="备件删除成功")
