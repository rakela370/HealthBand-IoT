"""Tests for backend history period resolution."""

from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest

from control_backend.services.time_range import (
    resolve_time_range,
)


def test_one_hour_period() -> None:
    now = datetime(
        2026,
        8,
        25,
        10,
        0,
        tzinfo=timezone.utc,
    )

    start, end = (
        resolve_time_range(
            period="1h",
            now=now,
        )
    )

    assert end == now

    assert (
        end - start
        == timedelta(
            hours=1
        )
    )


def test_custom_range() -> None:
    start, end = (
        resolve_time_range(
            start=(
                "2026-08-01T00:00:00Z"
            ),
            end=(
                "2026-08-02T00:00:00Z"
            ),
        )
    )

    assert (
        end - start
        == timedelta(
            days=1
        )
    )


def test_unknown_period_is_rejected() -> None:
    with pytest.raises(
        ValueError
    ):
        resolve_time_range(
            period="90d"
        )


def test_invalid_custom_order_is_rejected() -> None:
    with pytest.raises(
        ValueError
    ):
        resolve_time_range(
            start=(
                "2026-08-02T00:00:00Z"
            ),
            end=(
                "2026-08-01T00:00:00Z"
            ),
        )