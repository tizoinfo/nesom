"""FastAPI router for Report and statistics module."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.shared.schemas import ok
from . import service

router = APIRouter()


# ── Dashboard / Statistics ────────────────────────────────────────────────────

@router.get("/stats/dashboard", summary="获取仪表盘统计数据")
async def get_dashboard(
    station_id: Optional[str] = Query(None, description="场站ID"),
    period: str = Query("month", description="统计周期: today/week/month/quarter/year"),
    db: AsyncSession = Depends(get_db),
):
    data = await service.get_dashboard_data(db, station_id=station_id, period=period)
    return ok(data=data, message="成功")


@router.get("/stats/device", summary="获取设备运行统计")
async def get_device_stats(
    station_id: Optional[str] = Query(None, description="场站ID"),
    db: AsyncSession = Depends(get_db),
):
    data = await service.get_device_stats(db, station_id=station_id)
    return ok(data=data, message="成功")


@router.get("/stats/workorder", summary="获取工单统计")
async def get_workorder_stats(
    station_id: Optional[str] = Query(None, description="场站ID"),
    period: str = Query("month", description="统计周期"),
    db: AsyncSession = Depends(get_db),
):
    data = await service.get_workorder_stats(db, station_id=station_id, period=period)
    return ok(data=data, message="成功")


@router.get("/stats/inspection", summary="获取巡检统计")
async def get_inspection_stats(
    station_id: Optional[str] = Query(None, description="场站ID"),
    period: str = Query("month", description="统计周期"),
    db: AsyncSession = Depends(get_db),
):
    data = await service.get_inspection_stats(db, station_id=station_id, period=period)
    return ok(data=data, message="成功")


from src.shared.schemas import PaginatedData
from .schemas import (
    ReportTemplateCreate,
    ReportTemplateUpdate,
    ReportTemplateRead,
    ReportTemplateDetail,
    ReportQueryRequest,
    ReportQueryResponse,
)


# ── Report Templates ──────────────────────────────────────────────────────────

@router.get("/reports/templates", summary="获取报表模板列表")
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    templates, total = await service.list_templates(
        db, page=page, page_size=page_size, category=category, search=search, is_active=is_active
    )
    items = [ReportTemplateRead.model_validate(t) for t in templates]
    paginated = PaginatedData(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return ok(data=paginated, message="成功")


@router.get("/reports/templates/{template_id}", summary="获取报表模板详情")
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    template = await service.get_template(db, template_id)
    return ok(data=ReportTemplateDetail.model_validate(template), message="成功")


@router.post("/reports/templates", summary="创建报表模板", status_code=201)
async def create_template(body: ReportTemplateCreate, db: AsyncSession = Depends(get_db)):
    template = await service.create_template(
        db,
        template_code=body.template_code,
        template_name=body.template_name,
        category=body.category,
        created_by="system",
        sub_category=body.sub_category,
        description=body.description,
        data_source_type=body.data_source_type,
        data_source_config=body.data_source_config,
        parameter_definitions=body.parameter_definitions,
        column_definitions=body.column_definitions,
        visualization_config=body.visualization_config,
        layout_config=body.layout_config,
        export_config=body.export_config,
        access_level=body.access_level,
    )
    return ok(
        data={"id": template.id, "template_code": template.template_code},
        message="报表模板创建成功",
    )


@router.put("/reports/templates/{template_id}", summary="更新报表模板")
async def update_template(
    template_id: str, body: ReportTemplateUpdate, db: AsyncSession = Depends(get_db)
):
    update_data = body.model_dump(exclude_none=True)
    template = await service.update_template(db, template_id, **update_data)
    return ok(
        data={"id": template.id, "template_code": template.template_code, "version": template.version},
        message="报表模板更新成功",
    )


@router.delete("/reports/templates/{template_id}", summary="删除报表模板", status_code=204)
async def delete_template(template_id: str, db: AsyncSession = Depends(get_db)):
    await service.delete_template(db, template_id)


# ── Report Query ──────────────────────────────────────────────────────────────

@router.post("/reports/query", summary="执行报表查询")
async def execute_report_query(body: ReportQueryRequest, db: AsyncSession = Depends(get_db)):
    result = await service.execute_report_query(
        db,
        template_id=body.template_id,
        parameters=body.parameters,
        page=body.page,
        page_size=body.page_size,
        enable_cache=body.enable_cache,
    )
    return ok(data=result, message="查询成功")


from .schemas import ReportExportRequest, ReportExportResponse


# ── Report Export ─────────────────────────────────────────────────────────────

@router.post("/reports/{template_id}/export", summary="导出报表", status_code=202)
async def export_report(
    template_id: str,
    body: ReportExportRequest,
    db: AsyncSession = Depends(get_db),
):
    execution = await service.create_export_task(
        db,
        template_id=template_id,
        parameters=body.parameters,
        export_format=body.format,
        options=body.options,
    )
    return ok(
        data=ReportExportResponse(
            task_id=execution.id,
            status=execution.status,
            message="报表导出任务已提交",
        ),
        message="报表导出任务已提交",
    )


@router.get("/reports/tasks/{task_id}", summary="查询导出任务状态")
async def get_export_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    execution = await service.get_export_task_status(db, task_id)
    return ok(
        data={
            "task_id": execution.id,
            "execution_id": execution.execution_id,
            "status": execution.status,
            "progress": execution.progress,
            "error_message": execution.error_message,
            "output_files": execution.output_files,
            "start_time": execution.start_time,
            "end_time": execution.end_time,
        },
        message="成功",
    )
