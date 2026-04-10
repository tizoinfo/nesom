from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class AppException(Exception):
    def __init__(self, status_code: int, message: str, detail: dict | None = None):
        self.status_code = status_code
        self.message = message
        self.detail = detail


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.message,
            "detail": exc.detail,
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": 422,
            "message": "请求参数验证失败",
            "detail": exc.errors(),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from loguru import logger
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "detail": str(exc) if exc else None,
        },
    )
