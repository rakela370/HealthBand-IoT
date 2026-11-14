"""Regression tests for restart/OTA-safe HealthBand runtime sensor state."""

from device_simulator.sensors.sensor_manager import SensorManager
from device_simulator.simulation.scenario import SimulationScenario
from device_simulator.simulation.scenario_engine import ScenarioEngine


def test_sensor_state_survives_manager_recreation() -> None:
    engine = ScenarioEngine()
    engine.set_scenario(SimulationScenario.RUNNING)

    original = SensorManager(random_seed=3, software_version="2.0.0")
    for _ in range(20):
        original.read_all(engine.get_context(), elapsed_sec=2.0)

    battery = original.get_sensor("battery")
    battery.set_percentage(71.25)  # type: ignore[attr-defined]
    state = original.export_runtime_state()

    restored = SensorManager(random_seed=9, software_version="2.0.0")
    restored.restore_runtime_state(state)
    restored_state = restored.export_runtime_state()

    assert restored_state["totalDailySteps"] == state["totalDailySteps"]
    assert restored_state["fractionalSteps"] == state["fractionalSteps"]
    assert restored_state["cadenceStepsPerMinute"] == state["cadenceStepsPerMinute"]
    assert restored_state["heartRateBpm"] == state["heartRateBpm"]
    assert restored_state["skinTemperatureCelsius"] == state["skinTemperatureCelsius"]
    assert restored_state["batteryPercentage"] == 71.25
    assert restored_state["oxygenSaturationPercentage"] == state["oxygenSaturationPercentage"]


def test_zero_percent_battery_is_preserved_not_replaced_by_default() -> None:
    manager = SensorManager(random_seed=1, software_version="2.0.0")
    manager.restore_runtime_state(
        {
            "batteryPercentage": 0.0,
            "charging": False,
            "totalDailySteps": 4321,
        }
    )

    state = manager.export_runtime_state()
    assert state["batteryPercentage"] == 0.0
    assert state["totalDailySteps"] == 4321


def test_failed_sensor_survives_runtime_restore_until_explicit_restore() -> None:
    original = SensorManager(random_seed=1, software_version="2.0.0")
    original.simulate_sensor_failure("heart_rate")
    state = original.export_runtime_state()

    restored = SensorManager(random_seed=2, software_version="2.0.0")
    restored.restore_runtime_state(state)
    assert restored.sensor_statuses()["heart_rate"] == "FAILED"

    restored.restore_sensor("heart_rate")
    assert restored.sensor_statuses()["heart_rate"] == "OK"
