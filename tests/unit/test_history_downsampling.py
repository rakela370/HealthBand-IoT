"""Tests for long-range analytics history reduction."""

from datetime import datetime, timedelta, timezone

from control_backend.services.history_downsampling import (
    downsample_analytics_history,
)


def _item(timestamp: datetime, average: float, maximum: float) -> dict:
    return {
        "windowStart": (timestamp - timedelta(seconds=10)).isoformat(),
        "windowEnd": timestamp.isoformat(),
        "softwareVersion": "2.0.0",
        "analytics": {
            "heartRate": {
                "averageBpm": average,
                "minimumBpm": average - 2,
                "maximumBpm": maximum,
                "validSamples": 5,
                "rejectedSamples": 0,
                "thresholdExceedances": 0,
            },
            "skinTemperature": {
                "averageCelsius": 33.5,
                "minimumCelsius": 33.4,
                "maximumCelsius": 33.6,
                "validSamples": 5,
            },
            "steps": {
                "total": 2,
                "averagePerInterval": 0.4,
            },
            "battery": {
                "startPercentage": 90.0,
                "endPercentage": 89.9,
                "consumptionPercentage": 0.1,
            },
            "alertsGenerated": 0,
            "dataQualityPercentage": 100.0,
        },
    }


def test_downsampling_preserves_full_order_and_requested_bound() -> None:
    start = datetime(2026, 9, 13, 8, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=24)
    items = [
        _item(start + timedelta(minutes=index), 70 + index % 5, 75 + index % 5)
        for index in range(1440)
    ]

    reduced = downsample_analytics_history(
        items,
        start.isoformat(),
        end.isoformat(),
        max_points=120,
    )

    assert 0 < len(reduced) <= 120
    timestamps = [datetime.fromisoformat(item["windowEnd"]) for item in reduced]
    assert timestamps == sorted(timestamps)
    assert timestamps[0] >= start
    assert timestamps[-1] <= end


def test_downsampling_does_not_lose_heart_rate_peak() -> None:
    start = datetime(2026, 9, 13, 8, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    items = [
        _item(start + timedelta(seconds=index * 10), 72.0, 74.0)
        for index in range(360)
    ]
    items[240]["analytics"]["heartRate"]["maximumBpm"] = 190.0
    items[240]["analytics"]["heartRate"]["averageBpm"] = 181.0

    reduced = downsample_analytics_history(
        items,
        start.isoformat(),
        end.isoformat(),
        max_points=20,
    )

    maxima = [
        item["analytics"]["heartRate"]["maximumBpm"]
        for item in reduced
    ]
    assert max(maxima) == 190.0


def test_downsampling_preserves_battery_end_value() -> None:
    start = datetime(2026, 9, 13, 8, 0, tzinfo=timezone.utc)
    end = start + timedelta(minutes=10)
    items = [
        _item(start + timedelta(minutes=index), 72.0, 75.0)
        for index in range(10)
    ]
    items[-1]["analytics"]["battery"]["endPercentage"] = 83.2

    reduced = downsample_analytics_history(
        items,
        start.isoformat(),
        end.isoformat(),
        max_points=1,
    )

    assert reduced[0]["analytics"]["battery"]["endPercentage"] == 83.2
