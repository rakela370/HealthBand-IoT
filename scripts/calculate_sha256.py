"""Calculate SHA-256 for a HealthBand OTA artifact."""

import argparse
from pathlib import Path

from device_simulator.ota.package_verifier import (
    PackageVerifier,
)


def main() -> None:
    """Print SHA-256 of one file."""

    parser = (
        argparse.ArgumentParser(
            description=(
                "Calculate SHA-256 for "
                "a HealthBand OTA file."
            )
        )
    )


    parser.add_argument(
        "path",
        help="Path to file.",
    )


    args = (
        parser.parse_args()
    )


    path = (
        Path(
            args.path
        )
        .expanduser()
        .resolve()
    )


    digest = (
        PackageVerifier
        .calculate_sha256(
            path
        )
    )


    print(
        f"{digest}  {path.name}"
    )


if __name__ == "__main__":
    main()