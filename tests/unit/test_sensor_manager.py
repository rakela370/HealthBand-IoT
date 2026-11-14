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


def test_sensor_failure_persists_until_explicit_restore(
) -> None:
    manager = SensorManager(random_seed=1)
    engine = ScenarioEngine()

    engine.set_scenario(SimulationScenario.RUNNING)
    manager.simulate_sensor_failure("heart_rate")

    failed = manager.read_all(
        context=engine.get_context(),
        elapsed_sec=2.0,
    )
    assert "heartRateBpm" not in failed.measurements
    assert failed.sensor_status["heart_rate"] == "FAILED"
    assert failed.scenario == "RUNNING"

    # Changing physical activity must not magically repair hardware.
    engine.set_scenario(SimulationScenario.WALKING)
    still_failed = manager.read_all(
        context=engine.get_context(),
        elapsed_sec=2.0,
    )
    assert "heartRateBpm" not in still_failed.measurements
    assert still_failed.sensor_status["heart_rate"] == "FAILED"
    assert still_failed.scenario == "WALKING"

    manager.restore_sensor("heart_rate")
    restored = manager.read_all(
        context=engine.get_context(),
        elapsed_sec=2.0,
    )
    assert "heartRateBpm" in restored.measurements
    assert restored.sensor_status["heart_rate"] == "OK"


def test_scenario_failure_restore_survives_next_read() -> None:
    manager = SensorManager(random_seed=5)
    engine = ScenarioEngine()
    engine.set_scenario(SimulationScenario.RUNNING)
    engine.set_scenario(
        SimulationScenario.SENSOR_FAILURE,
        failed_sensor_name="heart_rate",
    )

    failed = manager.read_all(engine.get_context(), elapsed_sec=2.0)
    assert failed.sensor_status["heart_rate"] == "FAILED"

    engine.clear_sensor_failure("heart_rate")
    manager.restore_sensor("heart_rate")
    restored = manager.read_all(engine.get_context(), elapsed_sec=2.0)
    assert restored.scenario == "RUNNING"
    assert restored.sensor_status["heart_rate"] == "OK"
    assert "heartRateBpm" in restored.measurements
