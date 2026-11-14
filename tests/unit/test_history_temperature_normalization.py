"""Regression tests for canonical Celsius history rendering."""

from control_backend.api.history_routes import (
    normalize_telemetry_temperature_history,
)


def test_fahrenheit_telemetry_is_normalized_to_celsius_for_history() -> None:
    items = [
        {
            "timestamp": "2026-09-04T08:00:00+00:00",
            "measurements": {
                "skinTemperature": 92.48,
                "temperatureUnit": "FAHRENHEIT",
            },
        }
    ]

    result = normalize_telemetry_temperature_history(items)
    measurements = result[0]["measurements"]

    assert measurements["temperatureUnit"] == "CELSIUS"
    assert measurements["skinTemperature"] == 33.6
    assert measurements["skinTemperatureCelsius"] == 33.6


def test_canonical_celsius_wins_even_when_display_value_is_fahrenheit() -> None:
    items = [
        {
            "measurements": {
                "skinTemperatureCelsius": 33.61,
                "skinTemperature": 92.5,
                "temperatureUnit": "FAHRENHEIT",
            }
        }
    ]

    result = normalize_telemetry_temperature_history(items)
    measurements = result[0]["measurements"]

    assert measurements["skinTemperature"] == 33.61
    assert measurements["temperatureUnit"] == "CELSIUS"
