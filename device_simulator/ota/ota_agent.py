"""Local HealthBand OTA transaction orchestrator."""

from collections.abc import Callable
from dataclasses import dataclass
import logging
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

from device_simulator.ota.manifest import (
    ManifestValidationError,
)
from device_simulator.ota.ota_status import (
    OtaPhase,
    OtaProgress,
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


logger = logging.getLogger(
    __name__
)


ProgressCallback = Callable[
    [
        OtaProgress
    ],
    None,
]


@dataclass(
    frozen=True,
    slots=True,
)
class OtaInstallRequest:
    """One cloud-neutral OTA installation request."""

    source: str

    expected_sha256: str

    expected_size_bytes: int

    target_version: str


@dataclass(
    frozen=True,
    slots=True,
)
class OtaResult:
    """Final result of one OTA transaction."""

    success: bool

    phase: OtaPhase

    target_version: str

    active_version: str

    rollback_performed: bool

    restart_required: bool

    message: str


class OtaAgent:
    """
    Coordinate:

    download
    → archive verification
    → manifest/version validation
    → backup
    → extraction
    → pre-install check
    → installation
    → activation
    → self-test
    → success or rollback
    """

    def __init__(
        self,
        downloader: PackageDownloader,
        verifier: PackageVerifier,
        release_manager: ReleaseManager,
        rollback_manager: RollbackManager,
        staging_root: Path | str = ".ota_staging",
        progress_callback: ProgressCallback | None = None,
    ) -> None:

        self.downloader = (
            downloader
        )

        self.verifier = (
            verifier
        )

        self.release_manager = (
            release_manager
        )

        self.rollback_manager = (
            rollback_manager
        )

        self.staging_root = (
            Path(
                staging_root
            )
            .resolve()
        )

        self.staging_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.progress_callback = (
            progress_callback
        )

        self.phase = (
            OtaPhase.IDLE
        )


    def install(
        self,
        request: OtaInstallRequest,
    ) -> OtaResult:
        """Execute complete OTA transaction."""

        previous_version = (
            self.release_manager
            .get_active_version()
        )

        activated_new_release = (
            False
        )

        staging_directory: (
            Path
            | None
        ) = None

        target_version = (
            request.target_version
        )

        try:

            self._progress(
                OtaPhase.DOWNLOADING,
                10,
                "Obtaining OTA package.",
            )

            downloaded = (
                self.downloader
                .download(
                    request.source
                )
            )

            self._progress(
                OtaPhase.VERIFYING,
                25,
                "Verifying package size and SHA-256.",
            )

            verified = (
                self.verifier
                .verify_archive(
                    archive_path=(
                        downloaded
                    ),
                    expected_sha256=(
                        request
                        .expected_sha256
                    ),
                    expected_size_bytes=(
                        request
                        .expected_size_bytes
                    ),
                )
            )

            self._progress(
                OtaPhase.VALIDATING,
                35,
                "Validating manifest and version compatibility.",
            )

            manifest = (
                verified.manifest
            )

            if (
                manifest.version
                !=
                request.target_version
            ):
                raise ManifestValidationError(
                    "Requested target version "
                    "does not match package manifest."
                )

            manifest.validate_upgrade_from(
                previous_version
            )

            self._progress(
                OtaPhase.BACKING_UP,
                45,
                (
                    "Backing up active release "
                    f"{previous_version}."
                ),
            )

            self.rollback_manager.backup_active_release()

            self._progress(
                OtaPhase.EXTRACTING,
                55,
                "Safely extracting verified OTA package.",
            )

            staging_directory = (
                self.staging_root
                /
                (
                    f"{manifest.version}-"
                    f"{uuid4().hex}"
                )
            )

            self.verifier.extract_and_verify(
                verified,
                staging_directory,
            )

            self._progress(
                OtaPhase.PRE_INSTALL_CHECK,
                65,
                "Running pre-install checks.",
            )

            self._pre_install_check(
                staging_directory
            )

            self._progress(
                OtaPhase.INSTALLING,
                75,
                (
                    "Installing release "
                    f"{manifest.version}."
                ),
            )

            self.release_manager.install_from_staging(
                staging_root=(
                    staging_directory
                ),
                manifest=(
                    manifest
                ),
                replace_existing=True,
            )

            self._progress(
                OtaPhase.ACTIVATING,
                85,
                (
                    "Activating release "
                    f"{manifest.version}."
                ),
            )

            self.release_manager.activate(
                manifest.version
            )

            activated_new_release = (
                True
            )

            self._progress(
                OtaPhase.SELF_TEST,
                92,
                (
                    "Running release "
                    f"{manifest.version} "
                    "self-test."
                ),
            )

            self._run_release_self_test(
                manifest.version
            )

            self._progress(
                OtaPhase.COMPLETED,
                100,
                (
                    "OTA installation "
                    f"{manifest.version} "
                    "completed."
                ),
            )

            active_version = (
                self.release_manager
                .get_active_version()
            )

            return OtaResult(
                success=(
                    True
                ),
                phase=(
                    OtaPhase.COMPLETED
                ),
                target_version=(
                    manifest.version
                ),
                active_version=(
                    active_version
                ),
                rollback_performed=(
                    False
                ),
                restart_required=(
                    True
                ),
                message=(
                    "OTA installation completed. "
                    "Application restart is required "
                    "to boot the newly active release."
                ),
            )


        except Exception as exc:

            logger.exception(
                "OTA installation failed."
            )

            rollback_performed = (
                False
            )

            if (
                activated_new_release
            ):

                self._progress(
                    OtaPhase.ROLLING_BACK,
                    96,
                    (
                        "OTA failed after activation. "
                        "Rolling back to "
                        f"{previous_version}."
                    ),
                )

                try:

                    self.rollback_manager.rollback_to(
                        previous_version,
                        reason=(
                            str(
                                exc
                            )
                        ),
                    )

                    rollback_performed = (
                        True
                    )

                except Exception:

                    logger.exception(
                        "OTA rollback also failed."
                    )

            self._progress(
                OtaPhase.FAILED,
                100,
                f"OTA failed: {exc}",
            )

            try:

                active_version = (
                    self.release_manager
                    .get_active_version()
                )

            except Exception:

                active_version = (
                    previous_version
                )

            return OtaResult(
                success=(
                    False
                ),
                phase=(
                    OtaPhase.FAILED
                ),
                target_version=(
                    target_version
                ),
                active_version=(
                    active_version
                ),
                rollback_performed=(
                    rollback_performed
                ),
                restart_required=(
                    rollback_performed
                ),
                message=(
                    str(
                        exc
                    )
                ),
            )


        finally:

            if (
                staging_directory
                is not None
            ):

                shutil.rmtree(
                    staging_directory,
                    ignore_errors=True,
                )


    def _pre_install_check(
        self,
        staging_directory: Path,
    ) -> None:
        """Perform checks before activating new release."""

        payload = (
            staging_directory
            / "payload"
        )

        package_root = (
            payload
            / "device_simulator"
        )

        if (
            not package_root
            .is_dir()
        ):
            raise RuntimeError(
                "OTA payload does not contain "
                "device_simulator package."
            )

        main_file = (
            package_root
            / "main.py"
        )

        if (
            not main_file
            .is_file()
        ):
            raise RuntimeError(
                "OTA payload does not contain "
                "device_simulator/main.py."
            )

        result = (
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "compileall",
                    "-q",
                    str(
                        package_root
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        )

        if (
            result.returncode
            != 0
        ):
            raise RuntimeError(
                "Pre-install Python compilation "
                "failed: "
                + (
                    result.stderr.strip()
                    or
                    result.stdout.strip()
                )
            )


    def _run_release_self_test(
        self,
        version: str,
    ) -> None:
        """Execute bundled release self-test."""

        release_path = (
            self.release_manager
            .installed_release_path(
                version
            )
        )

        self_test = (
            release_path
            / "self_test.py"
        )

        if (
            not self_test
            .is_file()
        ):
            raise RuntimeError(
                "Installed release does not "
                "contain self_test.py."
            )

        result = (
            subprocess.run(
                [
                    sys.executable,
                    str(
                        self_test
                    ),
                ],
                cwd=(
                    release_path
                ),
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
        )

        if (
            result.returncode
            != 0
        ):
            raise RuntimeError(
                "Release self-test failed: "
                + (
                    result.stderr.strip()
                    or
                    result.stdout.strip()
                )
            )

        if (
            "SELF_TEST_OK"
            not in result.stdout
        ):
            raise RuntimeError(
                "Release self-test did not "
                "report SELF_TEST_OK."
            )


    def _progress(
        self,
        phase: OtaPhase,
        progress_percentage: int,
        message: str,
    ) -> None:
        """Store, log and optionally publish progress."""

        self.phase = (
            phase
        )

        progress = (
            OtaProgress(
                phase=(
                    phase
                ),
                progress_percentage=(
                    max(
                        0,
                        min(
                            100,
                            int(
                                progress_percentage
                            ),
                        ),
                    )
                ),
                message=(
                    message
                ),
            )
        )

        logger.info(
            "OTA | phase=%s | progress=%s | %s",
            progress.phase.value,
            progress.progress_percentage,
            progress.message,
        )

        if (
            self.progress_callback
            is not None
        ):

            self.progress_callback(
                progress
            )