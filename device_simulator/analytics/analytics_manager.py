"""Window-based local analytics manager for HealthBand."""

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4
from typing import Any

from device_simulator.analytics.activity_analyzer import (
    ActivityAnalyzer,
)
from device_simulator.analytics.health_metrics_analyzer import (
    HealthMetricsAnalyzer,
)
from device_simulator.analytics.spo2_analyzer import (
    SpO2Analyzer,
)
from device_simulator.sensors.sensor_manager import (
    SensorSnapshot,
)
from device_simulator.utils.versioning import (
    is_at_least,
)


@dataclass(frozen=True, slots=True)
class AnalyticsResult:
    """One completed local analytics window."""

    message_id: str
    device_id: str
    software_version: str

    window_start: datetime
    window_end: datetime

    analytics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a serializable dictionary."""

        return {
            "schemaVersion": (
                2
                if is_at_least(
                    self.software_version,
                    "2.0.0",
                )
                else 1
            ),
            "messageId": self.message_id,
            "deviceId": self.device_id,
            "windowStart": (
                self.window_start.isoformat()
            ),
            "windowEnd": (
                self.window_end.isoformat()
            ),
            "softwareVersion": (
                self.software_version
            ),
            "analytics": self.analytics,
            "simulated": True,
        }


class AnalyticsManager:
    """Collect measurements and periodically calculate analytics."""

    EXPECTED_MEASUREMENTS_V1 = {
        "heart_rate": "heartRateBpm",
        "skin_temperature": (
            "skinTemperatureCelsius"
        ),
        "step_counter": "stepsInInterval",
        "battery": "batteryPercentage",
    }

    def __init__(
        self,
        device_id: str,
        software_version: str,
        window_sec: float = 10.0,
        spo2_minimum_threshold: float = 92.0,
        spo2_enabled: bool | None = None,
    ) -> None:
        if window_sec <= 0:
            raise ValueError(
                "Analytics window must be greater than zero."
            )

        self.device_id = device_id
        self.software_version = software_version
        self.window_sec = window_sec

        self._supports_spo2 = is_at_least(
            software_version,
            "2.0.0",
        )

        self._spo2_enabled = (
            self._supports_spo2
            if spo2_enabled is None
            else (
                self._supports_spo2
                and bool(
                    spo2_enabled
                )
            )
        )

        self._snapshots: list[
            SensorSnapshot
        ] = []

        self._elapsed_sec = 0.0
        self._alerts_generated = 0

        self._health_analyzer = (
            HealthMetricsAnalyzer()
        )

        self._activity_analyzer = (
            ActivityAnalyzer()
        )

        self._spo2_analyzer = (
            SpO2Analyzer(
                minimum_threshold=(
                    spo2_minimum_threshold
                )
            )
            if self._supports_spo2
            else None
        )

    def add_snapshot(
        self,
        snapshot: SensorSnapshot,
        elapsed_sec: float,
        alerts_generated: int = 0,
    ) -> AnalyticsResult | None:
        """Add one measurement and complete the window when due."""

        if elapsed_sec <= 0:
            raise ValueError(
                "elapsed_sec must be greater than zero."
            )

        self._snapshots.append(
            snapshot
        )

        self._elapsed_sec += elapsed_sec

        self._alerts_generated += max(
            0,
            alerts_generated,
        )

        if self._elapsed_sec < self.window_sec:
            return None

        return self._complete_window()

    def _complete_window(
        self,
    ) -> AnalyticsResult:
        """Calculate and reset one analytics window."""

        snapshots = tuple(
            self._snapshots
        )

        analytics = (
            self._health_analyzer.analyze(
                snapshots
            )
        )

        analytics.update(
            self._activity_analyzer.analyze(
                snapshots
            )
        )

        if (
            self._spo2_analyzer is not None
            and self._spo2_enabled
        ):
            analytics.update(
                self._spo2_analyzer.analyze(
                    snapshots
                )
            )

        calorie_intervals = [
            float(
                snapshot.measurements[
                    "caloriesBurnedInInterval"
                ]
            )
            for snapshot in snapshots
            if (
                "caloriesBurnedInInterval"
                in snapshot.measurements
            )
        ]

        calorie_totals = [
            float(
                snapshot.measurements[
                    "caloriesBurnedToday"
                ]
            )
            for snapshot in snapshots
            if (
                "caloriesBurnedToday"
                in snapshot.measurements
            )
        ]

        if calorie_intervals:
            analytics[
                "calories"
            ] = {
                "estimated": True,
                "totalKcal": round(
                    sum(
                        calorie_intervals
                    ),
                    2,
                ),
                "averagePerIntervalKcal": round(
                    sum(
                        calorie_intervals
                    )
                    / len(
                        calorie_intervals
                    ),
                    4,
                ),
                "dailyTotalKcal": (
                    round(
                        calorie_totals[-1],
                        2,
                    )
                    if calorie_totals
                    else None
                ),
            }

        analytics["alertsGenerated"] = (
            self._alerts_generated
        )

        analytics["dataQualityPercentage"] = (
            self._calculate_data_quality(
                snapshots
            )
        )

        result = AnalyticsResult(
            message_id=str(uuid4()),
            device_id=self.device_id,
            software_version=(
                self.software_version
            ),
            window_start=(
                snapshots[0].timestamp
            ),
            window_end=(
                snapshots[-1].timestamp
            ),
            analytics=analytics,
        )

        self._snapshots.clear()
        self._elapsed_sec = 0.0
        self._alerts_generated = 0

        return result

    def _expected_measurements(
        self,
    ) -> dict[str, str]:
        expected = dict(
            self.EXPECTED_MEASUREMENTS_V1
        )

        if self._spo2_enabled:
            expected[
                "spo2"
            ] = (
                "oxygenSaturationPercentage"
            )

        return expected

    def _calculate_data_quality(
        self,
        snapshots: tuple[SensorSnapshot, ...],
    ) -> float:
        """Calculate percentage of valid expected sensor values."""

        if not snapshots:
            return 0.0

        expected = (
            self._expected_measurements()
        )

        valid = 0

        total = (
            len(snapshots)
            * len(
                expected
            )
        )

        for snapshot in snapshots:
            for (
                sensor_name,
                measurement_name,
            ) in expected.items():

                status = (
                    snapshot.sensor_status.get(
                        sensor_name
                    )
                )

                if (
                    status == "OK"
                    and measurement_name
                    in snapshot.measurements
                ):
                    valid += 1

        return round(
            100.0 * valid / total,
            2,
        )