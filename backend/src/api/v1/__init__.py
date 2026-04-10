from fastapi import APIRouter

from src.modules.auth.router import router as auth_router
from src.modules.auth.auth_router import router as auth_login_router
from src.modules.auth.user_router import router as user_router
from src.modules.auth.audit_router import router as audit_router
from src.modules.device.router import router as device_router
from src.modules.workorder.router import router as workorder_router
from src.modules.sparepart.router import router as sparepart_router
from src.modules.sparepart.inventory_router import router as inventory_router
from src.modules.inspection.router import router as inspection_router
from src.modules.inspection.mobile_router import router as inspection_mobile_router
from src.modules.report.router import router as report_router
from src.modules.system.router import router as system_router
from src.modules.integration.router import router as integration_router

api_router = APIRouter()

api_router.include_router(auth_login_router, tags=["认证管理"])
api_router.include_router(user_router, tags=["用户管理"])
api_router.include_router(auth_router, tags=["用户权限管理"])
api_router.include_router(audit_router, tags=["审计日志"])
api_router.include_router(device_router, tags=["设备监控"])
api_router.include_router(workorder_router, tags=["工单管理"])
api_router.include_router(sparepart_router, tags=["备件管理"])
api_router.include_router(inventory_router, tags=["库存管理"])
api_router.include_router(inspection_router, tags=["巡检管理"])
api_router.include_router(inspection_mobile_router, tags=["移动端巡检"])
api_router.include_router(report_router, tags=["报表统计"])
api_router.include_router(system_router, tags=["系统配置"])
api_router.include_router(integration_router, tags=["系统集成"])
