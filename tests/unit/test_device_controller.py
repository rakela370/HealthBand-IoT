"""Unit tests for the HealthBand DeviceController."""

import pytest

from device_simulator.core.device_controller import DeviceController
from device_simulator.core.device_state import DeviceState
from device_simulator.core.event_bus import EventBus
from device_simulator.core.scheduler import Scheduler


@pytest.mark.asyncio
async def test_controller_reaches_monitoring_state() -> None:
    event_bus = EventBus()
    scheduler = Scheduler()

    controller = DeviceController(
        event_bus=event_bus,
        scheduler=scheduler,
    )

    await controller.start()

    assert controller.current_state == DeviceState.MONITORING

    await controller.shutdown()


@pytest.mark.asyncio
async def test_controller_publishes_state_change_events() -> None:
    event_bus = EventBus()
    scheduler = Scheduler()

    received_events: list[dict[str, object]] = []

    event_bus.subscribe(
        DeviceController.STATE_CHANGED_EVENT,
        received_events.append,
    )

    controller = DeviceController(
        event_bus=event_bus,
        scheduler=scheduler,
    )

    await controller.start()

    reached_states = [
        event["currentState"]
        for event in received_events
    ]

    assert reached_states == [
        "SELF_TEST",
        "CONNECTING",
        "MONITORING",
    ]

    await controller.shutdown()

    assert (
        received_events[-1]["currentState"]
        == "SHUTTING_DOWN"
    )


@pytest.mark.asyncio
async def test_controller_shutdown_is_controlled() -> None:
    controller = DeviceController(
        event_bus=EventBus(),
        scheduler=Scheduler(),
    )

    await controller.start()
    await controller.shutdown()

    assert (
        controller.current_state
        == DeviceState.SHUTTING_DOWN
    )