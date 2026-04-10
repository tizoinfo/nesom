"""WebSocket manager for real-time device data and alert push."""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per device."""

    def __init__(self):
        # device_id -> set of active WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, device_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if device_id not in self._connections:
            self._connections[device_id] = set()
        self._connections[device_id].add(websocket)
        logger.info("WebSocket connected for device %s", device_id)

    def disconnect(self, device_id: str, websocket: WebSocket) -> None:
        if device_id in self._connections:
            self._connections[device_id].discard(websocket)
            if not self._connections[device_id]:
                del self._connections[device_id]
        logger.info("WebSocket disconnected for device %s", device_id)

    async def broadcast_to_device(self, device_id: str, message: dict) -> None:
        """Send a message to all connections subscribed to a device."""
        connections = self._connections.get(device_id, set()).copy()
        dead = set()
        for ws in connections:
            try:
                await ws.send_text(json.dumps(message, default=str))
            except Exception:
                dead.add(ws)
        # Clean up dead connections
        for ws in dead:
            self.disconnect(device_id, ws)

    async def broadcast_alert(self, device_id: str, alert: dict) -> None:
        """Broadcast an alert notification to all device subscribers."""
        message = {
            "type": "alert",
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "alert": alert,
        }
        await self.broadcast_to_device(device_id, message)

    async def broadcast_status(self, device_id: str, status: str, health_score: int = None) -> None:
        """Broadcast a device status change."""
        message = {
            "type": "status",
            "device_id": device_id,
            "status": status,
            "health_score": health_score,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast_to_device(device_id, message)

    async def broadcast_metrics(self, device_id: str, metrics: list) -> None:
        """Broadcast real-time metric data."""
        message = {
            "type": "metrics",
            "device_id": device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": metrics,
        }
        await self.broadcast_to_device(device_id, message)


# Global connection manager singleton
manager = ConnectionManager()


async def handle_device_websocket(device_id: str, websocket: WebSocket) -> None:
    """Handle a WebSocket connection for a specific device."""
    await manager.connect(device_id, websocket)
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "device_id": device_id,
            "message": "已连接到设备实时数据流",
        }))

        # Listen for client messages (subscribe/unsubscribe)
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                msg = json.loads(data)
                action = msg.get("action")

                if action == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif action == "subscribe":
                    # Client subscribes to specific metric types
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "device_id": device_id,
                        "metrics": msg.get("metric_types", []),
                    }))
            except asyncio.TimeoutError:
                # Send heartbeat ping
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket error for device %s: %s", device_id, e)
    finally:
        manager.disconnect(device_id, websocket)
