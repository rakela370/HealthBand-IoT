"""Simulated step-counter sensor."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from device_simulator.sensors.base_sensor import (
    BaseSensor,
    SensorReading,
    SensorStatus,
)
from device_simulator.simulation.scenario import ScenarioContext
from device_simulator.simulation.signal_generator import SignalGenerator


class StepCounterSensor(BaseSensor):
    """Generate smooth cadence, interval steps and a persistent daily total."""

    def __init__(
        self,
        signal_generator: SignalGenerator,
        timezone_name: str = "Europe/Sarajevo",
    ) -> None:
        super().__init__("step_counter")
        self._signal_generator = signal_generator
        self._timezone = ZoneInfo(timezone_name)
        self._total_daily_steps = 0
        self._fractional_steps = 0.0
        self._current_cadence = 0.0
        self._local_date = self._today()

    @property
    def total_daily_steps(self) -> int:
        """Return the current simulated daily total."""
        return self._total_daily_steps

    @property
    def fractional_steps(self) -> float:
        return self._fractional_steps

    @property
    def current_cadence(self) -> float:
        """Return current smoothed cadence in steps/minute."""
        return self._current_cadence

    @property
    def local_date(self) -> str:
        """Return local date associated with the daily counter."""
        return self._local_date

    def _today(self) -> str:
        return datetime.now(timezone.utc).astimezone(self._timezone).date().isoformat()

    def reset_daily_steps(self) -> None:
        """Reset the simulated daily step count."""
        self._total_daily_steps = 0
        self._fractional_steps = 0.0
        self._local_date = self._today()

    def restore_runtime_state(
        self,
        *,
        total_daily_steps: int,
        fractional_steps: float = 0.0,
        cadence_steps_per_minute: float = 0.0,
        local_date: str | None = None,
    ) -> None:
        """Restore daily counter and cadence after process restart/OTA."""

        restored_date = local_date or self._today()
        if restored_date != self._today():
            self.reset_daily_steps()
            return

        self._local_date = restored_date
        self._total_daily_steps = max(0, int(total_daily_steps))
        self._fractional_steps = max(0.0, min(0.999999, float(fractional_steps)))
        self._current_cadence = max(0.0, min(240.0, float(cadence_steps_per_minute)))

    def read(
        self,
        context: ScenarioContext,
        elapsed_sec: float,
    ) -> SensorReading:
        """Generate the number of steps for this interval."""

        if self.status in {SensorStatus.FAILED, SensorStatus.DISABLED}:
            return self._unavailable_reading()

        if self._local_date != self._today():
            self.reset_daily_steps()

        elapsed = max(float(elapsed_sec), 0.0)
        self._current_cadence = self._signal_generator.exponential_towards(
            current=self._current_cadence,
            target=context.steps_per_minute,
            elapsed_sec=elapsed,
            time_constant_sec=context.cadence_time_constant_sec,
            noise=0.8 if context.steps_per_minute > 0 else 0.0,
            minimum=0.0,
            maximum=240.0,
        )

        expected_steps = self._current_cadence * elapsed / 60.0
        if expected_steps > 0:
            expected_steps *= self._signal_generator.variation_factor(0.03)

        self._fractional_steps += expected_steps
        steps_in_interval = int(self._fractional_steps)
        self._fractional_steps -= steps_in_interval
        self._total_daily_steps += steps_in_interval

        return self._reading(
            {
                "stepsInInterval": steps_in_interval,
                "totalDailySteps": self._total_daily_steps,
                "cadenceStepsPerMinute": round(self._current_cadence, 1),
            }
        )
