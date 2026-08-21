"""Simulated step-counter sensor."""

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


class StepCounterSensor(BaseSensor):
    """Generate simulated interval and daily step counts."""

    def __init__(
        self,
        signal_generator: SignalGenerator,
    ) -> None:
        super().__init__("step_counter")

        self._signal_generator = signal_generator

        self._total_daily_steps = 0
        self._fractional_steps = 0.0

    @property
    def total_daily_steps(self) -> int:
        """Return the current simulated daily total."""

        return self._total_daily_steps

    def reset_daily_steps(self) -> None:
        """Reset the simulated daily step count."""

        self._total_daily_steps = 0
        self._fractional_steps = 0.0

    def read(
        self,
        context: ScenarioContext,
        elapsed_sec: float,
    ) -> SensorReading:
        """Generate the number of steps for this interval."""

        if self.status in {
            SensorStatus.FAILED,
            SensorStatus.DISABLED,
        }:
            return self._unavailable_reading()

        elapsed = max(
            elapsed_sec,
            0.0,
        )

        expected_steps = (
            context.steps_per_minute
            * elapsed
            / 60.0
        )

        if expected_steps > 0:
            expected_steps *= (
                self._signal_generator.variation_factor(
                    0.08
                )
            )

        self._fractional_steps += expected_steps

        steps_in_interval = int(
            self._fractional_steps
        )

        self._fractional_steps -= (
            steps_in_interval
        )

        self._total_daily_steps += (
            steps_in_interval
        )

        return self._reading(
            {
                "stepsInInterval": steps_in_interval,
                "totalDailySteps": (
                    self._total_daily_steps
                ),
            }
        )