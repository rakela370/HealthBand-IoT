"""Local analytics for HealthBand simulated measurements."""

from collections.abc import Sequence
from typing import Any

from device_simulator.analytics.base_analyzer import (
    BaseAnalyzer,
)
from device_simulator.analytics.rolling_statistics import (
    calculate_statistics,
)
from device_simulator.sensors.sensor_manager import (
    SensorSnapshot,
)


class HealthMetricsAnalyzer(BaseAnalyzer):
    """Calculate local statistics from HealthBand measurements."""

    def __init__(
        self,
        heart_rate_minimum_threshold: float = 50.0,
        heart_rate_maximum_resting_threshold: float = 110.0,
    ) -> None:
        self._heart_rate_minimum_threshold = (
            heart_rate_minimum_threshold
        )

        self._heart_rate_maximum_resting_threshold = (
            heart_rate_maximum_resting_threshold
        )

    def analyze(
        self,
        snapshots: Sequence[SensorSnapshot],
    ) -> dict[str, Any]:
        """Calculate sensor statistics for one analytics window."""

        heart_rates = [
            float(snapshot.measurements["heartRateBpm"])
            for snapshot in snapshots
            if "heartRateBpm" in snapshot.measurements
        ]

        temperatures = [
            float(
                snapshot.measurements[
                    "skinTemperatureCelsius"
                ]
            )
            for snapshot in snapshots
            if (
                "skinTemperatureCelsius"
                in snapshot.measurements
            )
        ]

        steps = [
            int(
                snapshot.measurements.get(
                    "stepsInInterval",
                    0,
                )
            )
            for snapshot in snapshots
        ]

        batteries = [
            float(snapshot.measurements["batteryPercentage"])
            for snapshot in snapshots
            if "batteryPercentage" in snapshot.measurements
        ]

        analytics: dict[str, Any] = {}

        heart_statistics = calculate_statistics(
            heart_rates
        )

        if heart_statistics is not None:
            threshold_exceedances = 0

            for snapshot in snapshots:
                value = snapshot.measurements.get(
                    "heartRateBpm"
                )

                if value is None:
                    continue

                numeric_value = float(value)

                if (
                    numeric_value
                    < self._heart_rate_minimum_threshold
                ):
                    threshold_exceedances += 1

                elif (
                    snapshot.activity_level == "RESTING"
                    and numeric_value
                    > self._heart_rate_maximum_resting_threshold
                ):
                    threshold_exceedances += 1

            analytics["heartRate"] = {
                "averageBpm": round(
                    heart_statistics.average,
                    2,
                ),
                "minimumBpm": round(
                    heart_statistics.minimum,
                    2,
                ),
                "maximumBpm": round(
                    heart_statistics.maximum,
                    2,
                ),
                "validSamples": (
                    heart_statistics.count
                ),
                "rejectedSamples": (
                    len(snapshots)
                    - heart_statistics.count
                ),
                "thresholdExceedances": (
                    threshold_exceedances
                ),
            }

        temperature_statistics = calculate_statistics(
            temperatures
        )

        if temperature_statistics is not None:
            analytics["skinTemperature"] = {
                "averageCelsius": round(
                    temperature_statistics.average,
                    2,
                ),
                "minimumCelsius": round(
                    temperature_statistics.minimum,
                    2,
                ),
                "maximumCelsius": round(
                    temperature_statistics.maximum,
                    2,
                ),
                "validSamples": (
                    temperature_statistics.count
                ),
            }

        analytics["steps"] = {
            "total": sum(steps),
            "averagePerInterval": round(
                (
                    sum(steps) / len(steps)
                    if steps
                    else 0.0
                ),
                2,
            ),
        }

        if batteries:
            analytics["battery"] = {
                "startPercentage": round(
                    batteries[0],
                    2,
                ),
                "endPercentage": round(
                    batteries[-1],
                    2,
                ),
                "consumptionPercentage": round(
                    max(
                        0.0,
                        batteries[0] - batteries[-1],
                    ),
                    2,
                ),
            }

        return analytics