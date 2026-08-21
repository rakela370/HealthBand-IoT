"""Base interface for HealthBand local analytics modules."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from device_simulator.sensors.sensor_manager import (
    SensorSnapshot,
)


class BaseAnalyzer(ABC):
    """Base interface implemented by analytics components."""

    @abstractmethod
    def analyze(
        self,
        snapshots: Sequence[SensorSnapshot],
    ) -> dict[str, Any]:
        """Analyze a sequence of sensor snapshots."""

        raise NotImplementedError