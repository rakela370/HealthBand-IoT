"""HealthBand runtime configuration model."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class TemperatureUnit(StrEnum):
    """Temperature units supported by HealthBand."""

    CELSIUS = "CELSIUS"
    FAHRENHEIT = "FAHRENHEIT"


@dataclass(frozen=True, slots=True)
class DeviceConfig:
    """Validated persistent HealthBand configuration."""

    measurement_interval_sec: float = 2.0
    telemetry_interval_sec: float = 2.0
    analytics_window_sec: float = 10.0
    health_report_interval_sec: float = 5.0

    temperature_unit: TemperatureUnit = (
        TemperatureUnit.CELSIUS
    )

    heart_rate_minimum_bpm: float = 50.0
    heart_rate_maximum_resting_bpm: float = 110.0

    skin_temperature_minimum_c: float = 30.0
    skin_temperature_maximum_c: float = 37.0

    low_battery_percentage: float = 15.0

    alerts_enabled: bool = True
    heart_rate_alerts_enabled: bool = True
    temperature_alerts_enabled: bool = True
    battery_alerts_enabled: bool = True
    sensor_failure_alerts_enabled: bool = True

    offline_queue_maximum_items: int = 5000

    active_user_profile: str = "simulated-user-001"

    analytics_enabled: bool = True

    # HealthBand 2.0.0-only configuration. None means unsupported.
    spo2_alerts_enabled: bool | None = None
    spo2_minimum_threshold: float | None = None
    spo2_measurement_enabled: bool | None = None

    def to_shadow_dict(self) -> dict[str, Any]:
        """Convert configuration to Device Shadow representation."""

        result: dict[str, Any] = {
            "measurementIntervalSec": (
                self.measurement_interval_sec
            ),
            "telemetryIntervalSec": (
                self.telemetry_interval_sec
            ),
            "analyticsWindowSec": (
                self.analytics_window_sec
            ),
            "healthReportIntervalSec": (
                self.health_report_interval_sec
            ),
            "temperatureUnit": (
                self.temperature_unit.value
            ),
            "thresholds": {
                "heartRateMinimumBpm": (
                    self.heart_rate_minimum_bpm
                ),
                "heartRateMaximumRestingBpm": (
                    self.heart_rate_maximum_resting_bpm
                ),
                "skinTemperatureMinimumC": (
                    self.skin_temperature_minimum_c
                ),
                "skinTemperatureMaximumC": (
                    self.skin_temperature_maximum_c
                ),
                "lowBatteryPercentage": (
                    self.low_battery_percentage
                ),
            },
            "alerts": {
                "enabled": (
                    self.alerts_enabled
                ),
                "heartRate": (
                    self.heart_rate_alerts_enabled
                ),
                "temperature": (
                    self.temperature_alerts_enabled
                ),
                "battery": (
                    self.battery_alerts_enabled
                ),
                "sensorFailure": (
                    self.sensor_failure_alerts_enabled
                ),
            },
            "offlineQueueMaximumItems": (
                self.offline_queue_maximum_items
            ),
            "activeUserProfile": (
                self.active_user_profile
            ),
            "analyticsEnabled": (
                self.analytics_enabled
            ),
        }

        if self.spo2_alerts_enabled is not None:
            result[
                "spo2AlertsEnabled"
            ] = self.spo2_alerts_enabled

        if self.spo2_minimum_threshold is not None:
            result[
                "spo2MinimumThreshold"
            ] = self.spo2_minimum_threshold

        if self.spo2_measurement_enabled is not None:
            result[
                "spo2MeasurementEnabled"
            ] = self.spo2_measurement_enabled

        return result

    def convert_temperature_from_celsius(
        self,
        temperature_celsius: float,
    ) -> float:
        """Convert canonical Celsius value to configured unit."""

        if (
            self.temperature_unit
            == TemperatureUnit.CELSIUS
        ):
            return round(
                temperature_celsius,
                2,
            )

        fahrenheit = (
            temperature_celsius
            * 9.0
            / 5.0
            + 32.0
        )

        return round(
            fahrenheit,
            2,
        )