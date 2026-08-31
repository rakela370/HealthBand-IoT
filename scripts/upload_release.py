"""Upload one HealthBand OTA release to the private S3 OTA bucket."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import boto3
from dotenv import load_dotenv


DEFAULT_REGION = "eu-central-1"
DEFAULT_S3_PREFIX = "releases"
DEFAULT_ARTIFACTS_ROOT = "ota_artifacts"
DEFAULT_RESOURCE_STATE_PATH = "runtime/ota_aws_resources.json"


def normalized_prefix(value: str) -> str:
    """Return an S3 prefix without leading/trailing slashes."""

    return value.strip().strip("/") or DEFAULT_S3_PREFIX


def resolve_project_path(
    value: str,
) -> Path:
    """Resolve one path relative to the repository root."""

    path = Path(value).expanduser()

    if not path.is_absolute():
        path = Path.cwd() / path

    return path.resolve()


def load_resources(
    path: Path,
) -> dict[str, Any]:
    """Read local non-secret OTA resource metadata when available."""

    if not path.is_file():
        return {}

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(data, dict):
        raise RuntimeError(
            f"{path} must contain a JSON object."
        )

    return data


def calculate_sha256(
    path: Path,
) -> str:
    """Calculate the SHA-256 digest of one release artifact."""

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def expected_sha256(
    sha_file: Path,
) -> str:
    """Parse the first SHA-256 digest from the release sidecar file."""

    content = sha_file.read_text(
        encoding="utf-8"
    ).strip()

    if not content:
        raise RuntimeError(
            f"SHA-256 file is empty: {sha_file}"
        )

    value = content.split()[0].strip().lower()

    if (
        len(value) != 64
        or any(
            character not in "0123456789abcdef"
            for character in value
        )
    ):
        raise RuntimeError(
            f"Invalid SHA-256 digest in {sha_file}."
        )

    return value


def build_s3_key(
    prefix: str,
    version: str,
    filename: str,
) -> str:
    """Build an OTA object key below the configured prefix."""

    return "/".join(
        (
            normalized_prefix(prefix),
            version.strip(),
            filename.strip(),
        )
    )


def main() -> None:
    """Validate and upload ZIP, manifest and SHA file."""

    project_root = Path.cwd()

    load_dotenv(
        project_root / ".env",
        override=False,
    )

    parser = argparse.ArgumentParser(
        description=(
            "Upload a HealthBand OTA release to private S3."
        )
    )

    parser.add_argument(
        "--version",
        required=True,
    )

    parser.add_argument(
        "--bucket",
        default=None,
    )

    parser.add_argument(
        "--prefix",
        default=None,
    )

    parser.add_argument(
        "--region",
        default=None,
    )

    parser.add_argument(
        "--profile",
        default=None,
    )

    parser.add_argument(
        "--artifacts-root",
        default=None,
    )

    args = parser.parse_args()

    resource_state_value = os.getenv(
        "OTA_RESOURCE_STATE_PATH",
        DEFAULT_RESOURCE_STATE_PATH,
    ).strip() or DEFAULT_RESOURCE_STATE_PATH

    resources = load_resources(
        resolve_project_path(
            resource_state_value
        )
    )

    region = (
        args.region
        or os.getenv(
            "AWS_REGION",
            "",
        ).strip()
        or str(
            resources.get(
                "region",
                "",
            )
        ).strip()
        or DEFAULT_REGION
    )

    profile = (
        args.profile
        or os.getenv(
            "AWS_PROFILE",
            "",
        ).strip()
        or None
    )

    bucket = (
        args.bucket
        or os.getenv(
            "OTA_S3_BUCKET",
            "",
        ).strip()
        or str(
            resources.get(
                "bucket",
                "",
            )
        ).strip()
    )

    if not bucket:
        raise RuntimeError(
            "OTA S3 bucket is unknown. Configure OTA_S3_BUCKET "
            "or run scripts.provision_ota_aws."
        )

    prefix = normalized_prefix(
        args.prefix
        or os.getenv(
            "OTA_S3_PREFIX",
            "",
        ).strip()
        or str(
            resources.get(
                "s3Prefix",
                "",
            )
        ).strip()
        or DEFAULT_S3_PREFIX
    )

    artifacts_root_value = (
        args.artifacts_root
        or os.getenv(
            "OTA_ARTIFACTS_ROOT",
            DEFAULT_ARTIFACTS_ROOT,
        ).strip()
        or DEFAULT_ARTIFACTS_ROOT
    )

    artifacts_root = resolve_project_path(
        artifacts_root_value
    )

    version = args.version.strip()

    directory = (
        artifacts_root
        / f"version_{version}"
    )

    archive = (
        directory
        / f"healthband-{version}.zip"
    )

    manifest = directory / "manifest.json"

    sha_file = (
        directory
        / f"healthband-{version}.zip.sha256"
    )

    required = (
        archive,
        manifest,
        sha_file,
    )

    missing = [
        str(path)
        for path in required
        if not path.is_file()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing release artifact(s): "
            + ", ".join(missing)
        )

    manifest_data = json.loads(
        manifest.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(manifest_data, dict):
        raise RuntimeError(
            "Release manifest must contain a JSON object."
        )

    manifest_version = str(
        manifest_data.get(
            "version",
            "",
        )
    ).strip()

    manifest_artifact = str(
        manifest_data.get(
            "artifact",
            "",
        )
    ).strip()

    if manifest_version != version:
        raise RuntimeError(
            "Release manifest version does not match --version: "
            f"{manifest_version!r} != {version!r}."
        )

    if manifest_artifact != archive.name:
        raise RuntimeError(
            "Release manifest artifact does not match archive: "
            f"{manifest_artifact!r} != {archive.name!r}."
        )

    expected_digest = expected_sha256(
        sha_file
    )

    actual_digest = calculate_sha256(
        archive
    )

    if actual_digest != expected_digest:
        raise RuntimeError(
            "Release archive SHA-256 verification failed before upload. "
            f"Expected {expected_digest}, got {actual_digest}."
        )

    session_kwargs: dict[str, str] = {
        "region_name": str(region),
    }

    if profile:
        session_kwargs["profile_name"] = str(
            profile
        )

    session = boto3.Session(
        **session_kwargs
    )

    s3 = session.client("s3")

    for path in required:
        key = build_s3_key(
            prefix,
            version,
            path.name,
        )

        s3.upload_file(
            str(path),
            str(bucket),
            key,
            ExtraArgs={
                "ServerSideEncryption": "AES256",
            },
        )

        head = s3.head_object(
            Bucket=str(bucket),
            Key=key,
        )

        print(
            f"Uploaded s3://{bucket}/{key} "
            f"({head['ContentLength']} bytes)"
        )

    print(
        "Release upload complete. "
        f"version={version} prefix={prefix}"
    )


if __name__ == "__main__":
    main()