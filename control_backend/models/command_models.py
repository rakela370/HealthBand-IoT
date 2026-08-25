"""Pydantic models used by backend command API."""

from enum import StrEnum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class BackendCommandType(StrEnum):
    """Commands supported by HealthBand 1.0.0."""

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


class CommandCreateRequest(BaseModel):
    """REST request for issuing one HealthBand command."""

    model_config = ConfigDict(
        extra="forbid"
    )

    type: BackendCommandType

    parameters: dict[
        str,
        Any,
    ] = Field(
        default_factory=dict
    )