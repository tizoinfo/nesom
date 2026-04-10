from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None


class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


def ok(data: Any = None, message: str = "success") -> dict:
    return {"code": 200, "message": message, "data": data}
