"""Simulated skin-temperature sensor."""

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


class SkinTemperatureSensor(BaseSensor):
    """Generate gradual simulated skin-temperature values."""

    def __init__(
        self,
        signal_generator: SignalGenerator,
        user_profile: UserProfile,
    ) -> None:
        super().__init__("skin_temperature")

        self._signal_generator = signal_generator

        self._current_c = float(
            user_profile.base_skin_temperature_c
        )

    @property
    def current_celsius(self) -> float:
        """Return the current canonical Celsius value."""

        return self._current_c

    def read(
        self,
        context: ScenarioContext,
        elapsed_sec: float,
    ) -> SensorReading:
        """Generate one skin-temperature measurement."""

        if self.status in {
            SensorStatus.FAILED,
            SensorStatus.DISABLED,
        }:
            return self._unavailable_reading()

        max_delta = max(
            0.02,
            0.04 * max(elapsed_sec, 0.1),
        )

        self._current_c = (
            self._signal_generator.move_towards(
                current=self._current_c,
                target=(
                    context.skin_temperature_target_c
                ),
                max_delta=max_delta,
                noise=0.02,
                minimum=25.0,
                maximum=42.0,
            )
        )

        return self._reading(
            {
                "skinTemperatureCelsius": round(
                    self._current_c,
                    2,
                )
            }
        )