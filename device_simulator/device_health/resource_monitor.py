"""Local computer resource monitoring for the HealthBand simulator."""

from dataclasses import dataclass

import psutil


@dataclass(frozen=True, slots=True)
class ResourceSnapshot:
    """Resource usage of the simulated HealthBand process."""

    process_cpu_percentage: float
    process_memory_mb: float
    system_available_memory_mb: float


class ResourceMonitor:
    """Read CPU and memory information for the simulator."""

    def __init__(self) -> None:
        self._process = psutil.Process()

    def read(self) -> ResourceSnapshot:
        """Read current process and system resource usage."""

        process_memory = (
            self._process.memory_info().rss
            / 1024
            / 1024
        )

        available_memory = (
            psutil.virtual_memory().available
            / 1024
            / 1024
        )

        cpu = self._process.cpu_percent(
            interval=None
        )

        return ResourceSnapshot(
            process_cpu_percentage=round(
                cpu,
                2,
            ),
            process_memory_mb=round(
                process_memory,
                2,
            ),
            system_available_memory_mb=round(
                available_memory,
                2,
            ),
        )