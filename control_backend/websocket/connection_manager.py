"""Management of browser WebSocket connections."""

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class WebSocketConnectionManager:
    """Track WebSocket clients per HealthBand device."""

    def __init__(
        self,
    ) -> None:
        self._connections: dict[
            str,
            list[WebSocket],
        ] = defaultdict(
            list
        )

        self._lock = (
            asyncio.Lock()
        )

    async def connect(
        self,
        device_id: str,
        websocket: WebSocket,
    ) -> None:
        """Accept and register browser connection."""

        await websocket.accept()

        async with self._lock:
            self._connections[
                device_id
            ].append(
                websocket
            )

    async def disconnect(
        self,
        device_id: str,
        websocket: WebSocket,
    ) -> None:
        """Remove browser connection."""

        async with self._lock:
            connections = (
                self._connections.get(
                    device_id,
                    [],
                )
            )

            if (
                websocket
                in connections
            ):
                connections.remove(
                    websocket
                )

            if not connections:
                self._connections.pop(
                    device_id,
                    None,
                )

    async def broadcast(
        self,
        device_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Send JSON event to every browser watching device."""

        async with self._lock:
            connections = list(
                self._connections.get(
                    device_id,
                    [],
                )
            )

        disconnected: list[
            WebSocket
        ] = []

        for websocket in connections:
            try:
                await websocket.send_json(
                    payload
                )

            except Exception:
                disconnected.append(
                    websocket
                )

        for websocket in disconnected:
            await self.disconnect(
                device_id,
                websocket,
            )