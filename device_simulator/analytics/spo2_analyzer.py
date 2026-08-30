"""SpO2 analytics introduced in HealthBand 2.0.0."""

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


class SpO2Analyzer(BaseAnalyzer):
    """Calculate aggregate statistics for simulated SpO2 measurements."""

    def __init__(
        self,
        minimum_threshold: float = 92.0,
    ) -> None:
        self.minimum_threshold = float(
            minimum_threshold
        )

    def analyze(
        self,
        snapshots: Sequence[SensorSnapshot],
    ) -> dict[str, Any]:
        """Calculate SpO2 statistics for one analytics window."""

        values = [
            float(
                snapshot.measurements[
                    "oxygenSaturationPercentage"
                ]
            )
            for snapshot in snapshots
            if (
                "oxygenSaturationPercentage"
                in snapshot.measurements
            )
        ]

        statistics = (
            calculate_statistics(
                values
            )
        )

        if statistics is None:
            return {}

        below_threshold = sum(
            1
            for value in values
            if value < self.minimum_threshold
        )

        expected_samples = sum(
            1
            for snapshot in snapshots
            if (
                snapshot.sensor_status.get(
                    "spo2"
                )
                != "DISABLED"
            )
        )

        data_quality = (
            100.0
            if expected_samples == 0
            else (
                100.0
                * statistics.count
                / expected_samples
            )
        )

        return {
            "spo2": {
                "averagePercentage": round(
                    statistics.average,
                    2,
                ),
                "minimumPercentage": round(
                    statistics.minimum,
                    2,
                ),
                "maximumPercentage": round(
                    statistics.maximum,
                    2,
                ),
                "validSamples": (
                    statistics.count
                ),
                "belowThresholdSamples": (
                    below_threshold
                ),
                "configuredMinimumThreshold": (
                    self.minimum_threshold
                ),
                "dataQualityPercentage": round(
                    data_quality,
                    2,
                ),
            }
        }