"""Regression tests for Module 12 OTA backend wiring."""

from pathlib import Path

from control_backend.models.ota_models import (
    OtaStartRequest,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


def test_ota_request_exposes_target_version() -> None:
    request = (
        OtaStartRequest(
            targetVersion="2.0.0",
        )
    )

    assert (
        request.target_version
        == "2.0.0"
    )


def test_ota_route_uses_target_version_property() -> None:
    source = (
        ROOT
        .joinpath(
            "control_backend",
            "api",
            "ota_routes.py",
        )
        .read_text(
            encoding="utf-8"
        )
    )

    assert (
        "body.target_version"
        in source
    )

    assert (
        "body.version"
        not in source
    )


def test_ota_frontend_api_uses_target_version_json_field() -> None:
    source = (
        ROOT
        .joinpath(
            "web_frontend",
            "js",
            "api.js",
        )
        .read_text(
            encoding="utf-8"
        )
    )

    assert (
        "startOta"
        in source
    )

    assert (
        "targetVersion"
        in source
    )