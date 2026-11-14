"""Regression tests for Module 12 OTA backend wiring."""

import json
from pathlib import Path

from control_backend.models.ota_models import (
    OtaStartRequest,
)
from control_backend.aws.ota_service import OtaService


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

def test_hidden_release_is_not_returned_by_ota_listing(tmp_path: Path) -> None:
    visible = tmp_path / "version_2.0.0"
    hidden = tmp_path / "version_2.0.1"
    visible.mkdir()
    hidden.mkdir()

    for directory, version, is_hidden in (
        (visible, "2.0.0", False),
        (hidden, "2.0.1", True),
    ):
        artifact = f"healthband-{version}.zip"
        (directory / artifact).write_bytes(b"demo")
        (directory / f"{artifact}.sha256").write_text("a" * 64 + "\n")
        (directory / "manifest.json").write_text(
            json.dumps(
                {
                    "version": version,
                    "artifact": artifact,
                    "capabilities": [],
                    "hidden": is_hidden,
                }
            ),
            encoding="utf-8",
        )

    service = object.__new__(OtaService)
    service.artifacts_root = tmp_path
    service.bucket = ""
    service.s3_prefix = "releases"

    releases = service.list_releases()

    assert [item["version"] for item in releases] == ["2.0.0"]
