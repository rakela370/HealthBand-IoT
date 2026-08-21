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
from device_simulator.sensors.sensor_manager import (
    SensorSnapshot,
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
            "schemaVersion": 1,
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

    EXPECTED_MEASUREMENTS = {
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
    ) -> None:
        if window_sec <= 0:
            raise ValueError(
                "Analytics window must be greater than zero."
            )

        self.device_id = device_id
        self.software_version = software_version
        self.window_sec = window_sec

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

    def add_snapshot(
        self,
        snapshot: SensorSnapshot,
        elapsed_sec: float,
        alerts_generated: int = 0,
    ) -> AnalyticsResult | None:
        """
        Add one measurement to the current analytics window.

        Returns a completed AnalyticsResult when the configured
        window duration has been reached.
        """

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

    def _calculate_data_quality(
        self,
        snapshots: tuple[SensorSnapshot, ...],
    ) -> float:
        """Calculate percentage of valid expected sensor values."""

        if not snapshots:
            return 0.0

        valid = 0

        total = (
            len(snapshots)
            * len(
                self.EXPECTED_MEASUREMENTS
            )
        )

        for snapshot in snapshots:
            for (
                sensor_name,
                measurement_name,
            ) in self.EXPECTED_MEASUREMENTS.items():

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