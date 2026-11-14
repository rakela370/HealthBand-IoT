"""Simulated heart-rate sensor."""

from device_simulator.sensors.base_sensor import (
    BaseSensor,
    SensorReading,
    SensorStatus,
)
from device_simulator.simulation.scenario import (
    ScenarioContext,
    SimulationScenario,
)
from device_simulator.simulation.signal_generator import SignalGenerator
from device_simulator.simulation.user_profile import UserProfile


class HeartRateSensor(BaseSensor):
    """Generate smooth simulated heart-rate measurements."""

    def __init__(
        self,
        signal_generator: SignalGenerator,
        user_profile: UserProfile,
    ) -> None:
        super().__init__("heart_rate")
        self._signal_generator = signal_generator
        self._current_bpm = float(user_profile.resting_heart_rate_bpm)

    @property
    def current_bpm(self) -> float:
        """Return the current internal heart-rate value."""
        return self._current_bpm

    def restore_runtime_value(self, bpm: float) -> None:
        """Restore persisted HR after restart/OTA without creating a jump."""
        self._current_bpm = max(35.0, min(210.0, float(bpm)))

    def read(
        self,
        context: ScenarioContext,
        elapsed_sec: float,
    ) -> SensorReading:
        """Generate one heart-rate measurement."""

        if self.status in {SensorStatus.FAILED, SensorStatus.DISABLED}:
            return self._unavailable_reading()

        time_constant_sec = context.heart_rate_time_constant_sec

        # A sudden threat is different from normal exercise onset: sympathetic
        # activation can accelerate HR within only a few beats. If the user is
        # already above the stress target (for example while running), do not
        # create an artificial rapid HR drop just because STRESS_EVENT starts.
        if (
            context.scenario == SimulationScenario.STRESS_EVENT
            and self._current_bpm > context.heart_rate_target_bpm
        ):
            time_constant_sec = 60.0

        self._current_bpm = self._signal_generator.exponential_towards(
            current=self._current_bpm,
            target=context.heart_rate_target_bpm,
            elapsed_sec=elapsed_sec,
            time_constant_sec=time_constant_sec,
            noise=0.35,
            minimum=35.0,
            maximum=210.0,
        )

        return self._reading({"heartRateBpm": int(round(self._current_bpm))})
