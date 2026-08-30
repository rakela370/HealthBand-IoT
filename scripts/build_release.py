"""Build a versioned HealthBand OTA ZIP artifact."""

import argparse
from datetime import (
    datetime,
    timezone,
)
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import zipfile


DEFAULT_CAPABILITIES = [
    "HEART_RATE_MONITORING",
    "SKIN_TEMPERATURE_MONITORING",
    "STEP_COUNTING",
    "LOCAL_ANALYTICS",
]


def sha256_file(
    path: Path,
) -> str:
    """Calculate SHA-256 of a file."""

    digest = (
        hashlib.sha256()
    )

    with path.open(
        "rb"
    ) as source:

        for chunk in iter(
            lambda:
                source.read(
                    1024
                    * 1024
                ),
            b"",
        ):

            digest.update(
                chunk
            )

    return (
        digest.hexdigest()
    )


def should_include(
    path: Path,
) -> bool:
    """Allow only source/config files in OTA payload."""

    if (
        "__pycache__"
        in path.parts
    ):
        return (
            False
        )

    if (
        path.suffix
        in {
            ".pyc",
            ".pyo",
            ".log",
            ".db",
            ".sqlite",
            ".sqlite3",
        }
    ):
        return (
            False
        )

    return (
        path.is_file()
        and path.suffix
        in {
            ".py",
            ".json",
        }
    )


def copy_device_source(
    source_root: Path,
    payload_root: Path,
) -> None:
    """Copy safe device source into release payload."""

    device_source = (
        source_root
        / "device_simulator"
    )

    if (
        not device_source
        .is_dir()
    ):
        raise RuntimeError(
            "device_simulator directory "
            "was not found."
        )

    destination = (
        payload_root
        / "device_simulator"
    )

    for path in (
        device_source.rglob(
            "*"
        )
    ):

        if (
            not should_include(
                path
            )
        ):
            continue

        relative = (
            path.relative_to(
                device_source
            )
        )

        target = (
            destination
            / relative
        )

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            path,
            target,
        )


def build_file_hashes(
    staging_root: Path,
) -> dict[
    str,
    str,
]:
    """Hash all package files except manifest itself."""

    result: dict[
        str,
        str,
    ] = {}

    for path in sorted(
        staging_root.rglob(
            "*"
        )
    ):

        if (
            not path
            .is_file()
        ):
            continue

        if (
            path.name
            == "manifest.json"
        ):
            continue

        relative = (
            path.relative_to(
                staging_root
            )
            .as_posix()
        )

        result[
            relative
        ] = (
            sha256_file(
                path
            )
        )

    return (
        result
    )


def create_self_test(
    staging_root: Path,
    version: str,
    capabilities: list[
        str
    ],
) -> None:
    """Generate a release-bundled self-test."""

    capabilities_literal = (
        repr(
            sorted(
                set(
                    capabilities
                )
            )
        )
    )

    source = f'''"""HealthBand release self-test."""

from pathlib import Path
import sys


RELEASE_ROOT = Path(__file__).resolve().parent
PAYLOAD_ROOT = RELEASE_ROOT / "payload"

sys.path.insert(
    0,
    str(PAYLOAD_ROOT),
)


def main() -> None:
    """Verify release imports and basic simulated sensing."""

    from device_simulator.core.device_state import DeviceState
    from device_simulator.sensors.sensor_manager import SensorManager
    from device_simulator.simulation.scenario_engine import ScenarioEngine

    assert DeviceState.MONITORING.value == "MONITORING"

    engine = ScenarioEngine()

    manager = SensorManager(
        random_seed=123,
        software_version={version!r},
    )

    snapshot = manager.read_all(
        engine.get_context(),
        2.0,
    )

    assert "heartRateBpm" in snapshot.measurements
    assert "totalDailySteps" in snapshot.measurements
    assert "batteryPercentage" in snapshot.measurements

    capabilities = {capabilities_literal}

    if "SPO2_MONITORING" in capabilities:
        from device_simulator.sensors.spo2_sensor import SpO2Sensor

        assert SpO2Sensor is not None
        assert "oxygenSaturationPercentage" in snapshot.measurements
        assert snapshot.sensor_status.get("spo2") == "OK"

    if "CALORIE_ESTIMATION" in capabilities:
        from device_simulator.analytics.calorie_estimator import CalorieEstimator

        assert CalorieEstimator is not None

    print("SELF_TEST_OK")


if __name__ == "__main__":
    main()
'''

    (
        staging_root
        / "self_test.py"
    ).write_text(
        source,
        encoding="utf-8",
    )


def write_zip(
    staging_root: Path,
    output_path: Path,
) -> None:
    """Create deterministic ZIP package."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with zipfile.ZipFile(
        output_path,
        "w",
        compression=(
            zipfile.ZIP_DEFLATED
        ),
        compresslevel=9,
    ) as archive:

        for path in sorted(
            staging_root.rglob(
                "*"
            )
        ):

            if (
                not path
                .is_file()
            ):
                continue

            relative = (
                path.relative_to(
                    staging_root
                )
                .as_posix()
            )

            info = (
                zipfile.ZipInfo(
                    relative
                )
            )

            info.date_time = (
                2026,
                1,
                1,
                0,
                0,
                0,
            )

            info.compress_type = (
                zipfile.ZIP_DEFLATED
            )

            archive.writestr(
                info,
                path.read_bytes(),
            )


def build_release(
    source_root: Path,
    version: str,
    minimum_current_version: str,
    capabilities: list[
        str
    ],
    output_root: Path,
) -> tuple[
    Path,
    Path,
    Path,
]:
    """Build archive, manifest copy and SHA-256 file."""

    artifact_name = (
        f"healthband-{version}.zip"
    )

    version_directory = (
        output_root
        / f"version_{version}"
    )

    version_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    archive_path = (
        version_directory
        / artifact_name
    )

    manifest_copy_path = (
        version_directory
        / "manifest.json"
    )

    sha_path = (
        version_directory
        / (
            f"{artifact_name}"
            ".sha256"
        )
    )

    with tempfile.TemporaryDirectory(
        prefix=(
            "healthband-release-"
        )
    ) as temporary:

        staging_root = (
            Path(
                temporary
            )
        )

        payload_root = (
            staging_root
            / "payload"
        )

        payload_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        copy_device_source(
            source_root,
            payload_root,
        )

        create_self_test(
            staging_root,
            version,
            capabilities,
        )

        created_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        release_info = {

            "product":
                "HealthBand",

            "version":
                version,

            "entryPoint":
                "device_simulator.main",

            "capabilities":
                sorted(
                    set(
                        capabilities
                    )
                ),

            "createdAt":
                created_at,
        }

        (
            staging_root
            / "release_info.json"
        ).write_text(
            json.dumps(
                release_info,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        file_hashes = (
            build_file_hashes(
                staging_root
            )
        )

        manifest = {

            "product":
                "HealthBand",

            "version":
                version,

            "minimumCurrentVersion":
                minimum_current_version,

            "artifact":
                artifact_name,

            "capabilities":
                sorted(
                    set(
                        capabilities
                    )
                ),

            "files":
                file_hashes,

            "entryPoint":
                (
                    "payload/"
                    "device_simulator/"
                    "main.py"
                ),

            "createdAt":
                created_at,
        }

        (
            staging_root
            / "manifest.json"
        ).write_text(
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
            f"{artifact_name}\n"
        ),
        encoding="utf-8",
    )

    return (
        archive_path,
        manifest_copy_path,
        sha_path,
    )


def main() -> None:
    """CLI entry point."""

    parser = (
        argparse.ArgumentParser(
            description=(
                "Build HealthBand OTA release."
            )
        )
    )

    parser.add_argument(
        "--version",
        required=True,
    )

    parser.add_argument(
        "--minimum-current-version",
        required=True,
    )

    parser.add_argument(
        "--capability",
        action="append",
        default=[],
        help=(
            "Additional capability. "
            "Can be supplied multiple times."
        ),
    )

    parser.add_argument(
        "--output-root",
        default="ota_artifacts",
    )

    args = (
        parser.parse_args()
    )

    capabilities = sorted(
        set(
            DEFAULT_CAPABILITIES
            + args.capability
        )
    )

    (
        archive,
        manifest,
        sha_file,
    ) = build_release(
        source_root=(
            Path.cwd()
            .resolve()
        ),
        version=(
            args.version
        ),
        minimum_current_version=(
            args.minimum_current_version
        ),
        capabilities=(
            capabilities
        ),
        output_root=(
            Path(
                args.output_root
            )
            .resolve()
        ),
    )

    print(
        f"Release built: {archive}"
    )

    print(
        f"Manifest: {manifest}"
    )

    print(
        f"SHA file: {sha_file}"
    )

    print(
        (
            "Archive size: "
            f"{archive.stat().st_size} bytes"
        )
    )

    print(
        (
            "Archive SHA-256: "
            f"{sha256_file(archive)}"
        )
    )


if __name__ == "__main__":
    main()