"""Unit tests for the HealthBand ScenarioEngine."""

from device_simulator.simulation.scenario import (
    ActivityLevel,
    SimulationScenario,
)
from device_simulator.simulation.scenario_engine import (
    ScenarioEngine,
)


def test_default_scenario_is_resting() -> None:
    engine = ScenarioEngine()

    context = engine.get_context()

    assert (
        engine.current_scenario
        == SimulationScenario.RESTING
    )

    assert (
        context.activity_level
        == ActivityLevel.RESTING
    )


def test_running_scenario_has_high_activity_and_steps(
) -> None:
    engine = ScenarioEngine()

    engine.set_scenario(
        SimulationScenario.RUNNING
    )

    context = engine.get_context()

    assert (
        context.activity_level
        == ActivityLevel.HIGH
    )

    assert context.steps_per_minute > 0

    assert (
        context.heart_rate_target_bpm
        > 100
    )


def test_stress_event_has_resting_activity_and_elevated_pulse_target(
) -> None:
    engine = ScenarioEngine()

    resting_target = (
        engine.get_context()
        .heart_rate_target_bpm
    )

    engine.set_scenario(
        SimulationScenario.STRESS_EVENT
    )

    context = engine.get_context()

    assert (
        context.activity_level
        == ActivityLevel.RESTING
    )

    assert (
        context.heart_rate_target_bpm
        > resting_target
    )


def test_sensor_failure_stores_selected_sensor(
) -> None:
    engine = ScenarioEngine()

    engine.set_scenario(
        SimulationScenario.SENSOR_FAILURE,
        failed_sensor_name=(
            "skin_temperature"
        ),
    )

    context = engine.get_context()

    assert (
        context.failed_sensor_name
        == "skin_temperature"
    )

def test_network_outage_is_overlay_and_preserves_running_context() -> None:
    engine = ScenarioEngine()
    engine.set_scenario(SimulationScenario.RUNNING)
    before = engine.get_context()

    engine.set_scenario(SimulationScenario.NETWORK_OUTAGE)
    after = engine.get_context()

    assert engine.current_scenario == SimulationScenario.RUNNING
    assert after.scenario == SimulationScenario.RUNNING
    assert after.activity_level == ActivityLevel.HIGH
    assert after.heart_rate_target_bpm == before.heart_rate_target_bpm
    assert after.steps_per_minute == before.steps_per_minute


def test_low_battery_is_overlay_and_preserves_running_context() -> None:
    engine = ScenarioEngine()
    engine.set_scenario(SimulationScenario.RUNNING)
    engine.set_scenario(SimulationScenario.LOW_BATTERY)
    context = engine.get_context()

    assert engine.current_scenario == SimulationScenario.RUNNING
    assert context.scenario == SimulationScenario.RUNNING
    assert context.activity_level == ActivityLevel.HIGH
    assert context.force_low_battery is True


def test_sensor_failure_is_overlay_and_preserves_running_context() -> None:
    engine = ScenarioEngine()
    engine.set_scenario(SimulationScenario.RUNNING)
    engine.set_scenario(
        SimulationScenario.SENSOR_FAILURE,
        failed_sensor_name="skin_temperature",
    )
    context = engine.get_context()

    assert engine.current_scenario == SimulationScenario.RUNNING
    assert context.scenario == SimulationScenario.RUNNING
    assert context.failed_sensor_name == "skin_temperature"


def test_sensor_failure_overlay_can_be_cleared_without_changing_activity() -> None:
    engine = ScenarioEngine()
    engine.set_scenario(SimulationScenario.RUNNING)
    engine.set_scenario(
        SimulationScenario.SENSOR_FAILURE,
        failed_sensor_name="heart_rate",
    )
    assert engine.get_context().failed_sensor_name == "heart_rate"

    engine.clear_sensor_failure("heart_rate")
    context = engine.get_context()
    assert engine.current_scenario == SimulationScenario.RUNNING
    assert context.failed_sensor_name is None


def test_overexertion_scenario_has_high_activity_and_190_bpm_target() -> None:
    engine = ScenarioEngine()
    engine.set_scenario(SimulationScenario.OVEREXERTION)
    context = engine.get_context()

    assert context.activity_level == ActivityLevel.HIGH
    assert context.heart_rate_target_bpm == 190.0
    assert context.steps_per_minute > 170.0
    assert context.heart_rate_time_constant_sec < 20.0
