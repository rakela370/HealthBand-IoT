"""Tests for offline MQTT synchronization."""

from pathlib import Path
from typing import Any

from device_simulator.storage.local_database import (
    LocalDatabase,
)
from device_simulator.storage.offline_queue import (
    OfflineMessageType,
    OfflineQueue,
)
from device_simulator.storage.synchronization_manager import (
    SynchronizationManager,
)


class FakePublisher:
    """Minimal MQTT publisher used by synchronization tests."""

    def __init__(
        self,
    ) -> None:
        self.connected = (
            True
        )

        self.fail = (
            False
        )

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

    def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        qos: int,
    ) -> str:
        if self.fail:
            raise ConnectionError(
                "Simulated publish failure."
            )

        self.published.append(
            (
                topic,
                payload,
                qos,
            )
        )

        return str(
            payload[
                "messageId"
            ]
        )


def create_queue(
    tmp_path: Path,
) -> OfflineQueue:
    return OfflineQueue(
        LocalDatabase(
            tmp_path
            / "healthband.db"
        ),
        maximum_items=100,
    )


def test_synchronization_sends_priority_first_and_removes_items(
    tmp_path: Path,
) -> None:
    queue = (
        create_queue(
            tmp_path
        )
    )

    queue.enqueue(
        OfflineMessageType.TELEMETRY,
        "telemetry",
        {
            "messageId": "telemetry-1",
            "timestamp": (
                "2026-08-24T10:00:00+00:00"
            ),
        },
        0,
    )

    queue.enqueue(
        OfflineMessageType.ALERT,
        "alerts",
        {
            "messageId": "alert-1",
            "timestamp": (
                "2026-08-24T10:00:01+00:00"
            ),
        },
        1,
    )

    mqtt = (
        FakePublisher()
    )

    manager = (
        SynchronizationManager(
            offline_queue=queue,
            mqtt_client=mqtt,
        )
    )

    result = (
        manager.synchronize()
    )

    assert result.sent == 2

    assert result.failed == 0

    assert result.remaining == 0

    assert [
        topic
        for (
            topic,
            _,
            _,
        )
        in mqtt.published
    ] == [
        "alerts",
        "telemetry",
    ]


def test_failed_sync_keeps_message_and_increments_attempts(
    tmp_path: Path,
) -> None:
    queue = (
        create_queue(
            tmp_path
        )
    )

    queue.enqueue(
        OfflineMessageType.EVENT,
        "events",
        {
            "messageId": "event-1",
            "timestamp": (
                "2026-08-24T10:00:00+00:00"
            ),
        },
        1,
    )

    mqtt = (
        FakePublisher()
    )

    mqtt.fail = (
        True
    )

    manager = (
        SynchronizationManager(
            offline_queue=queue,
            mqtt_client=mqtt,
        )
    )

    result = (
        manager.synchronize()
    )

    assert result.failed == 1

    assert result.remaining == 1

    item = (
        queue
        .get_for_synchronization()[0]
    )

    assert (
        item.attempt_count
        == 1
    )

    assert (
        item.status.value
        == "FAILED"
    )


def test_message_id_is_preserved_during_sync(
    tmp_path: Path,
) -> None:
    queue = (
        create_queue(
            tmp_path
        )
    )

    queue.enqueue(
        OfflineMessageType.ANALYTICS,
        "analytics",
        {
            "messageId": (
                "original-message-id"
            ),
            "timestamp": (
                "2026-08-24T10:00:00+00:00"
            ),
            "value": 123,
        },
        1,
    )

    mqtt = (
        FakePublisher()
    )

    manager = (
        SynchronizationManager(
            offline_queue=queue,
            mqtt_client=mqtt,
        )
    )

    manager.synchronize()

    assert (
        mqtt.published[0][1][
            "messageId"
        ]
        == "original-message-id"
    )