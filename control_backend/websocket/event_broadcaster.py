"""Convert backend events into WebSocket messages."""

from datetime import datetime, timezone
from typing import Any

from control_backend.websocket.connection_manager import (
    WebSocketConnectionManager,
)


class EventBroadcaster:
    """Broadcast realtime HealthBand events to browsers."""

    def __init__(
        self,
        connection_manager: WebSocketConnectionManager,
    ) -> None:
        self.connection_manager = (
            connection_manager
        )

    async def broadcast(
        self,
        device_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Broadcast standardized WebSocket envelope."""

        await (
            self.connection_manager
            .broadcast(
                device_id,
                {
                    "type": (
                        event_type
                    ),
                    "deviceId": (
                        device_id
                    ),
                    "receivedAt": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                    "data": (
                        data
                    ),
                },
            )
        )