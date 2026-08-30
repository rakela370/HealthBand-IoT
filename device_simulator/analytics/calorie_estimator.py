"""Estimated energy expenditure for the simulated HealthBand user.

Calories are derived analytics. They are not directly measured by a sensor.
"""

import json
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from device_simulator.simulation.user_profile import (
    UserProfile,
)
from device_simulator.storage.local_database import (
    LocalDatabase,
)


class CalorieEstimator:
    """Estimate interval and current-day calories using a MET-based model."""

    STATE_PREFIX = "calorie-estimator"

    _MET_BY_ACTIVITY = {
        "SLEEPING": 0.95,
        "RESTING": 1.30,
        "LIGHT": 2.50,
        "MODERATE": 4.00,
        "HIGH": 6.50,
    }

    _SCENARIO_MET_OVERRIDE = {
        "SLEEPING": 0.95,
        "RESTING": 1.30,
        "WALKING": 3.50,
        "RUNNING": 8.30,
        "EXERCISING": 6.00,
        "RECOVERY": 2.00,
        "STRESS_EVENT": 1.50,
        "LOW_BATTERY": 1.30,
        "NETWORK_OUTAGE": 1.30,
        "SENSOR_FAILURE": 1.30,
    }

    def __init__(
        self,
        user_profile: UserProfile,
        database: LocalDatabase | None = None,
    ) -> None:
        self.user_profile = (
            user_profile
        )

        self.database = database

        self._timezone = ZoneInfo(
            user_profile.timezone_name
        )

        self._local_date: str | None = None
        self._calories_today = 0.0

        self._restore_state()

    @property
    def calories_today(self) -> float:
        """Return the current accumulated estimated calories."""

        return round(
            self._calories_today,
            2,
        )

    def estimate_interval(
        self,
        *,
        measurements: dict[str, Any],
        activity_level: str,
        scenario: str,
        elapsed_sec: float,
        timestamp: datetime | None = None,
    ) -> dict[str, float]:
        """Estimate calories for one measurement interval and accumulate today."""

        if elapsed_sec <= 0:
            raise ValueError(
                "elapsed_sec must be greater than zero."
            )

        if timestamp is None:
            timestamp = datetime.now(
                timezone.utc
            )

        if timestamp.tzinfo is None:
            raise ValueError(
                "timestamp must be timezone-aware."
            )

        local_date = (
            timestamp
            .astimezone(
                self._timezone
            )
            .date()
            .isoformat()
        )

        if self._local_date != local_date:
            self._local_date = local_date
            self._calories_today = 0.0

        met = float(
            self._SCENARIO_MET_OVERRIDE.get(
                scenario,
                self._MET_BY_ACTIVITY.get(
                    activity_level,
                    1.30,
                ),
            )
        )

        resting_hr = max(
            1.0,
            float(
                self.user_profile
                .resting_heart_rate_bpm
            ),
        )

        heart_rate = measurements.get(
            "heartRateBpm"
        )

        heart_factor = 1.0

        if heart_rate is not None:
            ratio = (
                float(heart_rate)
                / resting_hr
            )

            heart_factor = min(
                1.25,
                max(
                    0.90,
                    0.85
                    + 0.15 * ratio,
                ),
            )

        kcal_per_minute = (
            met
            * 3.5
            * float(
                self.user_profile.weight_kg
            )
            / 200.0
        )

        interval_kcal = (
            kcal_per_minute
            * (
                elapsed_sec
                / 60.0
            )
            * heart_factor
        )

        interval_kcal = max(
            0.0,
            interval_kcal,
        )

        self._calories_today += (
            interval_kcal
        )

        self._persist_state()

        return {
            "caloriesBurnedInInterval": round(
                interval_kcal,
                4,
            ),
            "caloriesBurnedToday": round(
                self._calories_today,
                2,
            ),
        }

    def _state_key(self) -> str:
        return (
            f"{self.STATE_PREFIX}:"
            f"{self.user_profile.user_id}"
        )

    def _restore_state(self) -> None:
        if self.database is None:
            return

        raw = self.database.get_state(
            self._state_key()
        )

        if raw is None:
            return

        try:
            data = json.loads(
                raw
            )

            local_date = str(
                data.get(
                    "localDate",
                    "",
                )
            ).strip()

            calories = float(
                data.get(
                    "caloriesToday",
                    0.0,
                )
            )

        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            return

        if not local_date:
            return

        self._local_date = local_date
        self._calories_today = max(
            0.0,
            calories,
        )

    def _persist_state(self) -> None:
        if (
            self.database is None
            or self._local_date is None
        ):
            return

        self.database.set_state(
            self._state_key(),
            json.dumps(
                {
                    "localDate": (
                        self._local_date
                    ),
                    "caloriesToday": (
                        self._calories_today
                    ),
                },
                separators=(
                    ",",
                    ":",
                ),
            ),
        )