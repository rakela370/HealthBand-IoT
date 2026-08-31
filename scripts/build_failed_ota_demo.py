"""Build an intentionally failing HealthBand 2.0.1 OTA demo release.

The generated release is structurally valid:
- ZIP package is valid.
- Manifest is valid.
- File hashes are valid.
- Outer ZIP SHA-256 is valid.
- Version compatibility is valid.

The bundled release self-test intentionally fails after activation so
the HealthBand OTA rollback mechanism can be demonstrated.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import zipfile

from scripts.build_release import (
    build_file_hashes,
    build_release,
    sha256_file,
    write_zip,
)


TARGET_VERSION = "2.0.1"

MINIMUM_CURRENT_VERSION = "2.0.0"

CAPABILITIES = [
    "HEART_RATE_MONITORING",
    "SKIN_TEMPERATURE_MONITORING",
    "STEP_COUNTING",
    "LOCAL_ANALYTICS",
    "SPO2_MONITORING",
    "CALORIE_ESTIMATION",
]


FAILED_SELF_TEST_SOURCE = '''"""Intentional HealthBand OTA rollback demonstration self-test."""


def main() -> None:
    """Fail intentionally to demonstrate automatic OTA rollback."""

    raise RuntimeError(
        "INTENTIONAL_DEMO_SELF_TEST_FAILURE"
    )


if __name__ == "__main__":
    main()
'''


def main() -> None:
    """Build HealthBand 2.0.1 with an intentional self-test failure."""

    project_root = (
        Path.cwd()
        .resolve()
    )

    output_root = (
        project_root
        / "ota_artifacts"
    )

    print(
        "Building intentional HealthBand "
        f"{TARGET_VERSION} rollback-demo release..."
    )

    (
        archive_path,
        manifest_copy_path,
        sha_path,
    ) = build_release(
        source_root=(
            project_root
        ),
        version=(
            TARGET_VERSION
        ),
        minimum_current_version=(
            MINIMUM_CURRENT_VERSION
        ),
        capabilities=(
            CAPABILITIES
        ),
        output_root=(
            output_root
        ),
    )

    with tempfile.TemporaryDirectory(
        prefix="healthband-failed-ota-demo-"
    ) as temporary_directory:

        staging_root = (
            Path(
                temporary_directory
            )
        )

        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:

            archive.extractall(
                staging_root
            )

        self_test_path = (
            staging_root
            / "self_test.py"
        )

        if not self_test_path.is_file():
            raise RuntimeError(
                "Generated release does not contain "
                "self_test.py."
            )

        self_test_path.write_text(
            FAILED_SELF_TEST_SOURCE,
            encoding="utf-8",
        )

        manifest_path = (
            staging_root
            / "manifest.json"
        )

        if not manifest_path.is_file():
            raise RuntimeError(
                "Generated release does not contain "
                "manifest.json."
            )

        manifest = json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(
            manifest,
            dict,
        ):
            raise RuntimeError(
                "Generated manifest must contain "
                "a JSON object."
            )

        manifest_version = str(
            manifest.get(
                "version",
                "",
            )
        ).strip()

        if (
            manifest_version
            != TARGET_VERSION
        ):
            raise RuntimeError(
                "Generated manifest contains "
                f"unexpected version {manifest_version!r}."
            )

        manifest[
            "demoFailure"
        ] = True

        manifest[
            "demoPurpose"
        ] = (
            "Intentional release self-test failure "
            "used to demonstrate automatic "
            "HealthBand OTA rollback."
        )

        manifest[
            "files"
        ] = (
            build_file_hashes(
                staging_root
            )
        )

        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        write_zip(
            staging_root,
            archive_path,
        )

        manifest_copy_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    archive_sha256 = (
        sha256_file(
            archive_path
        )
    )

    sha_path.write_text(
        (
            f"{archive_sha256}  "
            f"{archive_path.name}\n"
        ),
        encoding="utf-8",
    )

    print()
    print(
        "HealthBand failed-demo release created."
    )

    print(
        f"Version: {TARGET_VERSION}"
    )

    print(
        f"Archive: {archive_path}"
    )

    print(
        f"Manifest: {manifest_copy_path}"
    )

    print(
        f"SHA file: {sha_path}"
    )

    print(
        f"Archive SHA-256: {archive_sha256}"
    )

    print()
    print(
        "Expected OTA behaviour:"
    )

    print(
        "2.0.0 -> install 2.0.1 "
        "-> activation -> self-test FAILED "
        "-> automatic rollback -> 2.0.0"
    )


if __name__ == "__main__":
    main()