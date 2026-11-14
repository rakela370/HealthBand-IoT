"""Regression tests for local telemetry during AWS/MQTT outages."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from control_backend.services.local_device_bridge import LocalDeviceTelemetryBridge
from control_backend.services.realtime_state_store import RealtimeStateStore
from device_simulator.storage.local_database import LocalDatabase


class RecordingBroadcaster:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, dict[str, Any]]] = []

    async def broadcast(
        self,
        device_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        self.messages.append((device_id, event_type, dict(data)))


def _write_runtime_state(
    database: LocalDatabase,
    *,
    state: str,
    timestamp: str,
    heart_rate: float,
    steps: int,
) -> None:
    telemetry = {
        "deviceId": "healthband-device-001",
        "softwareVersion": "1.0.0",
        "deviceState": state,
        "scenario": "RUNNING",
        "activityLevel": "HIGH",
        "measurements": {
            "heartRateBpm": heart_rate,
            "totalDailySteps": steps,
            "batteryPercentage": 71.0,
        },
        "sensorStatus": {
            "heart_rate": "OK",
            "step_counter": "OK",
            "battery": "OK",
        },
        "timestamp": timestamp,
        "simulated": True,
    }
    database.set_state(
        LocalDeviceTelemetryBridge.RUNTIME_STATE_KEY,
        json.dumps(
            {
                "physiologicalScenario": "RUNNING",
                "deviceState": state,
                "latestTelemetry": telemetry,
            }
        ),
    )


@pytest.mark.asyncio
async def test_bridge_forwards_new_offline_telemetry_without_frontend_changes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "healthband.db"
    database = LocalDatabase(path)
    store = RealtimeStateStore()
    broadcaster = RecordingBroadcaster()
    bridge = LocalDeviceTelemetryBridge(
        device_id="healthband-device-001",
        database_path=path,
        realtime_store=store,
        broadcaster=broadcaster,  # type: ignore[arg-type]
        maximum_age_sec=30.0,
    )

    first_timestamp = datetime.now(timezone.utc).isoformat()
    _write_runtime_state(
        database,
        state="OFFLINE",
        timestamp=first_timestamp,
        heart_rate=91.0,
        steps=126,
    )

    assert await bridge.poll_once() is True
    latest = await store.get_latest("healthband-device-001", "telemetry")
    assert latest is not None
    assert latest["deviceState"] == "OFFLINE"
    assert latest["scenario"] == "RUNNING"
    assert latest["measurements"]["heartRateBpm"] == 91.0
    assert len(broadcaster.messages) == 1

    # Same reading is not rebroadcast on every 0.5 s bridge poll.
    assert await bridge.poll_once() is False
    assert len(broadcaster.messages) == 1

    second_timestamp = datetime.now(timezone.utc).isoformat()
    _write_runtime_state(
        database,
        state="OFFLINE",
        timestamp=second_timestamp,
        heart_rate=99.0,
        steps=141,
    )
    assert await bridge.poll_once() is True
    latest = await store.get_latest("healthband-device-001", "telemetry")
    assert latest is not None
    assert latest["measurements"]["heartRateBpm"] == 99.0
    assert latest["measurements"]["totalDailySteps"] == 141
    assert len(broadcaster.messages) == 2


@pytest.mark.asyncio
async def test_bridge_does_not_override_cloud_telemetry_while_online(
    tmp_path: Path,
) -> None:
    path = tmp_path / "healthband.db"
    database = LocalDatabase(path)
    store = RealtimeStateStore()
    broadcaster = RecordingBroadcaster()
    bridge = LocalDeviceTelemetryBridge(
        device_id="healthband-device-001",
        database_path=path,
        realtime_store=store,
        broadcaster=broadcaster,  # type: ignore[arg-type]
        maximum_age_sec=30.0,
    )

    _write_runtime_state(
        database,
        state="MONITORING",
        timestamp=datetime.now(timezone.utc).isoformat(),
        heart_rate=110.0,
        steps=200,
    )

    assert await bridge.poll_once() is False
    assert broadcaster.messages == []
    assert await store.get_latest("healthband-device-001", "telemetry") is None


@pytest.mark.asyncio
async def test_bridge_stops_immediately_when_controller_has_reconnected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "healthband.db"
    database = LocalDatabase(path)
    store = RealtimeStateStore()
    broadcaster = RecordingBroadcaster()
    bridge = LocalDeviceTelemetryBridge(
        device_id="healthband-device-001",
        database_path=path,
        realtime_store=store,
        broadcaster=broadcaster,  # type: ignore[arg-type]
        maximum_age_sec=30.0,
    )

    timestamp = datetime.now(timezone.utc).isoformat()
    telemetry = {
        "deviceId": "healthband-device-001",
        "deviceState": "OFFLINE",
        "scenario": "RUNNING",
        "activityLevel": "HIGH",
        "measurements": {"heartRateBpm": 120.0},
        "sensorStatus": {},
        "timestamp": timestamp,
    }
    # The latest sample was captured offline, but the controller state has
    # already moved back to MONITORING. Cloud data must take over immediately.
    database.set_state(
        bridge.RUNTIME_STATE_KEY,
        json.dumps(
            {
                "physiologicalScenario": "RUNNING",
                "deviceState": "MONITORING",
                "latestTelemetry": telemetry,
            }
        ),
    )

    assert await bridge.poll_once() is False
    assert broadcaster.messages == []


def test_bridge_writes_local_restore_network_request(tmp_path: Path) -> None:
    path = tmp_path / "healthband.db"
    store = RealtimeStateStore()
    broadcaster = RecordingBroadcaster()
    bridge = LocalDeviceTelemetryBridge(
        device_id="healthband-device-001",
        database_path=path,
        realtime_store=store,
        broadcaster=broadcaster,  # type: ignore[arg-type]
    )

    request = bridge.request_network_restore("restore-local-1")
    raw = bridge.database.get_state(bridge.NETWORK_RESTORE_REQUEST_KEY)

    assert raw is not None
    persisted = json.loads(raw)
    assert request["commandId"] == "restore-local-1"
    assert persisted["status"] == "REQUESTED"
    assert persisted["type"] == "RESTORE_NETWORK"
