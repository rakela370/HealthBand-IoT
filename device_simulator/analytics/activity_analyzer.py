"""Activity and scenario analytics for HealthBand."""

from collections import Counter
from collections.abc import Sequence
from typing import Any

from device_simulator.analytics.base_analyzer import (
    BaseAnalyzer,
)
from device_simulator.sensors.sensor_manager import (
    SensorSnapshot,
)


class ActivityAnalyzer(BaseAnalyzer):
    """Determine dominant activity and simulation scenario."""

    def analyze(
        self,
        snapshots: Sequence[SensorSnapshot],
    ) -> dict[str, Any]:
        """Calculate dominant scenario and activity."""

        if not snapshots:
            return {}

        scenarios = Counter(
            snapshot.scenario
            for snapshot in snapshots
        )

        activities = Counter(
            snapshot.activity_level
            for snapshot in snapshots
        )

        dominant_scenario = (
            scenarios.most_common(1)[0][0]
        )

        dominant_activity = (
            activities.most_common(1)[0][0]
        )

        return {
            "dominantScenario": dominant_scenario,
            "activity": {
                "dominantLevel": dominant_activity,
            },
        }