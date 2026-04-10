"""FastAPI router for user management (section 3.2).

Endpoints:
  GET    /users           - List users
  POST   /users           - Create user
  GET    /users/{user_id} - Get user
  PUT    /users/{user_id} - Update user
  DELETE /users/{user_id} - Delete user (soft)
  POST   /users/change-password        - Change own password
  POST   /users/{user_id}/reset-password - Admin reset password
  POST   /users/{user_id}/lock          - Lock user
  POST   /users/{user_id}/unlock        - Unlock user
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.shared.schemas import ok, PaginatedData
from .audit import enqueue_audit_log
from . import user_service
from .schemas import (
    ChangePasswordRequest,
    LockUserRequest,
    ResetPasswordRequest,
    UserCreate,
    UserRead,
    UserUpdate,
)

router = APIRouter(prefix="/users")


def _user_to_read(user) -> UserRead:
    return UserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        real_name=user.real_name,
        status=user.status,
        is_superadmin=user.is_superadmin,
        failed_login_attempts=user.failed_login_attempts,
        lockout_until=user.lockout_until,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=[r.role_code for r in user.roles],
    )


@router.get("", summary="获取用户列表")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="搜索用户名/姓名/邮箱"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    db: AsyncSession = Depends(get_db),
):
    users, total = await user_service.list_users(
        db, page=page, page_size=page_size, search=search, status=status
    )
    items = [_user_to_read(u) for u in users]
    paginated = PaginatedData(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    return ok(data=paginated, message="成功")


@router.post("", summary="创建用户", status_code=201)
async def create_user(
    request: Request,
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.create_user(
        db,
        username=body.username,
        email=body.email,
        real_name=body.real_name,
        password=body.password,
        role_ids=body.role_ids,
    )
    enqueue_audit_log(
        user_id=None,
        username="admin",
        action="create",
        resource_type="user",
        resource_id=str(user.id),
        new_value={"username": user.username, "email": user.email},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ok(data={"id": user.id, "username": user.username}, message="用户创建成功")


@router.get("/{user_id}", summary="获取用户详情")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.get_user(db, user_id)
    return ok(data=_user_to_read(user), message="成功")


@router.put("/{user_id}", summary="更新用户")
async def update_user(
    user_id: int,
    request: Request,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.update_user(
        db,
        user_id=user_id,
        real_name=body.real_name,
        email=body.email,
        status=body.status,
        role_ids=body.role_ids,
    )
    enqueue_audit_log(
        user_id=None,
        username="admin",
        action="update",
        resource_type="user",
        resource_id=str(user.id),
        new_value=body.model_dump(exclude_none=True),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ok(data=_user_to_read(user), message="用户更新成功")


@router.delete("/{user_id}", summary="删除用户", status_code=204)
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # TODO: extract current_user_id from JWT in production
    await user_service.delete_user(db, user_id, current_user_id=0)
    enqueue_audit_log(
        user_id=None,
        username="admin",
        action="delete",
        resource_type="user",
        resource_id=str(user_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/change-password", summary="修改密码")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    # TODO: extract user_id from JWT in production
    user_id = 0
    await user_service.change_password(db, user_id, body.current_password, body.new_password)
    enqueue_audit_log(
        user_id=user_id,
        username="self",
        action="change_password",
        resource_type="user",
        resource_id=str(user_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ok(message="密码修改成功")


@router.post("/{user_id}/reset-password", summary="重置用户密码")
async def reset_password(
    user_id: int,
    request: Request,
    body: ResetPasswordRequest = ResetPasswordRequest(),
    db: AsyncSession = Depends(get_db),
):
    new_pw = await user_service.reset_password(db, user_id, body.new_password)
    enqueue_audit_log(
        user_id=None,
        username="admin",
        action="reset_password",
        resource_type="user",
        resource_id=str(user_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ok(message="密码重置成功")


@router.post("/{user_id}/lock", summary="锁定用户")
async def lock_user(
    user_id: int,
    request: Request,
    body: LockUserRequest = LockUserRequest(),
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.lock_user(db, user_id, body.duration_minutes)
    enqueue_audit_log(
        user_id=None,
        username="admin",
        action="lock",
        resource_type="user",
        resource_id=str(user_id),
        new_value={"reason": body.reason, "duration_minutes": body.duration_minutes},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ok(data={"lockout_until": str(user.lockout_until)}, message="用户已锁定")


@router.post("/{user_id}/unlock", summary="解锁用户")
async def unlock_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await user_service.unlock_user(db, user_id)
    enqueue_audit_log(
        user_id=None,
        username="admin",
        action="unlock",
        resource_type="user",
        resource_id=str(user_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ok(message="用户已解锁")
