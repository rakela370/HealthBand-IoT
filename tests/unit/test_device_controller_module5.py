"""Module 5 DeviceController tests."""

from typing import Any

import pytest

from device_simulator.communication.mqtt_client import (
    IncomingMqttMessage,
)
from device_simulator.core.device_controller import (
    DeviceController,
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


class FakeMqttClient:
    """Small MQTT fake used by Module 5 tests."""

    def __init__(
        self,
    ) -> None:
        self.connected = False

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
        self.connected = True

    def disconnect(
        self,
    ) -> None:
        self.connected = False

    def subscribe(
        self,
        topic: str,
        qos: int = 1,
    ) -> None:
        del topic
        del qos

    def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        qos: int,
    ) -> str:
        self.published.append(
            (
                topic,
                payload,
                qos,
            )
        )

        return "test-message"

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

        return messages


@pytest.mark.asyncio
async def test_change_scenario_command_changes_device() -> None:
    mqtt = FakeMqttClient()

    controller = DeviceController(
        event_bus=EventBus(),
        scheduler=Scheduler(),
        random_seed=1,
        mqtt_client=mqtt,  # type: ignore[arg-type]
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
                "commandId": "scenario-1",
                "type": (
                    "CHANGE_SIMULATION_SCENARIO"
                ),
                "parameters": {
                    "scenario": "RUNNING"
                },
            },
            duplicate=False,
            retained=False,
        )
    )

    await controller.process_mqtt_messages_now()

    assert (
        controller.current_scenario
        == SimulationScenario.RUNNING
    )

    await controller.shutdown()


@pytest.mark.asyncio
async def test_duplicate_command_returns_cached_result() -> None:
    mqtt = FakeMqttClient()

    controller = DeviceController(
        event_bus=EventBus(),
        scheduler=Scheduler(),
        random_seed=1,
        mqtt_client=mqtt,  # type: ignore[arg-type]
    )

    await controller.start()

    message = IncomingMqttMessage(
        topic=(
            controller
            .mqtt_topics
            .commands_request
        ),
        payload={
            "commandId": "duplicate-1",
            "type": (
                "CHANGE_SIMULATION_SCENARIO"
            ),
            "parameters": {
                "scenario": "RUNNING"
            },
        },
        duplicate=False,
        retained=False,
    )

    mqtt.incoming.append(
        message
    )

    await controller.process_mqtt_messages_now()

    mqtt.incoming.append(
        message
    )

    await controller.process_mqtt_messages_now()

    responses = [
        payload
        for topic, payload, _
        in mqtt.published
        if (
            topic
            == controller
            .mqtt_topics
            .commands_response
            and payload[
                "commandId"
            ]
            == "duplicate-1"
        )
    ]

    assert len(
        responses
    ) == 4

    assert (
        responses[-1][
            "duplicate"
        ]
        is True
    )

    await controller.shutdown()


@pytest.mark.asyncio
async def test_configuration_changes_scheduler_intervals() -> None:
    controller = DeviceController(
        event_bus=EventBus(),
        scheduler=Scheduler(),
        random_seed=1,
    )

    await controller.start()

    applied = (
        await controller.apply_configuration_delta_now(
            {
                "measurementIntervalSec": 4,
                "telemetryIntervalSec": 8,
                "healthReportIntervalSec": 10,
            }
        )
    )

    assert applied is True

    assert (
        controller.scheduler
        .get_periodic_job_interval(
            "sensor-reading"
        )
        == 4
    )

    assert (
        controller.scheduler
        .get_periodic_job_interval(
            "telemetry-publish"
        )
        == 8
    )

    assert (
        controller.scheduler
        .get_periodic_job_interval(
            "device-health"
        )
        == 10
    )

    await controller.shutdown()


@pytest.mark.asyncio
async def test_fahrenheit_configuration_changes_external_telemetry() -> None:
    controller = DeviceController(
        event_bus=EventBus(),
        scheduler=Scheduler(),
        random_seed=1,
    )

    await controller.start()

    applied = (
        await controller.apply_configuration_delta_now(
            {
                "temperatureUnit": "FAHRENHEIT"
            }
        )
    )

    assert applied is True

    snapshot = (
        await controller.read_sensors_now()
    )

    payload = (
        controller
        ._build_telemetry_payload(
            snapshot
        )
    )

    measurements = (
        payload[
            "measurements"
        ]
    )

    assert (
        measurements[
            "temperatureUnit"
        ]
        == "FAHRENHEIT"
    )

    assert (
        measurements[
            "skinTemperature"
        ]
        > 80
    )

    assert (
        "skinTemperatureCelsius"
        not in measurements
    )

    await controller.shutdown()