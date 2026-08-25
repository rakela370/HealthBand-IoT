"""In-memory latest-state cache for realtime backend data."""

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


class RealtimeStateStore:
    """Store latest MQTT messages received by FastAPI backend."""

    def __init__(
        self,
    ) -> None:
        self._latest: dict[
            str,
            dict[
                str,
                dict[str, Any],
            ],
        ] = {}

        self._commands: dict[
            str,
            dict[
                str,
                dict[str, Any],
            ],
        ] = {}

        self._lock = (
            asyncio.Lock()
        )

    async def update(
        self,
        device_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """Store latest message for one realtime event type."""

        async with self._lock:
            device = (
                self._latest.setdefault(
                    device_id,
                    {},
                )
            )

            device[
                event_type
            ] = deepcopy(
                payload
            )

            if (
                event_type
                == "command_response"
            ):
                command_id = (
                    payload.get(
                        "commandId"
                    )
                )

                if isinstance(
                    command_id,
                    str,
                ):
                    commands = (
                        self._commands.setdefault(
                            device_id,
                            {},
                        )
                    )

                    commands[
                        command_id
                    ] = deepcopy(
                        payload
                    )

    async def register_command_submission(
        self,
        device_id: str,
        command_id: str,
        command_type: str,
        parameters: dict[str, Any],
    ) -> None:
        """Remember a command immediately after REST publication."""

        payload = {
            "commandId": (
                command_id
            ),
            "deviceId": (
                device_id
            ),
            "type": (
                command_type
            ),
            "status": (
                "PUBLISHED"
            ),
            "parameters": deepcopy(
                parameters
            ),
            "timestamp": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }

        async with self._lock:
            commands = (
                self._commands.setdefault(
                    device_id,
                    {},
                )
            )

            commands[
                command_id
            ] = payload

    async def get_latest(
        self,
        device_id: str,
        event_type: str,
    ) -> dict[str, Any] | None:
        """Return latest message for one event category."""

        async with self._lock:
            value = (
                self._latest
                .get(
                    device_id,
                    {},
                )
                .get(
                    event_type
                )
            )

            return (
                deepcopy(
                    value
                )
                if value is not None
                else None
            )

    async def get_command(
        self,
        device_id: str,
        command_id: str,
    ) -> dict[str, Any] | None:
        """Return latest known status of one command."""

        async with self._lock:
            value = (
                self._commands
                .get(
                    device_id,
                    {},
                )
                .get(
                    command_id
                )
            )

            return (
                deepcopy(
                    value
                )
                if value is not None
                else None
            )

    async def snapshot(
        self,
        device_id: str,
    ) -> dict[str, Any]:
        """Return complete realtime snapshot for one device."""

        async with self._lock:
            return deepcopy(
                self._latest.get(
                    device_id,
                    {},
                )
            )