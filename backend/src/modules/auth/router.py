"""FastAPI router for Role and Permission management (section 3.3 & 3.4)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.shared.schemas import ok, PaginatedData
from . import service
from .audit import enqueue_audit_log
from .schemas import (
    PermissionRead,
    RoleCreate,
    RoleDetail,
    RolePermissionsUpdate,
    RoleRead,
    RoleUpdate,
)

router = APIRouter()


# ── Permissions ───────────────────────────────────────────────────────────────

@router.get("/permissions", summary="获取权限列表")
async def list_permissions(
    module: Optional[str] = Query(None, description="按模块过滤"),
    resource: Optional[str] = Query(None, description="按资源过滤"),
    action: Optional[str] = Query(None, description="按操作过滤"),
    db: AsyncSession = Depends(get_db),
):
    perms = await service.list_permissions(db, module=module, resource=resource, action=action)
    data = [PermissionRead.model_validate(p) for p in perms]
    return ok(data=data, message="成功")


# ── Roles ─────────────────────────────────────────────────────────────────────

@router.get("/roles", summary="获取角色列表")
async def list_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    roles, total = await service.list_roles(db, page=page, page_size=page_size)
    items = [
        RoleRead(
            **{k: v for k, v in role.__dict__.items() if not k.startswith("_")},
            user_count=len(role.users),
        )
        for role in roles
    ]
    paginated = PaginatedData(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return ok(data=paginated, message="成功")


@router.get("/roles/{role_id}", summary="获取角色详情")
async def get_role(
    role_id: int,
    expand: Optional[str] = Query(None, description="传入 'permissions' 展开权限"),
    db: AsyncSession = Depends(get_db),
):
    with_perms = expand == "permissions" if expand else True
    role = await service.get_role(db, role_id, with_permissions=with_perms)
    data = RoleDetail(
        **{k: v for k, v in role.__dict__.items() if not k.startswith("_")},
        user_count=len(role.users),
        permissions=[PermissionRead.model_validate(p) for p in role.permissions],
    )
    return ok(data=data, message="成功")


@router.post("/roles", summary="创建角色", status_code=201)
async def create_role(
    request: Request,
    body: RoleCreate,
    db: AsyncSession = Depends(get_db),
):
    role = await service.create_role(
        db,
        role_code=body.role_code,
        role_name=body.role_name,
        description=body.description,
        role_type=body.role_type,
        is_default=body.is_default,
        data_scope=body.data_scope,
        permission_ids=body.permission_ids,
    )
    enqueue_audit_log(
        user_id=None,
        username="system",
        action="create",
        resource_type="role",
        resource_id=str(role.id),
        new_value={"role_code": role.role_code, "role_name": role.role_name},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ok(data={"id": role.id, "role_code": role.role_code}, message="角色创建成功")


@router.put("/roles/{role_id}", summary="更新角色")
async def update_role(
    role_id: int,
    request: Request,
    body: RoleUpdate,
    db: AsyncSession = Depends(get_db),
):
    role = await service.update_role(
        db,
        role_id=role_id,
        role_name=body.role_name,
        description=body.description,
        is_default=body.is_default,
        data_scope=body.data_scope,
    )
    enqueue_audit_log(
        user_id=None,
        username="system",
        action="update",
        resource_type="role",
        resource_id=str(role.id),
        new_value=body.model_dump(exclude_none=True),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ok(data={"id": role.id, "role_code": role.role_code}, message="角色更新成功")


@router.delete("/roles/{role_id}", summary="删除角色", status_code=204)
async def delete_role(
    role_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await service.delete_role(db, role_id)
    enqueue_audit_log(
        user_id=None,
        username="system",
        action="delete",
        resource_type="role",
        resource_id=str(role_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.put("/roles/{role_id}/permissions", summary="更新角色权限")
async def update_role_permissions(
    role_id: int,
    request: Request,
    body: RolePermissionsUpdate,
    db: AsyncSession = Depends(get_db),
):
    role = await service.update_role_permissions(
        db,
        role_id=role_id,
        permission_ids=body.permission_ids,
        append=body.append,
    )
    perm_codes = [p.perm_code for p in role.permissions]
    enqueue_audit_log(
        user_id=None,
        username="system",
        action="update_permissions",
        resource_type="role",
        resource_id=str(role_id),
        new_value={"permission_ids": body.permission_ids, "append": body.append},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ok(data={"role_id": role_id, "permissions": perm_codes}, message="角色权限更新成功")
