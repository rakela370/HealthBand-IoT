"""High-level MQTT client used by the HealthBand simulator."""

import logging
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any

from awscrt import mqtt

from device_simulator.communication.connection_manager import (
    AwsIotConnectionSettings,
    ConnectionManager,
)
from device_simulator.communication.message_serializer import (
    MessageSerializationError,
    deserialize_message,
    prepare_message,
    serialize_message,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IncomingMqttMessage:
    """One MQTT message received from AWS IoT Core."""

    topic: str
    payload: dict[str, Any]

    duplicate: bool
    retained: bool


class MqttClient:
    """Publish and receive HealthBand MQTT messages."""

    def __init__(
        self,
        settings: AwsIotConnectionSettings,
        connection_manager: (
            ConnectionManager | None
        ) = None,
    ) -> None:
        self.settings = settings

        self.connection_manager = (
            connection_manager
            or ConnectionManager(
                settings
            )
        )

        self._incoming_messages: Queue[
            IncomingMqttMessage
        ] = Queue()

        self._subscriptions: set[
            str
        ] = set()

    @property
    def is_connected(self) -> bool:
        """Return MQTT connection status."""

        return (
            self.connection_manager.is_connected
        )

    def connect(self) -> None:
        """Connect to AWS IoT Core."""

        self.connection_manager.connect()

    def disconnect(self) -> None:
        """Disconnect from AWS IoT Core."""

        self.connection_manager.disconnect()

    def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        qos: int,
    ) -> str:
        """
        Publish one JSON message.

        Returns the generated or existing messageId.
        """

        if not self.is_connected:
            raise ConnectionError(
                "Cannot publish because MQTT "
                "is not connected."
            )

        prepared = prepare_message(
            payload
        )

        serialized = serialize_message(
            prepared
        )

        publish_future, _ = (
            self.connection_manager
            .mqtt_connection
            .publish(
                topic=topic,
                payload=serialized,
                qos=self._to_qos(
                    qos
                ),
            )
        )

        publish_future.result(
            timeout=10
        )

        message_id = str(
            prepared["messageId"]
        )

        logger.debug(
            "MQTT published | "
            "topic=%s | qos=%s | messageId=%s",
            topic,
            qos,
            message_id,
        )

        return message_id

    def subscribe(
        self,
        topic: str,
        qos: int = 1,
    ) -> None:
        """Subscribe to one MQTT topic."""

        if not self.is_connected:
            raise ConnectionError(
                "Cannot subscribe because MQTT "
                "is not connected."
            )

        if topic in self._subscriptions:
            return

        subscribe_future, _ = (
            self.connection_manager
            .mqtt_connection
            .subscribe(
                topic=topic,
                qos=self._to_qos(
                    qos
                ),
                callback=(
                    self._on_message_received
                ),
            )
        )

        subscribe_future.result(
            timeout=10
        )

        self._subscriptions.add(
            topic
        )

        logger.info(
            "MQTT subscribed | topic=%s | qos=%s",
            topic,
            qos,
        )

    def drain_incoming_messages(
        self,
        maximum_items: int = 100,
    ) -> list[IncomingMqttMessage]:
        """Return currently queued inbound MQTT messages."""

        messages: list[
            IncomingMqttMessage
        ] = []

        while (
            len(messages)
            < maximum_items
        ):
            try:
                messages.append(
                    self._incoming_messages.get_nowait()
                )

            except Empty:
                break

        return messages

    def _on_message_received(
        self,
        topic: str,
        payload: bytes,
        dup: bool,
        qos: mqtt.QoS,
        retain: bool,
        **kwargs: Any,
    ) -> None:
        """
        Receive an AWS SDK callback.

        No blocking work is done here. The parsed message is placed
        into a queue and processed later by DeviceController.
        """

        del qos
        del kwargs

        try:
            parsed = deserialize_message(
                payload
            )

        except MessageSerializationError:
            logger.exception(
                "Rejected invalid MQTT payload "
                "received on topic '%s'.",
                topic,
            )
            return

        self._incoming_messages.put(
            IncomingMqttMessage(
                topic=topic,
                payload=parsed,
                duplicate=dup,
                retained=retain,
            )
        )

        logger.info(
            "MQTT message queued | topic=%s",
            topic,
        )

    @staticmethod
    def _to_qos(
        qos: int,
    ) -> mqtt.QoS:
        """Convert integer QoS into AWS CRT enum."""

        if qos == 0:
            return mqtt.QoS.AT_MOST_ONCE

        if qos == 1:
            return mqtt.QoS.AT_LEAST_ONCE

        raise ValueError(
            "HealthBand supports MQTT QoS 0 or QoS 1."
        )