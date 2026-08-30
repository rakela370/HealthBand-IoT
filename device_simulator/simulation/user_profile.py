"""Synthetic user profile used only to parameterize the simulation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserProfile:
    """
    Synthetic profile used as a baseline for HealthBand simulation.

    The values are not medical recommendations and do not represent
    measurements of a real user.
    """

    user_id: str = "simulated-user-001"

    sleeping_heart_rate_bpm: float = 58.0
    resting_heart_rate_bpm: float = 72.0
    walking_heart_rate_bpm: float = 98.0
    running_heart_rate_bpm: float = 148.0
    exercising_heart_rate_bpm: float = 132.0
    recovery_heart_rate_bpm: float = 88.0
    stress_heart_rate_bpm: float = 122.0

    base_skin_temperature_c: float = 33.6

    # Synthetic profile values used only by derived calorie estimation.
    weight_kg: float = 75.0
    timezone_name: str = "Europe/Sarajevo"