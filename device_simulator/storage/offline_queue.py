"""Persistent SQLite-backed queue for unsent HealthBand MQTT messages."""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from device_simulator.communication.message_serializer import (
    prepare_message,
)
from device_simulator.storage.local_database import (
    LocalDatabase,
)


class OfflineMessageType(StrEnum):
    """Outgoing message types stored while HealthBand is offline."""

    ALERT = "ALERT"
    COMMAND_RESPONSE = "COMMAND_RESPONSE"
    EVENT = "EVENT"
    ANALYTICS = "ANALYTICS"
    HEALTH = "HEALTH"
    TELEMETRY = "TELEMETRY"
    OTHER = "OTHER"


class OfflineMessageStatus(StrEnum):
    """Persistence status of one offline message."""

    PENDING = "PENDING"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class OfflineQueueItem:
    """One outgoing message persisted in SQLite."""

    database_id: int

    original_timestamp: str

    message_id: str
    message_type: OfflineMessageType

    topic: str
    payload: dict[str, Any]

    qos: int
    priority: int

    attempt_count: int
    status: OfflineMessageStatus

    last_error: str | None


@dataclass(frozen=True, slots=True)
class QueueInsertResult:
    """Result of one OfflineQueue enqueue attempt."""

    inserted: bool

    message_id: str

    queue_size: int

    dropped_message_id: str | None = None

    reason: str | None = None


class OfflineQueue:
    """Store and prioritize MQTT messages that could not be sent."""

    PRIORITIES: dict[
        OfflineMessageType,
        int,
    ] = {
        OfflineMessageType.ALERT: 1,
        OfflineMessageType.COMMAND_RESPONSE: 1,
        OfflineMessageType.EVENT: 2,
        OfflineMessageType.ANALYTICS: 3,
        OfflineMessageType.HEALTH: 4,
        OfflineMessageType.TELEMETRY: 5,
        OfflineMessageType.OTHER: 6,
    }

    def __init__(
        self,
        database: LocalDatabase,
        maximum_items: int = 5000,
    ) -> None:
        if maximum_items <= 0:
            raise ValueError(
                "OfflineQueue maximum_items must be positive."
            )

        self.database = (
            database
        )

        self.maximum_items = (
            maximum_items
        )

    @property
    def database_size_bytes(
        self,
    ) -> int:
        """Return SQLite database size."""

        return (
            self.database.size_bytes
        )

    def size(
        self,
    ) -> int:
        """Return number of queued messages."""

        row = self.database.fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM offline_messages
            """
        )

        if row is None:
            return 0

        return int(
            row["total"]
        )

    def is_near_limit(
        self,
        threshold_fraction: float = 0.80,
    ) -> bool:
        """Return whether queue has reached a configured fraction."""

        if not (
            0.0
            < threshold_fraction
            <= 1.0
        ):
            raise ValueError(
                "threshold_fraction must be in range (0, 1]."
            )

        return (
            self.size()
            >= (
                self.maximum_items
                * threshold_fraction
            )
        )

    def count_by_type(
        self,
    ) -> dict[str, int]:
        """Return queued item count grouped by message type."""

        rows = self.database.fetch_all(
            """
            SELECT
                message_type,
                COUNT(*) AS total
            FROM offline_messages
            GROUP BY message_type
            ORDER BY message_type
            """
        )

        return {
            str(
                row["message_type"]
            ): int(
                row["total"]
            )
            for row in rows
        }

    def enqueue(
        self,
        message_type: OfflineMessageType,
        topic: str,
        payload: dict[str, Any],
        qos: int,
    ) -> QueueInsertResult:
        """Persist one outgoing MQTT message."""

        if qos not in {
            0,
            1,
        }:
            raise ValueError(
                "OfflineQueue supports MQTT QoS 0 or QoS 1."
            )

        prepared = (
            prepare_message(
                payload
            )
        )

        message_id = str(
            prepared[
                "messageId"
            ]
        )

        original_timestamp = str(
            prepared[
                "timestamp"
            ]
        )

        serialized_payload = json.dumps(
            prepared,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )

        priority = (
            self.PRIORITIES[
                message_type
            ]
        )

        dropped_message_id: (
            str | None
        ) = None

        with self.database.transaction() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM offline_messages
                WHERE message_id = ?
                """,
                (
                    message_id,
                ),
            ).fetchone()

            if existing is not None:
                count = connection.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM offline_messages
                    """
                ).fetchone()

                return QueueInsertResult(
                    inserted=False,
                    message_id=message_id,
                    queue_size=int(
                        count["total"]
                    ),
                    reason=(
                        "Message with the same "
                        "messageId is already queued."
                    ),
                )

            count_row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM offline_messages
                """
            ).fetchone()

            current_size = int(
                count_row[
                    "total"
                ]
            )

            if (
                current_size
                >= self.maximum_items
            ):
                candidate = (
                    self._find_eviction_candidate(
                        connection=connection,
                        new_priority=priority,
                    )
                )

                if candidate is None:
                    return QueueInsertResult(
                        inserted=False,
                        message_id=message_id,
                        queue_size=current_size,
                        reason=(
                            "OfflineQueue is full and "
                            "contains no lower-priority "
                            "message that can be removed."
                        ),
                    )

                dropped_message_id = str(
                    candidate[
                        "message_id"
                    ]
                )

                connection.execute(
                    """
                    DELETE FROM offline_messages
                    WHERE id = ?
                    """,
                    (
                        int(
                            candidate[
                                "id"
                            ]
                        ),
                    ),
                )

            connection.execute(
                """
                INSERT INTO offline_messages (
                    original_timestamp,
                    message_id,
                    message_type,
                    topic,
                    payload,
                    qos,
                    priority,
                    attempt_count,
                    status,
                    last_error,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, NULL, ?)
                """,
                (
                    original_timestamp,
                    message_id,
                    message_type.value,
                    topic,
                    serialized_payload,
                    qos,
                    priority,
                    OfflineMessageStatus.PENDING.value,
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
                ),
            )

            final_count_row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM offline_messages
                """
            ).fetchone()

            final_size = int(
                final_count_row[
                    "total"
                ]
            )

        return QueueInsertResult(
            inserted=True,
            message_id=message_id,
            queue_size=final_size,
            dropped_message_id=(
                dropped_message_id
            ),
        )

    def get_for_synchronization(
        self,
        limit: int = 100,
    ) -> list[OfflineQueueItem]:
        """Read messages in synchronization priority order."""

        if limit <= 0:
            raise ValueError(
                "limit must be positive."
            )

        rows = self.database.fetch_all(
            """
            SELECT
                id,
                original_timestamp,
                message_id,
                message_type,
                topic,
                payload,
                qos,
                priority,
                attempt_count,
                status,
                last_error
            FROM offline_messages
            WHERE status IN ('PENDING', 'FAILED')
            ORDER BY
                priority ASC,
                original_timestamp ASC,
                id ASC
            LIMIT ?
            """,
            (
                limit,
            ),
        )

        items: list[
            OfflineQueueItem
        ] = []

        for row in rows:
            items.append(
                OfflineQueueItem(
                    database_id=int(
                        row[
                            "id"
                        ]
                    ),
                    original_timestamp=str(
                        row[
                            "original_timestamp"
                        ]
                    ),
                    message_id=str(
                        row[
                            "message_id"
                        ]
                    ),
                    message_type=(
                        OfflineMessageType(
                            row[
                                "message_type"
                            ]
                        )
                    ),
                    topic=str(
                        row[
                            "topic"
                        ]
                    ),
                    payload=json.loads(
                        row[
                            "payload"
                        ]
                    ),
                    qos=int(
                        row[
                            "qos"
                        ]
                    ),
                    priority=int(
                        row[
                            "priority"
                        ]
                    ),
                    attempt_count=int(
                        row[
                            "attempt_count"
                        ]
                    ),
                    status=(
                        OfflineMessageStatus(
                            row[
                                "status"
                            ]
                        )
                    ),
                    last_error=(
                        row[
                            "last_error"
                        ]
                    ),
                )
            )

        return items

    def remove(
        self,
        database_id: int,
    ) -> None:
        """Delete successfully synchronized message."""

        with self.database.transaction() as connection:
            connection.execute(
                """
                DELETE FROM offline_messages
                WHERE id = ?
                """,
                (
                    database_id,
                ),
            )

    def mark_failed(
        self,
        database_id: int,
        error: str,
    ) -> None:
        """Increment send attempts and remember synchronization error."""

        with self.database.transaction() as connection:
            connection.execute(
                """
                UPDATE offline_messages
                SET
                    attempt_count = attempt_count + 1,
                    status = ?,
                    last_error = ?
                WHERE id = ?
                """,
                (
                    OfflineMessageStatus.FAILED.value,
                    error,
                    database_id,
                ),
            )

    def update_maximum_items(
        self,
        maximum_items: int,
    ) -> None:
        """Apply new queue capacity and trim lowest-priority items."""

        if maximum_items <= 0:
            raise ValueError(
                "maximum_items must be positive."
            )

        self.maximum_items = (
            maximum_items
        )

        with self.database.transaction() as connection:
            while True:
                count_row = connection.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM offline_messages
                    """
                ).fetchone()

                current_size = int(
                    count_row[
                        "total"
                    ]
                )

                if (
                    current_size
                    <= self.maximum_items
                ):
                    break

                candidate = connection.execute(
                    """
                    SELECT
                        id,
                        message_id
                    FROM offline_messages
                    ORDER BY
                        priority DESC,
                        id ASC
                    LIMIT 1
                    """
                ).fetchone()

                if candidate is None:
                    break

                connection.execute(
                    """
                    DELETE FROM offline_messages
                    WHERE id = ?
                    """,
                    (
                        int(
                            candidate[
                                "id"
                            ]
                        ),
                    ),
                )

    def clear(
        self,
    ) -> None:
        """Remove all queued messages. Intended mainly for tests."""

        with self.database.transaction() as connection:
            connection.execute(
                """
                DELETE FROM offline_messages
                """
            )

    def _find_eviction_candidate(
        self,
        connection: Any,
        new_priority: int,
    ) -> Any:
        """
        Choose which existing message may be discarded.

        Old raw telemetry is discarded first. If no telemetry exists,
        a message less important than the new message may be removed.
        """

        telemetry = connection.execute(
            """
            SELECT
                id,
                message_id
            FROM offline_messages
            WHERE message_type = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (
                OfflineMessageType.TELEMETRY.value,
            ),
        ).fetchone()

        if telemetry is not None:
            return telemetry

        return connection.execute(
            """
            SELECT
                id,
                message_id
            FROM offline_messages
            WHERE priority > ?
            ORDER BY
                priority DESC,
                id ASC
            LIMIT 1
            """,
            (
                new_priority,
            ),
        ).fetchone()