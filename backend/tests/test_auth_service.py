"""Tests for authentication service (requirements 2.1, 2.2, 2.4)."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.exceptions import AppException
from src.core.security import get_password_hash, create_refresh_token, hash_token


# ── Helpers ───────────────────────────────────────────────────────────────────

class _FakePermission:
    def __init__(self, perm_code="device:read"):
        self.perm_code = perm_code


class _FakeRole:
    def __init__(self, role_code="ROLE_OPERATOR", permissions=None):
        self.role_code = role_code
        self.permissions = permissions or [_FakePermission()]


class _FakeUser:
    def __init__(self, **overrides):
        defaults = dict(
            id=1,
            username="testuser",
            email="test@example.com",
            real_name="Test User",
            hashed_password=get_password_hash("correct_password"),
            status="active",
            is_superadmin=False,
            failed_login_count=0,
            locked_until=None,
            last_login_at=None,
            roles=[_FakeRole()],
        )
        defaults.update(overrides)
        for k, v in defaults.items():
            setattr(self, k, v)


class _FakeRefreshToken:
    def __init__(self, **overrides):
        defaults = dict(
            id=1,
            token_hash="abc",
            user_id=1,
            expires_at=datetime.utcnow() + timedelta(days=7),
            revoked=False,
        )
        defaults.update(overrides)
        for k, v in defaults.items():
            setattr(self, k, v)


# ── Login tests ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success():
    """Successful login returns tokens and user info."""
    from src.modules.auth import auth_service

    user = _FakeUser()
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()

    with patch.object(auth_service, "_store_refresh_token", new_callable=AsyncMock):
        result = await auth_service.login(db, "testuser", "correct_password")

    assert "access_token" in result
    assert "refresh_token" in result
    assert result["user"]["username"] == "testuser"
    assert user.failed_login_count == 0


@pytest.mark.asyncio
async def test_login_wrong_password_increments_counter():
    """Wrong password increments failed_login_count."""
    from src.modules.auth import auth_service

    user = _FakeUser()
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()

    with pytest.raises(AppException) as exc_info:
        await auth_service.login(db, "testuser", "wrong_password")
    assert exc_info.value.status_code == 401
    assert user.failed_login_count == 1


@pytest.mark.asyncio
async def test_login_lockout_after_5_failures():
    """Account locks after 5 consecutive failed attempts."""
    from src.modules.auth import auth_service

    user = _FakeUser(failed_login_count=4)
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()

    with pytest.raises(AppException) as exc_info:
        await auth_service.login(db, "testuser", "wrong_password")
    assert exc_info.value.status_code == 401
    # After 5th failure, locked_until should be set
    assert user.locked_until is not None
    assert user.locked_until > datetime.utcnow()


@pytest.mark.asyncio
async def test_login_locked_account_rejected():
    """Locked account returns 423."""
    from src.modules.auth import auth_service

    user = _FakeUser(locked_until=datetime.utcnow() + timedelta(minutes=30))
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await auth_service.login(db, "testuser", "correct_password")
    assert exc_info.value.status_code == 423


@pytest.mark.asyncio
async def test_login_nonexistent_user():
    """Login with unknown username returns 401."""
    from src.modules.auth import auth_service

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await auth_service.login(db, "nobody", "password")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_account():
    """Inactive account returns 403."""
    from src.modules.auth import auth_service

    user = _FakeUser(status="disabled")
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await auth_service.login(db, "testuser", "correct_password")
    assert exc_info.value.status_code == 403


# ── Refresh token tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_tokens_success():
    """Valid refresh token returns new token pair."""
    from src.modules.auth import auth_service

    raw_token = create_refresh_token({"sub": "1", "username": "testuser"})
    fake_rt = _FakeRefreshToken(token_hash=hash_token(raw_token))

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_rt
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()

    with patch.object(auth_service, "_store_refresh_token", new_callable=AsyncMock):
        result = await auth_service.refresh_tokens(db, raw_token)

    assert "access_token" in result
    assert "refresh_token" in result
    # Old token should be revoked
    assert fake_rt.revoked is True


@pytest.mark.asyncio
async def test_refresh_revoked_token_raises():
    """Using a revoked refresh token raises 403."""
    from src.modules.auth import auth_service

    raw_token = create_refresh_token({"sub": "1", "username": "testuser"})
    fake_rt = _FakeRefreshToken(token_hash=hash_token(raw_token), revoked=True)

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_rt
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()

    with pytest.raises(AppException) as exc_info:
        await auth_service.refresh_tokens(db, raw_token)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_refresh_expired_token_raises():
    """Using an expired refresh token raises 401."""
    from src.modules.auth import auth_service

    raw_token = create_refresh_token({"sub": "1", "username": "testuser"})
    fake_rt = _FakeRefreshToken(
        token_hash=hash_token(raw_token),
        expires_at=datetime.utcnow() - timedelta(hours=1),
    )

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_rt
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await auth_service.refresh_tokens(db, raw_token)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_unknown_token_raises():
    """Using a token not in DB raises 401."""
    from src.modules.auth import auth_service

    raw_token = create_refresh_token({"sub": "1", "username": "testuser"})

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await auth_service.refresh_tokens(db, raw_token)
    assert exc_info.value.status_code == 401
