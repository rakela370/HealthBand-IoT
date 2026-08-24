"""Synchronization of locally queued MQTT data after reconnect."""

import logging
from dataclasses import dataclass
from typing import Protocol

from device_simulator.storage.offline_queue import (
    OfflineQueue,
)


logger = logging.getLogger(__name__)


class MqttPublisher(Protocol):
    """Minimal MQTT interface required by SynchronizationManager."""

    @property
    def is_connected(
        self,
    ) -> bool:
        ...

    def publish(
        self,
        topic: str,
        payload: dict[str, object],
        qos: int,
    ) -> str:
        ...


@dataclass(frozen=True, slots=True)
class SynchronizationResult:
    """Summary of one offline synchronization pass."""

    attempted: int
    sent: int
    failed: int
    remaining: int


class SynchronizationManager:
    """Send queued MQTT messages after connectivity is restored."""

    def __init__(
        self,
        offline_queue: OfflineQueue,
        mqtt_client: MqttPublisher,
    ) -> None:
        self.offline_queue = (
            offline_queue
        )

        self.mqtt_client = (
            mqtt_client
        )

    def synchronize(
        self,
        maximum_items: int = 1000,
    ) -> SynchronizationResult:
        """Synchronize queued messages according to queue priority."""

        if maximum_items <= 0:
            raise ValueError(
                "maximum_items must be positive."
            )

        if not self.mqtt_client.is_connected:
            return SynchronizationResult(
                attempted=0,
                sent=0,
                failed=0,
                remaining=(
                    self.offline_queue.size()
                ),
            )

        items = (
            self.offline_queue
            .get_for_synchronization(
                limit=maximum_items
            )
        )

        attempted = 0
        sent = 0
        failed = 0

        for item in items:
            if not self.mqtt_client.is_connected:
                break

            attempted += 1

            try:
                self.mqtt_client.publish(
                    topic=item.topic,
                    payload=item.payload,
                    qos=item.qos,
                )

                self.offline_queue.remove(
                    item.database_id
                )

                sent += 1

                logger.info(
                    "Offline sync sent | "
                    "type=%s | "
                    "messageId=%s | "
                    "topic=%s",
                    item.message_type.value,
                    item.message_id,
                    item.topic,
                )

            except Exception as exc:
                failed += 1

                self.offline_queue.mark_failed(
                    database_id=(
                        item.database_id
                    ),
                    error=str(
                        exc
                    ),
                )

                logger.warning(
                    "Offline sync failed | "
                    "type=%s | "
                    "messageId=%s | "
                    "error=%s",
                    item.message_type.value,
                    item.message_id,
                    exc,
                )

                # If one MQTT send fails, continuing to send hundreds
                # of subsequent messages is usually counterproductive.
                break

        return SynchronizationResult(
            attempted=attempted,
            sent=sent,
            failed=failed,
            remaining=(
                self.offline_queue.size()
            ),
        )