"""Unit tests for HealthBand simulated sensors."""

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
    SimulationScenario,
)
from device_simulator.simulation.scenario_engine import (
    ScenarioEngine,
)
from device_simulator.simulation.signal_generator import (
    SignalGenerator,
)
from device_simulator.simulation.user_profile import (
    UserProfile,
)


def test_heart_rate_moves_up_in_running_scenario(
) -> None:
    profile = UserProfile()

    sensor = HeartRateSensor(
        signal_generator=SignalGenerator(
            seed=1
        ),
        user_profile=profile,
    )

    engine = ScenarioEngine(
        user_profile=profile
    )

    engine.set_scenario(
        SimulationScenario.RUNNING
    )

    before = sensor.current_bpm

    sensor.read(
        context=engine.get_context(),
        elapsed_sec=2.0,
    )

    assert sensor.current_bpm > before


def test_skin_temperature_changes_gradually(
) -> None:
    profile = UserProfile()

    sensor = SkinTemperatureSensor(
        signal_generator=SignalGenerator(
            seed=1
        ),
        user_profile=profile,
    )

    engine = ScenarioEngine(
        user_profile=profile
    )

    engine.set_scenario(
        SimulationScenario.RUNNING
    )

    before = sensor.current_celsius

    sensor.read(
        context=engine.get_context(),
        elapsed_sec=2.0,
    )

    # Wrist/peripheral skin temperature is modeled separately from core
    # temperature and changes slowly during running.
    assert sensor.current_celsius < before
    assert before - sensor.current_celsius < 0.2


def test_resting_step_count_is_zero() -> None:
    sensor = StepCounterSensor(
        signal_generator=SignalGenerator(
            seed=1
        )
    )

    engine = ScenarioEngine()

    reading = sensor.read(
        context=engine.get_context(),
        elapsed_sec=60.0,
    )

    assert (
        reading.values[
            "stepsInInterval"
        ]
        == 0
    )


def test_walking_generates_steps() -> None:
    sensor = StepCounterSensor(
        signal_generator=SignalGenerator(
            seed=1
        )
    )

    engine = ScenarioEngine()

    engine.set_scenario(
        SimulationScenario.WALKING
    )

    reading = sensor.read(
        context=engine.get_context(),
        elapsed_sec=60.0,
    )

    assert (
        reading.values[
            "stepsInInterval"
        ]
        > 0
    )

    assert (
        reading.values[
            "totalDailySteps"
        ]
        > 0
    )


def test_battery_drains_and_charges() -> None:
    battery = BatteryModel(
        initial_percentage=50
    )

    engine = ScenarioEngine()

    context = engine.get_context()

    battery.read(
        context=context,
        elapsed_sec=60.0,
    )

    after_drain = (
        battery.percentage
    )

    assert after_drain < 50

    battery.start_charging()

    battery.read(
        context=context,
        elapsed_sec=60.0,
    )

    assert (
        battery.percentage
        > after_drain
    )


def test_low_battery_scenario_forces_low_level(
) -> None:
    battery = BatteryModel(
        initial_percentage=80
    )

    engine = ScenarioEngine()

    engine.set_scenario(
        SimulationScenario.LOW_BATTERY
    )

    reading = battery.read(
        context=engine.get_context(),
        elapsed_sec=1.0,
    )

    assert (
        reading.values[
            "batteryPercentage"
        ]
        < 15
    )