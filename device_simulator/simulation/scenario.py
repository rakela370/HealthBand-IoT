"""Scenario definitions and simulation context models."""

from dataclasses import dataclass
from enum import StrEnum


class ActivityLevel(StrEnum):
    """Activity levels reported by the simulated HealthBand."""

    SLEEPING = "SLEEPING"
    RESTING = "RESTING"
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class SimulationScenario(StrEnum):
    """Simulation scenarios supported by HealthBand."""

    SLEEPING = "SLEEPING"
    RESTING = "RESTING"
    WALKING = "WALKING"
    RUNNING = "RUNNING"
    EXERCISING = "EXERCISING"
    RECOVERY = "RECOVERY"
    STRESS_EVENT = "STRESS_EVENT"
    OVEREXERTION = "OVEREXERTION"

    # Technical fault/demo overlays. They must not replace the user's
    # physiological activity; ScenarioEngine keeps the physical scenario
    # active while applying the requested technical effect.
    SENSOR_FAILURE = "SENSOR_FAILURE"
    LOW_BATTERY = "LOW_BATTERY"
    NETWORK_OUTAGE = "NETWORK_OUTAGE"


@dataclass(frozen=True, slots=True)
class ScenarioContext:
    """Parameters that sensors use while generating simulated values."""

    scenario: SimulationScenario
    activity_level: ActivityLevel

    heart_rate_target_bpm: float
    skin_temperature_target_c: float
    steps_per_minute: float

    battery_drain_multiplier: float
    spo2_target_percentage: float = 98.0

    # First-order response constants. They intentionally differ between
    # signals because cardiovascular, gait and distal-skin responses do not
    # change on the same time scale.
    heart_rate_time_constant_sec: float = 45.0
    cadence_time_constant_sec: float = 8.0
    skin_temperature_time_constant_sec: float = 240.0
    spo2_time_constant_sec: float = 20.0

    failed_sensor_name: str | None = None
    force_low_battery: bool = False
