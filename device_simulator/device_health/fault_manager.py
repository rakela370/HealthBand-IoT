"""Simple fault tracking for HealthBand device health."""

from collections import deque


class FaultManager:
    """Remember recent internal HealthBand faults."""

    def __init__(
        self,
        maximum_faults: int = 50,
    ) -> None:
        self._faults: deque[str] = deque(
            maxlen=maximum_faults
        )

    @property
    def last_error(self) -> str | None:
        """Return the most recently recorded fault."""

        if not self._faults:
            return None

        return self._faults[-1]

    def record(
        self,
        error: str,
    ) -> None:
        """Record one technical fault."""

        if error:
            self._faults.append(
                error
            )

    def clear(self) -> None:
        """Clear recorded faults."""

        self._faults.clear()