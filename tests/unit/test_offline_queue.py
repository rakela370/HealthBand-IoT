"""Tests for persistent HealthBand OfflineQueue."""

from pathlib import Path

from device_simulator.storage.local_database import (
    LocalDatabase,
)
from device_simulator.storage.offline_queue import (
    OfflineMessageType,
    OfflineQueue,
)


def create_queue(
    tmp_path: Path,
    maximum_items: int = 10,
) -> OfflineQueue:
    database = (
        LocalDatabase(
            tmp_path
            / "healthband.db"
        )
    )

    return OfflineQueue(
        database=database,
        maximum_items=(
            maximum_items
        ),
    )


def test_message_is_persisted_with_required_fields(
    tmp_path: Path,
) -> None:
    queue = (
        create_queue(
            tmp_path
        )
    )

    result = queue.enqueue(
        message_type=(
            OfflineMessageType.TELEMETRY
        ),
        topic=(
            "healthband/test/telemetry"
        ),
        payload={
            "messageId": "message-1",
            "timestamp": (
                "2026-08-24T10:00:00+00:00"
            ),
            "value": 123,
        },
        qos=0,
    )

    assert result.inserted is True

    items = (
        queue.get_for_synchronization()
    )

    assert len(
        items
    ) == 1

    item = (
        items[0]
    )

    assert (
        item.message_id
        == "message-1"
    )

    assert (
        item.original_timestamp
        == "2026-08-24T10:00:00+00:00"
    )

    assert (
        item.topic
        == "healthband/test/telemetry"
    )

    assert item.qos == 0

    assert (
        item.attempt_count
        == 0
    )

    assert (
        item.status.value
        == "PENDING"
    )


def test_duplicate_message_id_is_not_inserted_twice(
    tmp_path: Path,
) -> None:
    queue = (
        create_queue(
            tmp_path
        )
    )

    payload = {
        "messageId": "duplicate-1",
        "timestamp": (
            "2026-08-24T10:00:00+00:00"
        ),
    }

    first = queue.enqueue(
        OfflineMessageType.EVENT,
        "healthband/test/events",
        payload,
        1,
    )

    second = queue.enqueue(
        OfflineMessageType.EVENT,
        "healthband/test/events",
        payload,
        1,
    )

    assert first.inserted is True

    assert second.inserted is False

    assert queue.size() == 1


def test_sync_order_uses_message_priority(
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
        OfflineMessageType.ANALYTICS,
        "analytics",
        {
            "messageId": "analytics-1",
            "timestamp": (
                "2026-08-24T10:00:01+00:00"
            ),
        },
        1,
    )

    queue.enqueue(
        OfflineMessageType.ALERT,
        "alerts",
        {
            "messageId": "alert-1",
            "timestamp": (
                "2026-08-24T10:00:02+00:00"
            ),
        },
        1,
    )

    items = (
        queue.get_for_synchronization()
    )

    assert [
        item.message_type
        for item in items
    ] == [
        OfflineMessageType.ALERT,
        OfflineMessageType.ANALYTICS,
        OfflineMessageType.TELEMETRY,
    ]


def test_full_queue_discards_old_telemetry_for_alert(
    tmp_path: Path,
) -> None:
    queue = (
        create_queue(
            tmp_path,
            maximum_items=2,
        )
    )

    queue.enqueue(
        OfflineMessageType.TELEMETRY,
        "telemetry",
        {
            "messageId": "old-telemetry",
            "timestamp": (
                "2026-08-24T10:00:00+00:00"
            ),
        },
        0,
    )

    queue.enqueue(
        OfflineMessageType.HEALTH,
        "health",
        {
            "messageId": "health-1",
            "timestamp": (
                "2026-08-24T10:00:01+00:00"
            ),
        },
        1,
    )

    result = queue.enqueue(
        OfflineMessageType.ALERT,
        "alerts",
        {
            "messageId": "alert-1",
            "timestamp": (
                "2026-08-24T10:00:02+00:00"
            ),
        },
        1,
    )

    assert result.inserted is True

    assert (
        result.dropped_message_id
        == "old-telemetry"
    )

    ids = {
        item.message_id
        for item
        in queue.get_for_synchronization()
    }

    assert (
        "old-telemetry"
        not in ids
    )

    assert (
        "alert-1"
        in ids
    )


def test_new_telemetry_replaces_old_telemetry_when_full(
    tmp_path: Path,
) -> None:
    queue = (
        create_queue(
            tmp_path,
            maximum_items=1,
        )
    )

    queue.enqueue(
        OfflineMessageType.TELEMETRY,
        "telemetry",
        {
            "messageId": "telemetry-old",
            "timestamp": (
                "2026-08-24T10:00:00+00:00"
            ),
        },
        0,
    )

    queue.enqueue(
        OfflineMessageType.TELEMETRY,
        "telemetry",
        {
            "messageId": "telemetry-new",
            "timestamp": (
                "2026-08-24T10:00:10+00:00"
            ),
        },
        0,
    )

    items = (
        queue.get_for_synchronization()
    )

    assert len(
        items
    ) == 1

    assert (
        items[0].message_id
        == "telemetry-new"
    )