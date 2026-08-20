"""Logical states supported by the simulated HealthBand device."""

from enum import StrEnum


class DeviceState(StrEnum):
    """All logical states defined for the HealthBand device."""

    BOOTING = "BOOTING"
    SELF_TEST = "SELF_TEST"
    CONNECTING = "CONNECTING"
    MONITORING = "MONITORING"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    LOW_BATTERY = "LOW_BATTERY"
    CHARGING = "CHARGING"
    MAINTENANCE = "MAINTENANCE"
    UPDATING = "UPDATING"
    RESTARTING = "RESTARTING"
    ERROR = "ERROR"
    SHUTTING_DOWN = "SHUTTING_DOWN"
