"""Tests for Role and Permission management API (requirement 2.3)."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.modules.auth.schemas import RoleCreate
from src.core.exceptions import AppException


# ── Helpers ───────────────────────────────────────────────────────────────────

class _FakePerm:
    def __init__(self, id=1, perm_code="device:read", module="device",
                 resource="monitor", action="read"):
        self.id = id
        self.perm_code = perm_code
        self.perm_name = "查看设备"
        self.module = module
        self.resource = resource
        self.action = action
        self.description = None
        self.is_system = True
        self.created_at = datetime(2026, 1, 1)


class _FakeRole:
    def __init__(self, id=1, role_code="ROLE_OPERATOR", is_protected=False,
                 is_default=False, users=None, permissions=None):
        self.id = id
        self.role_code = role_code
        self.role_name = "操作员"
        self.description = None
        self.role_type = "custom"
        self.is_protected = is_protected
        self.is_default = is_default
        self.data_scope = "self"
        self.users = users or []
        self.permissions = permissions or []
        self.created_at = datetime(2026, 1, 1)
        self.updated_at = datetime(2026, 1, 1)


def _make_permission(**kwargs):
    return _FakePerm(**kwargs)


def _make_role(**kwargs):
    return _FakeRole(**kwargs)


# ── Schema validation tests ───────────────────────────────────────────────────

def test_role_create_valid_code():
    schema = RoleCreate(role_code="ROLE_ENGINEER", role_name="工程师")
    assert schema.role_code == "ROLE_ENGINEER"


def test_role_create_invalid_code():
    with pytest.raises(Exception):
        RoleCreate(role_code="engineer", role_name="工程师")


def test_role_create_invalid_role_type():
    with pytest.raises(Exception):
        RoleCreate(role_code="ROLE_X", role_name="X", role_type="unknown")


def test_role_create_invalid_data_scope():
    with pytest.raises(Exception):
        RoleCreate(role_code="ROLE_X", role_name="X", data_scope="invalid")


# ── Service unit tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_permissions_no_filter():
    from src.modules.auth import service
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [_make_permission()]
    db.execute = AsyncMock(return_value=mock_result)

    perms = await service.list_permissions(db)
    assert len(perms) == 1


@pytest.mark.asyncio
async def test_get_permission_not_found():
    from src.modules.auth import service
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await service.get_permission(db, 999)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_role_duplicate_code():
    from src.modules.auth import service
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = _make_role()
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await service.create_role(db, role_code="ROLE_OPERATOR", role_name="操作员")
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_delete_protected_role_raises():
    from src.modules.auth import service
    db = AsyncMock()
    protected_role = _make_role(is_protected=True)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = protected_role
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await service.delete_role(db, 1)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_default_role_raises():
    from src.modules.auth import service
    db = AsyncMock()
    default_role = _make_role(is_default=True)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = default_role
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await service.delete_role(db, 1)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_role_with_users_raises():
    from src.modules.auth import service
    db = AsyncMock()
    role_with_users = _make_role(users=[MagicMock()])
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = role_with_users
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await service.delete_role(db, 1)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_update_protected_role_raises():
    from src.modules.auth import service
    db = AsyncMock()
    protected_role = _make_role(is_protected=True)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = protected_role
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await service.update_role(db, 1, role_name="新名称")
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_update_role_permissions_protected_raises():
    from src.modules.auth import service
    db = AsyncMock()
    protected_role = _make_role(is_protected=True)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = protected_role
    db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(AppException) as exc_info:
        await service.update_role_permissions(db, 1, permission_ids=[1, 2])
    assert exc_info.value.status_code == 403


# ── Redis cache tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_permissions_uses_cache():
    """When Redis has cached permissions, DB should not be queried."""
    from src.modules.auth import service
    db = AsyncMock()

    with patch("src.modules.auth.service._redis_client") as mock_redis_factory:
        mock_r = AsyncMock()
        mock_r.get = AsyncMock(return_value='["device:read", "workorder:create"]')
        mock_r.aclose = AsyncMock()
        mock_redis_factory.return_value = mock_r

        perms = await service.get_user_permissions_cached(db, user_id=1)

    assert "device:read" in perms
    assert "workorder:create" in perms
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_user_permissions_cache_miss_queries_db():
    """On cache miss, permissions are fetched from DB and cached."""
    from src.modules.auth import service
    db = AsyncMock()

    perm = _make_permission(perm_code="device:read")
    role = _make_role(permissions=[perm])

    mock_db_result = MagicMock()
    mock_db_result.scalars.return_value.all.return_value = [role]
    db.execute = AsyncMock(return_value=mock_db_result)

    with patch("src.modules.auth.service._redis_client") as mock_redis_factory:
        mock_r = AsyncMock()
        mock_r.get = AsyncMock(return_value=None)  # cache miss
        mock_r.setex = AsyncMock()
        mock_r.aclose = AsyncMock()
        mock_redis_factory.return_value = mock_r

        perms = await service.get_user_permissions_cached(db, user_id=1)

    assert "device:read" in perms
    mock_r.setex.assert_called_once()
    # Verify TTL is 5 minutes (300 seconds)
    call_args = mock_r.setex.call_args
    assert call_args[0][1] == 300


@pytest.mark.asyncio
async def test_invalidate_role_cache_called_on_permission_update():
    """Updating role permissions should invalidate the role cache."""
    from src.modules.auth import service

    role = _make_role()
    perm = _make_permission()

    db = AsyncMock()
    # First call: get_role, second call: get permissions
    mock_role_result = MagicMock()
    mock_role_result.scalar_one_or_none.return_value = role
    mock_perm_result = MagicMock()
    mock_perm_result.scalars.return_value.all.return_value = [perm]
    mock_user_result = MagicMock()
    mock_user_result.fetchall.return_value = []

    db.execute = AsyncMock(side_effect=[mock_role_result, mock_perm_result, mock_user_result])
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch("src.modules.auth.service._redis_client") as mock_redis_factory:
        mock_r = AsyncMock()
        mock_r.delete = AsyncMock()
        mock_r.aclose = AsyncMock()
        mock_redis_factory.return_value = mock_r

        await service.update_role_permissions(db, role_id=1, permission_ids=[1])

    # delete should have been called for role cache invalidation
    mock_r.delete.assert_called()
