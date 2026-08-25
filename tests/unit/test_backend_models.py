"""Tests for backend Pydantic API models."""

import pytest
from pydantic import (
    ValidationError,
)

from control_backend.models.command_models import (
    BackendCommandType,
    CommandCreateRequest,
)
from control_backend.models.configuration_models import (
    ConfigurationUpdateRequest,
)


def test_valid_partial_configuration() -> None:
    model = (
        ConfigurationUpdateRequest(
            measurementIntervalSec=4,
            temperatureUnit=(
                "FAHRENHEIT"
            ),
        )
    )

    assert (
        model.measurementIntervalSec
        == 4
    )


def test_invalid_interval_is_rejected() -> None:
    with pytest.raises(
        ValidationError
    ):
        ConfigurationUpdateRequest(
            measurementIntervalSec=0
        )


def test_version2_field_is_rejected_in_version1_api() -> None:
    with pytest.raises(
        ValidationError
    ):
        ConfigurationUpdateRequest(
            spo2MeasurementEnabled=True
        )


def test_valid_command_type() -> None:
    model = (
        CommandCreateRequest(
            type=(
                "REQUEST_DEVICE_HEALTH"
            )
        )
    )

    assert (
        model.type
        == BackendCommandType
        .REQUEST_DEVICE_HEALTH
    )


def test_unknown_command_type_is_rejected() -> None:
    with pytest.raises(
        ValidationError
    ):
        CommandCreateRequest(
            type="FLY_TO_THE_MOON"
        )