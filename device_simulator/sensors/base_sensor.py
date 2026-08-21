"""Base classes shared by simulated HealthBand sensors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from device_simulator.simulation.scenario import (
    ScenarioContext,
)


class SensorStatus(StrEnum):
    """Technical state of a simulated sensor."""

    INITIALIZING = "INITIALIZING"
    OK = "OK"
    CALIBRATING = "CALIBRATING"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


@dataclass(frozen=True, slots=True)
class SensorReading:
    """One reading returned by a HealthBand sensor."""

    sensor_name: str
    values: dict[str, Any]
    status: SensorStatus
    timestamp: datetime
    valid: bool


class BaseSensor(ABC):
    """Common functionality shared by every simulated sensor."""

    def __init__(
        self,
        name: str,
    ) -> None:
        self.name = name

        self._status = SensorStatus.INITIALIZING

        # There is no physical hardware initialization in the
        # simulator, therefore the sensor becomes ready immediately.
        self._status = SensorStatus.OK

    @property
    def status(self) -> SensorStatus:
        """Return the current technical sensor status."""

        return self._status

    def simulate_failure(self) -> None:
        """Put the sensor into FAILED state."""

        self._status = SensorStatus.FAILED

    def restore(self) -> None:
        """Restore a simulated sensor to normal operation."""

        self._status = SensorStatus.OK

    def disable(self) -> None:
        """Disable this sensor."""

        self._status = SensorStatus.DISABLED

    def enable(self) -> None:
        """Enable a previously disabled sensor."""

        if self._status == SensorStatus.DISABLED:
            self._status = SensorStatus.OK

    def calibrate(self) -> None:
        """Simulate a simple calibration operation."""

        if self._status in {
            SensorStatus.FAILED,
            SensorStatus.DISABLED,
        }:
            return

        self._status = SensorStatus.CALIBRATING

        # Physical calibration delay is not simulated in Module 2.
        self._status = SensorStatus.OK

    def _unavailable_reading(
        self,
    ) -> SensorReading:
        """Create a reading representing unavailable sensor data."""

        return SensorReading(
            sensor_name=self.name,
            values={},
            status=self._status,
            timestamp=datetime.now(timezone.utc),
            valid=False,
        )

    def _reading(
        self,
        values: dict[str, Any],
    ) -> SensorReading:
        """Create a valid sensor reading."""

        return SensorReading(
            sensor_name=self.name,
            values=values,
            status=self._status,
            timestamp=datetime.now(timezone.utc),
            valid=True,
        )

    @abstractmethod
    def read(
        self,
        context: ScenarioContext,
        elapsed_sec: float,
    ) -> SensorReading:
        """Generate one simulated sensor reading."""

        raise NotImplementedError