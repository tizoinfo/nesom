from contextlib import asynccontextmanager
from datetime import datetime

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.core.config import settings
from src.core.exceptions import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
)
from src.core.middleware import LoggingMiddleware, RequestIDMiddleware
from src.api.v1 import api_router
from src.database.session import check_db_connection, engine, AsyncSessionLocal
from src.modules.auth.audit import start_audit_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} [{settings.ENVIRONMENT}]")
    worker_task = start_audit_worker(AsyncSessionLocal)
    yield
    worker_task.cancel()
    logger.info("Shutting down...")
    await engine.dispose()


app = FastAPI(
    title=f"{settings.PROJECT_NAME} API",
    description="新能源运维管理系统 API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["health"])
async def health_check():
    """健康检查端点 - 返回服务及依赖组件状态"""
    db_ok = await check_db_connection()

    redis_ok = False
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        pass

    overall = "healthy" if (db_ok and redis_ok) else "degraded"

    return {
        "status": overall,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
        },
    }
