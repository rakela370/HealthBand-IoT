"""Simulated heart-rate sensor."""

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
from device_simulator.simulation.user_profile import (
    UserProfile,
)


class HeartRateSensor(BaseSensor):
    """Generate smooth simulated heart-rate measurements."""

    def __init__(
        self,
        signal_generator: SignalGenerator,
        user_profile: UserProfile,
    ) -> None:
        super().__init__("heart_rate")

        self._signal_generator = signal_generator

        self._current_bpm = float(
            user_profile.resting_heart_rate_bpm
        )

    @property
    def current_bpm(self) -> float:
        """Return the current internal heart-rate value."""

        return self._current_bpm

    def read(
        self,
        context: ScenarioContext,
        elapsed_sec: float,
    ) -> SensorReading:
        """Generate one heart-rate measurement."""

        if self.status in {
            SensorStatus.FAILED,
            SensorStatus.DISABLED,
        }:
            return self._unavailable_reading()

        max_delta = max(
            1.0,
            3.0 * max(elapsed_sec, 0.1),
        )

        self._current_bpm = (
            self._signal_generator.move_towards(
                current=self._current_bpm,
                target=context.heart_rate_target_bpm,
                max_delta=max_delta,
                noise=1.2,
                minimum=35.0,
                maximum=210.0,
            )
        )

        return self._reading(
            {
                "heartRateBpm": int(
                    round(self._current_bpm)
                )
            }
        )