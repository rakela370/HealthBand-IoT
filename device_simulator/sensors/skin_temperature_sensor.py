"""Simulated wrist skin-temperature sensor."""

from device_simulator.sensors.base_sensor import (
    BaseSensor,
    SensorReading,
    SensorStatus,
)
from device_simulator.simulation.scenario import ScenarioContext
from device_simulator.simulation.signal_generator import SignalGenerator
from device_simulator.simulation.user_profile import UserProfile


class SkinTemperatureSensor(BaseSensor):
    """Generate gradual distal/wrist skin-temperature values."""

    def __init__(
        self,
        signal_generator: SignalGenerator,
        user_profile: UserProfile,
    ) -> None:
        super().__init__("skin_temperature")
        self._signal_generator = signal_generator
        self._current_c = float(user_profile.base_skin_temperature_c)

    @property
    def current_celsius(self) -> float:
        """Return the current canonical Celsius value."""
        return self._current_c

    def restore_runtime_value(self, celsius: float) -> None:
        """Restore persisted wrist temperature after restart/OTA."""
        self._current_c = max(25.0, min(42.0, float(celsius)))

    def read(
        self,
        context: ScenarioContext,
        elapsed_sec: float,
    ) -> SensorReading:
        """Generate one wrist skin-temperature measurement."""

        if self.status in {SensorStatus.FAILED, SensorStatus.DISABLED}:
            return self._unavailable_reading()

        self._current_c = self._signal_generator.exponential_towards(
            current=self._current_c,
            target=context.skin_temperature_target_c,
            elapsed_sec=elapsed_sec,
            time_constant_sec=context.skin_temperature_time_constant_sec,
            noise=0.006,
            minimum=25.0,
            maximum=42.0,
        )

        return self._reading(
            {"skinTemperatureCelsius": round(self._current_c, 2)}
        )
