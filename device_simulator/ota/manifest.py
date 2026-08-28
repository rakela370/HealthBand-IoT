"""HealthBand OTA manifest parsing and version validation."""

from dataclasses import dataclass
import re
from typing import Any


_SHA256_RE = re.compile(
    r"^[0-9a-fA-F]{64}$"
)

_VERSION_RE = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)$"
)


class ManifestValidationError(
    ValueError
):
    """Raised when an OTA manifest is structurally invalid."""


def parse_version(
    value: str,
) -> tuple[
    int,
    int,
    int,
]:
    """Parse strict MAJOR.MINOR.PATCH project version."""

    match = (
        _VERSION_RE.fullmatch(
            value.strip()
        )
    )

    if (
        match is None
    ):
        raise ManifestValidationError(
            f"Invalid semantic version '{value}'. "
            "Expected MAJOR.MINOR.PATCH."
        )

    return tuple(
        int(
            part
        )
        for part
        in match.groups()
    )


def is_newer_version(
    candidate: str,
    current: str,
) -> bool:
    """Return True only when candidate is newer than current."""

    return (
        parse_version(
            candidate
        )
        >
        parse_version(
            current
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class OtaManifest:
    """Validated metadata embedded in a HealthBand OTA archive."""

    product: str

    version: str

    minimum_current_version: str

    artifact: str

    capabilities: tuple[
        str,
        ...
    ]

    files: dict[
        str,
        str,
    ]

    entry_point: str

    created_at: str


    @classmethod
    def from_dict(
        cls,
        data: dict[
            str,
            Any,
        ],
    ) -> "OtaManifest":
        """Validate decoded manifest JSON."""

        required = {
            "product",
            "version",
            "minimumCurrentVersion",
            "artifact",
            "capabilities",
            "files",
            "entryPoint",
            "createdAt",
        }


        missing = sorted(
            required
            - data.keys()
        )


        if missing:
            raise ManifestValidationError(
                "Manifest is missing required field(s): "
                + ", ".join(
                    missing
                )
            )


        product = str(
            data[
                "product"
            ]
        ).strip()


        if (
            product
            != "HealthBand"
        ):
            raise ManifestValidationError(
                "Manifest product must be 'HealthBand'."
            )


        version = str(
            data[
                "version"
            ]
        ).strip()


        minimum_current_version = str(
            data[
                "minimumCurrentVersion"
            ]
        ).strip()


        parse_version(
            version
        )


        parse_version(
            minimum_current_version
        )


        artifact = str(
            data[
                "artifact"
            ]
        ).strip()


        if (
            not artifact
            .lower()
            .endswith(
                ".zip"
            )
        ):
            raise ManifestValidationError(
                "Manifest artifact must be a .zip file."
            )


        capabilities_raw = (
            data[
                "capabilities"
            ]
        )


        if (
            not isinstance(
                capabilities_raw,
                list,
            )
            or not capabilities_raw
        ):
            raise ManifestValidationError(
                "Manifest capabilities must be "
                "a non-empty list."
            )


        capabilities = tuple(
            str(
                value
            ).strip()
            for value
            in capabilities_raw
            if str(
                value
            ).strip()
        )


        if (
            len(
                capabilities
            )
            !=
            len(
                capabilities_raw
            )
        ):
            raise ManifestValidationError(
                "Manifest capabilities cannot "
                "contain empty values."
            )


        files_raw = (
            data[
                "files"
            ]
        )


        if (
            not isinstance(
                files_raw,
                dict,
            )
            or not files_raw
        ):
            raise ManifestValidationError(
                "Manifest files must be a non-empty object."
            )


        files: dict[
            str,
            str,
        ] = {}


        for (
            relative_path,
            digest,
        ) in files_raw.items():

            path = str(
                relative_path
            ).replace(
                "\\",
                "/",
            ).strip()


            sha256 = str(
                digest
            ).strip().lower()


            if (
                not path
                or path.startswith(
                    "/"
                )
                or ".."
                in path.split(
                    "/"
                )
            ):
                raise ManifestValidationError(
                    f"Unsafe manifest file path "
                    f"'{relative_path}'."
                )


            if (
                _SHA256_RE.fullmatch(
                    sha256
                )
                is None
            ):
                raise ManifestValidationError(
                    f"Invalid SHA-256 for '{path}'."
                )


            files[
                path
            ] = (
                sha256
            )


        entry_point = str(
            data[
                "entryPoint"
            ]
        ).strip()


        if (
            not entry_point
            or entry_point.startswith(
                "/"
            )
            or ".."
            in entry_point.split(
                "/"
            )
        ):
            raise ManifestValidationError(
                "Manifest entryPoint is unsafe."
            )


        created_at = str(
            data[
                "createdAt"
            ]
        ).strip()


        if (
            not created_at
        ):
            raise ManifestValidationError(
                "Manifest createdAt cannot be empty."
            )


        return cls(
            product=(
                product
            ),
            version=(
                version
            ),
            minimum_current_version=(
                minimum_current_version
            ),
            artifact=(
                artifact
            ),
            capabilities=(
                capabilities
            ),
            files=(
                files
            ),
            entry_point=(
                entry_point
            ),
            created_at=(
                created_at
            ),
        )


    def validate_upgrade_from(
        self,
        current_version: str,
    ) -> None:
        """
        Validate target version and minimum source version.

        Downgrade or reinstall of the same version is rejected.
        """

        current = (
            parse_version(
                current_version
            )
        )


        target = (
            parse_version(
                self.version
            )
        )


        minimum = (
            parse_version(
                self.minimum_current_version
            )
        )


        if (
            target
            <= current
        ):
            raise ManifestValidationError(
                f"Target version {self.version} "
                f"must be newer than current "
                f"version {current_version}."
            )


        if (
            current
            < minimum
        ):
            raise ManifestValidationError(
                f"Current version {current_version} "
                f"is below minimum supported "
                f"version "
                f"{self.minimum_current_version}."
            )