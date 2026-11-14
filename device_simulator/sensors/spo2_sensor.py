"""Simulated oxygen-saturation sensor introduced in HealthBand 2.0.0."""

from device_simulator.sensors.base_sensor import (
    BaseSensor,
    SensorReading,
    SensorStatus,
)
from device_simulator.simulation.scenario import ScenarioContext
from device_simulator.simulation.signal_generator import SignalGenerator


class SpO2Sensor(BaseSensor):
    """Generate smooth SpO2 values for a healthy synthetic user."""

    def __init__(
        self,
        signal_generator: SignalGenerator,
    ) -> None:
        super().__init__("spo2")
        self._signal_generator = signal_generator
        self._current_percentage = 98.0

    @property
    def current_percentage(self) -> float:
        """Return the current internal oxygen-saturation value."""
        return self._current_percentage

    def restore_runtime_value(self, percentage: float) -> None:
        """Restore persisted SpO2 after restart/OTA."""
        self._current_percentage = max(85.0, min(100.0, float(percentage)))

    def read(
        self,
        context: ScenarioContext,
        elapsed_sec: float,
    ) -> SensorReading:
        """Generate one simulated SpO2 measurement."""

        if self.status in {SensorStatus.FAILED, SensorStatus.DISABLED}:
            return self._unavailable_reading()

        self._current_percentage = self._signal_generator.exponential_towards(
            current=self._current_percentage,
            target=context.spo2_target_percentage,
            elapsed_sec=elapsed_sec,
            time_constant_sec=context.spo2_time_constant_sec,
            noise=0.035,
            minimum=85.0,
            maximum=100.0,
        )

        return self._reading(
            {
                "oxygenSaturationPercentage": round(
                    self._current_percentage,
                    1,
                )
            }
        )
