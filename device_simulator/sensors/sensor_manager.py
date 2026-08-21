"""Registration and coordinated reading of HealthBand sensors."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from device_simulator.sensors.base_sensor import (
    BaseSensor,
)
from device_simulator.sensors.battery_model import (
    BatteryModel,
)
from device_simulator.sensors.heart_rate_sensor import (
    HeartRateSensor,
)
from device_simulator.sensors.skin_temperature_sensor import (
    SkinTemperatureSensor,
)
from device_simulator.sensors.step_counter_sensor import (
    StepCounterSensor,
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


@dataclass(frozen=True, slots=True)
class SensorSnapshot:
    """Combined measurements produced during one sampling cycle."""

    measurements: dict[str, Any]
    sensor_status: dict[str, str]

    scenario: str
    activity_level: str

    timestamp: datetime


class SensorManager:
    """Register, control and read all HealthBand sensors."""

    def __init__(
        self,
        user_profile: UserProfile | None = None,
        random_seed: int | None = None,
    ) -> None:
        profile = user_profile or UserProfile()

        generator = SignalGenerator(
            seed=random_seed
        )

        self._sensors: dict[
            str,
            BaseSensor,
        ] = {}

        self._scenario_failed_sensor: (
            str | None
        ) = None

        self.register(
            HeartRateSensor(
                signal_generator=generator,
                user_profile=profile,
            )
        )

        self.register(
            SkinTemperatureSensor(
                signal_generator=generator,
                user_profile=profile,
            )
        )

        self.register(
            StepCounterSensor(
                signal_generator=generator
            )
        )

        self.register(
            BatteryModel()
        )

    @property
    def sensors(
        self,
    ) -> tuple[BaseSensor, ...]:
        """Return all currently registered sensors."""

        return tuple(
            self._sensors.values()
        )

    def register(
        self,
        sensor: BaseSensor,
    ) -> None:
        """Register one sensor with the manager."""

        if sensor.name in self._sensors:
            raise ValueError(
                f"Sensor '{sensor.name}' "
                "is already registered."
            )

        self._sensors[sensor.name] = sensor

    def get_sensor(
        self,
        name: str,
    ) -> BaseSensor:
        """Return a registered sensor by name."""

        try:
            return self._sensors[name]

        except KeyError as exc:
            raise KeyError(
                f"Unknown sensor '{name}'."
            ) from exc

    def read_all(
        self,
        context: ScenarioContext,
        elapsed_sec: float,
    ) -> SensorSnapshot:
        """Read all currently available sensors."""

        self._apply_scenario_failure(
            context.failed_sensor_name
        )

        measurements: dict[
            str,
            Any,
        ] = {}

        statuses: dict[
            str,
            str,
        ] = {}

        for sensor in self._sensors.values():
            reading = sensor.read(
                context=context,
                elapsed_sec=elapsed_sec,
            )

            statuses[sensor.name] = (
                reading.status.value
            )

            if reading.valid:
                measurements.update(
                    reading.values
                )

        measurements[
            "activityLevel"
        ] = context.activity_level.value

        return SensorSnapshot(
            measurements=measurements,
            sensor_status=statuses,
            scenario=context.scenario.value,
            activity_level=(
                context.activity_level.value
            ),
            timestamp=datetime.now(
                timezone.utc
            ),
        )

    def _apply_scenario_failure(
        self,
        failed_sensor_name: str | None,
    ) -> None:
        """Apply or remove a SENSOR_FAILURE scenario failure."""

        if (
            self._scenario_failed_sensor
            and self._scenario_failed_sensor
            != failed_sensor_name
        ):
            self.get_sensor(
                self._scenario_failed_sensor
            ).restore()

            self._scenario_failed_sensor = None

        if failed_sensor_name is not None:
            sensor = self.get_sensor(
                failed_sensor_name
            )

            sensor.simulate_failure()

            self._scenario_failed_sensor = (
                failed_sensor_name
            )

    def simulate_sensor_failure(
        self,
        name: str,
    ) -> None:
        """Put a selected sensor into FAILED state."""

        self.get_sensor(
            name
        ).simulate_failure()

    def restore_sensor(
        self,
        name: str,
    ) -> None:
        """Restore a selected sensor."""

        self.get_sensor(
            name
        ).restore()

        if (
            self._scenario_failed_sensor
            == name
        ):
            self._scenario_failed_sensor = None

    def sensor_statuses(
        self,
    ) -> dict[str, str]:
        """Return technical status of every registered sensor."""

        return {
            name: sensor.status.value
            for name, sensor
            in self._sensors.items()
        }