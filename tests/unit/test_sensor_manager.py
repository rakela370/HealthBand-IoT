"""Unit tests for the HealthBand SensorManager."""

from device_simulator.sensors.sensor_manager import (
    SensorManager,
)
from device_simulator.simulation.scenario import (
    SimulationScenario,
)
from device_simulator.simulation.scenario_engine import (
    ScenarioEngine,
)


def test_snapshot_contains_version1_measurements(
) -> None:
    manager = SensorManager(
        random_seed=1
    )

    engine = ScenarioEngine()

    snapshot = manager.read_all(
        context=engine.get_context(),
        elapsed_sec=2.0,
    )

    expected_measurements = (
        "heartRateBpm",
        "skinTemperatureCelsius",
        "stepsInInterval",
        "totalDailySteps",
        "batteryPercentage",
        "activityLevel",
    )

    for key in expected_measurements:
        assert key in snapshot.measurements

    assert snapshot.scenario == "RESTING"


def test_sensor_failure_removes_failed_sensor_value(
) -> None:
    manager = SensorManager(
        random_seed=1
    )

    engine = ScenarioEngine()

    engine.set_scenario(
        SimulationScenario.SENSOR_FAILURE,
        failed_sensor_name="heart_rate",
    )

    snapshot = manager.read_all(
        context=engine.get_context(),
        elapsed_sec=2.0,
    )

    assert (
        "heartRateBpm"
        not in snapshot.measurements
    )

    assert (
        snapshot.sensor_status[
            "heart_rate"
        ]
        == "FAILED"
    )


def test_leaving_sensor_failure_restores_sensor(
) -> None:
    manager = SensorManager(
        random_seed=1
    )

    engine = ScenarioEngine()

    engine.set_scenario(
        SimulationScenario.SENSOR_FAILURE,
        failed_sensor_name="heart_rate",
    )

    manager.read_all(
        context=engine.get_context(),
        elapsed_sec=2.0,
    )

    engine.set_scenario(
        SimulationScenario.RESTING
    )

    snapshot = manager.read_all(
        context=engine.get_context(),
        elapsed_sec=2.0,
    )

    assert (
        "heartRateBpm"
        in snapshot.measurements
    )

    assert (
        snapshot.sensor_status[
            "heart_rate"
        ]
        == "OK"
    )