"""Scenario engine for the HealthBand simulator."""

from device_simulator.simulation.scenario import (
    ActivityLevel,
    ScenarioContext,
    SimulationScenario,
)
from device_simulator.simulation.user_profile import UserProfile


class ScenarioEngine:
    """Provides simulation parameters for the currently active scenario."""

    def __init__(
        self,
        user_profile: UserProfile | None = None,
    ) -> None:
        self.user_profile = user_profile or UserProfile()

        self._current_scenario = (
            SimulationScenario.RESTING
        )

        self._failed_sensor_name: str | None = None

    @property
    def current_scenario(
        self,
    ) -> SimulationScenario:
        """Return the currently active scenario."""

        return self._current_scenario

    def set_scenario(
        self,
        scenario: SimulationScenario,
        failed_sensor_name: str | None = None,
    ) -> None:
        """Change the active simulation scenario."""

        if scenario == SimulationScenario.SENSOR_FAILURE:
            self._failed_sensor_name = (
                failed_sensor_name or "heart_rate"
            )
        else:
            self._failed_sensor_name = None

        self._current_scenario = scenario

    def get_context(self) -> ScenarioContext:
        """Build sensor parameters for the active scenario."""

        profile = self.user_profile

        base_temperature = (
            profile.base_skin_temperature_c
        )

        profiles = {
            SimulationScenario.SLEEPING: ScenarioContext(
                scenario=SimulationScenario.SLEEPING,
                activity_level=ActivityLevel.SLEEPING,
                heart_rate_target_bpm=(
                    profile.sleeping_heart_rate_bpm
                ),
                skin_temperature_target_c=(
                    base_temperature - 0.2
                ),
                steps_per_minute=0.0,
                battery_drain_multiplier=0.8,
            ),

            SimulationScenario.RESTING: ScenarioContext(
                scenario=SimulationScenario.RESTING,
                activity_level=ActivityLevel.RESTING,
                heart_rate_target_bpm=(
                    profile.resting_heart_rate_bpm
                ),
                skin_temperature_target_c=(
                    base_temperature
                ),
                steps_per_minute=0.0,
                battery_drain_multiplier=1.0,
            ),

            SimulationScenario.WALKING: ScenarioContext(
                scenario=SimulationScenario.WALKING,
                activity_level=ActivityLevel.MODERATE,
                heart_rate_target_bpm=(
                    profile.walking_heart_rate_bpm
                ),
                skin_temperature_target_c=(
                    base_temperature + 0.2
                ),
                steps_per_minute=105.0,
                battery_drain_multiplier=1.25,
            ),

            SimulationScenario.RUNNING: ScenarioContext(
                scenario=SimulationScenario.RUNNING,
                activity_level=ActivityLevel.HIGH,
                heart_rate_target_bpm=(
                    profile.running_heart_rate_bpm
                ),
                skin_temperature_target_c=(
                    base_temperature + 0.5
                ),
                steps_per_minute=170.0,
                battery_drain_multiplier=1.7,
            ),

            SimulationScenario.EXERCISING: ScenarioContext(
                scenario=SimulationScenario.EXERCISING,
                activity_level=ActivityLevel.HIGH,
                heart_rate_target_bpm=(
                    profile.exercising_heart_rate_bpm
                ),
                skin_temperature_target_c=(
                    base_temperature + 0.4
                ),
                steps_per_minute=65.0,
                battery_drain_multiplier=1.55,
            ),

            SimulationScenario.RECOVERY: ScenarioContext(
                scenario=SimulationScenario.RECOVERY,
                activity_level=ActivityLevel.MODERATE,
                heart_rate_target_bpm=(
                    profile.recovery_heart_rate_bpm
                ),
                skin_temperature_target_c=(
                    base_temperature + 0.2
                ),
                steps_per_minute=0.0,
                battery_drain_multiplier=1.15,
            ),

            SimulationScenario.STRESS_EVENT: ScenarioContext(
                scenario=SimulationScenario.STRESS_EVENT,
                activity_level=ActivityLevel.RESTING,
                heart_rate_target_bpm=(
                    profile.stress_heart_rate_bpm
                ),
                skin_temperature_target_c=(
                    base_temperature + 0.1
                ),
                steps_per_minute=0.0,
                battery_drain_multiplier=1.05,
            ),

            SimulationScenario.SENSOR_FAILURE: ScenarioContext(
                scenario=(
                    SimulationScenario.SENSOR_FAILURE
                ),
                activity_level=ActivityLevel.RESTING,
                heart_rate_target_bpm=(
                    profile.resting_heart_rate_bpm
                ),
                skin_temperature_target_c=(
                    base_temperature
                ),
                steps_per_minute=0.0,
                battery_drain_multiplier=1.0,
                failed_sensor_name=(
                    self._failed_sensor_name
                ),
            ),

            SimulationScenario.LOW_BATTERY: ScenarioContext(
                scenario=SimulationScenario.LOW_BATTERY,
                activity_level=ActivityLevel.RESTING,
                heart_rate_target_bpm=(
                    profile.resting_heart_rate_bpm
                ),
                skin_temperature_target_c=(
                    base_temperature
                ),
                steps_per_minute=0.0,
                battery_drain_multiplier=2.5,
                force_low_battery=True,
            ),

            SimulationScenario.NETWORK_OUTAGE: ScenarioContext(
                scenario=(
                    SimulationScenario.NETWORK_OUTAGE
                ),
                activity_level=ActivityLevel.RESTING,
                heart_rate_target_bpm=(
                    profile.resting_heart_rate_bpm
                ),
                skin_temperature_target_c=(
                    base_temperature
                ),
                steps_per_minute=0.0,
                battery_drain_multiplier=1.0,
            ),
        }

        return profiles[self._current_scenario]