"""Business logic for Role and Permission management with Redis caching."""
import json
from typing import List, Optional

import redis.asyncio as aioredis
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import settings
from src.core.exceptions import AppException
from .models import Permission, Role, user_roles

# Redis TTL for permission cache: 5 minutes
PERM_CACHE_TTL = 300


def _redis_client() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


# ── Cache helpers ─────────────────────────────────────────────────────────────

async def _invalidate_role_cache(role_id: int) -> None:
    """Remove cached permission list for a role."""
    try:
        r = _redis_client()
        await r.delete(f"role:perms:{role_id}")
        await r.aclose()
    except Exception:
        pass  # cache invalidation failure is non-fatal


async def _invalidate_users_cache_for_role(db: AsyncSession, role_id: int) -> None:
    """Remove cached permission lists for all users that have this role."""
    try:
        result = await db.execute(
            select(user_roles.c.user_id).where(user_roles.c.role_id == role_id)
        )
        user_ids = [row[0] for row in result.fetchall()]
        if not user_ids:
            return
        r = _redis_client()
        keys = [f"user:perms:{uid}" for uid in user_ids]
        await r.delete(*keys)
        await r.aclose()
    except Exception:
        pass


async def get_user_permissions_cached(db: AsyncSession, user_id: int) -> List[str]:
    """Return permission codes for a user, using Redis cache (5-min TTL)."""
    cache_key = f"user:perms:{user_id}"
    try:
        r = _redis_client()
        cached = await r.get(cache_key)
        await r.aclose()
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    # Cache miss – query DB
    result = await db.execute(
        select(Role)
        .join(user_roles, Role.id == user_roles.c.role_id)
        .where(user_roles.c.user_id == user_id)
        .options(selectinload(Role.permissions))
    )
    roles = result.scalars().all()
    perm_codes = list({p.perm_code for role in roles for p in role.permissions})

    try:
        r = _redis_client()
        await r.setex(cache_key, PERM_CACHE_TTL, json.dumps(perm_codes))
        await r.aclose()
    except Exception:
        pass

    return perm_codes


# ── Permission CRUD ───────────────────────────────────────────────────────────

async def list_permissions(
    db: AsyncSession,
    module: Optional[str] = None,
    resource: Optional[str] = None,
    action: Optional[str] = None,
) -> List[Permission]:
    stmt = select(Permission)
    if module:
        stmt = stmt.where(Permission.module == module)
    if resource:
        stmt = stmt.where(Permission.resource == resource)
    if action:
        stmt = stmt.where(Permission.action == action)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_permission(db: AsyncSession, permission_id: int) -> Permission:
    result = await db.execute(select(Permission).where(Permission.id == permission_id))
    perm = result.scalar_one_or_none()
    if not perm:
        raise AppException(status_code=404, message="权限不存在")
    return perm


# ── Role CRUD ─────────────────────────────────────────────────────────────────

async def list_roles(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> tuple[List[Role], int]:
    offset = (page - 1) * page_size
    count_result = await db.execute(select(func.count()).select_from(Role))
    total = count_result.scalar_one()

    result = await db.execute(
        select(Role)
        .options(selectinload(Role.users), selectinload(Role.permissions))
        .offset(offset)
        .limit(page_size)
        .order_by(Role.created_at)
    )
    roles = list(result.scalars().all())
    return roles, total


async def get_role(db: AsyncSession, role_id: int, with_permissions: bool = False) -> Role:
    stmt = select(Role).where(Role.id == role_id)
    if with_permissions:
        stmt = stmt.options(selectinload(Role.permissions), selectinload(Role.users))
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    if not role:
        raise AppException(status_code=404, message="角色不存在")
    return role


async def create_role(
    db: AsyncSession,
    role_code: str,
    role_name: str,
    description: Optional[str] = None,
    role_type: str = "custom",
    is_default: bool = False,
    data_scope: str = "self",
    permission_ids: Optional[List[int]] = None,
) -> Role:
    # Check uniqueness
    existing = await db.execute(select(Role).where(Role.role_code == role_code))
    if existing.scalar_one_or_none():
        raise AppException(status_code=409, message="角色编码已存在")

    role = Role(
        role_code=role_code,
        role_name=role_name,
        description=description,
        role_type=role_type,
        is_default=is_default,
        data_scope=data_scope,
    )
    db.add(role)
    await db.flush()  # get role.id

    if permission_ids:
        perms_result = await db.execute(
            select(Permission).where(Permission.id.in_(permission_ids))
        )
        role.permissions = list(perms_result.scalars().all())

    await db.commit()
    await db.refresh(role)
    return role


async def update_role(
    db: AsyncSession,
    role_id: int,
    role_name: Optional[str] = None,
    description: Optional[str] = None,
    is_default: Optional[bool] = None,
    data_scope: Optional[str] = None,
) -> Role:
    role = await get_role(db, role_id, with_permissions=True)
    if role.is_protected:
        raise AppException(status_code=403, message="系统角色不可修改")

    if role_name is not None:
        role.role_name = role_name
    if description is not None:
        role.description = description
    if is_default is not None:
        role.is_default = is_default
    if data_scope is not None:
        role.data_scope = data_scope

    await db.commit()
    await db.refresh(role)
    return role


async def delete_role(db: AsyncSession, role_id: int) -> None:
    role = await get_role(db, role_id, with_permissions=True)
    if role.is_protected:
        raise AppException(status_code=403, message="系统角色不可删除")
    if role.is_default:
        raise AppException(status_code=403, message="默认角色不可删除")
    if role.users:
        raise AppException(status_code=409, message="角色下存在用户，请先解除关联")

    await db.delete(role)
    await db.commit()
    await _invalidate_role_cache(role_id)


async def update_role_permissions(
    db: AsyncSession,
    role_id: int,
    permission_ids: List[int],
    append: bool = False,
) -> Role:
    role = await get_role(db, role_id, with_permissions=True)
    if role.is_protected:
        raise AppException(status_code=403, message="系统角色权限不可修改")

    perms_result = await db.execute(
        select(Permission).where(Permission.id.in_(permission_ids))
    )
    new_perms = list(perms_result.scalars().all())

    if append:
        existing_ids = {p.id for p in role.permissions}
        for p in new_perms:
            if p.id not in existing_ids:
                role.permissions.append(p)
    else:
        role.permissions = new_perms

    await db.commit()
    await db.refresh(role)

    # Invalidate caches
    await _invalidate_role_cache(role_id)
    await _invalidate_users_cache_for_role(db, role_id)

    return role
