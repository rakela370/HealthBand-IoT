"""HealthBand alert models."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class AlertSeverity(StrEnum):
    """Technical alert priority."""

    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"


class AlertType(StrEnum):
    """Alert types supported by the HealthBand architecture."""

    HEART_RATE_BELOW_THRESHOLD = (
        "HEART_RATE_BELOW_THRESHOLD"
    )

    HEART_RATE_ABOVE_RESTING_THRESHOLD = (
        "HEART_RATE_ABOVE_RESTING_THRESHOLD"
    )

    OVEREXERTION_HEART_RATE = (
        "OVEREXERTION_HEART_RATE"
    )

    TEMPERATURE_BELOW_THRESHOLD = (
        "TEMPERATURE_BELOW_THRESHOLD"
    )

    TEMPERATURE_ABOVE_THRESHOLD = (
        "TEMPERATURE_ABOVE_THRESHOLD"
    )

    LOW_BATTERY = "LOW_BATTERY"

    SENSOR_NO_DATA = "SENSOR_NO_DATA"

    SENSOR_INVALID_VALUE = (
        "SENSOR_INVALID_VALUE"
    )

    SENSOR_FAILED = "SENSOR_FAILED"

    MQTT_DISCONNECTED = "MQTT_DISCONNECTED"

    OFFLINE_QUEUE_NEAR_LIMIT = (
        "OFFLINE_QUEUE_NEAR_LIMIT"
    )

    OTA_UPDATE_FAILED = "OTA_UPDATE_FAILED"

    DEVICE_INTERNAL_ERROR = (
        "DEVICE_INTERNAL_ERROR"
    )

    SPO2_BELOW_THRESHOLD = (
        "SPO2_BELOW_THRESHOLD"
    )

    SPO2_SENSOR_FAILED = (
        "SPO2_SENSOR_FAILED"
    )


@dataclass(frozen=True, slots=True)
class Alert:
    """One technical HealthBand alert."""

    alert_id: str
    device_id: str

    type: AlertType
    severity: AlertSeverity

    timestamp: datetime

    scenario: str
    activity_level: str

    measured_value: Any = None
    configured_threshold: Any = None

    sensor_name: str | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert alert into a serializable dictionary."""

        return {
            "schemaVersion": 1,
            "alertId": self.alert_id,
            "deviceId": self.device_id,
            "type": self.type.value,
            "severity": self.severity.value,
            "measuredValue": (
                self.measured_value
            ),
            "configuredThreshold": (
                self.configured_threshold
            ),
            "sensorName": self.sensor_name,
            "activityLevel": (
                self.activity_level
            ),
            "scenario": self.scenario,
            "message": self.message,
            "timestamp": (
                self.timestamp.isoformat()
            ),
            "simulated": True,
        }