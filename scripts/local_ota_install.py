"""Run one HealthBand OTA installation from a local ZIP file."""

import argparse
from pathlib import Path

from device_simulator.ota.ota_agent import (
    OtaAgent,
    OtaInstallRequest,
)
from device_simulator.ota.package_downloader import (
    PackageDownloader,
)
from device_simulator.ota.package_verifier import (
    PackageVerifier,
)
from device_simulator.ota.release_manager import (
    ReleaseManager,
)
from device_simulator.ota.rollback_manager import (
    RollbackManager,
)


def read_sha_file(
    archive: Path,
) -> str:
    """Read sibling .sha256 file."""

    sha_file = (
        archive.with_name(
            archive.name
            + ".sha256"
        )
    )


    if (
        not sha_file
        .is_file()
    ):
        raise RuntimeError(
            f"Missing SHA file: {sha_file}"
        )


    return (
        sha_file
        .read_text(
            encoding="utf-8"
        )
        .strip()
        .split()[0]
    )


def main() -> None:
    """Install one newer release locally."""

    parser = (
        argparse.ArgumentParser(
            description=(
                "Install local HealthBand OTA package."
            )
        )
    )


    parser.add_argument(
        "archive",
    )


    parser.add_argument(
        "--target-version",
        required=True,
    )


    args = (
        parser.parse_args()
    )


    archive = (
        Path(
            args.archive
        )
        .expanduser()
        .resolve()
    )


    release_manager = (
        ReleaseManager(
            "releases"
        )
    )


    rollback_manager = (
        RollbackManager(
            release_manager
        )
    )


    downloader = (
        PackageDownloader(
            "ota_downloads"
        )
    )


    verifier = (
        PackageVerifier()
    )


    def progress(
        value,
    ) -> None:

        print(
            (
                f"[{value.progress_percentage:3d}%] "
                f"{value.phase.value}: "
                f"{value.message}"
            )
        )


    agent = (
        OtaAgent(
            downloader=(
                downloader
            ),
            verifier=(
                verifier
            ),
            release_manager=(
                release_manager
            ),
            rollback_manager=(
                rollback_manager
            ),
            staging_root=(
                ".ota_staging"
            ),
            progress_callback=(
                progress
            ),
        )
    )


    result = (
        agent.install(
            OtaInstallRequest(
                source=(
                    str(
                        archive
                    )
                ),
                expected_sha256=(
                    read_sha_file(
                        archive
                    )
                ),
                expected_size_bytes=(
                    archive.stat().st_size
                ),
                target_version=(
                    args.target_version
                ),
            )
        )
    )


    print()
    print(
        "Success:",
        result.success,
    )


    print(
        "Active version:",
        result.active_version,
    )


    print(
        "Rollback:",
        result.rollback_performed,
    )


    print(
        "Restart required:",
        result.restart_required,
    )


    print(
        "Message:",
        result.message,
    )


    if (
        not result.success
    ):
        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()