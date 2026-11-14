"""Behavioral guardrails for the synthetic physiology model."""

from device_simulator.sensors.heart_rate_sensor import HeartRateSensor
from device_simulator.sensors.skin_temperature_sensor import SkinTemperatureSensor
from device_simulator.sensors.spo2_sensor import SpO2Sensor
from device_simulator.sensors.step_counter_sensor import StepCounterSensor
from device_simulator.simulation.scenario import SimulationScenario
from device_simulator.simulation.scenario_engine import ScenarioEngine
from device_simulator.simulation.signal_generator import SignalGenerator
from device_simulator.simulation.user_profile import UserProfile


def test_running_heart_rate_rises_over_tens_of_seconds_not_instantly() -> None:
    profile = UserProfile()
    sensor = HeartRateSensor(SignalGenerator(seed=100), profile)
    engine = ScenarioEngine(profile)
    engine.set_scenario(SimulationScenario.RUNNING)
    context = engine.get_context()

    initial = sensor.current_bpm
    sensor.read(context, elapsed_sec=10.0)
    after_10 = sensor.current_bpm
    sensor.read(context, elapsed_sec=50.0)
    after_60 = sensor.current_bpm

    assert 65.0 <= initial <= 80.0
    assert initial < after_10 < 100.0
    assert after_10 < after_60 < context.heart_rate_target_bpm + 3.0
    assert after_60 < 135.0


def test_recovery_heart_rate_falls_gradually_after_running() -> None:
    profile = UserProfile()
    sensor = HeartRateSensor(SignalGenerator(seed=101), profile)
    engine = ScenarioEngine(profile)
    engine.set_scenario(SimulationScenario.RUNNING)

    # Reach a realistic end-exercise range first.
    for _ in range(6):
        sensor.read(engine.get_context(), elapsed_sec=30.0)
    end_run = sensor.current_bpm
    assert end_run > 135.0

    engine.set_scenario(SimulationScenario.RECOVERY)
    sensor.read(engine.get_context(), elapsed_sec=60.0)
    after_one_minute = sensor.current_bpm

    drop = end_run - after_one_minute
    assert 20.0 <= drop <= 40.0
    assert after_one_minute > profile.resting_heart_rate_bpm + 25.0


def test_wrist_skin_temperature_changes_slowly() -> None:
    profile = UserProfile()
    running_sensor = SkinTemperatureSensor(SignalGenerator(seed=102), profile)
    engine = ScenarioEngine(profile)
    engine.set_scenario(SimulationScenario.RUNNING)
    initial = running_sensor.current_celsius
    running_sensor.read(engine.get_context(), elapsed_sec=60.0)
    after_running_minute = running_sensor.current_celsius

    assert after_running_minute < initial
    assert initial - after_running_minute < 0.15

    sleeping_sensor = SkinTemperatureSensor(SignalGenerator(seed=103), profile)
    engine.set_scenario(SimulationScenario.SLEEPING)
    sleep_initial = sleeping_sensor.current_celsius
    sleeping_sensor.read(engine.get_context(), elapsed_sec=60.0)
    assert sleeping_sensor.current_celsius > sleep_initial
    assert sleeping_sensor.current_celsius - sleep_initial < 0.15


def test_healthy_spo2_remains_near_normal_across_activity_scenarios() -> None:
    engine = ScenarioEngine()
    sensor = SpO2Sensor(SignalGenerator(seed=104))

    observed: dict[str, float] = {}
    for scenario in (
        SimulationScenario.RESTING,
        SimulationScenario.WALKING,
        SimulationScenario.RUNNING,
        SimulationScenario.EXERCISING,
        SimulationScenario.RECOVERY,
        SimulationScenario.SLEEPING,
    ):
        engine.set_scenario(scenario)
        # Allow this synthetic signal to substantially approach its target.
        for _ in range(6):
            sensor.read(engine.get_context(), elapsed_sec=15.0)
        observed[scenario.value] = sensor.current_percentage

    assert all(95.5 <= value <= 99.0 for value in observed.values())
    assert observed["RUNNING"] > 96.5
    assert observed["EXERCISING"] > 96.5
    assert observed["SLEEPING"] < observed["RESTING"]


def test_running_cadence_ramps_quickly_but_not_instantly() -> None:
    engine = ScenarioEngine()
    engine.set_scenario(SimulationScenario.RUNNING)
    sensor = StepCounterSensor(SignalGenerator(seed=105))

    first = sensor.read(engine.get_context(), elapsed_sec=2.0)
    cadence_2s = float(first.values["cadenceStepsPerMinute"])
    assert 10.0 < cadence_2s < 90.0

    for _ in range(14):
        sensor.read(engine.get_context(), elapsed_sec=2.0)
    assert 150.0 <= sensor.current_cadence <= 185.0


def test_stress_event_heart_rate_accelerates_within_about_six_seconds() -> None:
    profile = UserProfile()
    sensor = HeartRateSensor(SignalGenerator(seed=106), profile)
    engine = ScenarioEngine(profile)
    engine.set_scenario(SimulationScenario.STRESS_EVENT)

    values = []
    for _ in range(3):
        sensor.read(engine.get_context(), elapsed_sec=2.0)
        values.append(sensor.current_bpm)

    assert values[0] > 100.0
    assert values[1] > 115.0
    assert 118.0 <= values[2] <= 125.0


def test_stress_event_does_not_force_rapid_drop_from_running_hr() -> None:
    profile = UserProfile()
    sensor = HeartRateSensor(SignalGenerator(seed=107), profile)
    sensor.restore_runtime_value(148.0)
    engine = ScenarioEngine(profile)
    engine.set_scenario(SimulationScenario.STRESS_EVENT)

    sensor.read(engine.get_context(), elapsed_sec=6.0)

    assert sensor.current_bpm > 140.0
