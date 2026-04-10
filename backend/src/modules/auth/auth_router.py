"""FastAPI router for authentication endpoints (section 3.1).

Endpoints:
  POST /auth/login    - User login
  POST /auth/refresh  - Refresh access token
  POST /auth/logout   - Logout (revoke tokens)
"""
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.core.security import decode_token
from src.database.session import get_db
from src.shared.schemas import ok
from .audit import enqueue_audit_log
from . import auth_service
from .schemas import LoginRequest, LogoutRequest, RefreshRequest

router = APIRouter(prefix="/auth")


@router.post("/login", summary="用户登录")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await auth_service.login(db, body.username, body.password)
    enqueue_audit_log(
        user_id=result["user"]["id"],
        username=result["user"]["username"],
        action="login",
        resource_type="session",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ok(data=result, message="登录成功")


@router.post("/refresh", summary="刷新访问令牌")
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await auth_service.refresh_tokens(db, body.refresh_token)
    return ok(data=result, message="令牌刷新成功")


@router.post("/logout", summary="用户登出")
async def logout(
    request: Request,
    body: LogoutRequest = LogoutRequest(),
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    # Extract token from "Bearer <token>"
    if not authorization.startswith("Bearer "):
        raise AppException(status_code=401, message="无效的认证头")
    access_token = authorization[7:]

    payload = decode_token(access_token)
    user_id = int(payload.get("sub", 0))
    if not user_id:
        raise AppException(status_code=401, message="无效的令牌")

    await auth_service.logout(db, access_token, user_id, body.revoke_all)

    enqueue_audit_log(
        user_id=user_id,
        username=payload.get("username", ""),
        action="logout",
        resource_type="session",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return ok(message="登出成功")
