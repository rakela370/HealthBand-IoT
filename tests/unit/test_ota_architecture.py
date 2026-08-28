"""Unit tests for HealthBand local OTA architecture."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from device_simulator.ota.job_handler import (
    JobDocumentValidationError,
    OtaJobDocument,
)
from device_simulator.ota.manifest import (
    ManifestValidationError,
    OtaManifest,
    is_newer_version,
)
from device_simulator.ota.ota_agent import (
    OtaAgent,
    OtaInstallRequest,
)
from device_simulator.ota.ota_status import (
    OtaPhase,
)
from device_simulator.ota.package_downloader import (
    PackageDownloader,
)
from device_simulator.ota.package_verifier import (
    PackageVerificationError,
    PackageVerifier,
)
from device_simulator.ota.release_manager import (
    ReleaseManager,
)
from device_simulator.ota.rollback_manager import (
    RollbackManager,
)
from scripts.run_active_release import (
    resolve_active_payload,
)


def sha256(
    path: Path,
) -> str:
    """Test helper."""

    digest = (
        hashlib.sha256()
    )

    digest.update(
        path.read_bytes()
    )

    return (
        digest.hexdigest()
    )


def make_archive(
    root: Path,
    version: str,
    minimum_current_version: str = "1.0.0",
    self_test_success: bool = True,
) -> tuple[
    Path,
    str,
    int,
]:
    """Create small valid OTA archive."""

    staging = (
        root
        / f"staging-{version}"
    )

    payload_package = (
        staging
        / "payload"
        / "device_simulator"
    )

    payload_package.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        payload_package
        / "__init__.py"
    ).write_text(
        "",
        encoding="utf-8",
    )

    (
        payload_package
        / "main.py"
    ).write_text(
        (
            'print("fake HealthBand")\n'
        ),
        encoding="utf-8",
    )

    self_test = (
        staging
        / "self_test.py"
    )

    if (
        self_test_success
    ):

        self_test.write_text(
            (
                'print("SELF_TEST_OK")\n'
            ),
            encoding="utf-8",
        )

    else:

        self_test.write_text(
            (
                'raise RuntimeError("broken release")\n'
            ),
            encoding="utf-8",
        )

    (
        staging
        / "release_info.json"
    ).write_text(
        json.dumps(
            {
                "product":
                    "HealthBand",

                "version":
                    version,
            }
        ),
        encoding="utf-8",
    )

    files: dict[
        str,
        str,
    ] = {}

    for path in (
        staging.rglob(
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
                staging
            )
            .as_posix()
        )

        files[
            relative
        ] = (
            sha256(
                path
            )
        )

    artifact_name = (
        f"healthband-{version}.zip"
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
            [
                "HEART_RATE_MONITORING"
            ],

        "files":
            files,

        "entryPoint":
            (
                "payload/"
                "device_simulator/"
                "main.py"
            ),

        "createdAt":
            "2026-08-27T10:00:00+00:00",
    }

    (
        staging
        / "manifest.json"
    ).write_text(
        json.dumps(
            manifest
        ),
        encoding="utf-8",
    )

    archive = (
        root
        / artifact_name
    )

    with zipfile.ZipFile(
        archive,
        "w",
        compression=(
            zipfile.ZIP_DEFLATED
        ),
    ) as output:

        for path in (
            staging.rglob(
                "*"
            )
        ):

            if (
                path.is_file()
            ):

                output.write(
                    path,
                    path.relative_to(
                        staging
                    ).as_posix(),
                )

    return (
        archive,
        sha256(
            archive
        ),
        archive.stat().st_size,
    )


def install_baseline(
    root: Path,
) -> ReleaseManager:
    """Create installed active version 1.0.0."""

    (
        archive,
        digest,
        size,
    ) = make_archive(
        root,
        "1.0.0",
    )

    verifier = (
        PackageVerifier()
    )

    verified = (
        verifier.verify_archive(
            archive,
            digest,
            size,
        )
    )

    extracted = (
        root
        / "extract-v1"
    )

    verifier.extract_and_verify(
        verified,
        extracted,
    )

    manager = (
        ReleaseManager(
            root
            / "releases"
        )
    )

    manager.install_from_staging(
        extracted,
        verified.manifest,
    )

    manager.initialize_active_release(
        "1.0.0"
    )

    return (
        manager
    )


def test_valid_manifest() -> None:

    digest = (
        "a"
        * 64
    )

    manifest = (
        OtaManifest.from_dict(
            {
                "product":
                    "HealthBand",

                "version":
                    "2.0.0",

                "minimumCurrentVersion":
                    "1.0.0",

                "artifact":
                    "healthband-2.0.0.zip",

                "capabilities":
                    [
                        "SPO2_MONITORING"
                    ],

                "files":
                    {
                        "payload/test.py":
                            digest
                    },

                "entryPoint":
                    "payload/test.py",

                "createdAt":
                    "2026-08-27T10:00:00Z",
            }
        )
    )

    assert (
        manifest.version
        == "2.0.0"
    )


def test_invalid_product_is_rejected() -> None:

    with pytest.raises(
        ManifestValidationError
    ):

        OtaManifest.from_dict(
            {
                "product":
                    "SomethingElse",

                "version":
                    "2.0.0",

                "minimumCurrentVersion":
                    "1.0.0",

                "artifact":
                    "healthband-2.0.0.zip",

                "capabilities":
                    [
                        "TEST"
                    ],

                "files":
                    {
                        "payload/test.py":
                            "a" * 64
                    },

                "entryPoint":
                    "payload/test.py",

                "createdAt":
                    "now",
            }
        )


def test_version_comparison() -> None:

    assert (
        is_newer_version(
            "2.0.0",
            "1.0.0",
        )
        is True
    )

    assert (
        is_newer_version(
            "1.0.0",
            "1.0.0",
        )
        is False
    )


def test_manifest_rejects_same_version() -> None:

    manifest = (
        OtaManifest.from_dict(
            {
                "product":
                    "HealthBand",

                "version":
                    "1.0.0",

                "minimumCurrentVersion":
                    "1.0.0",

                "artifact":
                    "healthband-1.0.0.zip",

                "capabilities":
                    [
                        "TEST"
                    ],

                "files":
                    {
                        "payload/test.py":
                            "a" * 64
                    },

                "entryPoint":
                    "payload/test.py",

                "createdAt":
                    "now",
            }
        )
    )

    with pytest.raises(
        ManifestValidationError
    ):

        manifest.validate_upgrade_from(
            "1.0.0"
        )


def test_local_downloader_copies_file(
    tmp_path: Path,
) -> None:

    source = (
        tmp_path
        / "source.zip"
    )

    source.write_bytes(
        b"test"
    )

    downloader = (
        PackageDownloader(
            tmp_path
            / "downloads"
        )
    )

    copied = (
        downloader.download(
            str(
                source
            )
        )
    )

    assert (
        copied.is_file()
    )

    assert (
        copied.read_bytes()
        == b"test"
    )


def test_archive_verification_passes(
    tmp_path: Path,
) -> None:

    (
        archive,
        digest,
        size,
    ) = make_archive(
        tmp_path,
        "1.0.0",
    )

    verified = (
        PackageVerifier().verify_archive(
            archive,
            digest,
            size,
        )
    )

    assert (
        verified.manifest.version
        == "1.0.0"
    )


def test_wrong_archive_hash_is_rejected(
    tmp_path: Path,
) -> None:

    (
        archive,
        _,
        size,
    ) = make_archive(
        tmp_path,
        "1.0.0",
    )

    with pytest.raises(
        PackageVerificationError
    ):

        PackageVerifier().verify_archive(
            archive,
            "0" * 64,
            size,
        )


def test_extract_verifies_payload(
    tmp_path: Path,
) -> None:

    (
        archive,
        digest,
        size,
    ) = make_archive(
        tmp_path,
        "1.0.0",
    )

    verifier = (
        PackageVerifier()
    )

    verified = (
        verifier.verify_archive(
            archive,
            digest,
            size,
        )
    )

    extracted = (
        verifier.extract_and_verify(
            verified,
            tmp_path
            / "extracted",
        )
    )

    assert (
        extracted
        .joinpath(
            "payload",
            "device_simulator",
            "main.py",
        )
        .is_file()
    )


def test_zip_slip_is_rejected(
    tmp_path: Path,
) -> None:

    (
        archive,
        _,
        _,
    ) = make_archive(
        tmp_path,
        "1.0.0",
    )

    with zipfile.ZipFile(
        archive,
        "a",
    ) as output:

        output.writestr(
            "../evil.txt",
            "bad",
        )

    digest = (
        sha256(
            archive
        )
    )

    with pytest.raises(
        PackageVerificationError
    ):

        PackageVerifier().verify_archive(
            archive,
            digest,
            archive.stat().st_size,
        )


def test_release_manager_active_version(
    tmp_path: Path,
) -> None:

    manager = (
        install_baseline(
            tmp_path
        )
    )

    assert (
        manager.get_active_version()
        == "1.0.0"
    )


def test_release_backup_is_created(
    tmp_path: Path,
) -> None:

    manager = (
        install_baseline(
            tmp_path
        )
    )

    backup = (
        manager.create_backup(
            "1.0.0"
        )
    )

    assert (
        backup.is_dir()
    )

    assert (
        backup
        .joinpath(
            "payload",
            "device_simulator",
            "main.py",
        )
        .is_file()
    )


def test_valid_job_document() -> None:

    document = (
        OtaJobDocument.from_dict(
            {
                "targetVersion":
                    "2.0.0",

                "artifactUrl":
                    "https://example.test/update.zip",

                "sha256":
                    "a" * 64,

                "sizeBytes":
                    1000,

                "instruction":
                    "INSTALL_UPDATE",

                "timeoutSec":
                    300,

                "restart":
                    True,
            }
        )
    )

    assert (
        document.target_version
        == "2.0.0"
    )


def test_unknown_job_instruction_is_rejected() -> None:

    with pytest.raises(
        JobDocumentValidationError
    ):

        OtaJobDocument.from_dict(
            {
                "targetVersion":
                    "2.0.0",

                "artifactUrl":
                    "test",

                "sha256":
                    "a" * 64,

                "sizeBytes":
                    100,

                "instruction":
                    "DELETE_DEVICE",

                "timeoutSec":
                    100,

                "restart":
                    True,
            }
        )


def test_ota_agent_installs_new_release(
    tmp_path: Path,
) -> None:

    manager = (
        install_baseline(
            tmp_path
        )
    )

    (
        archive,
        digest,
        size,
    ) = make_archive(
        tmp_path,
        "2.0.0",
    )

    agent = (
        OtaAgent(
            downloader=(
                PackageDownloader(
                    tmp_path
                    / "downloads"
                )
            ),
            verifier=(
                PackageVerifier()
            ),
            release_manager=(
                manager
            ),
            rollback_manager=(
                RollbackManager(
                    manager
                )
            ),
            staging_root=(
                tmp_path
                / "staging"
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
                    digest
                ),
                expected_size_bytes=(
                    size
                ),
                target_version=(
                    "2.0.0"
                ),
            )
        )
    )

    assert (
        result.success
        is True
    )

    assert (
        result.phase
        == OtaPhase.COMPLETED
    )

    assert (
        manager.get_active_version()
        == "2.0.0"
    )


def test_failed_self_test_rolls_back(
    tmp_path: Path,
) -> None:

    manager = (
        install_baseline(
            tmp_path
        )
    )

    (
        archive,
        digest,
        size,
    ) = make_archive(
        tmp_path,
        "2.0.0",
        self_test_success=False,
    )

    agent = (
        OtaAgent(
            downloader=(
                PackageDownloader(
                    tmp_path
                    / "downloads"
                )
            ),
            verifier=(
                PackageVerifier()
            ),
            release_manager=(
                manager
            ),
            rollback_manager=(
                RollbackManager(
                    manager
                )
            ),
            staging_root=(
                tmp_path
                / "staging"
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
                    digest
                ),
                expected_size_bytes=(
                    size
                ),
                target_version=(
                    "2.0.0"
                ),
            )
        )
    )

    assert (
        result.success
        is False
    )

    assert (
        result.rollback_performed
        is True
    )

    assert (
        manager.get_active_version()
        == "1.0.0"
    )


def test_active_release_launcher_resolution(
    tmp_path: Path,
) -> None:

    manager = (
        install_baseline(
            tmp_path
        )
    )

    (
        version,
        payload,
    ) = (
        resolve_active_payload(
            manager.releases_root
        )
    )

    assert (
        version
        == "1.0.0"
    )

    assert (
        payload
        .joinpath(
            "device_simulator",
            "main.py",
        )
        .is_file()
    )