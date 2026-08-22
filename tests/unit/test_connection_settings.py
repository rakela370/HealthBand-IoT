"""Unit tests for AWS IoT connection configuration."""

from pathlib import Path

import pytest

from device_simulator.communication.connection_manager import (
    AwsIotConfigurationError,
    AwsIotConnectionSettings,
)


def create_test_certificate_files(
    tmp_path: Path,
) -> tuple[
    Path,
    Path,
    Path,
]:
    cert = (
        tmp_path
        / "device.pem.crt"
    )

    key = (
        tmp_path
        / "private.pem.key"
    )

    ca = (
        tmp_path
        / "AmazonRootCA1.pem"
    )

    cert.write_text(
        "test-certificate",
        encoding="utf-8",
    )

    key.write_text(
        "test-private-key",
        encoding="utf-8",
    )

    ca.write_text(
        "test-root-ca",
        encoding="utf-8",
    )

    return (
        cert,
        key,
        ca,
    )


def test_settings_are_loaded_from_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cert, key, ca = (
        create_test_certificate_files(
            tmp_path
        )
    )

    monkeypatch.chdir(
        tmp_path
    )

    monkeypatch.setenv(
        "AWS_REGION",
        "eu-central-1",
    )

    monkeypatch.setenv(
        "AWS_IOT_ENDPOINT",
        "example-ats.iot.eu-central-1.amazonaws.com",
    )

    monkeypatch.setenv(
        "HEALTHBAND_DEVICE_ID",
        "healthband-device-001",
    )

    monkeypatch.setenv(
        "AWS_IOT_CERT_PATH",
        str(cert),
    )

    monkeypatch.setenv(
        "AWS_IOT_PRIVATE_KEY_PATH",
        str(key),
    )

    monkeypatch.setenv(
        "AWS_ROOT_CA_PATH",
        str(ca),
    )

    settings = (
        AwsIotConnectionSettings.from_environment()
    )

    assert (
        settings.region
        == "eu-central-1"
    )

    assert (
        settings.client_id
        == "healthband-device-001"
    )

    assert (
        settings.port
        == 8883
    )


def test_missing_endpoint_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cert, key, ca = (
        create_test_certificate_files(
            tmp_path
        )
    )

    monkeypatch.chdir(
        tmp_path
    )

    monkeypatch.setenv(
        "AWS_REGION",
        "eu-central-1",
    )

    monkeypatch.delenv(
        "AWS_IOT_ENDPOINT",
        raising=False,
    )

    monkeypatch.setenv(
        "HEALTHBAND_DEVICE_ID",
        "healthband-device-001",
    )

    monkeypatch.setenv(
        "AWS_IOT_CERT_PATH",
        str(cert),
    )

    monkeypatch.setenv(
        "AWS_IOT_PRIVATE_KEY_PATH",
        str(key),
    )

    monkeypatch.setenv(
        "AWS_ROOT_CA_PATH",
        str(ca),
    )

    with pytest.raises(
        AwsIotConfigurationError
    ):
        AwsIotConnectionSettings.from_environment()