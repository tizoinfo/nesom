"""Pydantic schemas for System configuration module."""
import json
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


VALID_CONFIG_TYPES = {"STRING", "NUMBER", "BOOLEAN", "JSON"}
VALID_MODULES = {"SYSTEM", "USER", "ALERT", "REPORT", "DEVICE", "WORKORDER", "SPAREPART", "INSPECTION"}


# ── System Config schemas ─────────────────────────────────────────────────────

class SysConfigCreate(BaseModel):
    config_key: str = Field(..., min_length=1, max_length=100)
    config_value: Optional[str] = None
    config_type: str = Field(default="STRING", max_length=20)
    module: str = Field(default="SYSTEM", max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    is_sensitive: int = Field(default=0, ge=0, le=1)
    is_system: int = Field(default=0, ge=0, le=1)

    @field_validator("config_type")
    @classmethod
    def validate_config_type(cls, v: str) -> str:
        if v not in VALID_CONFIG_TYPES:
            raise ValueError(f"配置类型必须是 {VALID_CONFIG_TYPES} 之一")
        return v

    @field_validator("config_value")
    @classmethod
    def validate_config_value(cls, v: Optional[str], info) -> Optional[str]:
        if v is not None and info.data.get("config_type") == "JSON":
            try:
                json.loads(v)
            except (json.JSONDecodeError, TypeError):
                raise ValueError("JSON 类型的配置值必须是有效的 JSON 格式")
        return v


class SysConfigUpdate(BaseModel):
    config_value: Optional[str] = None
    config_type: Optional[str] = Field(None, max_length=20)
    module: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    is_sensitive: Optional[int] = Field(None, ge=0, le=1)

    @field_validator("config_type")
    @classmethod
    def validate_config_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_CONFIG_TYPES:
            raise ValueError(f"配置类型必须是 {VALID_CONFIG_TYPES} 之一")
        return v


class SysConfigRead(BaseModel):
    id: int
    config_key: str
    config_value: Optional[str] = None
    config_type: str
    module: str
    description: Optional[str] = None
    is_sensitive: int
    is_system: int
    created_time: datetime
    updated_time: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BatchConfigUpdate(BaseModel):
    configs: List[dict] = Field(..., min_length=1)

    @field_validator("configs")
    @classmethod
    def validate_configs(cls, v: List[dict]) -> List[dict]:
        for item in v:
            if "config_key" not in item or "config_value" not in item:
                raise ValueError("每个配置项必须包含 config_key 和 config_value")
        return v



# ── Dictionary schemas ────────────────────────────────────────────────────────

class SysDictCreate(BaseModel):
    dict_type: str = Field(..., min_length=1, max_length=50)
    dict_code: str = Field(..., min_length=1, max_length=50)
    dict_name: str = Field(..., min_length=1, max_length=100)
    dict_value: Optional[str] = Field(None, max_length=500)
    sort_order: int = Field(default=0, ge=0)
    parent_id: Optional[int] = None
    status: int = Field(default=1, ge=0, le=1)
    remark: Optional[str] = Field(None, max_length=500)


class SysDictUpdate(BaseModel):
    dict_name: Optional[str] = Field(None, min_length=1, max_length=100)
    dict_value: Optional[str] = Field(None, max_length=500)
    sort_order: Optional[int] = Field(None, ge=0)
    parent_id: Optional[int] = None
    status: Optional[int] = Field(None, ge=0, le=1)
    remark: Optional[str] = Field(None, max_length=500)


class SysDictRead(BaseModel):
    id: int
    dict_type: str
    dict_code: str
    dict_name: str
    dict_value: Optional[str] = None
    sort_order: int
    parent_id: Optional[int] = None
    is_system: int
    status: int
    remark: Optional[str] = None
    created_time: datetime

    model_config = {"from_attributes": True}



# ── Notice Template schemas ───────────────────────────────────────────────────

VALID_NOTICE_TYPES = {"EMAIL", "SMS", "WECHAT", "IN_APP"}


class NoticeTemplateCreate(BaseModel):
    template_code: str = Field(..., min_length=1, max_length=50)
    template_name: str = Field(..., min_length=1, max_length=100)
    notice_type: str = Field(..., max_length=20)
    title_template: Optional[str] = Field(None, max_length=500)
    content_template: str = Field(..., min_length=1)
    variables: Optional[List[dict]] = None
    is_html: int = Field(default=0, ge=0, le=1)
    status: int = Field(default=1, ge=0, le=1)

    @field_validator("notice_type")
    @classmethod
    def validate_notice_type(cls, v: str) -> str:
        if v not in VALID_NOTICE_TYPES:
            raise ValueError(f"通知类型必须是 {VALID_NOTICE_TYPES} 之一")
        return v


class NoticeTemplateUpdate(BaseModel):
    template_name: Optional[str] = Field(None, min_length=1, max_length=100)
    notice_type: Optional[str] = Field(None, max_length=20)
    title_template: Optional[str] = Field(None, max_length=500)
    content_template: Optional[str] = None
    variables: Optional[List[dict]] = None
    is_html: Optional[int] = Field(None, ge=0, le=1)
    status: Optional[int] = Field(None, ge=0, le=1)

    @field_validator("notice_type")
    @classmethod
    def validate_notice_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_NOTICE_TYPES:
            raise ValueError(f"通知类型必须是 {VALID_NOTICE_TYPES} 之一")
        return v


class NoticeTemplateRead(BaseModel):
    id: int
    template_code: str
    template_name: str
    notice_type: str
    title_template: Optional[str] = None
    content_template: str
    variables: Optional[List[dict]] = None
    is_html: int
    status: int
    created_time: datetime

    model_config = {"from_attributes": True}


class TemplateTestRequest(BaseModel):
    recipient: str = Field(..., min_length=1)
    variables: dict = Field(default_factory=dict)
