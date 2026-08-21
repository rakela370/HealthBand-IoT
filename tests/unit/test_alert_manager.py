"""Unit tests for HealthBand AlertManager."""

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from device_simulator.alerts.alert import (
    AlertType,
)
from device_simulator.alerts.alert_manager import (
    AlertManager,
)
from device_simulator.sensors.sensor_manager import (
    SensorSnapshot,
)


def make_snapshot(
    heart_rate: int = 72,
    temperature: float = 33.6,
    battery: float = 80.0,
    activity: str = "RESTING",
    scenario: str = "RESTING",
    heart_status: str = "OK",
    offset_sec: int = 0,
) -> SensorSnapshot:
    measurements = {
        "skinTemperatureCelsius": (
            temperature
        ),
        "stepsInInterval": 0,
        "totalDailySteps": 0,
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


def test_single_high_heart_rate_does_not_alert() -> None:
    manager = AlertManager(
        device_id="test-device"
    )

    alerts = manager.evaluate_snapshot(
        make_snapshot(
            heart_rate=130
        )
    )

    assert alerts == []


def test_three_high_resting_measurements_generate_alert() -> None:
    manager = AlertManager(
        device_id="test-device"
    )

    manager.evaluate_snapshot(
        make_snapshot(
            heart_rate=130,
            offset_sec=0,
        )
    )

    manager.evaluate_snapshot(
        make_snapshot(
            heart_rate=130,
            offset_sec=2,
        )
    )

    alerts = manager.evaluate_snapshot(
        make_snapshot(
            heart_rate=130,
            offset_sec=4,
        )
    )

    assert len(alerts) == 1

    assert (
        alerts[0].type
        == AlertType.HEART_RATE_ABOVE_RESTING_THRESHOLD
    )


def test_high_heart_rate_during_running_is_not_resting_alert() -> None:
    manager = AlertManager(
        device_id="test-device"
    )

    alerts = []

    for index in range(3):
        alerts.extend(
            manager.evaluate_snapshot(
                make_snapshot(
                    heart_rate=150,
                    activity="HIGH",
                    scenario="RUNNING",
                    offset_sec=index * 2,
                )
            )
        )

    assert (
        AlertType.HEART_RATE_ABOVE_RESTING_THRESHOLD
        not in [
            alert.type
            for alert in alerts
        ]
    )


def test_failed_sensor_generates_immediate_alert() -> None:
    manager = AlertManager(
        device_id="test-device"
    )

    alerts = manager.evaluate_snapshot(
        make_snapshot(
            heart_status="FAILED"
        )
    )

    assert any(
        alert.type
        == AlertType.SENSOR_FAILED
        for alert in alerts
    )


def test_low_battery_requires_three_measurements() -> None:
    manager = AlertManager(
        device_id="test-device"
    )

    alerts = []

    for index in range(3):
        alerts = manager.evaluate_snapshot(
            make_snapshot(
                battery=10.0,
                offset_sec=index * 2,
            )
        )

    assert any(
        alert.type
        == AlertType.LOW_BATTERY
        for alert in alerts
    )