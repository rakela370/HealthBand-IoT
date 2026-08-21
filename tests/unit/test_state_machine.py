"""Unit tests for the HealthBand state machine."""

import pytest

from device_simulator.core.device_state import DeviceState
from device_simulator.core.state_machine import (
    InvalidStateTransitionError,
    StateMachine,
)


def test_initial_state_is_booting() -> None:
    state_machine = StateMachine()

    assert state_machine.current_state == DeviceState.BOOTING


def test_booting_can_transition_to_self_test() -> None:
    state_machine = StateMachine()

    transition = state_machine.transition_to(
        DeviceState.SELF_TEST,
        reason="Test boot sequence.",
    )

    assert transition.previous_state == DeviceState.BOOTING
    assert transition.current_state == DeviceState.SELF_TEST
    assert state_machine.current_state == DeviceState.SELF_TEST


def test_monitoring_can_transition_to_updating() -> None:
    state_machine = StateMachine(
        initial_state=DeviceState.MONITORING
    )

    transition = state_machine.transition_to(
        DeviceState.UPDATING,
        reason="OTA update requested.",
    )

    assert transition.previous_state == DeviceState.MONITORING
    assert transition.current_state == DeviceState.UPDATING


def test_error_cannot_transition_directly_to_monitoring() -> None:
    state_machine = StateMachine(
        initial_state=DeviceState.ERROR
    )

    with pytest.raises(InvalidStateTransitionError):
        state_machine.transition_to(
            DeviceState.MONITORING,
            reason="Invalid recovery attempt.",
        )


def test_transition_is_stored_in_history() -> None:
    state_machine = StateMachine()

    state_machine.transition_to(
        DeviceState.SELF_TEST,
        reason="Test.",
    )

    assert len(state_machine.history) == 1
    assert (
        state_machine.history[0].current_state
        == DeviceState.SELF_TEST
    )