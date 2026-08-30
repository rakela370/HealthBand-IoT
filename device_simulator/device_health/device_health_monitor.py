"""Technical health monitoring for the simulated HealthBand."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from time import monotonic
from typing import Any

from device_simulator.core.device_state import (
    DeviceState,
)
from device_simulator.device_health.fault_manager import (
    FaultManager,
)
from device_simulator.device_health.resource_monitor import (
    ResourceMonitor,
)
from device_simulator.device_health.sensor_health_monitor import (
    SensorHealthMonitor,
)
from device_simulator.utils.versioning import (
    is_at_least,
)


class DeviceHealthStatus(StrEnum):
    """Overall technical HealthBand health state."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


@dataclass(frozen=True, slots=True)
class DeviceHealthReport:
    """One technical HealthBand device-health report."""

    device_id: str
    device_status: DeviceHealthStatus
    device_state: DeviceState
    software_version: str

    uptime_sec: int

    mqtt_connected: bool | None

    battery_percentage: float | None

    offline_queue_size: int
    local_database_size_bytes: int

    reconnect_attempts: int
    mqtt_send_failures: int

    sensors: dict[str, str]

    process_cpu_percentage: float
    process_memory_mb: float
    system_available_memory_mb: float

    capabilities: tuple[str, ...]

    last_error: str | None

    timestamp: datetime

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """Convert report into serializable dictionary."""

        return {
            "schemaVersion": (
                2
                if is_at_least(
                    self.software_version,
                    "2.0.0",
                )
                else 1
            ),
            "deviceId": (
                self.device_id
            ),
            "deviceStatus": (
                self.device_status.value
            ),
            "deviceState": (
                self.device_state.value
            ),
            "softwareVersion": (
                self.software_version
            ),
            "uptimeSec": (
                self.uptime_sec
            ),
            "mqttConnected": (
                self.mqtt_connected
            ),
            "batteryPercentage": (
                self.battery_percentage
            ),
            "offlineQueueSize": (
                self.offline_queue_size
            ),
            "localDatabaseSizeBytes": (
                self.local_database_size_bytes
            ),
            "reconnectAttempts": (
                self.reconnect_attempts
            ),
            "mqttSendFailures": (
                self.mqtt_send_failures
            ),
            "sensors": (
                self.sensors
            ),
            "resources": {
                "processCpuPercentage": (
                    self.process_cpu_percentage
                ),
                "processMemoryMb": (
                    self.process_memory_mb
                ),
                "systemAvailableMemoryMb": (
                    self.system_available_memory_mb
                ),
            },
            "capabilities": list(
                self.capabilities
            ),
            "lastError": (
                self.last_error
            ),
            "timestamp": (
                self.timestamp.isoformat()
            ),
            "simulated": True,
        }


class DeviceHealthMonitor:
    """Create technical health reports for HealthBand."""

    VERSION_1_CAPABILITIES = (
        "HEART_RATE_MONITORING",
        "SKIN_TEMPERATURE_MONITORING",
        "STEP_COUNTING",
        "LOCAL_ANALYTICS",
    )

    VERSION_2_CAPABILITIES = (
        *VERSION_1_CAPABILITIES,
        "SPO2_MONITORING",
        "CALORIE_ESTIMATION",
    )

    def __init__(
        self,
        device_id: str,
        software_version: str,
        low_battery_threshold: float = 15.0,
    ) -> None:
        self.device_id = (
            device_id
        )

        self.software_version = (
            software_version
        )

        self.low_battery_threshold = (
            low_battery_threshold
        )

        self._start_time = (
            monotonic()
        )

        self.resource_monitor = (
            ResourceMonitor()
        )

        self.sensor_health_monitor = (
            SensorHealthMonitor()
        )

        self.fault_manager = (
            FaultManager()
        )

    @property
    def capabilities(
        self,
    ) -> tuple[str, ...]:
        """Return capabilities supported by the active software version."""

        if is_at_least(
            self.software_version,
            "2.0.0",
        ):
            return (
                self.VERSION_2_CAPABILITIES
            )

        return (
            self.VERSION_1_CAPABILITIES
        )

    def record_fault(
        self,
        error: str,
    ) -> None:
        """Record one technical device fault."""

        self.fault_manager.record(
            error
        )

    def create_report(
        self,
        device_state: DeviceState,
        sensor_statuses: dict[str, str],
        battery_percentage: float | None,
        mqtt_connected: bool | None = None,
        offline_queue_size: int = 0,
        local_database_size_bytes: int = 0,
        reconnect_attempts: int = 0,
        mqtt_send_failures: int = 0,
    ) -> DeviceHealthReport:
        """Create one technical device-health report."""

        sensor_summary = (
            self.sensor_health_monitor.evaluate(
                sensor_statuses
            )
        )

        health_status = (
            DeviceHealthStatus.HEALTHY
        )

        if (
            device_state
            == DeviceState.ERROR
        ):
            health_status = (
                DeviceHealthStatus.UNHEALTHY
            )

        elif (
            sensor_summary.failed_sensors
            or sensor_summary.degraded_sensors
            or (
                battery_percentage
                is not None
                and battery_percentage
                < self.low_battery_threshold
            )
            or mqtt_connected is False
            or offline_queue_size > 0
            or device_state
            == DeviceState.OFFLINE
        ):
            health_status = (
                DeviceHealthStatus.DEGRADED
            )

        resources = (
            self.resource_monitor.read()
        )

        return DeviceHealthReport(
            device_id=(
                self.device_id
            ),
            device_status=(
                health_status
            ),
            device_state=(
                device_state
            ),
            software_version=(
                self.software_version
            ),
            uptime_sec=int(
                monotonic()
                - self._start_time
            ),
            mqtt_connected=(
                mqtt_connected
            ),
            battery_percentage=(
                battery_percentage
            ),
            offline_queue_size=(
                offline_queue_size
            ),
            local_database_size_bytes=(
                local_database_size_bytes
            ),
            reconnect_attempts=(
                reconnect_attempts
            ),
            mqtt_send_failures=(
                mqtt_send_failures
            ),
            sensors=dict(
                sensor_statuses
            ),
            process_cpu_percentage=(
                resources.process_cpu_percentage
            ),
            process_memory_mb=(
                resources.process_memory_mb
            ),
            system_available_memory_mb=(
                resources.system_available_memory_mb
            ),
            capabilities=(
                self.capabilities
            ),
            last_error=(
                self.fault_manager.last_error
            ),
            timestamp=(
                datetime.now(
                    timezone.utc
                )
            ),
        )