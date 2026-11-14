"""Regression tests for final old-style HealthBand History data."""

from datetime import datetime, timedelta, timezone

from control_backend.services.history_series import build_history_series


def _telemetry(timestamp: datetime, hr: float, *, steps: int = 0) -> dict:
    return {
        "timestamp": timestamp.isoformat(),
        "scenario": "RESTING",
        "measurements": {
            "heartRateBpm": hr,
            "skinTemperature": 33.6,
            "temperatureUnit": "CELSIUS",
            "totalDailySteps": steps,
            "batteryPercentage": 90.0,
        },
    }


def _analytics(timestamp: datetime, average: float, steps: int = 10) -> dict:
    return {
        "windowStart": (timestamp - timedelta(hours=1)).isoformat(),
        "windowEnd": timestamp.isoformat(),
        "historicalScenario": "WALKING",
        "analytics": {
            "heartRate": {
                "averageBpm": average,
                "minimumBpm": average - 4,
                "maximumBpm": average + 5,
                "validSamples": 6,
            },
            "skinTemperature": {
                "averageCelsius": 33.5,
                "minimumCelsius": 33.3,
                "maximumCelsius": 33.7,
                "validSamples": 6,
            },
            "steps": {"total": steps, "averagePerInterval": steps / 6},
            "battery": {
                "startPercentage": 95.0,
                "endPercentage": 94.5,
                "consumptionPercentage": 0.5,
            },
        },
    }


def test_15m_keeps_every_real_telemetry_point() -> None:
    start = datetime(2026, 9, 13, 10, 0, tzinfo=timezone.utc)
    telemetry = [
        _telemetry(start + timedelta(seconds=index * 2), 70 + index)
        for index in range(20)
    ]
    points = build_history_series(
        telemetry_items=telemetry, analytics_items=[],
        start_iso=start.isoformat(),
        end_iso=(start + timedelta(minutes=15)).isoformat(),
        period="15m",
    )
    assert len(points) == 20
    assert points[0]["heartRateBpm"] == 70
    assert points[-1]["heartRateBpm"] == 89


def test_1h_keeps_190_as_normal_measurement() -> None:
    start = datetime(2026, 9, 13, 10, 0, tzinfo=timezone.utc)
    peak_time = start + timedelta(minutes=40, seconds=12)
    telemetry = []
    for index in range(1800):
        timestamp = start + timedelta(seconds=index * 2)
        telemetry.append(
            _telemetry(timestamp, 190.0 if timestamp == peak_time else 72.0)
        )
    points = build_history_series(
        telemetry_items=telemetry, analytics_items=[],
        start_iso=start.isoformat(),
        end_iso=(start + timedelta(hours=1)).isoformat(),
        period="1h",
    )
    peak = [point for point in points if point.get("heartRateBpm") == 190.0]
    assert len(peak) == 1
    assert peak[0]["timestamp"] == peak_time.isoformat()
    assert "heartRatePeakTimestamp" not in peak[0]
    assert "heartRateMaxBpm" not in peak[0]


def test_24h_density_reduction_keeps_real_190_measurement() -> None:
    end = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
    start = end - timedelta(hours=24)
    raw_start = end - timedelta(hours=1)
    peak_time = end - timedelta(minutes=20)
    raw = [
        _telemetry(
            raw_start + timedelta(seconds=index * 2),
            190.0 if raw_start + timedelta(seconds=index * 2) == peak_time else 75.0,
            steps=index // 8,
        )
        for index in range(1800)
    ]
    points = build_history_series(
        telemetry_items=raw, analytics_items=[],
        start_iso=start.isoformat(), end_iso=end.isoformat(), period="24h",
    )
    assert any(point.get("heartRateBpm") == 190.0 for point in points)
    assert all("heartRatePeakTimestamp" not in point for point in points)
    assert len(points) <= 1500


def test_long_history_combines_seeded_analytics_and_live_telemetry() -> None:
    end = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
    start = end - timedelta(hours=24)
    seeded = [_analytics(start + timedelta(hours=h), 72.0 + h % 3) for h in range(1, 13)]
    raw_start = end - timedelta(hours=1)
    raw = [_telemetry(raw_start + timedelta(minutes=i), 75.0 + i % 4) for i in range(60)]
    points = build_history_series(
        telemetry_items=raw, analytics_items=seeded,
        start_iso=start.isoformat(), end_iso=end.isoformat(), period="24h",
    )
    assert any(point["source"] == "ANALYTICS" for point in points)
    assert any(point["source"] == "TELEMETRY" for point in points)


def test_fahrenheit_history_is_converted_to_celsius() -> None:
    start = datetime(2026, 9, 13, 10, 0, tzinfo=timezone.utc)
    item = _telemetry(start, 72.0)
    item["measurements"]["skinTemperature"] = 92.48
    item["measurements"]["temperatureUnit"] = "FAHRENHEIT"
    points = build_history_series(
        telemetry_items=[item], analytics_items=[],
        start_iso=start.isoformat(),
        end_iso=(start + timedelta(minutes=15)).isoformat(),
        period="15m",
    )
    assert points[0]["skinTemperatureCelsius"] == 33.6


def test_seeded_analytics_reconstructs_daily_steps() -> None:
    start = datetime(2026, 9, 12, 8, 0, tzinfo=timezone.utc)
    analytics = [
        _analytics(start + timedelta(hours=1), 72.0, steps=100),
        _analytics(start + timedelta(hours=2), 73.0, steps=150),
    ]
    points = build_history_series(
        telemetry_items=[], analytics_items=analytics,
        start_iso=start.isoformat(),
        end_iso=(start + timedelta(days=7)).isoformat(),
        period="7d",
    )
    assert points[0]["totalDailySteps"] == 100
    assert points[1]["totalDailySteps"] == 250


def test_recent_telemetry_query_uses_newest_rows_and_returns_chronological() -> None:
    from control_backend.aws.dynamodb_service import DynamoDbService
    service = object.__new__(DynamoDbService)
    service.telemetry = object()
    captured: dict[str, object] = {}
    def fake_query_range(**kwargs):
        captured.update(kwargs)
        return [
            {"timestamp": "2026-09-13T11:00:02+00:00"},
            {"timestamp": "2026-09-13T11:00:00+00:00"},
        ]
    service._query_range = fake_query_range  # type: ignore[method-assign]
    items = service.get_telemetry_recent(
        "healthband-device-001",
        "2026-09-13T10:00:00+00:00",
        "2026-09-13T11:00:00+00:00",
        100,
    )
    assert captured["scan_index_forward"] is False
    assert items[0]["timestamp"] == "2026-09-13T11:00:00+00:00"
    assert items[1]["timestamp"] == "2026-09-13T11:00:02+00:00"
