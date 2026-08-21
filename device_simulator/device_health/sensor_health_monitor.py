"""Technical sensor-health evaluation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SensorHealthSummary:
    """Summary of unhealthy HealthBand sensors."""

    failed_sensors: tuple[str, ...]
    degraded_sensors: tuple[str, ...]


class SensorHealthMonitor:
    """Evaluate technical status of all registered sensors."""

    def evaluate(
        self,
        sensor_statuses: dict[str, str],
    ) -> SensorHealthSummary:
        """Return failed and degraded sensors."""

        failed = tuple(
            name
            for name, status
            in sensor_statuses.items()
            if status == "FAILED"
        )

        degraded = tuple(
            name
            for name, status
            in sensor_statuses.items()
            if status == "DEGRADED"
        )

        return SensorHealthSummary(
            failed_sensors=failed,
            degraded_sensors=degraded,
        )