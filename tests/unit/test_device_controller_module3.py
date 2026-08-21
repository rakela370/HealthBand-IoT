"""Module 3 tests for the HealthBand DeviceController."""

import pytest

from device_simulator.alerts.alert import (
    AlertType,
)
from device_simulator.core.device_controller import (
    DeviceController,
)
from device_simulator.core.event_bus import (
    EventBus,
)
from device_simulator.core.scheduler import (
    Scheduler,
)
from device_simulator.device_health.device_health_monitor import (
    DeviceHealthStatus,
)
from device_simulator.simulation.scenario import (
    SimulationScenario,
)


@pytest.mark.asyncio
async def test_controller_produces_analytics_event() -> None:
    event_bus = EventBus()

    analytics_events: list[
        dict[str, object]
    ] = []

    event_bus.subscribe(
        DeviceController.ANALYTICS_EVENT,
        analytics_events.append,
    )

    controller = DeviceController(
        event_bus=event_bus,
        scheduler=Scheduler(),
        random_seed=1,
    )

    await controller.start()

    for _ in range(4):
        await controller.read_sensors_now()

    assert len(
        analytics_events
    ) >= 1

    await controller.shutdown()


@pytest.mark.asyncio
async def test_stress_event_eventually_generates_alert() -> None:
    event_bus = EventBus()

    alert_events: list[
        dict[str, object]
    ] = []

    event_bus.subscribe(
        DeviceController.ALERT_EVENT,
        alert_events.append,
    )

    controller = DeviceController(
        event_bus=event_bus,
        scheduler=Scheduler(),
        random_seed=1,
    )

    await controller.start()

    controller.change_scenario(
        SimulationScenario.STRESS_EVENT
    )

    for _ in range(15):
        await controller.read_sensors_now()

    types = [
        event["type"]
        for event in alert_events
    ]

    assert (
        AlertType.HEART_RATE_ABOVE_RESTING_THRESHOLD.value
        in types
    )

    await controller.shutdown()


@pytest.mark.asyncio
async def test_controller_creates_healthy_report() -> None:
    controller = DeviceController(
        event_bus=EventBus(),
        scheduler=Scheduler(),
        random_seed=1,
    )

    await controller.start()

    report = (
        await controller.create_health_report_now()
    )

    assert (
        report.device_status
        == DeviceHealthStatus.HEALTHY
    )

    await controller.shutdown()