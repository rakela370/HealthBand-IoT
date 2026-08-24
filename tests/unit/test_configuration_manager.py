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