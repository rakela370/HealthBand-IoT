"""Stateful threshold evaluation for HealthBand alerts."""

from datetime import datetime


class ThresholdEvaluator:
    """
    Track consecutive rule violations and alert cooldown periods.

    This prevents one short abnormal sample from immediately
    generating an alert.
    """

    def __init__(self) -> None:
        self._consecutive: dict[
            str,
            int,
        ] = {}

        self._last_triggered: dict[
            str,
            datetime,
        ] = {}

    def should_trigger(
        self,
        rule_key: str,
        condition: bool,
        now: datetime,
        consecutive_required: int = 3,
        cooldown_sec: float = 30.0,
    ) -> bool:
        """Return True when an alert rule should trigger."""

        if consecutive_required <= 0:
            raise ValueError(
                "consecutive_required must be positive."
            )

        if not condition:
            self._consecutive[
                rule_key
            ] = 0

            return False

        count = (
            self._consecutive.get(
                rule_key,
                0,
            )
            + 1
        )

        self._consecutive[
            rule_key
        ] = count

        if count < consecutive_required:
            return False

        previous_trigger = (
            self._last_triggered.get(
                rule_key
            )
        )

        if previous_trigger is not None:
            elapsed = (
                now - previous_trigger
            ).total_seconds()

            if elapsed < cooldown_sec:
                return False

        self._last_triggered[
            rule_key
        ] = now

        self._consecutive[
            rule_key
        ] = 0

        return True

    def clear(self) -> None:
        """Clear all threshold history."""

        self._consecutive.clear()
        self._last_triggered.clear()