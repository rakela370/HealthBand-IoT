"""Registration and coordinated reading of HealthBand sensors."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from device_simulator.sensors.base_sensor import BaseSensor
from device_simulator.sensors.battery_model import BatteryModel
from device_simulator.sensors.heart_rate_sensor import HeartRateSensor
from device_simulator.sensors.skin_temperature_sensor import SkinTemperatureSensor
from device_simulator.sensors.spo2_sensor import SpO2Sensor
from device_simulator.sensors.step_counter_sensor import StepCounterSensor
from device_simulator.simulation.scenario import ScenarioContext
from device_simulator.simulation.signal_generator import SignalGenerator
from device_simulator.simulation.user_profile import UserProfile
from device_simulator.utils.versioning import is_at_least


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
        software_version: str = "1.0.0",
        spo2_measurement_enabled: bool | None = None,
    ) -> None:
        profile = user_profile or UserProfile()
        generator = SignalGenerator(seed=random_seed)

        self.software_version = software_version
        self._sensors: dict[str, BaseSensor] = {}
        self._scenario_failed_sensor: str | None = None
        self._spo2_measurement_enabled = (
            True
            if spo2_measurement_enabled is None
            else bool(spo2_measurement_enabled)
        )

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
                signal_generator=generator,
                timezone_name=profile.timezone_name,
            )
        )
        self.register(BatteryModel())

        if is_at_least(software_version, "2.0.0"):
            spo2_sensor = SpO2Sensor(signal_generator=generator)
            self.register(spo2_sensor)
            if not self._spo2_measurement_enabled:
                spo2_sensor.disable()

    @property
    def sensors(self) -> tuple[BaseSensor, ...]:
        return tuple(self._sensors.values())

    def register(self, sensor: BaseSensor) -> None:
        if sensor.name in self._sensors:
            raise ValueError(f"Sensor '{sensor.name}' is already registered.")
        self._sensors[sensor.name] = sensor

    def has_sensor(self, name: str) -> bool:
        return name in self._sensors

    def get_sensor(self, name: str) -> BaseSensor:
        try:
            return self._sensors[name]
        except KeyError as exc:
            raise KeyError(f"Unknown sensor '{name}'.") from exc

    def set_spo2_enabled(self, enabled: bool) -> None:
        if not self.has_sensor("spo2"):
            return

        sensor = self.get_sensor("spo2")
        self._spo2_measurement_enabled = bool(enabled)
        if enabled:
            sensor.enable()
        else:
            sensor.disable()

    def read_all(
        self,
        context: ScenarioContext,
        elapsed_sec: float,
    ) -> SensorSnapshot:
        """Read all sensors without letting technical failures change activity."""

        self._apply_scenario_failure(context.failed_sensor_name)

        measurements: dict[str, Any] = {}
        statuses: dict[str, str] = {}

        for sensor in self._sensors.values():
            reading = sensor.read(context=context, elapsed_sec=elapsed_sec)
            statuses[sensor.name] = reading.status.value
            if reading.valid:
                measurements.update(reading.values)

        measurements["activityLevel"] = context.activity_level.value

        return SensorSnapshot(
            measurements=measurements,
            sensor_status=statuses,
            scenario=context.scenario.value,
            activity_level=context.activity_level.value,
            timestamp=datetime.now(timezone.utc),
        )

    def _apply_scenario_failure(self, failed_sensor_name: str | None) -> None:
        """Apply a requested failure; never auto-heal it on scenario change."""

        if failed_sensor_name is None:
            return

        sensor = self.get_sensor(failed_sensor_name)
        sensor.simulate_failure()
        self._scenario_failed_sensor = failed_sensor_name

    def simulate_sensor_failure(self, name: str) -> None:
        self.get_sensor(name).simulate_failure()
        self._scenario_failed_sensor = name

    def restore_sensor(self, name: str) -> None:
        self._restore_sensor_status(name)
        if self._scenario_failed_sensor == name:
            self._scenario_failed_sensor = None

    def _restore_sensor_status(self, name: str) -> None:
        sensor = self.get_sensor(name)
        sensor.restore()
        if name == "spo2" and not self._spo2_measurement_enabled:
            sensor.disable()

    def sensor_statuses(self) -> dict[str, str]:
        return {
            name: sensor.status.value
            for name, sensor in self._sensors.items()
        }

    def export_runtime_state(self) -> dict[str, Any]:
        """Return restart-safe canonical state for sensors that carry history."""

        state: dict[str, Any] = {}

        heart = self.get_sensor("heart_rate")
        if isinstance(heart, HeartRateSensor):
            state["heartRateBpm"] = heart.current_bpm

        temperature = self.get_sensor("skin_temperature")
        if isinstance(temperature, SkinTemperatureSensor):
            state["skinTemperatureCelsius"] = temperature.current_celsius

        steps = self.get_sensor("step_counter")
        if isinstance(steps, StepCounterSensor):
            state.update(
                {
                    "totalDailySteps": steps.total_daily_steps,
                    "fractionalSteps": steps.fractional_steps,
                    "cadenceStepsPerMinute": steps.current_cadence,
                    "stepsLocalDate": steps.local_date,
                }
            )

        battery = self.get_sensor("battery")
        if isinstance(battery, BatteryModel):
            state["batteryPercentage"] = battery.percentage
            state["charging"] = battery.charging

        if self.has_sensor("spo2"):
            spo2 = self.get_sensor("spo2")
            if isinstance(spo2, SpO2Sensor):
                state["oxygenSaturationPercentage"] = spo2.current_percentage

        state["failedSensors"] = [
            name
            for name, sensor in self._sensors.items()
            if sensor.status.value == "FAILED"
        ]

        return state

    def restore_runtime_state(self, state: dict[str, Any]) -> None:
        """Restore canonical sensor state saved by a prior process/release."""

        heart = self.get_sensor("heart_rate")
        if isinstance(heart, HeartRateSensor) and state.get("heartRateBpm") is not None:
            heart.restore_runtime_value(float(state["heartRateBpm"]))

        temperature = self.get_sensor("skin_temperature")
        if (
            isinstance(temperature, SkinTemperatureSensor)
            and state.get("skinTemperatureCelsius") is not None
        ):
            temperature.restore_runtime_value(float(state["skinTemperatureCelsius"]))

        steps = self.get_sensor("step_counter")
        if isinstance(steps, StepCounterSensor):
            steps.restore_runtime_state(
                total_daily_steps=int(state.get("totalDailySteps", 0)),
                fractional_steps=float(state.get("fractionalSteps", 0.0)),
                cadence_steps_per_minute=float(
                    state.get("cadenceStepsPerMinute", 0.0)
                ),
                local_date=(
                    str(state["stepsLocalDate"])
                    if state.get("stepsLocalDate")
                    else None
                ),
            )

        battery = self.get_sensor("battery")
        if isinstance(battery, BatteryModel) and state.get("batteryPercentage") is not None:
            battery.restore_runtime_state(
                percentage=float(state["batteryPercentage"]),
                charging=bool(state.get("charging", False)),
            )

        if self.has_sensor("spo2") and state.get("oxygenSaturationPercentage") is not None:
            spo2 = self.get_sensor("spo2")
            if isinstance(spo2, SpO2Sensor):
                spo2.restore_runtime_value(float(state["oxygenSaturationPercentage"]))

        for sensor_name in state.get("failedSensors", []):
            if isinstance(sensor_name, str) and self.has_sensor(sensor_name):
                self.simulate_sensor_failure(sensor_name)
