"""Offline-related DeviceHealthMonitor tests."""

from device_simulator.core.device_state import (
    DeviceState,
)
from device_simulator.device_health.device_health_monitor import (
    DeviceHealthMonitor,
    DeviceHealthStatus,
)


def test_offline_device_is_degraded() -> None:
    monitor = (
        DeviceHealthMonitor(
            device_id="test-device",
            software_version="1.0.0",
        )
    )

    report = monitor.create_report(
        device_state=(
            DeviceState.OFFLINE
        ),
        sensor_statuses={
            "heart_rate": "OK",
            "skin_temperature": "OK",
            "step_counter": "OK",
            "battery": "OK",
        },
        battery_percentage=80.0,
        mqtt_connected=False,
        offline_queue_size=4,
    )

    assert (
        report.device_status
        == DeviceHealthStatus.DEGRADED
    )

    assert (
        report.offline_queue_size
        == 4
    )