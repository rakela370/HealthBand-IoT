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