"""Bridge device-local telemetry into the existing backend realtime channel.

The browser UI intentionally remains unchanged. When the simulated wearable is
OFFLINE from AWS IoT, the device still writes its newest real sensor snapshot to
runtime/healthband.db. This service reads that local snapshot and broadcasts it
through the same WebSocket event envelope that cloud MQTT normally uses.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from control_backend.services.realtime_state_store import RealtimeStateStore
from control_backend.websocket.event_broadcaster import EventBroadcaster
from device_simulator.storage.local_database import LocalDatabase


logger = logging.getLogger(__name__)


class LocalDeviceTelemetryBridge:
    """Publish fresh device-local telemetry only while the device is offline."""

    RUNTIME_STATE_KEY = "healthband-runtime-state-v2"
    NETWORK_RESTORE_REQUEST_KEY = (
        "healthband-local-control-restore-network-v1"
    )

    def __init__(
        self,
        *,
        device_id: str,
        database_path: Path | str,
        realtime_store: RealtimeStateStore,
        broadcaster: EventBroadcaster,
        poll_interval_sec: float = 0.5,
        maximum_age_sec: float = 15.0,
    ) -> None:
        if poll_interval_sec <= 0:
            raise ValueError("poll_interval_sec must be greater than zero.")
        if maximum_age_sec <= 0:
            raise ValueError("maximum_age_sec must be greater than zero.")

        self.device_id = device_id
        self.database = LocalDatabase(database_path)
        self.realtime_store = realtime_store
        self.broadcaster = broadcaster
        self.poll_interval_sec = float(poll_interval_sec)
        self.maximum_age_sec = float(maximum_age_sec)

        self._stop_event = asyncio.Event()
        self._last_forwarded_timestamp: str | None = None

    def request_network_restore(
        self,
        command_id: str,
    ) -> dict[str, Any]:
        """Queue one same-host RESTORE_NETWORK request in shared SQLite."""

        requested_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "schemaVersion": 1,
            "commandId": command_id,
            "deviceId": self.device_id,
            "type": "RESTORE_NETWORK",
            "status": "REQUESTED",
            "requestedAt": requested_at,
            "transport": "LOCAL_SIMULATION_CONTROL",
        }

        self.database.set_state(
            self.NETWORK_RESTORE_REQUEST_KEY,
            json.dumps(payload, separators=(",", ":")),
        )

        logger.info(
            "Queued local RESTORE_NETWORK request | commandId=%s",
            command_id,
        )
        return payload

    def stop(self) -> None:
        """Request a graceful stop of the polling loop."""

        self._stop_event.set()

    async def run(self) -> None:
        """Poll SQLite until ``stop`` is requested."""

        logger.info(
            "Local device telemetry bridge started | database=%s",
            self.database.database_path,
        )

        try:
            while not self._stop_event.is_set():
                try:
                    await self.poll_once()
                except Exception:
                    # A temporary SQLite lock/corrupt row must never bring the
                    # FastAPI backend down. The next poll can recover.
                    logger.exception("Local telemetry bridge poll failed.")

                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.poll_interval_sec,
                    )
                except TimeoutError:
                    pass
        finally:
            logger.info("Local device telemetry bridge stopped.")

    async def poll_once(self) -> bool:
        """Forward one new offline telemetry snapshot, if available."""

        state = await asyncio.to_thread(self._read_runtime_state)
        if state is None:
            return False

        telemetry = state.get("latestTelemetry")
        if not isinstance(telemetry, dict):
            return False

        if telemetry.get("deviceId") != self.device_id:
            return False

        # Cloud MQTT remains authoritative while the device is connected.
        # Require both the controller's current persisted transport state and
        # the snapshot itself to be OFFLINE. The double check prevents a stale
        # offline telemetry sample from being replayed during reconnect.
        persisted_device_state = state.get(
            "deviceState", telemetry.get("deviceState")
        )
        if persisted_device_state != "OFFLINE":
            return False
        if telemetry.get("deviceState") != "OFFLINE":
            return False

        timestamp = telemetry.get("timestamp")
        if not isinstance(timestamp, str) or not timestamp:
            return False

        if timestamp == self._last_forwarded_timestamp:
            return False

        if not self._is_fresh(timestamp):
            return False

        payload = dict(telemetry)

        await self.realtime_store.update(
            device_id=self.device_id,
            event_type="telemetry",
            payload=payload,
        )
        await self.broadcaster.broadcast(
            device_id=self.device_id,
            event_type="telemetry",
            data=payload,
        )

        self._last_forwarded_timestamp = timestamp

        logger.debug(
            "Forwarded local OFFLINE telemetry | timestamp=%s | scenario=%s",
            timestamp,
            payload.get("scenario"),
        )
        return True

    def _read_runtime_state(self) -> dict[str, Any] | None:
        raw = self.database.get_state(self.RUNTIME_STATE_KEY)
        if raw is None:
            return None

        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Ignoring invalid JSON in local runtime state.")
            return None

        if not isinstance(value, dict):
            return None

        return value

    def _is_fresh(self, timestamp: str) -> bool:
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return False

        if parsed.tzinfo is None:
            return False

        age = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds()
        return -2.0 <= age <= self.maximum_age_sec
