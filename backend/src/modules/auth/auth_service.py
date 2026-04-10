"""Authentication business logic: login, logout, token refresh.

Design ref: docs/06-详细设计/03-用户权限管理/API接口设计.md §3.1
Requirements: 2.1, 2.2, 2.4
"""
from datetime import datetime, timedelta
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import settings
from src.core.exceptions import AppException
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)
from .models import RefreshToken, Role, User


# ── Constants ─────────────────────────────────────────────────────────────────

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 30
ACCESS_TOKEN_BLACKLIST_PREFIX = "token:blacklist:"


def _redis_client() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(
        select(User)
        .where((User.username == username) | (User.email == username))
        .options(
            selectinload(User.roles).selectinload(Role.permissions)
        )
    )
    return result.scalar_one_or_none()


async def _blacklist_access_token(jti: str, ttl_seconds: int) -> None:
    """Add an access token JTI to the Redis blacklist."""
    try:
        r = _redis_client()
        await r.setex(f"{ACCESS_TOKEN_BLACKLIST_PREFIX}{jti}", ttl_seconds, "1")
        await r.aclose()
    except Exception:
        pass


async def is_token_blacklisted(jti: str) -> bool:
    try:
        r = _redis_client()
        val = await r.get(f"{ACCESS_TOKEN_BLACKLIST_PREFIX}{jti}")
        await r.aclose()
        return val is not None
    except Exception:
        return False


async def _store_refresh_token(db: AsyncSession, user_id: int, raw_token: str) -> None:
    """Persist a hashed refresh token in the DB."""
    payload = decode_token(raw_token)
    expires_at = datetime.utcfromtimestamp(payload["exp"])
    rt = RefreshToken(
        token_hash=hash_token(raw_token),
        user_id=user_id,
        expires_at=expires_at,
    )
    db.add(rt)
    await db.flush()


async def _revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
    """Mark a refresh token as revoked."""
    th = hash_token(raw_token)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == th)
        .values(revoked=True)
    )


async def _revoke_all_user_tokens(db: AsyncSession, user_id: int) -> None:
    """Revoke all refresh tokens for a user."""
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)
        .values(revoked=True)
    )


async def _validate_refresh_token_in_db(db: AsyncSession, raw_token: str) -> RefreshToken:
    """Check that the refresh token exists, is not revoked, and not expired."""
    th = hash_token(raw_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == th)
    )
    rt = result.scalar_one_or_none()
    if rt is None:
        raise AppException(status_code=401, message="刷新令牌无效")
    if rt.revoked:
        # Possible token reuse attack – revoke all tokens for this user
        await _revoke_all_user_tokens(db, rt.user_id)
        await db.flush()
        raise AppException(status_code=403, message="刷新令牌已被撤销")
    if rt.expires_at < datetime.utcnow():
        raise AppException(status_code=401, message="刷新令牌已过期")
    return rt


# ── Public API ────────────────────────────────────────────────────────────────

async def login(db: AsyncSession, username: str, password: str) -> dict:
    """Authenticate user and return tokens + user info."""
    user = await _get_user_by_username(db, username)
    if user is None:
        raise AppException(status_code=401, message="用户名或密码错误")

    # Check lockout
    if user.lockout_until and user.lockout_until > datetime.utcnow():
        raise AppException(status_code=423, message="账户已锁定，请稍后再试")

    # Check status
    if user.status != "active":
        raise AppException(status_code=403, message="账户未激活或已禁用")

    # Verify password
    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.lockout_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_attempts = 0
        await db.flush()
        raise AppException(status_code=401, message="用户名或密码错误")

    # Success – reset counters
    user.failed_login_attempts = 0
    user.lockout_until = None
    user.last_login_at = datetime.utcnow()

    # Gather permissions
    perm_codes = list({p.perm_code for role in user.roles for p in role.permissions})
    role_codes = [r.role_code for r in user.roles]

    token_data = {"sub": str(user.id), "username": user.username}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    await _store_refresh_token(db, user.id, refresh_token)
    await db.flush()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_expires_in": settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "real_name": user.real_name,
            "is_superadmin": user.is_superadmin,
            "roles": role_codes,
            "permissions": perm_codes,
        },
    }


async def refresh_tokens(db: AsyncSession, raw_refresh_token: str) -> dict:
    """Rotate refresh token and issue new access token."""
    # Decode to get user info
    payload = decode_token(raw_refresh_token)
    if payload.get("type") != "refresh":
        raise AppException(status_code=401, message="令牌类型无效")

    # Validate in DB (checks revoked / expired)
    rt = await _validate_refresh_token_in_db(db, raw_refresh_token)

    # Revoke old refresh token (rotation)
    rt.revoked = True

    # Issue new pair
    token_data = {"sub": payload["sub"], "username": payload.get("username", "")}
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    await _store_refresh_token(db, rt.user_id, new_refresh)
    await db.flush()

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_expires_in": settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    }


async def logout(
    db: AsyncSession,
    access_token: str,
    user_id: int,
    revoke_all: bool = False,
) -> None:
    """Revoke current session or all sessions."""
    # Blacklist the access token
    try:
        payload = decode_token(access_token)
        jti = payload.get("jti")
        if jti:
            ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            await _blacklist_access_token(jti, ttl)
    except Exception:
        pass

    if revoke_all:
        await _revoke_all_user_tokens(db, user_id)
    await db.flush()
