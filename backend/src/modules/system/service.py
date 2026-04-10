"""Business logic for System configuration module."""
import json
from typing import List, Optional, Tuple

import redis.asyncio as aioredis
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import AppException
from .models import SysConfig

CACHE_PREFIX = "config:"
CACHE_TTL = 300  # 5 minutes


# ── Redis helpers ─────────────────────────────────────────────────────────────

async def _get_redis():
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def _cache_get(key: str) -> Optional[str]:
    try:
        r = await _get_redis()
        val = await r.get(f"{CACHE_PREFIX}{key}")
        await r.aclose()
        return val
    except Exception:
        return None


async def _cache_set(key: str, value: str, ttl: int = CACHE_TTL) -> None:
    try:
        r = await _get_redis()
        await r.set(f"{CACHE_PREFIX}{key}", value, ex=ttl)
        await r.aclose()
    except Exception:
        pass


async def _cache_delete(key: str) -> None:
    try:
        r = await _get_redis()
        await r.delete(f"{CACHE_PREFIX}{key}")
        await r.aclose()
    except Exception:
        pass


async def _cache_delete_pattern(pattern: str) -> None:
    try:
        r = await _get_redis()
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor, match=f"{CACHE_PREFIX}{pattern}", count=100)
            if keys:
                await r.delete(*keys)
            if cursor == 0:
                break
        await r.aclose()
    except Exception:
        pass


# ── Config CRUD ───────────────────────────────────────────────────────────────

async def list_configs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    module: Optional[str] = None,
    config_key: Optional[str] = None,
    is_system: Optional[int] = None,
) -> Tuple[List[SysConfig], int]:
    stmt = select(SysConfig)

    if module:
        stmt = stmt.where(SysConfig.module == module)
    if config_key:
        stmt = stmt.where(SysConfig.config_key.ilike(f"%{config_key}%"))
    if is_system is not None:
        stmt = stmt.where(SysConfig.is_system == is_system)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(SysConfig.created_time.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_config(db: AsyncSession, config_key: str) -> SysConfig:
    # Try cache first
    cached = await _cache_get(config_key)
    if cached:
        # Still need the DB object for full response, but we can skip for read-heavy paths
        pass

    result = await db.execute(
        select(SysConfig).where(SysConfig.config_key == config_key)
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise AppException(status_code=404, message="配置不存在")

    # Update cache
    await _cache_set(config_key, cfg.config_value or "")
    return cfg


async def create_config(db: AsyncSession, **kwargs) -> SysConfig:
    config_key = kwargs.get("config_key")
    # Check duplicate
    existing = await db.execute(
        select(SysConfig).where(SysConfig.config_key == config_key)
    )
    if existing.scalar_one_or_none():
        raise AppException(status_code=409, message="配置键已存在")

    cfg = SysConfig(**kwargs)
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)

    # Set cache
    await _cache_set(config_key, cfg.config_value or "")
    return cfg


async def update_config(db: AsyncSession, config_key: str, **kwargs) -> SysConfig:
    cfg = await get_config(db, config_key)

    # System configs need extra care (but we don't block here, leave to permission layer)
    for key, value in kwargs.items():
        if value is not None:
            setattr(cfg, key, value)

    cfg.version = (cfg.version or 1) + 1
    await db.commit()
    await db.refresh(cfg)

    # Invalidate cache
    await _cache_delete(config_key)
    await _cache_set(config_key, cfg.config_value or "")
    return cfg


async def delete_config(db: AsyncSession, config_key: str) -> None:
    cfg = await get_config(db, config_key)

    if cfg.is_system == 1:
        raise AppException(status_code=403, message="系统级配置不允许删除")

    await db.delete(cfg)
    await db.commit()
    await _cache_delete(config_key)


async def batch_update_configs(
    db: AsyncSession, configs: List[dict]
) -> List[SysConfig]:
    updated = []
    for item in configs:
        key = item["config_key"]
        value = item["config_value"]
        result = await db.execute(
            select(SysConfig).where(SysConfig.config_key == key)
        )
        cfg = result.scalar_one_or_none()
        if cfg:
            cfg.config_value = value
            cfg.version = (cfg.version or 1) + 1
            updated.append(cfg)
            await _cache_delete(key)

    await db.commit()
    for cfg in updated:
        await db.refresh(cfg)
        await _cache_set(cfg.config_key, cfg.config_value or "")

    return updated


async def refresh_config_cache(db: AsyncSession) -> int:
    """Refresh all config cache entries. Returns count of refreshed items."""
    await _cache_delete_pattern("*")

    result = await db.execute(select(SysConfig))
    configs = list(result.scalars().all())
    for cfg in configs:
        await _cache_set(cfg.config_key, cfg.config_value or "")
    return len(configs)



# ── Dictionary CRUD ───────────────────────────────────────────────────────────

from .models import SysDict

DICT_CACHE_PREFIX = "dict:"
DICT_CACHE_TTL = 600  # 10 minutes


async def list_dict_types(db: AsyncSession) -> List[str]:
    """Return distinct dict types."""
    result = await db.execute(
        select(SysDict.dict_type).distinct().order_by(SysDict.dict_type)
    )
    return [row[0] for row in result.all()]


async def list_dict_data(
    db: AsyncSession,
    dict_type: str,
    status: Optional[int] = 1,
) -> List[SysDict]:
    stmt = select(SysDict).where(SysDict.dict_type == dict_type)
    if status is not None:
        stmt = stmt.where(SysDict.status == status)
    stmt = stmt.order_by(SysDict.sort_order)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_dict_item(db: AsyncSession, dict_id: int) -> SysDict:
    result = await db.execute(
        select(SysDict).where(SysDict.id == dict_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise AppException(status_code=404, message="字典数据不存在")
    return item


async def create_dict_item(db: AsyncSession, **kwargs) -> SysDict:
    # Check duplicate code within same type
    dict_type = kwargs.get("dict_type")
    dict_code = kwargs.get("dict_code")
    existing = await db.execute(
        select(SysDict).where(
            SysDict.dict_type == dict_type,
            SysDict.dict_code == dict_code,
        )
    )
    if existing.scalar_one_or_none():
        raise AppException(status_code=409, message="同一字典类型下编码已存在")

    item = SysDict(**kwargs)
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # Invalidate dict cache for this type
    await _cache_delete(f"{DICT_CACHE_PREFIX}{dict_type}")
    return item


async def update_dict_item(db: AsyncSession, dict_id: int, **kwargs) -> SysDict:
    item = await get_dict_item(db, dict_id)

    for key, value in kwargs.items():
        if value is not None:
            setattr(item, key, value)

    await db.commit()
    await db.refresh(item)

    await _cache_delete(f"{DICT_CACHE_PREFIX}{item.dict_type}")
    return item


async def delete_dict_item(db: AsyncSession, dict_id: int) -> None:
    item = await get_dict_item(db, dict_id)

    if item.is_system == 1:
        raise AppException(status_code=403, message="系统字典不允许删除")

    await db.delete(item)
    await db.commit()
    await _cache_delete(f"{DICT_CACHE_PREFIX}{item.dict_type}")



# ── Notice Template CRUD ──────────────────────────────────────────────────────

from .models import SysNoticeTemplate
import re


def render_template(template: str, variables: dict) -> str:
    """Render a template string by replacing {variable} placeholders.

    Supports:
    - Simple variables: {username}
    - Default values: {username|默认用户}
    """
    def replacer(match):
        expr = match.group(1)
        if "|" in expr:
            var_name, default = expr.split("|", 1)
            return str(variables.get(var_name.strip(), default.strip()))
        return str(variables.get(expr.strip(), match.group(0)))

    return re.sub(r"\{([^{}]+)\}", replacer, template)


async def list_notice_templates(
    db: AsyncSession,
    notice_type: Optional[str] = None,
    status: Optional[int] = None,
) -> List[SysNoticeTemplate]:
    stmt = select(SysNoticeTemplate)
    if notice_type:
        stmt = stmt.where(SysNoticeTemplate.notice_type == notice_type)
    if status is not None:
        stmt = stmt.where(SysNoticeTemplate.status == status)
    stmt = stmt.order_by(SysNoticeTemplate.created_time.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_notice_template(db: AsyncSession, template_code: str) -> SysNoticeTemplate:
    result = await db.execute(
        select(SysNoticeTemplate).where(SysNoticeTemplate.template_code == template_code)
    )
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise AppException(status_code=404, message="通知模板不存在")
    return tpl


async def create_notice_template(db: AsyncSession, **kwargs) -> SysNoticeTemplate:
    template_code = kwargs.get("template_code")
    existing = await db.execute(
        select(SysNoticeTemplate).where(SysNoticeTemplate.template_code == template_code)
    )
    if existing.scalar_one_or_none():
        raise AppException(status_code=409, message="模板编码已存在")

    tpl = SysNoticeTemplate(**kwargs)
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


async def update_notice_template(
    db: AsyncSession, template_code: str, **kwargs
) -> SysNoticeTemplate:
    tpl = await get_notice_template(db, template_code)
    for key, value in kwargs.items():
        if value is not None:
            setattr(tpl, key, value)
    await db.commit()
    await db.refresh(tpl)
    return tpl


async def delete_notice_template(db: AsyncSession, template_code: str) -> None:
    tpl = await get_notice_template(db, template_code)
    await db.delete(tpl)
    await db.commit()


async def test_notice_template(
    db: AsyncSession, template_code: str, recipient: str, variables: dict
) -> dict:
    """Render a template with test variables and return the result."""
    tpl = await get_notice_template(db, template_code)

    rendered_title = render_template(tpl.title_template or "", variables)
    rendered_content = render_template(tpl.content_template, variables)

    return {
        "template_code": template_code,
        "notice_type": tpl.notice_type,
        "recipient": recipient,
        "rendered_title": rendered_title,
        "rendered_content": rendered_content,
        "status": "preview",
    }



# ── Health Check ──────────────────────────────────────────────────────────────

from src.database.session import check_db_connection
from datetime import datetime as dt


async def check_system_health(db: AsyncSession) -> dict:
    """Check health of all system components: MySQL, Redis, MinIO."""
    # Database check
    db_ok = await check_db_connection()

    # Redis check
    redis_ok = False
    try:
        r = await _get_redis()
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        pass

    # MinIO check
    minio_ok = False
    try:
        from minio import Minio
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        client.list_buckets()
        minio_ok = True
    except Exception:
        pass

    # Config stats
    config_count = 0
    dict_count = 0
    try:
        config_result = await db.execute(select(func.count()).select_from(SysConfig))
        config_count = config_result.scalar_one()
        dict_result = await db.execute(select(func.count()).select_from(SysDict))
        dict_count = dict_result.scalar_one()
    except Exception:
        pass

    all_ok = db_ok and redis_ok and minio_ok
    status = "UP" if all_ok else "DEGRADED"

    return {
        "status": status,
        "components": {
            "database": "UP" if db_ok else "DOWN",
            "redis": "UP" if redis_ok else "DOWN",
            "minio": "UP" if minio_ok else "DOWN",
        },
        "details": {
            "configCount": config_count,
            "dictCount": dict_count,
            "lastRefreshTime": dt.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        },
    }
