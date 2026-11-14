"""Tests for persistent HealthBand configuration."""

from pathlib import Path

from device_simulator.configuration.configuration_manager import (
    ConfigurationManager,
)


def test_applied_configuration_is_persisted(
    tmp_path: Path,
) -> None:
    runtime_file = (
        tmp_path
        / "device_config.json"
    )

    manager = ConfigurationManager(
        runtime_config_path=(
            runtime_file
        )
    )

    result = manager.apply_delta(
        {
            "measurementIntervalSec": 4,
            "temperatureUnit": "FAHRENHEIT",
        }
    )

    assert result.applied is True

    reloaded = ConfigurationManager(
        runtime_config_path=(
            runtime_file
        )
    )

    assert (
        reloaded.current.measurement_interval_sec
        == 4
    )

    assert (
        reloaded.current.temperature_unit.value
        == "FAHRENHEIT"
    )


def test_invalid_configuration_does_not_replace_current(
    tmp_path: Path,
) -> None:
    runtime_file = (
        tmp_path
        / "device_config.json"
    )

    manager = ConfigurationManager(
        runtime_config_path=(
            runtime_file
        )
    )

    before = (
        manager.current
    )

    result = manager.apply_delta(
        {
            "measurementIntervalSec": 0
        }
    )

    assert result.applied is False

    assert (
        manager.current
        == before
    )

def test_v1_loads_shared_runtime_file_written_by_v2(
    tmp_path: Path,
) -> None:
    """A v1 boot/rollback must ignore persisted fields introduced by v2."""

    runtime_file = tmp_path / "device_config.json"
    runtime_file.write_text(
        __import__("json").dumps(
            {
                "measurementIntervalSec": 3,
                "telemetryIntervalSec": 4,
                "analyticsWindowSec": 60,
                "healthReportIntervalSec": 30,
                "temperatureUnit": "CELSIUS",
                "thresholds": {
                    "heartRateMinimumBpm": 50,
                    "heartRateMaximumRestingBpm": 110,
                    "skinTemperatureMinimumC": 30.0,
                    "skinTemperatureMaximumC": 37.0,
                    "lowBatteryPercentage": 15,
                },
                "alerts": {
                    "enabled": True,
                    "heartRate": True,
                    "temperature": True,
                    "battery": True,
                    "sensorFailure": True,
                },
                "offlineQueueMaximumItems": 1000,
                "activeUserProfile": "DEFAULT",
                "analyticsEnabled": True,
                "spo2AlertsEnabled": True,
                "spo2MinimumThreshold": 92.0,
                "spo2MeasurementEnabled": True,
            }
        ),
        encoding="utf-8",
    )

    manager = ConfigurationManager(
        runtime_config_path=runtime_file,
        software_version="1.0.0",
    )

    assert manager.current.measurement_interval_sec == 3
    assert manager.current.telemetry_interval_sec == 4
    assert manager.current.spo2_alerts_enabled is None
    assert manager.current.spo2_minimum_threshold is None
    assert manager.current.spo2_measurement_enabled is None


def test_v1_still_rejects_new_v2_fields_from_remote_delta(
    tmp_path: Path,
) -> None:
    """Compatibility on startup must not weaken v1 Shadow validation."""

    manager = ConfigurationManager(
        runtime_config_path=(tmp_path / "device_config.json"),
        software_version="1.0.0",
    )

    result = manager.apply_delta(
        {"spo2MeasurementEnabled": True}
    )

    assert result.applied is False
    assert any(
        "not supported by HealthBand version 1.0.0" in error
        for error in result.errors
    )
