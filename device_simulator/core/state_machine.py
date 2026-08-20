"""State machine implementation for the HealthBand device."""

from dataclasses import dataclass
from datetime import datetime, timezone

from device_simulator.core.device_state import DeviceState


class InvalidStateTransitionError(Exception):
    """Raised when an invalid device state transition is attempted."""


@dataclass(frozen=True)
class StateTransition:
    """Represents a validated transition between two device states."""

    previous_state: DeviceState
    current_state: DeviceState
    reason: str
    timestamp: datetime


class StateMachine:
    """Manages logical device state transitions and enforces allowed rules."""

    _ALLOWED_TRANSITIONS: dict[DeviceState, frozenset[DeviceState]] = {
        DeviceState.BOOTING: frozenset(
            {
                DeviceState.SELF_TEST,
                DeviceState.ERROR,
                DeviceState.SHUTTING_DOWN,
            }
        ),
        DeviceState.SELF_TEST: frozenset(
            {
                DeviceState.CONNECTING,
                DeviceState.ERROR,
                DeviceState.SHUTTING_DOWN,
            }
        ),
        DeviceState.CONNECTING: frozenset(
            {
                DeviceState.MONITORING,
                DeviceState.OFFLINE,
                DeviceState.ERROR,
                DeviceState.SHUTTING_DOWN,
            }
        ),
        DeviceState.MONITORING: frozenset(
            {
                DeviceState.WARNING,
                DeviceState.DEGRADED,
                DeviceState.OFFLINE,
                DeviceState.LOW_BATTERY,
                DeviceState.CHARGING,
                DeviceState.MAINTENANCE,
                DeviceState.UPDATING,
                DeviceState.RESTARTING,
                DeviceState.ERROR,
                DeviceState.SHUTTING_DOWN,
            }
        ),
        DeviceState.WARNING: frozenset(
            {
                DeviceState.MONITORING,
                DeviceState.DEGRADED,
                DeviceState.OFFLINE,
                DeviceState.LOW_BATTERY,
                DeviceState.ERROR,
                DeviceState.SHUTTING_DOWN,
            }
        ),
        DeviceState.DEGRADED: frozenset(
            {
                DeviceState.MONITORING,
                DeviceState.WARNING,
                DeviceState.OFFLINE,
                DeviceState.MAINTENANCE,
                DeviceState.ERROR,
                DeviceState.SHUTTING_DOWN,
            }
        ),
        DeviceState.OFFLINE: frozenset(
            {
                DeviceState.CONNECTING,
                DeviceState.MONITORING,
                DeviceState.ERROR,
                DeviceState.SHUTTING_DOWN,
            }
        ),
        DeviceState.LOW_BATTERY: frozenset(
            {
                DeviceState.CHARGING,
                DeviceState.MONITORING,
                DeviceState.SHUTTING_DOWN,
            }
        ),
        DeviceState.CHARGING: frozenset(
            {
                DeviceState.MONITORING,
                DeviceState.SHUTTING_DOWN,
            }
        ),
        DeviceState.MAINTENANCE: frozenset(
            {
                DeviceState.MONITORING,
                DeviceState.UPDATING,
                DeviceState.RESTARTING,
                DeviceState.ERROR,
                DeviceState.SHUTTING_DOWN,
            }
        ),
        DeviceState.UPDATING: frozenset(
            {
                DeviceState.RESTARTING,
                DeviceState.ERROR,
                DeviceState.SHUTTING_DOWN,
            }
        ),
        DeviceState.RESTARTING: frozenset(
            {
                DeviceState.BOOTING,
                DeviceState.ERROR,
                DeviceState.SHUTTING_DOWN,
            }
        ),
        DeviceState.ERROR: frozenset(
            {
                DeviceState.RESTARTING,
                DeviceState.SHUTTING_DOWN,
            }
        ),
        DeviceState.SHUTTING_DOWN: frozenset(),
    }

    def __init__(
        self,
        initial_state: DeviceState = DeviceState.BOOTING,
    ) -> None:
        self._current_state = initial_state
        self._history: list[StateTransition] = []

    @property
    def current_state(self) -> DeviceState:
        return self._current_state

    @property
    def history(self) -> tuple[StateTransition, ...]:
        return tuple(self._history)

    def can_transition_to(self, new_state: DeviceState) -> bool:
        return new_state in self._ALLOWED_TRANSITIONS[self._current_state]

    def transition_to(
        self,
        new_state: DeviceState,
        reason: str,
    ) -> StateTransition:
        if new_state == self._current_state:
            raise InvalidStateTransitionError(
                f"Device is already in state {self._current_state.value}."
            )

        if not self.can_transition_to(new_state):
            raise InvalidStateTransitionError(
                "Invalid state transition: "
                f"{self._current_state.value} -> {new_state.value}"
            )

        transition = StateTransition(
            previous_state=self._current_state,
            current_state=new_state,
            reason=reason,
            timestamp=datetime.now(timezone.utc),
        )

        self._current_state = new_state
        self._history.append(transition)

        return transition
