"""Generic OTA job-document validation."""

from dataclasses import dataclass
import re
from typing import Any

from device_simulator.ota.manifest import (
    parse_version,
)


_SHA256_RE = re.compile(
    r"^[0-9a-fA-F]{64}$"
)


class JobDocumentValidationError(
    ValueError
):
    """Raised when OTA job document is invalid."""


@dataclass(
    frozen=True,
    slots=True,
)
class OtaJobDocument:
    """
    Cloud-neutral representation of INSTALL_UPDATE.

    AWS-specific Jobs logic is added in Module 12.
    """

    target_version: str

    artifact_url: str

    sha256: str

    size_bytes: int

    instruction: str

    timeout_sec: int

    restart: bool


    @classmethod
    def from_dict(
        cls,
        data: dict[
            str,
            Any,
        ],
    ) -> "OtaJobDocument":
        """Validate OTA job document."""

        required = {
            "targetVersion",
            "artifactUrl",
            "sha256",
            "sizeBytes",
            "instruction",
            "timeoutSec",
            "restart",
        }


        missing = sorted(
            required
            - data.keys()
        )


        if missing:
            raise JobDocumentValidationError(
                "Job document is missing "
                "required field(s): "
                + ", ".join(
                    missing
                )
            )


        target_version = str(
            data[
                "targetVersion"
            ]
        ).strip()


        parse_version(
            target_version
        )


        artifact_url = str(
            data[
                "artifactUrl"
            ]
        ).strip()


        if (
            not artifact_url
        ):
            raise JobDocumentValidationError(
                "artifactUrl cannot be empty."
            )


        sha256 = str(
            data[
                "sha256"
            ]
        ).strip().lower()


        if (
            _SHA256_RE.fullmatch(
                sha256
            )
            is None
        ):
            raise JobDocumentValidationError(
                "sha256 must contain exactly "
                "64 hexadecimal characters."
            )


        try:

            size_bytes = int(
                data[
                    "sizeBytes"
                ]
            )


            timeout_sec = int(
                data[
                    "timeoutSec"
                ]
            )


        except (
            TypeError,
            ValueError,
        ) as exc:

            raise JobDocumentValidationError(
                "sizeBytes and timeoutSec "
                "must be integers."
            ) from exc


        if (
            size_bytes
            <= 0
        ):
            raise JobDocumentValidationError(
                "sizeBytes must be greater than zero."
            )


        if (
            timeout_sec
            <= 0
        ):
            raise JobDocumentValidationError(
                "timeoutSec must be greater than zero."
            )


        instruction = str(
            data[
                "instruction"
            ]
        ).strip()


        if (
            instruction
            != "INSTALL_UPDATE"
        ):
            raise JobDocumentValidationError(
                "Only INSTALL_UPDATE is supported."
            )


        restart = (
            data[
                "restart"
            ]
        )


        if (
            not isinstance(
                restart,
                bool,
            )
        ):
            raise JobDocumentValidationError(
                "restart must be boolean."
            )


        return cls(
            target_version=(
                target_version
            ),
            artifact_url=(
                artifact_url
            ),
            sha256=(
                sha256
            ),
            size_bytes=(
                size_bytes
            ),
            instruction=(
                instruction
            ),
            timeout_sec=(
                timeout_sec
            ),
            restart=(
                restart
            ),
        )