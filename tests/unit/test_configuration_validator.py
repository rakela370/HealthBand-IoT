"""Unit tests for remote configuration validation."""

import pytest

from device_simulator.configuration.configuration_validator import (
    ConfigurationValidationError,
    ConfigurationValidator,
)
from device_simulator.configuration.device_config import (
    DeviceConfig,
    TemperatureUnit,
)


def test_valid_partial_configuration_is_merged() -> None:
    validator = ConfigurationValidator()

    result = validator.apply_delta(
        DeviceConfig(),
        {
            "measurementIntervalSec": 4,
            "temperatureUnit": "FAHRENHEIT",
        },
    )

    assert (
        result.measurement_interval_sec
        == 4
    )

    assert (
        result.temperature_unit
        == TemperatureUnit.FAHRENHEIT
    )

    assert (
        result.telemetry_interval_sec
        == 2
    )


def test_zero_measurement_interval_is_rejected() -> None:
    validator = ConfigurationValidator()

    with pytest.raises(
        ConfigurationValidationError
    ):
        validator.apply_delta(
            DeviceConfig(),
            {
                "measurementIntervalSec": 0
            },
        )


def test_unknown_temperature_unit_is_rejected() -> None:
    validator = ConfigurationValidator()

    with pytest.raises(
        ConfigurationValidationError
    ):
        validator.apply_delta(
            DeviceConfig(),
            {
                "temperatureUnit": "KELVIN"
            },
        )


def test_invalid_threshold_order_is_rejected() -> None:
    validator = ConfigurationValidator()

    with pytest.raises(
        ConfigurationValidationError
    ):
        validator.apply_delta(
            DeviceConfig(),
            {
                "thresholds": {
                    "heartRateMinimumBpm": 150,
                    "heartRateMaximumRestingBpm": 100,
                }
            },
        )


def test_invalid_battery_percentage_is_rejected() -> None:
    validator = ConfigurationValidator()

    with pytest.raises(
        ConfigurationValidationError
    ):
        validator.apply_delta(
            DeviceConfig(),
            {
                "thresholds": {
                    "lowBatteryPercentage": 120
                }
            },
        )


def test_spo2_configuration_is_rejected_on_version1() -> None:
    validator = ConfigurationValidator()

    with pytest.raises(
        ConfigurationValidationError
    ):
        validator.apply_delta(
            DeviceConfig(),
            {
                "spo2MeasurementEnabled": True
            },
        )