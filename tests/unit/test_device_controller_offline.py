"""Offline behavior tests for HealthBand DeviceController."""

from pathlib import Path
from typing import Any

import pytest

from device_simulator.communication.mqtt_client import (
    IncomingMqttMessage,
)
from device_simulator.core.device_controller import (
    DeviceController,
)
from device_simulator.core.device_state import (
    DeviceState,
)
from device_simulator.core.event_bus import (
    EventBus,
)
from device_simulator.core.scheduler import (
    Scheduler,
)
from device_simulator.simulation.scenario import (
    SimulationScenario,
)
from device_simulator.storage.local_database import (
    LocalDatabase,
)
from device_simulator.storage.offline_queue import (
    OfflineQueue,
)


class FakeMqttClient:
    """MQTT fake supporting connect, disconnect and failures."""

    def __init__(
        self,
    ) -> None:
        self.connected = (
            False
        )

        self.incoming: list[
            IncomingMqttMessage
        ] = []

        self.published: list[
            tuple[
                str,
                dict[str, Any],
                int,
            ]
        ] = []

        self.subscriptions: list[
            tuple[
                str,
                int,
            ]
        ] = []

    @property
    def is_connected(
        self,
    ) -> bool:
        return (
            self.connected
        )

    def connect(
        self,
    ) -> None:
        self.connected = (
            True
        )

    def disconnect(
        self,
    ) -> None:
        self.connected = (
            False
        )

    def subscribe(
        self,
        topic: str,
        qos: int = 1,
    ) -> None:
        self.subscriptions.append(
            (
                topic,
                qos,
            )
        )

    def resubscribe_all(
        self,
    ) -> None:
        return None

    def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        qos: int,
    ) -> str:
        if not self.connected:
            raise ConnectionError(
                "MQTT disconnected."
            )

        self.published.append(
            (
                topic,
                payload,
                qos,
            )
        )

        return str(
            payload.get(
                "messageId",
                "fake-id",
            )
        )

    def drain_incoming_messages(
        self,
        maximum_items: int = 100,
    ) -> list[IncomingMqttMessage]:
        messages = (
            self.incoming[
                :maximum_items
            ]
        )

        del self.incoming[
            :maximum_items
        ]

        return (
            messages
        )


def create_queue(
    tmp_path: Path,
) -> OfflineQueue:
    return (
        OfflineQueue(
            database=(
                LocalDatabase(
                    tmp_path
                    / "healthband.db"
                )
            ),
            maximum_items=100,
        )
    )


@pytest.mark.asyncio
async def test_disconnected_telemetry_is_stored_in_offline_queue(
    tmp_path: Path,
) -> None:
    mqtt = (
        FakeMqttClient()
    )

    queue = (
        create_queue(
            tmp_path
        )
    )

    controller = (
        DeviceController(
            event_bus=EventBus(),
            scheduler=Scheduler(),
            random_seed=1,
            mqtt_client=mqtt,  # type: ignore[arg-type]
            offline_queue=queue,
        )
    )

    await controller.start()

    mqtt.connected = (
        False
    )

    await controller.read_sensors_now()

    await (
        controller
        ._publish_latest_telemetry(
            force=True
        )
    )

    assert (
        queue.size()
        >= 1
    )

    await controller.shutdown()


@pytest.mark.asyncio
async def test_network_outage_command_enters_offline_and_sensors_continue(
    tmp_path: Path,
) -> None:
    """A transport outage must not replace the physical RUNNING state."""

    mqtt = FakeMqttClient()
    queue = create_queue(tmp_path)

    controller = DeviceController(
        event_bus=EventBus(),
        scheduler=Scheduler(),
        random_seed=1,
        mqtt_client=mqtt,  # type: ignore[arg-type]
        offline_queue=queue,
    )

    await controller.start()
    controller.change_scenario(SimulationScenario.RUNNING)

    # Give the first-order HR/cadence models time to move away from rest.
    for _ in range(4):
        await controller.read_sensors_now()

    assert controller.latest_snapshot is not None
    before_hr = float(
        controller.latest_snapshot.measurements["heartRateBpm"]
    )
    before_steps = int(
        controller.latest_snapshot.measurements["totalDailySteps"]
    )
    before_battery = float(
        controller.latest_snapshot.measurements["batteryPercentage"]
    )

    mqtt.incoming.append(
        IncomingMqttMessage(
            topic=controller.mqtt_topics.commands_request,
            payload={
                "schemaVersion": 1,
                "commandId": "outage-test-1",
                "deviceId": "healthband-device-001",
                "type": "SIMULATE_NETWORK_OUTAGE",
                "parameters": {"durationSec": 10},
            },
            duplicate=False,
            retained=False,
        )
    )

    await controller.process_mqtt_messages_now()

    assert controller.current_state == DeviceState.OFFLINE
    assert controller.current_scenario == SimulationScenario.RUNNING
    assert mqtt.connected is False

    # Simulate several local measurement + telemetry cycles during outage.
    for _ in range(8):
        await controller.read_sensors_now()
        await controller._publish_latest_telemetry(force=True)

    assert controller.latest_snapshot is not None
    after = controller.latest_snapshot
    after_hr = float(after.measurements["heartRateBpm"])
    after_steps = int(after.measurements["totalDailySteps"])
    after_battery = float(after.measurements["batteryPercentage"])

    assert after.scenario == SimulationScenario.RUNNING.value
    assert after.activity_level == "HIGH"
    assert after_hr > before_hr
    assert after_steps > before_steps
    assert after_battery < before_battery
    assert queue.size() > 0

    persisted = queue.database.get_state(controller.RUNTIME_STATE_KEY)
    assert persisted is not None
    assert '"physiologicalScenario":"RUNNING"' in persisted
    assert '"deviceState":"OFFLINE"' in persisted

    await controller.shutdown()


@pytest.mark.asyncio
async def test_offline_messages_are_synchronized_after_connection_returns(
    tmp_path: Path,
) -> None:
    mqtt = (
        FakeMqttClient()
    )

    queue = (
        create_queue(
            tmp_path
        )
    )

    controller = (
        DeviceController(
            event_bus=EventBus(),
            scheduler=Scheduler(),
            random_seed=1,
            mqtt_client=mqtt,  # type: ignore[arg-type]
            offline_queue=queue,
        )
    )

    await controller.start()

    mqtt.connected = (
        False
    )

    await controller.read_sensors_now()

    await (
        controller
        ._publish_latest_telemetry(
            force=True
        )
    )

    assert (
        queue.size()
        > 0
    )

    mqtt.connected = (
        True
    )

    result = (
        await controller
        .synchronize_offline_queue_now()
    )

    assert (
        result is not None
    )

    assert (
        result.remaining
        == 0
    )

    assert (
        queue.size()
        == 0
    )

    await controller.shutdown()


@pytest.mark.asyncio
async def test_health_report_contains_offline_queue_size(
    tmp_path: Path,
) -> None:
    mqtt = (
        FakeMqttClient()
    )

    queue = (
        create_queue(
            tmp_path
        )
    )

    controller = (
        DeviceController(
            event_bus=EventBus(),
            scheduler=Scheduler(),
            random_seed=1,
            mqtt_client=mqtt,  # type: ignore[arg-type]
            offline_queue=queue,
        )
    )

    await controller.start()

    mqtt.connected = (
        False
    )

    await controller.read_sensors_now()

    await (
        controller
        ._publish_latest_telemetry(
            force=True
        )
    )

    report = (
        await controller
        .create_health_report_now()
    )

    assert (
        report.offline_queue_size
        >= 1
    )

    assert (
        report.mqtt_connected
        is False
    )

    await controller.shutdown()

@pytest.mark.asyncio
async def test_simulated_outage_reconnect_keeps_activity_and_flushes_queue(
    tmp_path: Path,
) -> None:
    mqtt = FakeMqttClient()
    queue = create_queue(tmp_path)
    controller = DeviceController(
        event_bus=EventBus(),
        scheduler=Scheduler(),
        random_seed=11,
        mqtt_client=mqtt,  # type: ignore[arg-type]
        offline_queue=queue,
    )

    await controller.start()
    controller.change_scenario(SimulationScenario.RUNNING)
    for _ in range(6):
        await controller.read_sensors_now()

    await controller._begin_simulated_network_outage(duration_sec=40.0)
    assert controller.current_state == DeviceState.OFFLINE
    assert controller.current_scenario == SimulationScenario.RUNNING

    for _ in range(8):
        await controller.read_sensors_now()
        await controller._publish_latest_telemetry(force=True)
    assert queue.size() > 0

    before_reconnect_steps = int(
        controller.latest_snapshot.measurements["totalDailySteps"]  # type: ignore[union-attr]
    )

    # Expire the simulated outage and execute the same connection-watch path
    # used by the running device.
    controller._simulated_outage_until = 0.0
    await controller._connection_watch_tick()

    assert mqtt.connected is True
    assert controller.current_state == DeviceState.MONITORING
    assert controller.current_scenario == SimulationScenario.RUNNING
    assert queue.size() == 0

    after = await controller.read_sensors_now()
    assert after.scenario == "RUNNING"
    assert int(after.measurements["totalDailySteps"]) >= before_reconnect_steps

    persisted = queue.database.get_state(controller.RUNTIME_STATE_KEY)
    assert persisted is not None
    assert '"deviceState":"MONITORING"' in persisted

    await controller.shutdown()


@pytest.mark.asyncio
async def test_local_restore_network_request_cancels_outage_immediately(
    tmp_path: Path,
) -> None:
    mqtt = FakeMqttClient()
    queue = create_queue(tmp_path)
    controller = DeviceController(
        event_bus=EventBus(),
        scheduler=Scheduler(),
        random_seed=17,
        mqtt_client=mqtt,  # type: ignore[arg-type]
        offline_queue=queue,
    )

    await controller.start()
    controller.change_scenario(SimulationScenario.RUNNING)
    await controller._begin_simulated_network_outage(duration_sec=120.0)

    assert controller.current_state == DeviceState.OFFLINE
    assert mqtt.connected is False

    queue.database.set_state(
        controller.LOCAL_NETWORK_RESTORE_KEY,
        __import__("json").dumps(
            {
                "schemaVersion": 1,
                "commandId": "restore-now-1",
                "deviceId": controller.device_id,
                "type": "RESTORE_NETWORK",
                "status": "REQUESTED",
                "requestedAt": "2026-09-04T00:00:00+00:00",
            }
        ),
    )

    # The configured outage still has almost two minutes remaining, but the
    # local control request must bypass that timeout on this tick.
    await controller._connection_watch_tick()

    assert mqtt.connected is True
    assert controller.current_state == DeviceState.MONITORING
    assert controller.current_scenario == SimulationScenario.RUNNING
    assert controller._simulated_outage_until is None

    raw = queue.database.get_state(controller.LOCAL_NETWORK_RESTORE_KEY)
    assert raw is not None
    persisted = __import__("json").loads(raw)
    assert persisted["status"] == "SUCCEEDED"
    assert persisted["commandId"] == "restore-now-1"

    responses = [
        payload
        for topic, payload, _qos in mqtt.published
        if topic == controller.mqtt_topics.commands_response
        and payload.get("commandId") == "restore-now-1"
    ]
    assert responses
    assert responses[-1]["status"] == "SUCCEEDED"

    await controller.shutdown()
