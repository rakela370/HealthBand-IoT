"""Regression test for RESTORE_NETWORK out-of-band delivery."""

from types import SimpleNamespace

import pytest

from control_backend.api.command_routes import send_command
from control_backend.models.command_models import (
    BackendCommandType,
    CommandCreateRequest,
)
from control_backend.services.realtime_state_store import RealtimeStateStore


class LocalBridgeFake:
    def __init__(self) -> None:
        self.command_ids: list[str] = []

    def request_network_restore(self, command_id: str) -> dict:
        self.command_ids.append(command_id)
        return {
            "commandId": command_id,
            "type": "RESTORE_NETWORK",
            "transport": "LOCAL_SIMULATION_CONTROL",
        }


class CloudCommandFake:
    def __init__(self) -> None:
        self.calls = 0

    def publish_command(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("RESTORE_NETWORK must not depend on offline MQTT")


@pytest.mark.asyncio
async def test_restore_network_uses_local_control_instead_of_mqtt() -> None:
    bridge = LocalBridgeFake()
    cloud = CloudCommandFake()
    store = RealtimeStateStore()
    state = SimpleNamespace(
        settings=SimpleNamespace(device_id="healthband-device-001"),
        local_telemetry_bridge=bridge,
        iot_data_client=cloud,
        realtime_store=store,
    )
    request = SimpleNamespace(app=SimpleNamespace(state=state))

    response = await send_command(
        "healthband-device-001",
        CommandCreateRequest(
            type=BackendCommandType.RESTORE_NETWORK,
            parameters={},
        ),
        request,  # type: ignore[arg-type]
    )

    assert response["accepted"] is True
    assert response["request"]["transport"] == "LOCAL_SIMULATION_CONTROL"
    assert cloud.calls == 0
    assert bridge.command_ids == [response["commandId"]]

    status = await store.get_command(
        "healthband-device-001",
        response["commandId"],
    )
    assert status is not None
    assert status["status"] == "PUBLISHED"
