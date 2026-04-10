"""Tests for the /health endpoint (requirement 1.4)."""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from src.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_200():
    """Health endpoint should return HTTP 200."""
    with (
        patch("src.main.check_db_connection", new_callable=AsyncMock, return_value=True),
        patch("redis.asyncio.from_url") as mock_redis,
    ):
        mock_r = AsyncMock()
        mock_r.ping = AsyncMock()
        mock_r.aclose = AsyncMock()
        mock_redis.return_value = mock_r

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_response_shape():
    """Health response must contain status, timestamp, and components."""
    with (
        patch("src.main.check_db_connection", new_callable=AsyncMock, return_value=True),
        patch("redis.asyncio.from_url") as mock_redis,
    ):
        mock_r = AsyncMock()
        mock_r.ping = AsyncMock()
        mock_r.aclose = AsyncMock()
        mock_redis.return_value = mock_r

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

    body = response.json()
    assert "status" in body
    assert "timestamp" in body
    assert "components" in body
    assert "database" in body["components"]
    assert "redis" in body["components"]


@pytest.mark.asyncio
async def test_health_degraded_when_db_down():
    """Health status should be 'degraded' when database is unreachable."""
    with (
        patch("src.main.check_db_connection", new_callable=AsyncMock, return_value=False),
        patch("redis.asyncio.from_url") as mock_redis,
    ):
        mock_r = AsyncMock()
        mock_r.ping = AsyncMock(side_effect=Exception("connection refused"))
        mock_redis.return_value = mock_r

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

    body = response.json()
    assert body["status"] == "degraded"
    assert body["components"]["database"] == "error"
