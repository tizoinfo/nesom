"""FastAPI router for System configuration module."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.shared.schemas import ok, PaginatedData
from . import service
from .schemas import (
    SysConfigCreate,
    SysConfigRead,
    SysConfigUpdate,
    BatchConfigUpdate,
    SysDictCreate,
    SysDictRead,
    SysDictUpdate,
    NoticeTemplateCreate,
    NoticeTemplateRead,
    NoticeTemplateUpdate,
    TemplateTestRequest,
)

router = APIRouter()


# ── System Config ─────────────────────────────────────────────────────────────

@router.get("/configs", summary="获取系统参数列表")
async def list_configs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    module: Optional[str] = Query(None),
    config_key: Optional[str] = Query(None, alias="configKey"),
    is_system: Optional[int] = Query(None, alias="isSystem"),
    db: AsyncSession = Depends(get_db),
):
    configs, total = await service.list_configs(
        db, page=page, page_size=size, module=module,
        config_key=config_key, is_system=is_system,
    )
    items = [SysConfigRead.model_validate(c) for c in configs]
    paginated = PaginatedData(
        items=items, total=total, page=page,
        page_size=size, total_pages=(total + size - 1) // size,
    )
    return ok(data=paginated, message="成功")


@router.post("/configs", summary="创建系统参数", status_code=201)
async def create_config(body: SysConfigCreate, db: AsyncSession = Depends(get_db)):
    cfg = await service.create_config(
        db,
        config_key=body.config_key,
        config_value=body.config_value,
        config_type=body.config_type,
        module=body.module,
        description=body.description,
        is_sensitive=body.is_sensitive,
        is_system=body.is_system,
    )
    return ok(
        data={"id": cfg.id, "config_key": cfg.config_key},
        message="配置创建成功",
    )


@router.put("/configs/batch", summary="批量更新系统参数")
async def batch_update_configs(
    body: BatchConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    updated = await service.batch_update_configs(db, body.configs)
    return ok(
        data={"updated_count": len(updated)},
        message="批量更新成功",
    )


@router.post("/configs/cache/refresh", summary="刷新配置缓存")
async def refresh_cache(db: AsyncSession = Depends(get_db)):
    count = await service.refresh_config_cache(db)
    return ok(data={"refreshed_count": count}, message="缓存刷新成功")


@router.get("/configs/{config_key}", summary="获取单个系统参数")
async def get_config(config_key: str, db: AsyncSession = Depends(get_db)):
    cfg = await service.get_config(db, config_key)
    return ok(data=SysConfigRead.model_validate(cfg), message="成功")


@router.put("/configs/{config_key}", summary="更新系统参数")
async def update_config(
    config_key: str,
    body: SysConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = body.model_dump(exclude_none=True)
    cfg = await service.update_config(db, config_key, **update_data)
    return ok(data=SysConfigRead.model_validate(cfg), message="配置更新成功")


@router.delete("/configs/{config_key}", summary="删除系统参数")
async def delete_config(config_key: str, db: AsyncSession = Depends(get_db)):
    await service.delete_config(db, config_key)
    return ok(message="配置删除成功")



# ── Dictionary Data ───────────────────────────────────────────────────────────

@router.get("/dict/types", summary="获取字典类型列表")
async def list_dict_types(db: AsyncSession = Depends(get_db)):
    types = await service.list_dict_types(db)
    return ok(data={"types": types}, message="成功")


@router.get("/dict/data", summary="获取字典数据列表")
async def list_dict_data(
    dict_type: str = Query(..., alias="dictType"),
    status: Optional[int] = Query(1),
    db: AsyncSession = Depends(get_db),
):
    items = await service.list_dict_data(db, dict_type=dict_type, status=status)
    return ok(data=[SysDictRead.model_validate(i) for i in items], message="成功")


@router.post("/dict/data", summary="创建字典数据", status_code=201)
async def create_dict_data(body: SysDictCreate, db: AsyncSession = Depends(get_db)):
    item = await service.create_dict_item(
        db,
        dict_type=body.dict_type,
        dict_code=body.dict_code,
        dict_name=body.dict_name,
        dict_value=body.dict_value,
        sort_order=body.sort_order,
        parent_id=body.parent_id,
        status=body.status,
        remark=body.remark,
    )
    return ok(data={"id": item.id}, message="字典数据创建成功")


@router.put("/dict/data/{dict_id}", summary="更新字典数据")
async def update_dict_data(
    dict_id: int,
    body: SysDictUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = body.model_dump(exclude_none=True)
    item = await service.update_dict_item(db, dict_id, **update_data)
    return ok(data=SysDictRead.model_validate(item), message="字典数据更新成功")


@router.delete("/dict/data/{dict_id}", summary="删除字典数据")
async def delete_dict_data(dict_id: int, db: AsyncSession = Depends(get_db)):
    await service.delete_dict_item(db, dict_id)
    return ok(message="字典数据删除成功")



# ── Notice Templates ──────────────────────────────────────────────────────────

@router.get("/notice/templates", summary="获取通知模板列表")
async def list_notice_templates(
    notice_type: Optional[str] = Query(None, alias="noticeType"),
    status: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    templates = await service.list_notice_templates(
        db, notice_type=notice_type, status=status,
    )
    return ok(data=[NoticeTemplateRead.model_validate(t) for t in templates], message="成功")


@router.get("/notice/templates/{template_code}", summary="获取通知模板详情")
async def get_notice_template(
    template_code: str, db: AsyncSession = Depends(get_db),
):
    tpl = await service.get_notice_template(db, template_code)
    return ok(data=NoticeTemplateRead.model_validate(tpl), message="成功")


@router.post("/notice/templates", summary="创建通知模板", status_code=201)
async def create_notice_template(
    body: NoticeTemplateCreate, db: AsyncSession = Depends(get_db),
):
    tpl = await service.create_notice_template(
        db,
        template_code=body.template_code,
        template_name=body.template_name,
        notice_type=body.notice_type,
        title_template=body.title_template,
        content_template=body.content_template,
        variables=body.variables,
        is_html=body.is_html,
        status=body.status,
    )
    return ok(data={"id": tpl.id, "template_code": tpl.template_code}, message="模板创建成功")


@router.put("/notice/templates/{template_code}", summary="更新通知模板")
async def update_notice_template(
    template_code: str,
    body: NoticeTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    update_data = body.model_dump(exclude_none=True)
    tpl = await service.update_notice_template(db, template_code, **update_data)
    return ok(data=NoticeTemplateRead.model_validate(tpl), message="模板更新成功")


@router.delete("/notice/templates/{template_code}", summary="删除通知模板")
async def delete_notice_template(
    template_code: str, db: AsyncSession = Depends(get_db),
):
    await service.delete_notice_template(db, template_code)
    return ok(message="模板删除成功")


@router.post("/notice/templates/{template_code}/test", summary="发送测试通知")
async def test_notice_template(
    template_code: str,
    body: TemplateTestRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await service.test_notice_template(
        db, template_code, body.recipient, body.variables,
    )
    return ok(data=result, message="测试通知预览成功")



# ── Health Check ──────────────────────────────────────────────────────────────

@router.get("/system/health", summary="获取系统健康状态")
async def system_health(db: AsyncSession = Depends(get_db)):
    result = await service.check_system_health(db)
    return ok(data=result, message="成功")
