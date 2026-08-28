"""Module 3 tests for the HealthBand DeviceController."""

import pytest

from device_simulator.alerts.alert import (
    AlertType,
)
from device_simulator.analytics.analytics_manager import (
    AnalyticsManager,
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


class ConfigOverride:
    """
    Read-only test configuration wrapper.

    Values explicitly supplied to the wrapper override the real
    persisted device configuration. All other values are delegated
    to the original configuration object.

    This keeps integration tests deterministic without modifying
    the user's persisted HealthBand configuration.
    """

    def __init__(
        self,
        base_config,
        **overrides,
    ) -> None:
        self._base_config = (
            base_config
        )

        self._overrides = (
            overrides
        )

    def __getattr__(
        self,
        name: str,
    ):
        if (
            name
            in self._overrides
        ):
            return (
                self._overrides[
                    name
                ]
            )

        return getattr(
            self._base_config,
            name,
        )


def install_test_configuration(
    monkeypatch: pytest.MonkeyPatch,
    controller: DeviceController,
    **overrides,
) -> ConfigOverride:
    """
    Override DeviceController.current_config only for one test.

    Pytest's monkeypatch fixture restores the original property
    automatically after the test finishes.
    """

    test_config = (
        ConfigOverride(
            controller.current_config,
            **overrides,
        )
    )

    monkeypatch.setattr(
        DeviceController,
        "current_config",
        property(
            lambda self: test_config
        ),
    )

    return (
        test_config
    )


@pytest.mark.asyncio
async def test_controller_produces_analytics_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verify DeviceController -> AnalyticsManager -> EventBus integration.

    The test deliberately enables analytics locally instead of using
    the user's persisted Device Shadow configuration.
    """

    event_bus = (
        EventBus()
    )

    analytics_events: list[
        dict[str, object]
    ] = []

    event_bus.subscribe(
        DeviceController.ANALYTICS_EVENT,
        analytics_events.append,
    )

    controller = (
        DeviceController(
            event_bus=event_bus,
            scheduler=Scheduler(),
            random_seed=1,
        )
    )

    install_test_configuration(
        monkeypatch=monkeypatch,
        controller=controller,
        measurement_interval_sec=2.0,
        analytics_window_sec=8.0,
        analytics_enabled=True,
    )

    controller.analytics_manager = (
        AnalyticsManager(
            device_id=(
                controller.device_id
            ),
            software_version=(
                controller.software_version
            ),
            window_sec=8.0,
        )
    )

    try:

        await controller.start()

        for _ in range(
            5
        ):
            await (
                controller
                .read_sensors_now()
            )

        assert (
            len(
                analytics_events
            )
            >= 1
        )

        assert (
            controller.latest_analytics
            is not None
        )

    finally:

        await (
            controller.shutdown()
        )


@pytest.mark.asyncio
async def test_stress_event_eventually_generates_alert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Verify STRESS_EVENT -> AlertManager -> EventBus integration.

    Heart-rate alerts are explicitly enabled for this test because
    the user's real persisted configuration may legitimately disable
    them.
    """

    event_bus = (
        EventBus()
    )

    alert_events: list[
        dict[str, object]
    ] = []

    event_bus.subscribe(
        DeviceController.ALERT_EVENT,
        alert_events.append,
    )

    controller = (
        DeviceController(
            event_bus=event_bus,
            scheduler=Scheduler(),
            random_seed=1,
        )
    )

    install_test_configuration(
        monkeypatch=monkeypatch,
        controller=controller,
        measurement_interval_sec=2.0,
        alerts_enabled=True,
        heart_rate_alerts_enabled=True,
    )

    controller.alert_manager.heart_rate_maximum_resting_threshold = (
        80.0
    )

    try:

        await controller.start()

        controller.change_scenario(
            SimulationScenario.STRESS_EVENT
        )

        for _ in range(
            12
        ):
            await (
                controller
                .read_sensors_now()
            )

        types = [
            event[
                "type"
            ]
            for event
            in alert_events
        ]

        assert (
            AlertType
            .HEART_RATE_ABOVE_RESTING_THRESHOLD
            .value
            in types
        )

    finally:

        await (
            controller.shutdown()
        )


@pytest.mark.asyncio
async def test_controller_creates_healthy_report() -> None:
    """Verify normal technical device-health reporting."""

    controller = (
        DeviceController(
            event_bus=EventBus(),
            scheduler=Scheduler(),
            random_seed=1,
        )
    )

    try:

        await controller.start()

        report = (
            await (
                controller
                .create_health_report_now()
            )
        )

        assert (
            report.device_status
            == DeviceHealthStatus.HEALTHY
        )

    finally:

        await (
            controller.shutdown()
        )