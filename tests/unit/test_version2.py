"""Unit tests for HealthBand 2.0.0 functionality."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from device_simulator.alerts.alert import AlertType
from device_simulator.alerts.alert_manager import AlertManager
from device_simulator.analytics.analytics_manager import AnalyticsManager
from device_simulator.analytics.calorie_estimator import CalorieEstimator
from device_simulator.configuration.configuration_manager import ConfigurationManager
from device_simulator.configuration.configuration_validator import ConfigurationValidator
from device_simulator.configuration.device_config import DeviceConfig
from device_simulator.core.device_state import DeviceState
from device_simulator.device_health.device_health_monitor import DeviceHealthMonitor
from device_simulator.sensors.sensor_manager import SensorManager, SensorSnapshot
from device_simulator.simulation.scenario_engine import ScenarioEngine
from device_simulator.simulation.user_profile import UserProfile
from device_simulator.storage.local_database import LocalDatabase


def make_v2_snapshot(
    *,
    spo2: float = 98.0,
    timestamp: datetime | None = None,
    spo2_status: str = "OK",
    calories_interval: float | None = None,
    calories_today: float | None = None,
) -> SensorSnapshot:
    """Build a deterministic version-2 snapshot for analytics/alert tests."""

    measurements: dict[str, object] = {
        "heartRateBpm": 72,
        "skinTemperatureCelsius": 33.6,
        "stepsInInterval": 0,
        "totalDailySteps": 100,
        "batteryPercentage": 80.0,
        "activityLevel": "RESTING",
    }

    if spo2_status == "OK":
        measurements[
            "oxygenSaturationPercentage"
        ] = spo2

    if calories_interval is not None:
        measurements[
            "caloriesBurnedInInterval"
        ] = calories_interval

    if calories_today is not None:
        measurements[
            "caloriesBurnedToday"
        ] = calories_today

    return SensorSnapshot(
        measurements=measurements,
        sensor_status={
            "heart_rate": "OK",
            "skin_temperature": "OK",
            "step_counter": "OK",
            "battery": "OK",
            "spo2": spo2_status,
        },
        scenario="RESTING",
        activity_level="RESTING",
        timestamp=(
            timestamp
            or datetime.now(
                timezone.utc
            )
        ),
    )


def test_version1_sensor_manager_does_not_register_spo2() -> None:
    manager = SensorManager(
        random_seed=1
    )

    assert manager.has_sensor(
        "spo2"
    ) is False


def test_version2_sensor_manager_adds_spo2_measurement() -> None:
    manager = SensorManager(
        random_seed=1,
        software_version="2.0.0",
    )

    snapshot = manager.read_all(
        ScenarioEngine().get_context(),
        2.0,
    )

    assert manager.has_sensor(
        "spo2"
    ) is True

    assert (
        "oxygenSaturationPercentage"
        in snapshot.measurements
    )

    assert snapshot.sensor_status[
        "spo2"
    ] == "OK"


def test_version2_spo2_can_be_disabled() -> None:
    manager = SensorManager(
        random_seed=1,
        software_version="2.0.0",
        spo2_measurement_enabled=False,
    )

    snapshot = manager.read_all(
        ScenarioEngine().get_context(),
        2.0,
    )

    assert (
        "oxygenSaturationPercentage"
        not in snapshot.measurements
    )

    assert snapshot.sensor_status[
        "spo2"
    ] == "DISABLED"


def test_version2_configuration_accepts_spo2_fields() -> None:
    validator = ConfigurationValidator(
        software_version="2.0.0"
    )

    current = DeviceConfig(
        spo2_alerts_enabled=True,
        spo2_minimum_threshold=92.0,
        spo2_measurement_enabled=True,
    )

    result = validator.apply_delta(
        current,
        {
            "spo2AlertsEnabled": False,
            "spo2MinimumThreshold": 93.5,
            "spo2MeasurementEnabled": True,
        },
    )

    assert result.spo2_alerts_enabled is False
    assert result.spo2_minimum_threshold == 93.5
    assert result.spo2_measurement_enabled is True


def test_version2_configuration_migrates_v1_runtime_file(
    tmp_path: Path,
) -> None:
    runtime_file = (
        tmp_path
        / "device_config.json"
    )

    runtime_file.write_text(
        __import__("json").dumps(
            DeviceConfig().to_shadow_dict()
        ),
        encoding="utf-8",
    )

    manager = ConfigurationManager(
        runtime_config_path=runtime_file,
        software_version="2.0.0",
    )

    assert manager.current.spo2_alerts_enabled is True
    assert manager.current.spo2_minimum_threshold == 92.0
    assert manager.current.spo2_measurement_enabled is True


def test_version2_analytics_contains_spo2_and_calories() -> None:
    manager = AnalyticsManager(
        device_id="test-device",
        software_version="2.0.0",
        window_sec=4.0,
        spo2_minimum_threshold=97.0,
        spo2_enabled=True,
    )

    start = datetime(
        2026,
        8,
        28,
        8,
        0,
        tzinfo=timezone.utc,
    )

    manager.add_snapshot(
        make_v2_snapshot(
            spo2=98.0,
            timestamp=start,
            calories_interval=0.4,
            calories_today=100.4,
        ),
        elapsed_sec=2.0,
    )

    result = manager.add_snapshot(
        make_v2_snapshot(
            spo2=96.0,
            timestamp=(
                start
                + timedelta(
                    seconds=2
                )
            ),
            calories_interval=0.6,
            calories_today=101.0,
        ),
        elapsed_sec=2.0,
    )

    assert result is not None
    assert result.to_dict()[
        "schemaVersion"
    ] == 2
    assert result.analytics[
        "spo2"
    ]["averagePercentage"] == 97.0
    assert result.analytics[
        "spo2"
    ]["belowThresholdSamples"] == 1
    assert result.analytics[
        "calories"
    ]["totalKcal"] == 1.0
    assert result.analytics[
        "calories"
    ]["dailyTotalKcal"] == 101.0


def test_spo2_below_threshold_requires_three_measurements() -> None:
    manager = AlertManager(
        device_id="test-device",
        spo2_minimum_threshold=95.0,
    )

    start = datetime(
        2026,
        8,
        28,
        8,
        0,
        tzinfo=timezone.utc,
    )

    alerts = []

    for index in range(3):
        alerts.extend(
            manager.evaluate_snapshot(
                make_v2_snapshot(
                    spo2=92.0,
                    timestamp=(
                        start
                        + timedelta(
                            seconds=(
                                index * 2
                            )
                        )
                    ),
                )
            )
        )

    assert (
        AlertType.SPO2_BELOW_THRESHOLD
        in {
            alert.type
            for alert in alerts
        }
    )


def test_spo2_failed_sensor_uses_version2_alert_type() -> None:
    manager = AlertManager(
        device_id="test-device"
    )

    alerts = manager.evaluate_snapshot(
        make_v2_snapshot(
            spo2_status="FAILED"
        )
    )

    assert (
        AlertType.SPO2_SENSOR_FAILED
        in {
            alert.type
            for alert in alerts
        }
    )


def test_version2_health_capabilities_include_new_features() -> None:
    monitor = DeviceHealthMonitor(
        device_id="test-device",
        software_version="2.0.0",
    )

    report = monitor.create_report(
        device_state=DeviceState.MONITORING,
        sensor_statuses={
            "heart_rate": "OK",
            "skin_temperature": "OK",
            "step_counter": "OK",
            "battery": "OK",
            "spo2": "OK",
        },
        battery_percentage=80.0,
    )

    assert "SPO2_MONITORING" in report.capabilities
    assert "CALORIE_ESTIMATION" in report.capabilities


def test_calorie_estimator_accumulates_and_persists(
    tmp_path: Path,
) -> None:
    database = LocalDatabase(
        tmp_path
        / "healthband.db"
    )

    profile = UserProfile()

    timestamp = datetime(
        2026,
        8,
        28,
        10,
        0,
        tzinfo=timezone.utc,
    )

    first = CalorieEstimator(
        profile,
        database,
    )

    first_result = first.estimate_interval(
        measurements={
            "heartRateBpm": 100
        },
        activity_level="MODERATE",
        scenario="WALKING",
        elapsed_sec=600.0,
        timestamp=timestamp,
    )

    second = CalorieEstimator(
        profile,
        database,
    )

    second_result = second.estimate_interval(
        measurements={
            "heartRateBpm": 100
        },
        activity_level="MODERATE",
        scenario="WALKING",
        elapsed_sec=600.0,
        timestamp=(
            timestamp
            + timedelta(
                minutes=10
            )
        ),
    )

    assert first_result[
        "caloriesBurnedInInterval"
    ] > 0
    assert second_result[
        "caloriesBurnedToday"
    ] > first_result[
        "caloriesBurnedToday"
    ]


def test_calorie_estimator_resets_at_sarajevo_midnight() -> None:
    estimator = CalorieEstimator(
        UserProfile()
    )

    before_midnight_utc = datetime(
        2026,
        8,
        28,
        21,
        50,
        tzinfo=timezone.utc,
    )

    before = estimator.estimate_interval(
        measurements={
            "heartRateBpm": 100
        },
        activity_level="MODERATE",
        scenario="WALKING",
        elapsed_sec=600.0,
        timestamp=before_midnight_utc,
    )

    after = estimator.estimate_interval(
        measurements={
            "heartRateBpm": 72
        },
        activity_level="RESTING",
        scenario="RESTING",
        elapsed_sec=60.0,
        timestamp=datetime(
            2026,
            8,
            28,
            22,
            10,
            tzinfo=timezone.utc,
        ),
    )

    assert after[
        "caloriesBurnedToday"
    ] == round(
        after[
            "caloriesBurnedInInterval"
        ],
        2,
    )
    assert after[
        "caloriesBurnedToday"
    ] < before[
        "caloriesBurnedToday"
    ]