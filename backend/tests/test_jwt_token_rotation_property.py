"""Property-based test for JWT token rotation (Property 1).

Feature: nesom-development, Property 1: JWT 令牌轮换
Validates: Requirements 2.4

Property: For any valid refresh token, using it to obtain new tokens
should invalidate the old refresh token (rotation mechanism).
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from hypothesis import given, settings as hyp_settings, strategies as st

from src.core.security import (
    create_refresh_token,
    hash_token,
)
from src.core.exceptions import AppException
from src.modules.auth import auth_service


# ── Strategies ────────────────────────────────────────────────────────────────

user_ids = st.integers(min_value=1, max_value=100_000)
usernames = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
    min_size=3,
    max_size=30,
).filter(lambda s: len(s) >= 3)


# ── Helpers ───────────────────────────────────────────────────────────────────

class _FakeRefreshToken:
    """Mutable stand-in for the RefreshToken ORM model."""
    def __init__(self, token_hash: str, user_id: int, expires_at: datetime):
        self.id = 1
        self.token_hash = token_hash
        self.user_id = user_id
        self.expires_at = expires_at
        self.revoked = False


# ── Property test ─────────────────────────────────────────────────────────────

@hyp_settings(max_examples=100)
@given(user_id=user_ids, username=usernames)
@pytest.mark.asyncio
async def test_refresh_token_rotation_invalidates_old_token(user_id: int, username: str):
    """Property 1: For any user, refreshing a token revokes the old one.

    Feature: nesom-development, Property 1: JWT 令牌轮换
    Validates: Requirements 2.4
    """
    # Arrange: create a valid refresh token
    raw_token = create_refresh_token({"sub": str(user_id), "username": username})
    fake_rt = _FakeRefreshToken(
        token_hash=hash_token(raw_token),
        user_id=user_id,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_rt
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()

    with patch.object(auth_service, "_store_refresh_token", new_callable=AsyncMock):
        result = await auth_service.refresh_tokens(db, raw_token)

    # Assert: old token is revoked
    assert fake_rt.revoked is True, "Old refresh token must be revoked after rotation"

    # Assert: new tokens are returned
    assert "access_token" in result
    assert "refresh_token" in result
    assert result["access_token"] != raw_token
    assert result["refresh_token"] != raw_token
