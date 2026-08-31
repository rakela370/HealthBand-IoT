"""AWS S3 and AWS IoT Jobs operations for HealthBand OTA."""

from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
import json
from math import ceil
from pathlib import Path
import re
from typing import Any

from botocore.exceptions import (
    ClientError,
)

from control_backend.settings import (
    BackendSettings,
)


_VERSION_RE = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)$"
)


CAPABILITY_LABELS = {
    "HEART_RATE_MONITORING":
        "Heart rate monitoring",

    "SKIN_TEMPERATURE_MONITORING":
        "Skin temperature monitoring",

    "STEP_COUNTING":
        "Step counting",

    "LOCAL_ANALYTICS":
        "Local analytics",

    "SPO2_MONITORING":
        "SpO₂ monitoring",

    "CALORIE_ESTIMATION":
        "Estimated calorie analytics",
}


class OtaServiceConfigurationError(
    RuntimeError
):
    """Raised when OTA AWS metadata is unavailable."""


class OtaReleaseNotFoundError(
    FileNotFoundError
):
    """Raised when requested release does not exist."""


class OtaService:
    """List releases, create Jobs and inspect Job execution state."""

    def __init__(
        self,
        settings: BackendSettings,
        s3_client: Any,
        iot_client: Any,
        sts_client: Any,
    ) -> None:
        self.settings = (
            settings
        )

        self.s3 = (
            s3_client
        )

        self.iot = (
            iot_client
        )

        self.sts = (
            sts_client
        )

        resources = (
            self._load_resource_file()
        )

        self.bucket = (
            settings
            .ota_s3_bucket
            .strip()
            or str(
                resources.get(
                    "bucket",
                    "",
                )
            ).strip()
        )

        self.s3_prefix = (
            settings
            .normalized_ota_s3_prefix
            or str(
                resources.get(
                    "s3Prefix",
                    "releases",
                )
            ).strip().strip("/")
            or "releases"
        )

        self.jobs_role_arn = (
            settings
            .ota_jobs_role_arn
            .strip()
            or str(
                resources.get(
                    "jobsRoleArn",
                    "",
                )
            ).strip()
        )

        self.presigned_url_expiry_sec = (
            settings
            .ota_presigned_url_expiry_sec
        )

        self.artifacts_root = (
            settings.resolve_path(
                settings
                .ota_artifacts_root
            )
        )

        self.account_id = str(
            self.sts
            .get_caller_identity()[
                "Account"
            ]
        )

    @staticmethod
    def parse_version(
        version: str,
    ) -> tuple[
        int,
        int,
        int,
    ]:
        match = (
            _VERSION_RE
            .fullmatch(
                version.strip()
            )
        )

        if match is None:
            raise ValueError(
                "Version must use numeric "
                "MAJOR.MINOR.PATCH format."
            )

        return tuple(
            int(
                value
            )
            for value
            in match.groups()
        )  # type: ignore[return-value]

    def list_releases(
        self,
    ) -> list[
        dict[str, Any]
    ]:
        """Return local OTA artifacts and private-S3 state."""

        if not (
            self.artifacts_root
            .is_dir()
        ):
            return []

        releases: list[
            dict[str, Any]
        ] = []

        for directory in (
            self.artifacts_root
            .glob(
                "version_*"
            )
        ):
            if not directory.is_dir():
                continue

            manifest_path = (
                directory
                / "manifest.json"
            )

            if not manifest_path.is_file():
                continue

            try:
                manifest = json.loads(
                    manifest_path
                    .read_text(
                        encoding="utf-8"
                    )
                )

            except (
                OSError,
                json.JSONDecodeError,
            ):
                continue

            version = str(
                manifest.get(
                    "version",
                    "",
                )
            ).strip()

            try:
                self.parse_version(
                    version
                )

            except ValueError:
                continue

            artifact_name = str(
                manifest.get(
                    "artifact",
                    (
                        "healthband-"
                        f"{version}.zip"
                    ),
                )
            ).strip()

            archive = (
                directory
                / artifact_name
            )

            sha_path = (
                directory
                / (
                    f"{artifact_name}"
                    ".sha256"
                )
            )

            if (
                not archive.is_file()
                or not sha_path.is_file()
            ):
                continue

            sha256 = (
                sha_path
                .read_text(
                    encoding="utf-8"
                )
                .strip()
                .split()[
                    0
                ]
            )

            capabilities = [
                str(
                    value
                )
                for value
                in manifest.get(
                    "capabilities",
                    [],
                )
            ]

            s3_key = (
                self._build_s3_key(
                    version=version,
                    filename=artifact_name,
                )
            )

            uploaded = False

            remote_size: (
                int | None
            ) = None

            if self.bucket:
                try:
                    response = (
                        self.s3
                        .head_object(
                            Bucket=(
                                self.bucket
                            ),
                            Key=(
                                s3_key
                            ),
                        )
                    )

                    uploaded = True

                    remote_size = int(
                        response[
                            "ContentLength"
                        ]
                    )

                except ClientError as exc:
                    code = str(
                        exc.response
                        .get(
                            "Error",
                            {},
                        )
                        .get(
                            "Code",
                            "",
                        )
                    )

                    if code not in {
                        "404",
                        "NoSuchKey",
                        "NotFound",
                    }:
                        raise

            releases.append(
                {
                    "version":
                        version,

                    "minimumCurrentVersion":
                        manifest.get(
                            "minimumCurrentVersion"
                        ),

                    "artifact":
                        artifact_name,

                    "sizeBytes":
                        archive
                        .stat()
                        .st_size,

                    "sha256":
                        sha256,

                    "capabilities":
                        capabilities,

                    "features": [
                        CAPABILITY_LABELS
                        .get(
                            capability,
                            capability,
                        )
                        for capability
                        in capabilities
                    ],

                    "uploaded":
                        uploaded,

                    "remoteSizeBytes":
                        remote_size,

                    "s3Key":
                        s3_key,

                    "demoFailure":
                        bool(
                            manifest.get(
                                "demoFailure",
                                False,
                            )
                        ),

                    "demoPurpose":
                        manifest.get(
                            "demoPurpose"
                        ),
                }
            )

        releases.sort(
            key=lambda item:
                self.parse_version(
                    item[
                        "version"
                    ]
                )
        )

        return releases

    def _build_s3_key(
        self,
        *,
        version: str,
        filename: str,
    ) -> str:
        """Build one OTA object key below the configured S3 prefix."""

        parts = [
            self.s3_prefix,
            version.strip(),
            filename.strip(),
        ]

        return "/".join(
            part.strip("/")
            for part in parts
            if part.strip("/")
        )

    def start_job(
        self,
        *,
        device_id: str,
        version: str,
    ) -> dict[str, Any]:
        """Create AWS IoT Job targeting selected release."""

        if (
            not self.bucket
            or not self.jobs_role_arn
        ):
            raise (
                OtaServiceConfigurationError(
                    "OTA AWS resources are "
                    "not configured. Run "
                    "python -m "
                    "scripts.provision_ota_aws "
                    "first."
                )
            )

        release = (
            self.get_release(
                version
            )
        )

        if not release[
            "uploaded"
        ]:
            raise (
                OtaServiceConfigurationError(
                    f"HealthBand {version} "
                    "is not uploaded to the "
                    "private OTA S3 bucket."
                )
            )

        s3_url = (
            "https://s3."
            f"{self.settings.aws_region}"
            ".amazonaws.com/"
            f"{self.bucket}/"
            f"{release['s3Key']}"
        )

        artifact_placeholder = (
            "${aws:iot:"
            "s3-presigned-url-v2:"
            + s3_url
            + "}"
        )

        timeout_sec = int(
            self.settings
            .ota_update_timeout_sec
        )

        job_document = {
            "schemaVersion": 1,
            "instruction": (
                "INSTALL_UPDATE"
            ),
            "targetVersion": (
                version
            ),
            "artifactUrl": (
                artifact_placeholder
            ),
            "sha256": (
                release[
                    "sha256"
                ]
            ),
            "sizeBytes": (
                release[
                    "sizeBytes"
                ]
            ),
            "timeoutSec": (
                timeout_sec
            ),
            "restart": True,
            "capabilities": (
                release[
                    "capabilities"
                ]
            ),
        }

        timestamp = (
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y%m%dT%H%M%S%fZ"
            )
        )

        version_slug = (
            version.replace(
                ".",
                "-",
            )
        )

        job_id = (
            "healthband-"
            f"{version_slug}-"
            f"{timestamp}"
        )

        thing_arn = (
            "arn:aws:iot:"
            f"{self.settings.aws_region}:"
            f"{self.account_id}:"
            f"thing/{device_id}"
        )

        response = (
            self.iot
            .create_job(
                jobId=(
                    job_id
                ),
                targets=[
                    thing_arn
                ],
                document=json.dumps(
                    job_document,
                    separators=(
                        ",",
                        ":",
                    ),
                ),
                description=(
                    "HealthBand OTA "
                    f"update to {version}"
                ),
                presignedUrlConfig={
                    "roleArn": (
                        self.jobs_role_arn
                    ),
                    "expiresInSec": int(
                        self
                        .presigned_url_expiry_sec
                    ),
                },
                targetSelection=(
                    "SNAPSHOT"
                ),
                timeoutConfig={
                    "inProgressTimeoutInMinutes":
                        max(
                            1,
                            ceil(
                                timeout_sec
                                / 60
                            ),
                        ),
                },
            )
        )

        return {
            "jobId":
                job_id,

            "jobArn":
                response.get(
                    "jobArn"
                ),

            "jobIdFromAws":
                response.get(
                    "jobId"
                ),

            "deviceId":
                device_id,

            "targetVersion":
                version,

            "jobDocument":
                job_document,

            "status":
                "QUEUED",
        }

    def get_release(
        self,
        version: str,
    ) -> dict[str, Any]:
        self.parse_version(
            version
        )

        for release in (
            self.list_releases()
        ):
            if (
                release[
                    "version"
                ]
                == version
            ):
                return release

        raise (
            OtaReleaseNotFoundError(
                "HealthBand OTA release "
                f"{version} was not found."
            )
        )

    def latest_job_execution(
        self,
        device_id: str,
    ) -> dict[str, Any] | None:
        """Return latest AWS IoT Job execution."""

        response = (
            self.iot
            .list_job_executions_for_thing(
                thingName=(
                    device_id
                ),
                maxResults=25,
            )
        )

        summaries = (
            response.get(
                "executionSummaries",
                [],
            )
        )

        if not summaries:
            return None

        def updated_at(
            item: dict[str, Any],
        ) -> datetime:
            summary = (
                item.get(
                    "jobExecutionSummary",
                    {},
                )
            )

            value = (
                summary.get(
                    "lastUpdatedAt"
                )
            )

            if isinstance(
                value,
                datetime,
            ):
                return value

            return (
                datetime.min
                .replace(
                    tzinfo=(
                        timezone.utc
                    )
                )
            )

        latest = max(
            summaries,
            key=updated_at,
        )

        job_id = (
            latest.get(
                "jobId"
            )
        )

        if not job_id:
            return None

        detail = (
            self.iot
            .describe_job_execution(
                jobId=str(
                    job_id
                ),
                thingName=(
                    device_id
                ),
            )
            .get(
                "execution",
                {},
            )
        )

        return (
            self._json_safe(
                detail
            )
        )

    def active_version_from_disk(
        self,
    ) -> str | None:
        """Read local active release as same-host fallback."""

        state_path = (
            Path.cwd()
            / "releases"
            / "active_release.json"
        )

        if not state_path.is_file():
            return None

        try:
            data = json.loads(
                state_path
                .read_text(
                    encoding="utf-8"
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ):
            return None

        version = str(
            data.get(
                "activeVersion",
                "",
            )
        ).strip()

        return (
            version
            or None
        )

    def _load_resource_file(
        self,
    ) -> dict[str, Any]:
        path = (
            self.settings
            .resolve_path(
                self.settings
                .ota_resource_state_path
            )
        )

        if not path.is_file():
            return {}

        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise (
                OtaServiceConfigurationError(
                    "Invalid OTA resource "
                    f"state file: {path}"
                )
            ) from exc

        if not isinstance(
            data,
            dict,
        ):
            raise (
                OtaServiceConfigurationError(
                    "OTA resource state must "
                    "be a JSON object."
                )
            )

        return data

    @classmethod
    def _json_safe(
        cls,
        value: Any,
    ) -> Any:
        if isinstance(
            value,
            datetime,
        ):
            return (
                value.isoformat()
            )

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key):
                    cls._json_safe(
                        item
                    )
                for key, item
                in value.items()
            }

        if isinstance(
            value,
            list,
        ):
            return [
                cls._json_safe(
                    item
                )
                for item
                in value
            ]

        return value