"""Unit tests for HealthBand local analytics."""

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from device_simulator.analytics.analytics_manager import (
    AnalyticsManager,
)
from device_simulator.sensors.sensor_manager import (
    SensorSnapshot,
)


def make_snapshot(
    heart_rate: int = 70,
    temperature: float = 33.5,
    steps: int = 0,
    battery: float = 100.0,
    activity: str = "RESTING",
    scenario: str = "RESTING",
    heart_status: str = "OK",
    offset_sec: int = 0,
) -> SensorSnapshot:
    measurements = {
        "skinTemperatureCelsius": (
            temperature
        ),
        "stepsInInterval": steps,
        "totalDailySteps": steps,
        "batteryPercentage": battery,
        "activityLevel": activity,
    }

    if heart_status == "OK":
        measurements["heartRateBpm"] = (
            heart_rate
        )

    return SensorSnapshot(
        measurements=measurements,
        sensor_status={
            "heart_rate": heart_status,
            "skin_temperature": "OK",
            "step_counter": "OK",
            "battery": "OK",
        },
        scenario=scenario,
        activity_level=activity,
        timestamp=(
            datetime.now(timezone.utc)
            + timedelta(
                seconds=offset_sec
            )
        ),
    )


def test_window_does_not_finish_too_early() -> None:
    manager = AnalyticsManager(
        device_id="test-device",
        software_version="1.0.0",
        window_sec=4.0,
    )

    result = manager.add_snapshot(
        make_snapshot(),
        elapsed_sec=2.0,
    )

    assert result is None


def test_window_calculates_statistics() -> None:
    manager = AnalyticsManager(
        device_id="test-device",
        software_version="1.0.0",
        window_sec=4.0,
    )

    manager.add_snapshot(
        make_snapshot(
            heart_rate=70,
            temperature=33.0,
            steps=4,
            battery=100.0,
        ),
        elapsed_sec=2.0,
    )

    result = manager.add_snapshot(
        make_snapshot(
            heart_rate=80,
            temperature=34.0,
            steps=6,
            battery=99.0,
            offset_sec=2,
        ),
        elapsed_sec=2.0,
    )

    assert result is not None

    assert (
        result.analytics[
            "heartRate"
        ]["averageBpm"]
        == 75.0
    )

    assert (
        result.analytics[
            "heartRate"
        ]["minimumBpm"]
        == 70.0
    )

    assert (
        result.analytics[
            "heartRate"
        ]["maximumBpm"]
        == 80.0
    )

    assert (
        result.analytics[
            "steps"
        ]["total"]
        == 10
    )

    assert (
        result.analytics[
            "battery"
        ]["consumptionPercentage"]
        == 1.0
    )


def test_data_quality_detects_failed_sensor() -> None:
    manager = AnalyticsManager(
        device_id="test-device",
        software_version="1.0.0",
        window_sec=4.0,
    )

    manager.add_snapshot(
        make_snapshot(),
        elapsed_sec=2.0,
    )

    result = manager.add_snapshot(
        make_snapshot(
            heart_status="FAILED",
            offset_sec=2,
        ),
        elapsed_sec=2.0,
    )

    assert result is not None

    assert (
        result.analytics[
            "dataQualityPercentage"
        ]
        == 87.5
    )


def test_dominant_activity_is_calculated() -> None:
    manager = AnalyticsManager(
        device_id="test-device",
        software_version="1.0.0",
        window_sec=6.0,
    )

    manager.add_snapshot(
        make_snapshot(
            activity="RESTING"
        ),
        elapsed_sec=2.0,
    )

    manager.add_snapshot(
        make_snapshot(
            activity="RESTING",
            offset_sec=2,
        ),
        elapsed_sec=2.0,
    )

    result = manager.add_snapshot(
        make_snapshot(
            activity="HIGH",
            scenario="RUNNING",
            offset_sec=4,
        ),
        elapsed_sec=2.0,
    )

    assert result is not None

    assert (
        result.analytics[
            "activity"
        ]["dominantLevel"]
        == "RESTING"
    )