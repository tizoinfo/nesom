"""User management business logic: CRUD, password, lock/unlock.

Design ref: docs/06-详细设计/03-用户权限管理/API接口设计.md §3.2
Requirements: 2.6
"""
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import settings
from src.core.exceptions import AppException
from src.core.security import get_password_hash, verify_password
from .models import Permission, Role, User, user_roles


async def list_users(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[List[User], int]:
    stmt = select(User).options(selectinload(User.roles))
    if search:
        stmt = stmt.where(
            User.username.contains(search)
            | User.real_name.contains(search)
            | User.email.contains(search)
        )
    if status:
        stmt = stmt.where(User.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    users = list(result.scalars().all())
    return users, total


async def get_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise AppException(status_code=404, message="用户不存在")
    return user


async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    real_name: str,
    password: Optional[str] = None,
    role_ids: Optional[List[int]] = None,
) -> User:
    # Check uniqueness
    existing = await db.execute(
        select(User).where((User.username == username) | (User.email == email))
    )
    if existing.scalar_one_or_none():
        raise AppException(status_code=409, message="用户名或邮箱已存在")

    if not password:
        password = secrets.token_urlsafe(12)

    user = User(
        username=username,
        email=email,
        real_name=real_name,
        password_hash=get_password_hash(password),
        status="active",
    )
    db.add(user)
    await db.flush()

    if role_ids:
        roles_result = await db.execute(
            select(Role).where(Role.id.in_(role_ids))
        )
        user.roles = list(roles_result.scalars().all())

    await db.flush()
    return user


async def update_user(
    db: AsyncSession,
    user_id: int,
    real_name: Optional[str] = None,
    email: Optional[str] = None,
    status: Optional[str] = None,
    role_ids: Optional[List[int]] = None,
) -> User:
    user = await get_user(db, user_id)

    if email and email != user.email:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise AppException(status_code=409, message="邮箱已存在")
        user.email = email

    if real_name is not None:
        user.real_name = real_name
    if status is not None:
        user.status = status

    if role_ids is not None:
        roles_result = await db.execute(
            select(Role).where(Role.id.in_(role_ids))
        )
        user.roles = list(roles_result.scalars().all())

    await db.flush()
    return user


async def delete_user(db: AsyncSession, user_id: int, current_user_id: int) -> None:
    if user_id == current_user_id:
        raise AppException(status_code=403, message="不能删除自己")
    user = await get_user(db, user_id)
    if user.is_superadmin:
        raise AppException(status_code=403, message="不能删除超级管理员")
    user.status = "deleted"
    await db.flush()


async def change_password(
    db: AsyncSession,
    user_id: int,
    current_password: str,
    new_password: str,
) -> None:
    user = await get_user(db, user_id)
    if not verify_password(current_password, user.password_hash):
        raise AppException(status_code=401, message="当前密码错误")
    user.password_hash = get_password_hash(new_password)
    await db.flush()


async def reset_password(
    db: AsyncSession,
    user_id: int,
    new_password: Optional[str] = None,
) -> str:
    user = await get_user(db, user_id)
    if not new_password:
        new_password = secrets.token_urlsafe(12)
    user.password_hash = get_password_hash(new_password)
    await db.flush()
    return new_password


async def lock_user(
    db: AsyncSession,
    user_id: int,
    duration_minutes: int = 1440,
) -> User:
    user = await get_user(db, user_id)
    if user.is_superadmin:
        raise AppException(status_code=403, message="不能锁定超级管理员")
    user.lockout_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
    await db.flush()
    return user


async def unlock_user(db: AsyncSession, user_id: int) -> User:
    user = await get_user(db, user_id)
    user.lockout_until = None
    user.failed_login_attempts = 0
    await db.flush()
    return user
