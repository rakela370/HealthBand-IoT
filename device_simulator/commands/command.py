"""Models used by the HealthBand command subsystem."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class CommandType(StrEnum):
    """Commands supported by HealthBand version 1.0.0."""

    START_MONITORING = "START_MONITORING"
    STOP_MONITORING = "STOP_MONITORING"
    RESTART_DEVICE = "RESTART_DEVICE"

    ENTER_MAINTENANCE = "ENTER_MAINTENANCE"
    EXIT_MAINTENANCE = "EXIT_MAINTENANCE"

    START_CHARGING = "START_CHARGING"
    STOP_CHARGING = "STOP_CHARGING"

    CALIBRATE_SENSOR = "CALIBRATE_SENSOR"

    REQUEST_IMMEDIATE_MEASUREMENT = (
        "REQUEST_IMMEDIATE_MEASUREMENT"
    )

    REQUEST_DEVICE_HEALTH = (
        "REQUEST_DEVICE_HEALTH"
    )

    CLEAR_ALERTS = "CLEAR_ALERTS"

    CHANGE_SIMULATION_SCENARIO = (
        "CHANGE_SIMULATION_SCENARIO"
    )

    SIMULATE_SENSOR_FAILURE = (
        "SIMULATE_SENSOR_FAILURE"
    )

    RESTORE_SENSOR = "RESTORE_SENSOR"

    SIMULATE_NETWORK_OUTAGE = (
        "SIMULATE_NETWORK_OUTAGE"
    )

    RESTORE_NETWORK = "RESTORE_NETWORK"


class CommandStatus(StrEnum):
    """Command execution statuses."""

    RECEIVED = "RECEIVED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class Command:
    """One validated command request."""

    command_id: str
    device_id: str
    type: CommandType

    parameters: dict[str, Any]

    received_at: datetime


@dataclass(frozen=True, slots=True)
class CommandResult:
    """One command status/result message."""

    command_id: str
    device_id: str
    command_type: str
    status: CommandStatus

    message: str

    details: dict[str, Any] | None = None
    error_code: str | None = None

    duplicate: bool = False

    timestamp: datetime = datetime.min.replace(
        tzinfo=timezone.utc
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """Convert command result to MQTT payload."""

        timestamp = (
            self.timestamp
            if (
                self.timestamp
                != datetime.min.replace(
                    tzinfo=timezone.utc
                )
            )
            else datetime.now(
                timezone.utc
            )
        )

        payload: dict[
            str,
            Any,
        ] = {
            "schemaVersion": 1,
            "commandId": (
                self.command_id
            ),
            "deviceId": (
                self.device_id
            ),
            "type": (
                self.command_type
            ),
            "status": (
                self.status.value
            ),
            "message": (
                self.message
            ),
            "duplicate": (
                self.duplicate
            ),
            "timestamp": (
                timestamp.isoformat()
            ),
        }

        if self.details is not None:
            payload[
                "details"
            ] = self.details

        if self.error_code is not None:
            payload[
                "errorCode"
            ] = self.error_code

        return payload