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


def test_version2_spo2_fields_are_accepted_by_api() -> None:
    model = (
        ConfigurationUpdateRequest(
            spo2MeasurementEnabled=True,
            spo2AlertsEnabled=True,
            spo2MinimumThreshold=92.0,
        )
    )

    assert (
        model.spo2MeasurementEnabled
        is True
    )

    assert (
        model.spo2AlertsEnabled
        is True
    )

    assert (
        model.spo2MinimumThreshold
        == 92.0
    )


def test_invalid_spo2_threshold_is_rejected_by_api() -> None:
    with pytest.raises(
        ValidationError
    ):
        ConfigurationUpdateRequest(
            spo2MinimumThreshold=120.0
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