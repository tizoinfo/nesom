"""Tests for user management service (requirement 2.6)."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.core.exceptions import AppException
from src.core.security import get_password_hash
from src.modules.auth.schemas import UserCreate


# ── Helpers ───────────────────────────────────────────────────────────────────

class _FakeRole:
    def __init__(self, id=1, role_code="ROLE_OPERATOR"):
        self.id = id
        self.role_code = role_code


class _FakeUser:
    def __init__(self, **overrides):
        defaults = dict(
            id=1,
            username="testuser",
            email="test@example.com",
            real_name="Test User",
            hashed_password=get_password_hash("password123"),
            status="active",
            is_superadmin=False,
            failed_login_count=0,
            locked_until=None,
            last_login_at=None,
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
            roles=[_FakeRole()],
        )
        defaults.update(overrides)
        for k, v in defaults.items():
            setattr(self, k, v)


# ── Schema validation tests ───────────────────────────────────────────────────

def test_user_create_valid():
    schema = UserCreate(username="john_doe", email="john@example.com", real_name="John")
    assert schema.username == "john_doe"


def test_user_create_invalid_username():
    with pytest.raises(Exception):
        UserCreate(username="a", email="john@example.com", real_name="John")


def test_user_create_invalid_email():
    with pytest.raises(Exception):
        UserCreate(username="john_doe", email="not-an-email", real_name="John")


# ── Service tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_not_found():
    from src.modules.auth import user_service
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await user_service.get_user(db, 999)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_user_duplicate():
    from src.modules.auth import user_service
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = _FakeUser()
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await user_service.create_user(db, "testuser", "test@example.com", "Test")
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_delete_self_raises():
    from src.modules.auth import user_service

    with pytest.raises(AppException) as exc_info:
        db = AsyncMock()
        await user_service.delete_user(db, user_id=1, current_user_id=1)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_superadmin_raises():
    from src.modules.auth import user_service
    db = AsyncMock()
    admin = _FakeUser(is_superadmin=True)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = admin
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()

    with pytest.raises(AppException) as exc_info:
        await user_service.delete_user(db, user_id=1, current_user_id=2)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_change_password_wrong_current():
    from src.modules.auth import user_service
    db = AsyncMock()
    user = _FakeUser()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await user_service.change_password(db, 1, "wrong_password", "new_password")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_lock_superadmin_raises():
    from src.modules.auth import user_service
    db = AsyncMock()
    admin = _FakeUser(is_superadmin=True)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = admin
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await user_service.lock_user(db, 1)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_unlock_user_clears_lock():
    from src.modules.auth import user_service
    db = AsyncMock()
    user = _FakeUser(locked_until=datetime(2026, 12, 31), failed_login_count=5)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()

    result = await user_service.unlock_user(db, 1)
    assert result.locked_until is None
    assert result.failed_login_count == 0
