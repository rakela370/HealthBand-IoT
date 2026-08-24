"""Validation and merging of HealthBand configuration updates."""

from copy import deepcopy
from typing import Any

from device_simulator.configuration.device_config import (
    DeviceConfig,
    TemperatureUnit,
)


class ConfigurationValidationError(ValueError):
    """Raised when a remote configuration update is invalid."""

    def __init__(
        self,
        errors: list[str],
    ) -> None:
        self.errors = tuple(
            errors
        )

        super().__init__(
            "; ".join(
                errors
            )
        )


class ConfigurationValidator:
    """Validate Device Shadow desired configuration."""

    _ALLOWED_TOP_LEVEL = {
        "measurementIntervalSec",
        "telemetryIntervalSec",
        "analyticsWindowSec",
        "healthReportIntervalSec",
        "temperatureUnit",
        "thresholds",
        "alerts",
        "offlineQueueMaximumItems",
        "activeUserProfile",
        "analyticsEnabled",
    }

    _ALLOWED_THRESHOLDS = {
        "heartRateMinimumBpm",
        "heartRateMaximumRestingBpm",
        "skinTemperatureMinimumC",
        "skinTemperatureMaximumC",
        "lowBatteryPercentage",
    }

    _ALLOWED_ALERTS = {
        "enabled",
        "heartRate",
        "temperature",
        "battery",
        "sensorFailure",
    }

    _VERSION_2_ONLY = {
        "spo2AlertsEnabled",
        "spo2MinimumThreshold",
        "spo2MeasurementEnabled",
    }

    def apply_delta(
        self,
        current: DeviceConfig,
        delta: dict[str, Any],
    ) -> DeviceConfig:
        """
        Merge partial desired state with current configuration.

        The original configuration is never modified.
        """

        if not isinstance(
            delta,
            dict,
        ):
            raise ConfigurationValidationError(
                [
                    "Configuration delta must be a JSON object."
                ]
            )

        errors: list[str] = []

        for key in delta:
            if key in self._VERSION_2_ONLY:
                errors.append(
                    f"'{key}' is not supported "
                    "by HealthBand version 1.0.0."
                )

            elif key not in self._ALLOWED_TOP_LEVEL:
                errors.append(
                    f"Unknown configuration field '{key}'."
                )

        merged = deepcopy(
            current.to_shadow_dict()
        )

        simple_fields = (
            "measurementIntervalSec",
            "telemetryIntervalSec",
            "analyticsWindowSec",
            "healthReportIntervalSec",
            "temperatureUnit",
            "offlineQueueMaximumItems",
            "activeUserProfile",
            "analyticsEnabled",
        )

        for field in simple_fields:
            if field in delta:
                merged[
                    field
                ] = delta[
                    field
                ]

        if "thresholds" in delta:
            thresholds = delta[
                "thresholds"
            ]

            if not isinstance(
                thresholds,
                dict,
            ):
                errors.append(
                    "'thresholds' must be an object."
                )

            else:
                for key in thresholds:
                    if (
                        key
                        not in self._ALLOWED_THRESHOLDS
                    ):
                        errors.append(
                            "Unknown threshold field "
                            f"'{key}'."
                        )

                    else:
                        merged[
                            "thresholds"
                        ][key] = thresholds[
                            key
                        ]

        if "alerts" in delta:
            alerts = delta[
                "alerts"
            ]

            if not isinstance(
                alerts,
                dict,
            ):
                errors.append(
                    "'alerts' must be an object."
                )

            else:
                for key in alerts:
                    if key not in self._ALLOWED_ALERTS:
                        errors.append(
                            "Unknown alerts field "
                            f"'{key}'."
                        )

                    else:
                        merged[
                            "alerts"
                        ][key] = alerts[
                            key
                        ]

        self._validate_merged(
            merged,
            errors,
        )

        if errors:
            raise ConfigurationValidationError(
                errors
            )

        thresholds = merged[
            "thresholds"
        ]

        alerts = merged[
            "alerts"
        ]

        return DeviceConfig(
            measurement_interval_sec=float(
                merged[
                    "measurementIntervalSec"
                ]
            ),
            telemetry_interval_sec=float(
                merged[
                    "telemetryIntervalSec"
                ]
            ),
            analytics_window_sec=float(
                merged[
                    "analyticsWindowSec"
                ]
            ),
            health_report_interval_sec=float(
                merged[
                    "healthReportIntervalSec"
                ]
            ),
            temperature_unit=TemperatureUnit(
                merged[
                    "temperatureUnit"
                ]
            ),
            heart_rate_minimum_bpm=float(
                thresholds[
                    "heartRateMinimumBpm"
                ]
            ),
            heart_rate_maximum_resting_bpm=float(
                thresholds[
                    "heartRateMaximumRestingBpm"
                ]
            ),
            skin_temperature_minimum_c=float(
                thresholds[
                    "skinTemperatureMinimumC"
                ]
            ),
            skin_temperature_maximum_c=float(
                thresholds[
                    "skinTemperatureMaximumC"
                ]
            ),
            low_battery_percentage=float(
                thresholds[
                    "lowBatteryPercentage"
                ]
            ),
            alerts_enabled=bool(
                alerts[
                    "enabled"
                ]
            ),
            heart_rate_alerts_enabled=bool(
                alerts[
                    "heartRate"
                ]
            ),
            temperature_alerts_enabled=bool(
                alerts[
                    "temperature"
                ]
            ),
            battery_alerts_enabled=bool(
                alerts[
                    "battery"
                ]
            ),
            sensor_failure_alerts_enabled=bool(
                alerts[
                    "sensorFailure"
                ]
            ),
            offline_queue_maximum_items=int(
                merged[
                    "offlineQueueMaximumItems"
                ]
            ),
            active_user_profile=str(
                merged[
                    "activeUserProfile"
                ]
            ),
            analytics_enabled=bool(
                merged[
                    "analyticsEnabled"
                ]
            ),
        )

    def _validate_merged(
        self,
        config: dict[str, Any],
        errors: list[str],
    ) -> None:
        """Validate a complete merged configuration."""

        self._validate_number(
            config.get(
                "measurementIntervalSec"
            ),
            "measurementIntervalSec",
            errors,
            minimum=0.5,
        )

        self._validate_number(
            config.get(
                "telemetryIntervalSec"
            ),
            "telemetryIntervalSec",
            errors,
            minimum=1.0,
        )

        self._validate_number(
            config.get(
                "analyticsWindowSec"
            ),
            "analyticsWindowSec",
            errors,
            minimum=1.0,
        )

        self._validate_number(
            config.get(
                "healthReportIntervalSec"
            ),
            "healthReportIntervalSec",
            errors,
            minimum=1.0,
        )

        unit = config.get(
            "temperatureUnit"
        )

        if unit not in {
            TemperatureUnit.CELSIUS.value,
            TemperatureUnit.FAHRENHEIT.value,
        }:
            errors.append(
                "temperatureUnit must be "
                "CELSIUS or FAHRENHEIT."
            )

        thresholds = config.get(
            "thresholds"
        )

        if isinstance(
            thresholds,
            dict,
        ):
            self._validate_number(
                thresholds.get(
                    "heartRateMinimumBpm"
                ),
                "heartRateMinimumBpm",
                errors,
                minimum=20.0,
                maximum=250.0,
            )

            self._validate_number(
                thresholds.get(
                    "heartRateMaximumRestingBpm"
                ),
                "heartRateMaximumRestingBpm",
                errors,
                minimum=20.0,
                maximum=250.0,
            )

            self._validate_number(
                thresholds.get(
                    "skinTemperatureMinimumC"
                ),
                "skinTemperatureMinimumC",
                errors,
                minimum=20.0,
                maximum=45.0,
            )

            self._validate_number(
                thresholds.get(
                    "skinTemperatureMaximumC"
                ),
                "skinTemperatureMaximumC",
                errors,
                minimum=20.0,
                maximum=45.0,
            )

            self._validate_number(
                thresholds.get(
                    "lowBatteryPercentage"
                ),
                "lowBatteryPercentage",
                errors,
                minimum=0.0,
                maximum=100.0,
            )

            heart_min = thresholds.get(
                "heartRateMinimumBpm"
            )

            heart_max = thresholds.get(
                "heartRateMaximumRestingBpm"
            )

            if (
                self._is_number(
                    heart_min
                )
                and self._is_number(
                    heart_max
                )
                and float(
                    heart_min
                )
                >= float(
                    heart_max
                )
            ):
                errors.append(
                    "heartRateMinimumBpm must be "
                    "lower than "
                    "heartRateMaximumRestingBpm."
                )

            temp_min = thresholds.get(
                "skinTemperatureMinimumC"
            )

            temp_max = thresholds.get(
                "skinTemperatureMaximumC"
            )

            if (
                self._is_number(
                    temp_min
                )
                and self._is_number(
                    temp_max
                )
                and float(
                    temp_min
                )
                >= float(
                    temp_max
                )
            ):
                errors.append(
                    "skinTemperatureMinimumC must be "
                    "lower than "
                    "skinTemperatureMaximumC."
                )

        alerts = config.get(
            "alerts"
        )

        if isinstance(
            alerts,
            dict,
        ):
            for key in self._ALLOWED_ALERTS:
                if not isinstance(
                    alerts.get(
                        key
                    ),
                    bool,
                ):
                    errors.append(
                        f"alerts.{key} must be boolean."
                    )

        if not isinstance(
            config.get(
                "analyticsEnabled"
            ),
            bool,
        ):
            errors.append(
                "analyticsEnabled must be boolean."
            )

        queue_maximum = config.get(
            "offlineQueueMaximumItems"
        )

        if (
            isinstance(
                queue_maximum,
                bool,
            )
            or not isinstance(
                queue_maximum,
                int,
            )
            or queue_maximum <= 0
        ):
            errors.append(
                "offlineQueueMaximumItems must "
                "be a positive integer."
            )

        profile = config.get(
            "activeUserProfile"
        )

        if (
            not isinstance(
                profile,
                str,
            )
            or not profile.strip()
        ):
            errors.append(
                "activeUserProfile must "
                "be a non-empty string."
            )

    @staticmethod
    def _is_number(
        value: Any,
    ) -> bool:
        return (
            not isinstance(
                value,
                bool,
            )
            and isinstance(
                value,
                (int, float),
            )
        )

    def _validate_number(
        self,
        value: Any,
        name: str,
        errors: list[str],
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> None:
        if not self._is_number(
            value
        ):
            errors.append(
                f"{name} must be numeric."
            )
            return

        numeric = float(
            value
        )

        if (
            minimum is not None
            and numeric < minimum
        ):
            errors.append(
                f"{name} must be at least "
                f"{minimum}."
            )

        if (
            maximum is not None
            and numeric > maximum
        ):
            errors.append(
                f"{name} must not exceed "
                f"{maximum}."
            )