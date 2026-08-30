"""SQLite infrastructure used by the HealthBand simulator."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class LocalDatabase:
    """Own the local SQLite database used by HealthBand."""

    def __init__(
        self,
        database_path: Path | str,
    ) -> None:
        self.database_path = Path(
            database_path
        ).resolve()

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._initialize_schema()

    def ping(self) -> bool:
        """Verify that SQLite database can be opened and queried."""

        with self.connection() as connection:
            row = connection.execute(
                "SELECT 1 AS value"
            ).fetchone()

        return (
            row is not None
            and row["value"] == 1
        )

    @property
    def size_bytes(self) -> int:
        """Return current SQLite database file size."""

        if not self.database_path.exists():
            return 0

        return (
            self.database_path.stat().st_size
        )

    @contextmanager
    def connection(
        self,
    ) -> Iterator[sqlite3.Connection]:
        """Open one configured SQLite connection."""

        connection = sqlite3.connect(
            self.database_path,
            timeout=10.0,
        )

        connection.row_factory = (
            sqlite3.Row
        )

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        connection.execute(
            "PRAGMA journal_mode = WAL"
        )

        try:
            yield connection

        finally:
            connection.close()

    @contextmanager
    def transaction(
        self,
    ) -> Iterator[sqlite3.Connection]:
        """Open one explicit write transaction."""

        with self.connection() as connection:
            try:
                connection.execute(
                    "BEGIN IMMEDIATE"
                )

                yield connection

                connection.commit()

            except Exception:
                connection.rollback()
                raise

    def fetch_one(
        self,
        query: str,
        parameters: tuple[Any, ...] = (),
    ) -> sqlite3.Row | None:
        """Execute SELECT and return one row."""

        with self.connection() as connection:
            return connection.execute(
                query,
                parameters,
            ).fetchone()

    def fetch_all(
        self,
        query: str,
        parameters: tuple[Any, ...] = (),
    ) -> list[sqlite3.Row]:
        """Execute SELECT and return all rows."""

        with self.connection() as connection:
            rows = connection.execute(
                query,
                parameters,
            ).fetchall()

        return list(
            rows
        )

    def get_state(
        self,
        key: str,
    ) -> str | None:
        """Return one small persisted runtime-state value."""

        row = self.fetch_one(
            """
            SELECT value
            FROM local_state
            WHERE key = ?
            """,
            (
                key,
            ),
        )

        if row is None:
            return None

        return str(
            row["value"]
        )

    def set_state(
        self,
        key: str,
        value: str,
    ) -> None:
        """Insert or replace one small persisted runtime-state value."""

        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO local_state (
                    key,
                    value,
                    updated_at
                )
                VALUES (?, ?, ?)

                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (
                    key,
                    value,
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
                ),
            )

    def _initialize_schema(
        self,
    ) -> None:
        """Create all HealthBand SQLite objects."""

        with self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS offline_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    original_timestamp TEXT NOT NULL,

                    message_id TEXT NOT NULL UNIQUE,
                    message_type TEXT NOT NULL,

                    topic TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    qos INTEGER NOT NULL,

                    priority INTEGER NOT NULL,

                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'PENDING',

                    last_error TEXT,

                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS
                    idx_offline_messages_sync_order
                ON offline_messages (
                    priority ASC,
                    original_timestamp ASC,
                    id ASC
                );

                CREATE INDEX IF NOT EXISTS
                    idx_offline_messages_status
                ON offline_messages (
                    status
                );

                CREATE INDEX IF NOT EXISTS
                    idx_offline_messages_type
                ON offline_messages (
                    message_type
                );

                CREATE TABLE IF NOT EXISTS local_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

            connection.commit()