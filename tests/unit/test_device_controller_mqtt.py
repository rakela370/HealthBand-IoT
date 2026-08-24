"""MQTT tests for DeviceController."""

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


class FakeMqttClient:
    """In-memory MQTT replacement."""

    def __init__(
        self,
    ) -> None:
        self.connected = False

        self.subscriptions: list[
            tuple[str, int]
        ] = []

        self.published: list[
            tuple[
                str,
                dict[str, Any],
                int,
            ]
        ] = []

        self.incoming: list[
            IncomingMqttMessage
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

        return "fake-message-id"

    def drain_incoming_messages(
        self,
        maximum_items: int = 100,
    ) -> list[IncomingMqttMessage]:
        result = (
            self.incoming[
                :maximum_items
            ]
        )

        del self.incoming[
            :maximum_items
        ]

        return result


@pytest.mark.asyncio
async def test_controller_connects_and_publishes_cloud_data() -> None:
    mqtt_client = (
        FakeMqttClient()
    )

    controller = DeviceController(
        event_bus=EventBus(),
        scheduler=Scheduler(),
        random_seed=1,
        mqtt_client=mqtt_client,  # type: ignore[arg-type]
    )

    await controller.start()

    assert mqtt_client.connected is True

    assert (
        (
            controller.mqtt_topics.commands_request,
            1,
        )
        in mqtt_client.subscriptions
    )

    published_topics = [
        topic
        for topic, _, _
        in mqtt_client.published
    ]

    assert (
        controller.mqtt_topics.telemetry
        in published_topics
    )

    assert (
        controller.mqtt_topics.health
        in published_topics
    )

    assert (
        controller.mqtt_topics.events
        in published_topics
    )

    assert (
        controller.mqtt_topics.presence
        in published_topics
    )

    await controller.shutdown()

    assert mqtt_client.connected is False


@pytest.mark.asyncio
async def test_valid_command_gets_complete_status_flow() -> None:
    mqtt_client = (
        FakeMqttClient()
    )

    controller = DeviceController(
        event_bus=EventBus(),
        scheduler=Scheduler(),
        random_seed=1,
        mqtt_client=mqtt_client,  # type: ignore[arg-type]
    )

    await controller.start()

    mqtt_client.incoming.append(
        IncomingMqttMessage(
            topic=(
                controller
                .mqtt_topics
                .commands_request
            ),
            payload={
                "schemaVersion": 1,
                "commandId": (
                    "module5-test-001"
                ),
                "deviceId": (
                    "healthband-device-001"
                ),
                "type": (
                    "REQUEST_DEVICE_HEALTH"
                ),
                "parameters": {},
            },
            duplicate=False,
            retained=False,
        )
    )

    await (
        controller
        .process_mqtt_messages_now()
    )

    responses = [
        payload
        for topic, payload, _
        in mqtt_client.published
        if (
            topic
            == controller
            .mqtt_topics
            .commands_response
        )
    ]

    statuses = [
        response[
            "status"
        ]
        for response in responses
        if (
            response[
                "commandId"
            ]
            == "module5-test-001"
        )
    ]

    assert statuses == [
        "RECEIVED",
        "IN_PROGRESS",
        "SUCCEEDED",
    ]

    await controller.shutdown()