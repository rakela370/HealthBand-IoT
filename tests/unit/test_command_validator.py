"""Tests for HealthBand command validation."""

import pytest

from device_simulator.commands.command import (
    CommandType,
)
from device_simulator.commands.command_validator import (
    CommandValidationError,
    CommandValidator,
)


def test_valid_scenario_command() -> None:
    validator = CommandValidator(
        "healthband-device-001"
    )

    command = validator.validate(
        {
            "schemaVersion": 1,
            "commandId": "cmd-1",
            "deviceId": "healthband-device-001",
            "type": "CHANGE_SIMULATION_SCENARIO",
            "parameters": {
                "scenario": "RUNNING"
            },
        }
    )

    assert (
        command.type
        == CommandType.CHANGE_SIMULATION_SCENARIO
    )


def test_unknown_command_is_rejected() -> None:
    validator = CommandValidator(
        "healthband-device-001"
    )

    with pytest.raises(
        CommandValidationError
    ):
        validator.validate(
            {
                "commandId": "cmd-2",
                "type": "DO_SOMETHING_UNKNOWN",
            }
        )


def test_invalid_scenario_is_rejected() -> None:
    validator = CommandValidator(
        "healthband-device-001"
    )

    with pytest.raises(
        CommandValidationError
    ):
        validator.validate(
            {
                "commandId": "cmd-3",
                "type": "CHANGE_SIMULATION_SCENARIO",
                "parameters": {
                    "scenario": "FLYING"
                },
            }
        )


def test_command_for_another_device_is_rejected() -> None:
    validator = CommandValidator(
        "healthband-device-001"
    )

    with pytest.raises(
        CommandValidationError
    ):
        validator.validate(
            {
                "commandId": "cmd-4",
                "deviceId": "another-device",
                "type": "REQUEST_DEVICE_HEALTH",
            }
        )