"""Scenario engine for the HealthBand simulator."""

from dataclasses import replace

from device_simulator.simulation.scenario import (
    ActivityLevel,
    ScenarioContext,
    SimulationScenario,
)
from device_simulator.simulation.user_profile import UserProfile


class ScenarioEngine:
    """Provide physiological parameters plus independent technical overlays."""

    _TECHNICAL_SCENARIOS = frozenset(
        {
            SimulationScenario.SENSOR_FAILURE,
            SimulationScenario.LOW_BATTERY,
            SimulationScenario.NETWORK_OUTAGE,
        }
    )

    def __init__(
        self,
        user_profile: UserProfile | None = None,
    ) -> None:
        self.user_profile = user_profile or UserProfile()
        self._current_scenario = SimulationScenario.RESTING
        self._failed_sensor_name: str | None = None
        self._force_low_battery = False

    @property
    def current_scenario(self) -> SimulationScenario:
        """Return the active *physiological* scenario."""

        return self._current_scenario

    def set_scenario(
        self,
        scenario: SimulationScenario,
        failed_sensor_name: str | None = None,
    ) -> None:
        """Change activity or apply a technical overlay.

        Network outage, low battery and sensor failure are not human
        activities. Applying one of those therefore leaves RUNNING/WALKING/
        SLEEPING/etc. intact.
        """

        if scenario == SimulationScenario.SENSOR_FAILURE:
            self._failed_sensor_name = failed_sensor_name or "heart_rate"
            return

        if scenario == SimulationScenario.LOW_BATTERY:
            self._force_low_battery = True
            return

        if scenario == SimulationScenario.NETWORK_OUTAGE:
            return

        if scenario in self._TECHNICAL_SCENARIOS:
            return

        self._current_scenario = scenario
        # A new physical scenario clears one-shot low-battery forcing, but a
        # failed sensor remains failed in SensorManager until RESTORE_SENSOR.
        self._force_low_battery = False
        self._failed_sensor_name = None

    def clear_sensor_failure(
        self,
        sensor_name: str | None = None,
    ) -> None:
        """Clear the technical sensor-failure overlay only."""

        if (
            sensor_name is None
            or self._failed_sensor_name == sensor_name
        ):
            self._failed_sensor_name = None

    def get_context(self) -> ScenarioContext:
        """Build sensor parameters for the active physiological scenario."""

        profile = self.user_profile
        base_temperature = profile.base_skin_temperature_c

        profiles = {
            SimulationScenario.SLEEPING: ScenarioContext(
                scenario=SimulationScenario.SLEEPING,
                activity_level=ActivityLevel.SLEEPING,
                heart_rate_target_bpm=profile.sleeping_heart_rate_bpm,
                skin_temperature_target_c=base_temperature + 0.45,
                steps_per_minute=0.0,
                battery_drain_multiplier=0.80,
                spo2_target_percentage=96.6,
                heart_rate_time_constant_sec=70.0,
                cadence_time_constant_sec=8.0,
                skin_temperature_time_constant_sec=600.0,
                spo2_time_constant_sec=45.0,
            ),
            SimulationScenario.RESTING: ScenarioContext(
                scenario=SimulationScenario.RESTING,
                activity_level=ActivityLevel.RESTING,
                heart_rate_target_bpm=profile.resting_heart_rate_bpm,
                skin_temperature_target_c=base_temperature,
                steps_per_minute=0.0,
                battery_drain_multiplier=1.0,
                spo2_target_percentage=98.2,
                heart_rate_time_constant_sec=55.0,
                cadence_time_constant_sec=7.0,
                skin_temperature_time_constant_sec=360.0,
                spo2_time_constant_sec=30.0,
            ),
            SimulationScenario.WALKING: ScenarioContext(
                scenario=SimulationScenario.WALKING,
                activity_level=ActivityLevel.MODERATE,
                heart_rate_target_bpm=profile.walking_heart_rate_bpm,
                skin_temperature_target_c=base_temperature - 0.15,
                steps_per_minute=105.0,
                battery_drain_multiplier=1.25,
                spo2_target_percentage=98.0,
                heart_rate_time_constant_sec=40.0,
                cadence_time_constant_sec=6.0,
                skin_temperature_time_constant_sec=300.0,
                spo2_time_constant_sec=25.0,
            ),
            SimulationScenario.RUNNING: ScenarioContext(
                scenario=SimulationScenario.RUNNING,
                activity_level=ActivityLevel.HIGH,
                heart_rate_target_bpm=profile.running_heart_rate_bpm,
                skin_temperature_target_c=base_temperature - 0.30,
                steps_per_minute=170.0,
                battery_drain_multiplier=1.70,
                spo2_target_percentage=97.6,
                # Healthy exercise-onset HR kinetics are well represented by
                # a first-order response over tens of seconds, not a jump.
                heart_rate_time_constant_sec=62.5,
                cadence_time_constant_sec=7.0,
                skin_temperature_time_constant_sec=300.0,
                spo2_time_constant_sec=25.0,
            ),
            SimulationScenario.EXERCISING: ScenarioContext(
                scenario=SimulationScenario.EXERCISING,
                activity_level=ActivityLevel.HIGH,
                heart_rate_target_bpm=profile.exercising_heart_rate_bpm,
                skin_temperature_target_c=base_temperature - 0.20,
                steps_per_minute=65.0,
                battery_drain_multiplier=1.55,
                spo2_target_percentage=97.5,
                heart_rate_time_constant_sec=55.0,
                cadence_time_constant_sec=8.0,
                skin_temperature_time_constant_sec=300.0,
                spo2_time_constant_sec=25.0,
            ),
            SimulationScenario.RECOVERY: ScenarioContext(
                scenario=SimulationScenario.RECOVERY,
                activity_level=ActivityLevel.LIGHT,
                heart_rate_target_bpm=profile.recovery_heart_rate_bpm,
                skin_temperature_target_c=base_temperature - 0.05,
                steps_per_minute=0.0,
                battery_drain_multiplier=1.15,
                spo2_target_percentage=97.9,
                # Gives roughly a 25-35 bpm fall in the first minute from a
                # typical end-run HR, followed by a slower approach.
                heart_rate_time_constant_sec=110.0,
                cadence_time_constant_sec=6.0,
                skin_temperature_time_constant_sec=360.0,
                spo2_time_constant_sec=30.0,
            ),
            SimulationScenario.STRESS_EVENT: ScenarioContext(
                scenario=SimulationScenario.STRESS_EVENT,
                activity_level=ActivityLevel.RESTING,
                heart_rate_target_bpm=profile.stress_heart_rate_bpm,
                skin_temperature_target_c=base_temperature - 0.15,
                steps_per_minute=0.0,
                battery_drain_multiplier=1.05,
                spo2_target_percentage=98.0,
                # Acute defensive/startle events are intentionally much
                # faster than exercise onset. With the default 2 s sampling
                # interval this reaches ~120 BPM from rest in about 5-6 s.
                heart_rate_time_constant_sec=1.5,
                cadence_time_constant_sec=7.0,
                skin_temperature_time_constant_sec=240.0,
                spo2_time_constant_sec=30.0,
            ),
            SimulationScenario.OVEREXERTION: ScenarioContext(
                scenario=SimulationScenario.OVEREXERTION,
                activity_level=ActivityLevel.HIGH,
                heart_rate_target_bpm=profile.overexertion_heart_rate_bpm,
                skin_temperature_target_c=base_temperature - 0.35,
                steps_per_minute=195.0,
                battery_drain_multiplier=2.0,
                spo2_target_percentage=97.2,
                # Deliberately faster than normal RUNNING so the defense demo
                # can reach the synthetic high-HR alert range in a practical
                # amount of time. This is a technical demo scenario, not a
                # medical threshold model.
                heart_rate_time_constant_sec=12.0,
                cadence_time_constant_sec=4.0,
                skin_temperature_time_constant_sec=300.0,
                spo2_time_constant_sec=25.0,
            ),
        }

        context = profiles[self._current_scenario]
        return replace(
            context,
            failed_sensor_name=self._failed_sensor_name,
            force_low_battery=self._force_low_battery,
        )
