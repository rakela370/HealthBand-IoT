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

    mqtt.incoming.append(
        IncomingMqttMessage(
            topic=(
                controller
                .mqtt_topics
                .commands_request
            ),
            payload={
                "schemaVersion": 1,
                "commandId": (
                    "outage-test-1"
                ),
                "deviceId": (
                    "healthband-device-001"
                ),
                "type": (
                    "SIMULATE_NETWORK_OUTAGE"
                ),
                "parameters": {
                    "durationSec": 10
                },
            },
            duplicate=False,
            retained=False,
        )
    )

    await (
        controller
        .process_mqtt_messages_now()
    )

    assert (
        controller.current_state
        == DeviceState.OFFLINE
    )

    assert (
        controller.current_scenario
        == SimulationScenario.NETWORK_OUTAGE
    )

    assert (
        mqtt.connected
        is False
    )

    before = (
        controller.latest_snapshot
    )

    after = (
        await controller
        .read_sensors_now()
    )

    assert (
        after is not None
    )

    assert (
        after
        is not before
    )

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