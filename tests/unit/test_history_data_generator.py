"""Tests for HealthBand historical data generation."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from device_simulator.simulation.scenario import (
    SimulationScenario,
)
from scripts.create_history_data import (
    generate_history_items,
    scenario_for_datetime,
    to_dynamodb_compatible,
)


def contains_float(
    value: Any,
) -> bool:
    """Recursively detect Python float values."""

    if isinstance(
        value,
        float,
    ):
        return True

    if isinstance(
        value,
        dict,
    ):
        return any(
            contains_float(
                item
            )
            for item in value.values()
        )

    if isinstance(
        value,
        list,
    ):
        return any(
            contains_float(
                item
            )
            for item in value
        )

    return False


def test_one_day_generates_24_hourly_records() -> None:
    end_time = datetime(
        2026,
        8,
        24,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    items = (
        generate_history_items(
            days=1,
            device_id="test-device",
            seed=1,
            end_time=end_time,
        )
    )

    assert (
        len(
            items
        )
        == 24
    )


def test_history_records_are_marked_as_simulated() -> None:
    end_time = datetime(
        2026,
        8,
        24,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    items = (
        generate_history_items(
            days=1,
            device_id="test-device",
            seed=2,
            end_time=end_time,
        )
    )

    window_ends = {
        item[
            "windowEnd"
        ]
        for item in items
    }

    assert (
        len(
            window_ends
        )
        == 24
    )

    assert all(
        item[
            "simulated"
        ]
        is True
        for item in items
    )

    assert all(
        item[
            "historyGenerated"
        ]
        is True
        for item in items
    )


def test_scenario_schedule_contains_sleep_and_activity() -> None:
    sleeping_time = datetime(
        2026,
        8,
        24,
        2,
        0,
        tzinfo=timezone.utc,
    )

    walking_time = datetime(
        2026,
        8,
        24,
        8,
        0,
        tzinfo=timezone.utc,
    )

    assert (
        scenario_for_datetime(
            sleeping_time
        )
        == SimulationScenario.SLEEPING
    )

    assert (
        scenario_for_datetime(
            walking_time
        )
        == SimulationScenario.WALKING
    )


def test_dynamodb_conversion_removes_python_floats() -> None:
    value = {
        "average": 72.5,
        "nested": {
            "temperature": 33.7
        },
        "items": [
            1.25,
            2,
        ],
    }

    converted = (
        to_dynamodb_compatible(
            value
        )
    )

    assert (
        contains_float(
            converted
        )
        is False
    )

    assert isinstance(
        converted[
            "average"
        ],
        Decimal,
    )


def test_version2_history_contains_spo2_and_calorie_analytics() -> None:
    end_time = datetime(
        2026,
        8,
        24,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    items = (
        generate_history_items(
            days=1,
            device_id="test-device",
            seed=3,
            end_time=end_time,
        )
    )

    assert all(
        item[
            "softwareVersion"
        ]
        == "2.0.0"
        for item in items
    )

    assert any(
        "spo2"
        in item.get(
            "analytics",
            {},
        )
        for item in items
    )

    assert all(
        "calories"
        in item.get(
            "analytics",
            {},
        )
        for item in items
    )

    assert all(
        item.get(
            "analytics",
            {}
        )
        .get(
            "calories",
            {}
        )
        .get(
            "estimated"
        )
        is True
        for item in items
    )

    assert all(
        item.get(
            "analytics",
            {}
        )
        .get(
            "calories",
            {}
        )
        .get(
            "dailyTotalKcal",
            0
        )
        >= 0
        for item in items
    )