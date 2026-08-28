"""Bootstrap local HealthBand release storage."""

import argparse
from pathlib import Path
import shutil

from device_simulator.ota.package_verifier import (
    PackageVerifier,
)
from device_simulator.ota.release_manager import (
    ReleaseManager,
)


def read_sha_file(
    path: Path,
) -> str:
    """Read first SHA-256 token."""

    text = (
        path.read_text(
            encoding="utf-8"
        )
        .strip()
    )


    if (
        not text
    ):
        raise RuntimeError(
            f"SHA file is empty: {path}"
        )


    return (
        text.split()[0]
    )


def main() -> None:
    """Verify, install and activate baseline release."""

    parser = (
        argparse.ArgumentParser(
            description=(
                "Bootstrap HealthBand release storage."
            )
        )
    )


    parser.add_argument(
        "archive",
    )


    parser.add_argument(
        "--releases-root",
        default="releases",
    )


    parser.add_argument(
        "--force",
        action="store_true",
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


    expected_sha256 = (
        read_sha_file(
            sha_file
        )
    )


    verifier = (
        PackageVerifier()
    )


    verified = (
        verifier.verify_archive(
            archive_path=(
                archive
            ),
            expected_sha256=(
                expected_sha256
            ),
            expected_size_bytes=(
                archive.stat().st_size
            ),
        )
    )


    staging = (
        archive.parent
        / ".bootstrap_staging"
    )


    try:

        verifier.extract_and_verify(
            verified,
            staging,
        )


        manager = (
            ReleaseManager(
                args.releases_root
            )
        )


        manager.install_from_staging(
            staging_root=(
                staging
            ),
            manifest=(
                verified.manifest
            ),
            replace_existing=(
                args.force
            ),
        )


        if (
            manager.read_active_state()
            is None
        ):

            manager.initialize_active_release(
                verified.manifest.version
            )


        print(
            "Installed release:",
            verified.manifest.version,
        )


        print(
            "Active release:",
            manager.get_active_version(),
        )


    finally:

        shutil.rmtree(
            staging,
            ignore_errors=True,
        )


if __name__ == "__main__":
    main()