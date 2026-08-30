"""Simulated oxygen-saturation sensor introduced in HealthBand 2.0.0."""

from device_simulator.sensors.base_sensor import (
    BaseSensor,
    SensorReading,
    SensorStatus,
)
from device_simulator.simulation.scenario import (
    ScenarioContext,
)
from device_simulator.simulation.signal_generator import (
    SignalGenerator,
)


class SpO2Sensor(BaseSensor):
    """Generate smooth simulated SpO2 values for demonstration purposes."""

    def __init__(
        self,
        signal_generator: SignalGenerator,
    ) -> None:
        super().__init__("spo2")

        self._signal_generator = (
            signal_generator
        )

        self._current_percentage = (
            98.0
        )

    @property
    def current_percentage(self) -> float:
        """Return the current internal oxygen-saturation value."""

        return (
            self._current_percentage
        )

    def read(
        self,
        context: ScenarioContext,
        elapsed_sec: float,
    ) -> SensorReading:
        """Generate one simulated SpO2 measurement."""

        if self.status in {
            SensorStatus.FAILED,
            SensorStatus.DISABLED,
        }:
            return (
                self._unavailable_reading()
            )

        max_delta = max(
            0.08,
            0.18 * max(
                elapsed_sec,
                0.1,
            ),
        )

        self._current_percentage = (
            self._signal_generator
            .move_towards(
                current=(
                    self._current_percentage
                ),
                target=(
                    context
                    .spo2_target_percentage
                ),
                max_delta=(
                    max_delta
                ),
                noise=0.12,
                minimum=85.0,
                maximum=100.0,
            )
        )

        value = round(
            self._current_percentage,
            1,
        )

        return self._reading(
            {
                "oxygenSaturationPercentage": (
                    value
                )
            }
        )