"""Simulated HealthBand battery model."""

from device_simulator.sensors.base_sensor import (
    BaseSensor,
    SensorReading,
    SensorStatus,
)
from device_simulator.simulation.scenario import (
    ScenarioContext,
)


class BatteryModel(BaseSensor):
    """Simulate HealthBand battery discharge and charging."""

    def __init__(
        self,
        initial_percentage: float = 100.0,
    ) -> None:
        super().__init__("battery")

        self._percentage = max(
            0.0,
            min(
                100.0,
                float(initial_percentage),
            ),
        )

        self._charging = False

    @property
    def percentage(self) -> float:
        """Return current battery percentage."""

        return self._percentage

    @property
    def charging(self) -> bool:
        """Return whether simulated charging is active."""

        return self._charging

    def start_charging(self) -> None:
        """Start simulated charging."""

        self._charging = True

    def stop_charging(self) -> None:
        """Stop simulated charging."""

        self._charging = False

    def set_percentage(
        self,
        percentage: float,
    ) -> None:
        """Directly set battery level for simulation/testing."""

        if not 0 <= percentage <= 100:
            raise ValueError(
                "Battery percentage must be between "
                "0 and 100."
            )

        self._percentage = float(percentage)

    def read(
        self,
        context: ScenarioContext,
        elapsed_sec: float,
    ) -> SensorReading:
        """Update and return simulated battery state."""

        if self.status in {
            SensorStatus.FAILED,
            SensorStatus.DISABLED,
        }:
            return self._unavailable_reading()

        elapsed = max(
            elapsed_sec,
            0.0,
        )

        if (
            context.force_low_battery
            and self._percentage > 12.0
        ):
            self._percentage = 12.0

        if self._charging:
            self._percentage = min(
                100.0,
                self._percentage
                + (0.08 * elapsed),
            )

        else:
            drain_per_second = (
                0.004
                * context.battery_drain_multiplier
            )

            self._percentage = max(
                0.0,
                self._percentage
                - (
                    drain_per_second
                    * elapsed
                ),
            )

        estimated_remaining_minutes: int | None = None

        if (
            not self._charging
            and self._percentage > 0
        ):
            drain_per_minute = max(
                0.001,
                (
                    0.004
                    * context.battery_drain_multiplier
                    * 60.0
                ),
            )

            estimated_remaining_minutes = int(
                self._percentage
                / drain_per_minute
            )

        return self._reading(
            {
                "batteryPercentage": round(
                    self._percentage,
                    2,
                ),
                "charging": self._charging,
                "estimatedRemainingTimeMinutes": (
                    estimated_remaining_minutes
                ),
            }
        )