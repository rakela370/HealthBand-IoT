"""Tests for HealthBand local SQLite database."""

from pathlib import Path

from device_simulator.storage.local_database import (
    LocalDatabase,
)


def test_database_is_created_and_available(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "healthband.db"
    )

    database = (
        LocalDatabase(
            path
        )
    )

    assert (
        path.exists()
    )

    assert (
        database.ping()
        is True
    )