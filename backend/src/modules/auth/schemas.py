"""Pydantic schemas for Auth, Role and Permission management."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator
import re


# ── Auth schemas ──────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenUserInfo(BaseModel):
    id: str
    username: str
    email: str
    real_name: str
    is_superadmin: bool
    roles: List[str] = []
    permissions: List[str] = []

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    user: TokenUserInfo


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class LogoutRequest(BaseModel):
    revoke_all: bool = False


# ── Permission schemas ────────────────────────────────────────────────────────

class PermissionBase(BaseModel):
    perm_code: str
    perm_name: str
    module: str
    resource: str
    action: str
    description: Optional[str] = None
    is_system: bool = True


class PermissionRead(PermissionBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Role schemas ──────────────────────────────────────────────────────────────

class RoleCreate(BaseModel):
    role_code: str
    role_name: str
    description: Optional[str] = None
    role_type: str = "custom"
    is_default: bool = False
    data_scope: str = "self"
    permission_ids: Optional[List[int]] = None

    @field_validator("role_code")
    @classmethod
    def validate_role_code(cls, v: str) -> str:
        if not re.match(r"^ROLE_[A-Z_]+$", v):
            raise ValueError("role_code 必须以 ROLE_ 开头，只含大写字母和下划线")
        return v

    @field_validator("role_type")
    @classmethod
    def validate_role_type(cls, v: str) -> str:
        allowed = {"system", "custom", "department"}
        if v not in allowed:
            raise ValueError(f"role_type 必须是 {allowed} 之一")
        return v

    @field_validator("data_scope")
    @classmethod
    def validate_data_scope(cls, v: str) -> str:
        allowed = {"all", "department", "self", "custom"}
        if v not in allowed:
            raise ValueError(f"data_scope 必须是 {allowed} 之一")
        return v


class RoleUpdate(BaseModel):
    role_name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    data_scope: Optional[str] = None

    @field_validator("data_scope")
    @classmethod
    def validate_data_scope(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"all", "department", "self", "custom"}
        if v not in allowed:
            raise ValueError(f"data_scope 必须是 {allowed} 之一")
        return v


class RoleRead(BaseModel):
    id: int
    role_code: str
    role_name: str
    description: Optional[str]
    role_type: str
    is_protected: bool
    is_default: bool
    data_scope: str
    user_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleDetail(RoleRead):
    permissions: List[PermissionRead] = []


# ── Permission assignment schemas ─────────────────────────────────────────────

class RolePermissionsUpdate(BaseModel):
    permission_ids: List[int]
    append: bool = False


# ── User management schemas ───────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    email: str
    real_name: str
    password: Optional[str] = None
    role_ids: Optional[List[int]] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]{3,50}$", v):
            raise ValueError("用户名只能包含字母、数字和下划线，长度3-50")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("邮箱格式不正确")
        return v


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    role_ids: Optional[List[int]] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("邮箱格式不正确")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in {"active", "disabled", "pending"}:
            raise ValueError("status 必须是 active, disabled, pending 之一")
        return v


class UserRead(BaseModel):
    id: str
    username: str
    email: str
    real_name: str
    status: str
    is_superadmin: bool
    failed_login_attempts: int = 0
    lockout_until: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    roles: List[str] = []

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("新密码长度不能少于8位")
        return v


class ResetPasswordRequest(BaseModel):
    new_password: Optional[str] = None


class LockUserRequest(BaseModel):
    reason: str = "manual"
    duration_minutes: int = 1440
