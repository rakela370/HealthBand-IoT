"""Unit tests for HealthBand DeviceHealthMonitor."""

from device_simulator.core.device_state import (
    DeviceState,
)
from device_simulator.device_health.device_health_monitor import (
    DeviceHealthMonitor,
    DeviceHealthStatus,
)


def test_healthy_device_report() -> None:
    monitor = DeviceHealthMonitor(
        device_id="test-device",
        software_version="1.0.0",
    )

    report = monitor.create_report(
        device_state=DeviceState.MONITORING,
        sensor_statuses={
            "heart_rate": "OK",
            "skin_temperature": "OK",
            "step_counter": "OK",
            "battery": "OK",
        },
        battery_percentage=80.0,
    )

    assert (
        report.device_status
        == DeviceHealthStatus.HEALTHY
    )


def test_failed_sensor_makes_device_degraded() -> None:
    monitor = DeviceHealthMonitor(
        device_id="test-device",
        software_version="1.0.0",
    )

    report = monitor.create_report(
        device_state=DeviceState.MONITORING,
        sensor_statuses={
            "heart_rate": "OK",
            "skin_temperature": "FAILED",
            "step_counter": "OK",
            "battery": "OK",
        },
        battery_percentage=80.0,
    )

    assert (
        report.device_status
        == DeviceHealthStatus.DEGRADED
    )


def test_error_state_makes_device_unhealthy() -> None:
    monitor = DeviceHealthMonitor(
        device_id="test-device",
        software_version="1.0.0",
    )

    report = monitor.create_report(
        device_state=DeviceState.ERROR,
        sensor_statuses={
            "heart_rate": "OK",
            "skin_temperature": "OK",
            "step_counter": "OK",
            "battery": "OK",
        },
        battery_percentage=80.0,
    )

    assert (
        report.device_status
        == DeviceHealthStatus.UNHEALTHY
    )


def test_version1_capabilities_are_reported() -> None:
    monitor = DeviceHealthMonitor(
        device_id="test-device",
        software_version="1.0.0",
    )

    report = monitor.create_report(
        device_state=DeviceState.MONITORING,
        sensor_statuses={
            "heart_rate": "OK",
            "skin_temperature": "OK",
            "step_counter": "OK",
            "battery": "OK",
        },
        battery_percentage=80.0,
    )

    assert (
        "HEART_RATE_MONITORING"
        in report.capabilities
    )

    assert (
        "LOCAL_ANALYTICS"
        in report.capabilities
    )

    assert (
        "SPO2_MONITORING"
        not in report.capabilities
    )