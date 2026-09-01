"""Reset the local HealthBand demo environment to release 1.0.0.

This script is intended for repeatable diploma-defense demonstrations.

Preserved:
- releases/1.0.0
- releases/backups
- ota_artifacts
- AWS/S3 content

Removed:
- locally installed semantic-version release directories newer/different than 1.0.0
- .ota_staging
- ota_downloads
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RELEASES_ROOT = (
    PROJECT_ROOT
    / "releases"
)

BASELINE_VERSION = (
    "1.0.0"
)

BASELINE_ROOT = (
    RELEASES_ROOT
    / BASELINE_VERSION
)

ACTIVE_RELEASE_FILE = (
    RELEASES_ROOT
    / "active_release.json"
)

RUNTIME_ROOT = (
    PROJECT_ROOT
    / "runtime"
)

PREVIOUS_STATE_BACKUP = (
    RUNTIME_ROOT
    / "active_release.before_demo_reset.json"
)

TEMPORARY_OTA_PATHS = [
    PROJECT_ROOT / ".ota_staging",
    PROJECT_ROOT / "ota_downloads",
]

SEMVER_DIRECTORY_PATTERN = re.compile(
    r"^\d+\.\d+\.\d+$"
)


class DemoResetError(
    RuntimeError
):
    """HealthBand demo reset failed."""


def verify_baseline_release() -> None:
    """Ensure that the HealthBand 1.0.0 baseline is available."""

    main_file = (
        BASELINE_ROOT
        / "payload"
        / "device_simulator"
        / "main.py"
    )

    if not main_file.is_file():

        raise DemoResetError(
            "HealthBand 1.0.0 baseline release "
            "was not found.\n"
            f"Expected:\n{main_file}"
        )


def backup_current_state() -> None:
    """Preserve the previous active release pointer for diagnostics."""

    if not ACTIVE_RELEASE_FILE.is_file():
        return

    RUNTIME_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        ACTIVE_RELEASE_FILE,
        PREVIOUS_STATE_BACKUP,
    )


def windows_clear_attributes(
    path: Path,
) -> None:
    """Remove read-only/system/hidden attributes on Windows."""

    if (
        os.name != "nt"
        or not path.exists()
    ):
        return

    if path.is_dir():

        subprocess.run(
            [
                "cmd",
                "/c",
                "attrib",
                "-R",
                "-S",
                "-H",
                str(
                    path
                    / "*"
                ),
                "/S",
                "/D",
            ],
            stdout=(
                subprocess.DEVNULL
            ),
            stderr=(
                subprocess.DEVNULL
            ),
            check=False,
        )

    subprocess.run(
        [
            "cmd",
            "/c",
            "attrib",
            "-R",
            "-S",
            "-H",
            str(
                path
            ),
        ],
        stdout=(
            subprocess.DEVNULL
        ),
        stderr=(
            subprocess.DEVNULL
        ),
        check=False,
    )


def make_writable_and_retry(
    function,
    path,
    _exc_info,
) -> None:
    """Make one filesystem entry writable and retry the operation."""

    target = (
        Path(
            path
        )
    )

    try:

        os.chmod(
            target,
            stat.S_IWRITE
            | stat.S_IREAD,
        )

    except OSError:

        pass

    function(
        path
    )


def windows_force_remove(
    path: Path,
) -> None:
    """Use native Windows deletion as a final fallback."""

    if (
        os.name != "nt"
        or not path.exists()
    ):
        return

    if path.is_dir():

        subprocess.run(
            [
                "cmd",
                "/c",
                "rmdir",
                "/s",
                "/q",
                str(
                    path
                ),
            ],
            stdout=(
                subprocess.DEVNULL
            ),
            stderr=(
                subprocess.DEVNULL
            ),
            check=False,
        )

    else:

        subprocess.run(
            [
                "cmd",
                "/c",
                "del",
                "/f",
                "/q",
                str(
                    path
                ),
            ],
            stdout=(
                subprocess.DEVNULL
            ),
            stderr=(
                subprocess.DEVNULL
            ),
            check=False,
        )


def remove_path(
    path: Path,
) -> None:
    """Remove a local release/staging path robustly."""

    if not path.exists():
        return

    last_error: (
        Exception
        | None
    ) = None

    for _attempt in range(
        3
    ):

        windows_clear_attributes(
            path
        )

        try:

            if path.is_dir():

                shutil.rmtree(
                    path,
                    onexc=(
                        make_writable_and_retry
                    ),
                )

            else:

                try:

                    path.chmod(
                        stat.S_IWRITE
                        | stat.S_IREAD
                    )

                except OSError:

                    pass

                path.unlink(
                    missing_ok=True
                )

        except Exception as exc:

            last_error = (
                exc
            )

        if not path.exists():
            return

        time.sleep(
            0.3
        )

    windows_clear_attributes(
        path
    )

    windows_force_remove(
        path
    )

    time.sleep(
        0.3
    )

    if not path.exists():
        return

    message = (
        "Ne mogu obrisati lokalni OTA direktorijum:\n"
        f"{path}\n\n"
        "Zatvori svaki stari HealthBand/Uvicorn proces. "
        "Ako nema Python procesa, OneDrive ili Windows "
        "trenutno drzi neki fajl zakljucanim."
    )

    if (
        last_error
        is not None
    ):

        message += (
            "\n\nOriginal error: "
            f"{last_error}"
        )

    raise DemoResetError(
        message
    )


def installed_release_directories() -> list[
    Path
]:
    """Return installed version directories except 1.0.0."""

    if not RELEASES_ROOT.is_dir():

        return (
            []
        )

    result: list[
        Path
    ] = []

    for path in (
        RELEASES_ROOT
        .iterdir()
    ):

        if not path.is_dir():
            continue

        if (
            path.name
            == BASELINE_VERSION
        ):
            continue

        if (
            SEMVER_DIRECTORY_PATTERN
            .fullmatch(
                path.name
            )
        ):

            result.append(
                path
            )

    return sorted(
        result,
        key=lambda item:
            item.name,
    )


def write_baseline_state() -> None:
    """Point the release manager back to HealthBand 1.0.0."""

    state = {

        "activeVersion":
            BASELINE_VERSION,

        "previousVersion":
            None,

        "activatedAt":
            None,

        "rollbackPerformed":
            False,

        "rollbackReason":
            None,
    }

    RELEASES_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    ACTIVE_RELEASE_FILE.write_text(
        json.dumps(
            state,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def verify_reset_result() -> None:
    """Verify the final local demo state."""

    try:

        state = json.loads(
            ACTIVE_RELEASE_FILE
            .read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:

        raise DemoResetError(
            "active_release.json could not "
            "be verified after the demo reset."
        ) from exc

    if (
        state.get(
            "activeVersion"
        )
        != BASELINE_VERSION
    ):

        raise DemoResetError(
            "Demo reset finished, but "
            "activeVersion is not 1.0.0."
        )

    remaining_versions = (
        installed_release_directories()
    )

    if remaining_versions:

        joined = "\n".join(
            str(
                path
            )
            for path
            in remaining_versions
        )

        raise DemoResetError(
            "Newer installed release directories "
            "still exist after reset:\n"
            f"{joined}"
        )

    for path in (
        TEMPORARY_OTA_PATHS
    ):

        if path.exists():

            raise DemoResetError(
                "Temporary OTA path still exists "
                "after reset:\n"
                f"{path}"
            )


def reset_demo_to_v1() -> None:
    """Perform a complete local HealthBand demo reset."""

    print()

    print(
        "========================================"
    )

    print(
        " HealthBand Demo Reset"
    )

    print(
        "========================================"
    )

    print()

    print(
        "Checking HealthBand 1.0.0..."
    )

    verify_baseline_release()

    print(
        "HealthBand 1.0.0 baseline: OK"
    )

    backup_current_state()

    for path in (
        installed_release_directories()
    ):

        print(
            "Removing installed release: "
            f"{path.name}"
        )

        remove_path(
            path
        )

    for path in (
        TEMPORARY_OTA_PATHS
    ):

        if path.exists():

            print(
                "Removing temporary OTA data: "
                f"{path.name}"
            )

            remove_path(
                path
            )

    print(
        "Writing active release state..."
    )

    write_baseline_state()

    verify_reset_result()

    print()

    print(
        "Demo reset completed."
    )

    print(
        "Active version: 1.0.0"
    )

    print(
        "Installed newer releases: removed"
    )

    print(
        "Temporary OTA data: removed"
    )

    print(
        "OTA artifacts: preserved"
    )

    print(
        "Release backups: preserved"
    )

    print(
        "AWS/S3 releases: unchanged"
    )

    print()


def main() -> None:
    """Command-line entry point."""

    try:

        reset_demo_to_v1()

    except DemoResetError as exc:

        print()

        print(
            "DEMO RESET ERROR"
        )

        print(
            "----------------"
        )

        print(
            str(
                exc
            )
        )

        print()

        raise SystemExit(
            1
        ) from exc


if __name__ == "__main__":

    main()