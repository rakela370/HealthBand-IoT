"""Run the active HealthBand release under a stable AWS IoT Jobs OTA supervisor."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
from time import (
    monotonic,
    sleep,
)

from device_simulator.communication.connection_manager import (
    AwsIotConnectionSettings,
    ConnectionManager,
)
from device_simulator.ota.aws_jobs_client import (
    AwsIotJobsClient,
    AwsJobExecution,
)
from device_simulator.ota.job_handler import (
    JobDocumentValidationError,
    OtaJobDocument,
)
from device_simulator.ota.ota_agent import (
    OtaAgent,
    OtaInstallRequest,
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


class ActiveReleaseProcess:
    """Own the child process that runs the active HealthBand release."""

    def __init__(
        self,
        project_root: Path,
    ) -> None:
        self.project_root = (
            project_root
        )

        self.process: (
            subprocess.Popen[bytes]
            | None
        ) = None

    @property
    def is_running(
        self,
    ) -> bool:
        return (
            self.process
            is not None
            and self.process.poll()
            is None
        )

    def start(
        self,
    ) -> None:
        if self.is_running:
            return

        logger.info(
            "Starting active "
            "HealthBand release process."
        )

        self.process = (
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "scripts.run_active_release",
                ],
                cwd=(
                    self.project_root
                ),
            )
        )

    def stop(
        self,
    ) -> None:
        if not self.is_running:
            self.process = None
            return

        assert (
            self.process
            is not None
        )

        logger.info(
            "Stopping active "
            "HealthBand release process."
        )

        self.process.terminate()

        try:
            self.process.wait(
                timeout=12
            )

        except subprocess.TimeoutExpired:
            logger.warning(
                "Release process did not "
                "stop in time; killing it."
            )

            self.process.kill()

            self.process.wait(
                timeout=5
            )

        self.process = None


class ManagedDeviceSupervisor:
    """Supervise immutable releases and process AWS IoT Jobs."""

    JOB_POLL_INTERVAL_SEC = 5.0
    RELEASE_BOOT_TIMEOUT_SEC = 35.0

    def __init__(
        self,
        project_root: Path,
    ) -> None:
        self.project_root = (
            project_root
        )

        base_settings = (
            AwsIotConnectionSettings
            .from_environment()
        )

        self.thing_name = (
            base_settings.client_id
        )

        supervisor_settings = replace(
            base_settings,
            client_id=(
                f"{self.thing_name}-ota"
            ),
        )

        self.jobs = (
            AwsIotJobsClient(
                connection_manager=(
                    ConnectionManager(
                        supervisor_settings
                    )
                ),
                thing_name=(
                    self.thing_name
                ),
            )
        )

        self.release_manager = (
            ReleaseManager(
                project_root
                / "releases"
            )
        )

        self.rollback_manager = (
            RollbackManager(
                self.release_manager
            )
        )

        self.release_process = (
            ActiveReleaseProcess(
                project_root
            )
        )

        self._last_job_id: (
            str | None
        ) = None

    def run(
        self,
    ) -> None:
        """Start supervisor and process AWS Jobs until Ctrl+C."""

        self.jobs.start()

        self.release_process.start()

        active = (
            self.release_manager
            .get_active_version()
        )

        self.jobs.publish_ota_status(
            job_id=None,
            phase="IDLE",
            progress_percentage=0,
            message=(
                "OTA supervisor ready."
            ),
            target_version=None,
            active_version=active,
            job_status="IDLE",
        )

        self.jobs.request_next()

        next_poll = (
            monotonic()
            + self.JOB_POLL_INTERVAL_SEC
        )

        print(
            "HealthBand managed device "
            "is running. "
            f"Active release: {active}. "
            "Press Ctrl+C to stop."
        )

        try:
            while True:
                now = monotonic()

                if (
                    self.jobs
                    .consume_notification()
                    or now >= next_poll
                ):
                    self.jobs.request_next()

                    next_poll = (
                        now
                        + self
                        .JOB_POLL_INTERVAL_SEC
                    )

                for execution in (
                    self.jobs
                    .drain_executions()
                ):
                    if (
                        execution.job_id
                        == self._last_job_id
                    ):
                        continue

                    self._last_job_id = (
                        execution.job_id
                    )

                    self._handle_execution(
                        execution
                    )

                    self.jobs.request_next()

                sleep(
                    0.2
                )

        except KeyboardInterrupt:
            print(
                "\nStopping HealthBand "
                "managed device..."
            )

        finally:
            self.release_process.stop()

            self.jobs.stop()

    def _handle_execution(
        self,
        execution: AwsJobExecution,
    ) -> None:
        previous_version = (
            self.release_manager
            .get_active_version()
        )

        job_id = (
            execution.job_id
        )

        try:
            document = (
                OtaJobDocument
                .from_dict(
                    execution
                    .job_document
                )
            )

        except (
            JobDocumentValidationError,
            ValueError,
        ) as exc:
            self._fail_job(
                job_id=job_id,
                target_version=None,
                active_version=(
                    previous_version
                ),
                message=(
                    "Invalid OTA job "
                    f"document: {exc}"
                ),
                rollback_performed=False,
            )

            return

        self.jobs.publish_ota_status(
            job_id=job_id,
            phase="QUEUED",
            progress_percentage=1,
            message=(
                "AWS IoT Job accepted for "
                f"HealthBand "
                f"{document.target_version}."
            ),
            target_version=(
                document.target_version
            ),
            active_version=(
                previous_version
            ),
            job_status="IN_PROGRESS",
        )

        self.jobs.update_execution(
            job_id,
            "IN_PROGRESS",
            {
                "phase": "QUEUED",
                "progress": "1",
                "targetVersion": (
                    document
                    .target_version
                ),
            },
        )

        self.jobs.publish_device_state_event(
            previous_state="MONITORING",
            current_state="UPDATING",
            reason=(
                f"AWS IoT Job "
                f"{job_id} started."
            ),
        )

        self.release_process.stop()

        def progress_callback(
            progress: OtaProgress,
        ) -> None:
            phase = (
                progress.phase.value
            )

            percentage = (
                progress
                .progress_percentage
            )

            message = (
                progress.message
            )

            if (
                progress.phase
                == OtaPhase.COMPLETED
            ):
                phase = "RESTARTING"

                percentage = 96

                message = (
                    "Release installed and "
                    "self-test passed. "
                    "Restarting active "
                    "HealthBand release."
                )

            self.jobs.publish_ota_status(
                job_id=job_id,
                phase=phase,
                progress_percentage=(
                    percentage
                ),
                message=message,
                target_version=(
                    document
                    .target_version
                ),
                active_version=(
                    self.release_manager
                    .get_active_version()
                ),
                job_status=(
                    "IN_PROGRESS"
                ),
                self_test=(
                    "PASSED"
                    if (
                        progress.phase
                        == OtaPhase.COMPLETED
                    )
                    else (
                        "RUNNING"
                        if (
                            progress.phase
                            == OtaPhase.SELF_TEST
                        )
                        else "NOT_RUN"
                    )
                ),
            )

            self.jobs.update_execution(
                job_id,
                "IN_PROGRESS",
                {
                    "phase": phase,
                    "progress": str(
                        percentage
                    ),
                    "targetVersion": (
                        document
                        .target_version
                    ),
                },
            )

        agent = OtaAgent(
            downloader=(
                PackageDownloader(
                    self.project_root
                    / "ota_downloads"
                )
            ),
            verifier=(
                PackageVerifier()
            ),
            release_manager=(
                self.release_manager
            ),
            rollback_manager=(
                self.rollback_manager
            ),
            staging_root=(
                self.project_root
                / ".ota_staging"
            ),
            progress_callback=(
                progress_callback
            ),
        )

        result = agent.install(
            OtaInstallRequest(
                source=(
                    document.artifact_url
                ),
                expected_sha256=(
                    document.sha256
                ),
                expected_size_bytes=(
                    document.size_bytes
                ),
                target_version=(
                    document.target_version
                ),
            )
        )

        if not result.success:
            self.release_process.start()

            self._fail_job(
                job_id=job_id,
                target_version=(
                    document.target_version
                ),
                active_version=(
                    result.active_version
                ),
                message=(
                    result.message
                ),
                rollback_performed=(
                    result
                    .rollback_performed
                ),
            )

            return

        self.jobs.clear_presence()

        self.release_process.start()

        if self._wait_for_release_presence(
            document.target_version,
            timeout_sec=min(
                self.RELEASE_BOOT_TIMEOUT_SEC,
                max(
                    10.0,
                    float(
                        document.timeout_sec
                    ),
                ),
            ),
        ):
            self.jobs.update_execution(
                job_id,
                "SUCCEEDED",
                {
                    "phase": "COMPLETED",
                    "progress": "100",
                    "activeVersion": (
                        document
                        .target_version
                    ),
                    "selfTest": "PASSED",
                },
            )

            self.jobs.publish_ota_status(
                job_id=job_id,
                phase="COMPLETED",
                progress_percentage=100,
                message=(
                    "HealthBand "
                    f"{document.target_version} "
                    "is online after OTA."
                ),
                target_version=(
                    document.target_version
                ),
                active_version=(
                    document.target_version
                ),
                job_status="SUCCEEDED",
                self_test="PASSED",
                rollback_performed=False,
            )

            logger.info(
                "AWS IoT Job %s "
                "succeeded; active version=%s",
                job_id,
                document.target_version,
            )

            return

        logger.error(
            "New release did not report "
            "ONLINE presence with target version."
        )

        self.release_process.stop()

        rollback_performed = False

        rollback_error: (
            Exception | None
        ) = None

        try:
            self.jobs.publish_ota_status(
                job_id=job_id,
                phase="ROLLING_BACK",
                progress_percentage=98,
                message=(
                    "Version "
                    f"{document.target_version} "
                    "failed post-restart "
                    "validation. Rolling back "
                    f"to {previous_version}."
                ),
                target_version=(
                    document.target_version
                ),
                active_version=(
                    self.release_manager
                    .get_active_version()
                ),
                job_status="IN_PROGRESS",
                self_test="PASSED",
                rollback_performed=False,
            )

            self.rollback_manager.rollback_to(
                previous_version,
                reason=(
                    "Target release did not "
                    "report expected ONLINE "
                    "presence."
                ),
            )

            rollback_performed = True

        except Exception as exc:
            rollback_error = exc

            logger.exception(
                "Post-restart rollback failed."
            )

        self.jobs.clear_presence()

        self.release_process.start()

        message = (
            "Post-restart validation failed; "
            "previous release restored."
            if rollback_performed
            else (
                "Post-restart validation "
                "and rollback failed: "
                f"{rollback_error}"
            )
        )

        self._fail_job(
            job_id=job_id,
            target_version=(
                document.target_version
            ),
            active_version=(
                self.release_manager
                .get_active_version()
            ),
            message=message,
            rollback_performed=(
                rollback_performed
            ),
        )

    def _wait_for_release_presence(
        self,
        target_version: str,
        timeout_sec: float,
    ) -> bool:
        deadline = (
            monotonic()
            + timeout_sec
        )

        while (
            monotonic()
            < deadline
        ):
            presence = (
                self.jobs
                .latest_presence()
            )

            if presence is not None:
                if (
                    presence.get(
                        "status"
                    )
                    == "ONLINE"
                    and str(
                        presence.get(
                            "softwareVersion",
                            "",
                        )
                    ).strip()
                    == target_version
                ):
                    return True

            sleep(
                0.25
            )

        return False

    def _fail_job(
        self,
        *,
        job_id: str,
        target_version: str | None,
        active_version: str,
        message: str,
        rollback_performed: bool,
    ) -> None:
        try:
            self.jobs.update_execution(
                job_id,
                "FAILED",
                {
                    "phase": "FAILED",
                    "progress": "100",
                    "activeVersion": (
                        active_version
                    ),
                    "rollbackPerformed": (
                        str(
                            rollback_performed
                        ).lower()
                    ),
                    "reason": (
                        message[
                            :250
                        ]
                    ),
                },
            )

        finally:
            self.jobs.publish_ota_status(
                job_id=job_id,
                phase="FAILED",
                progress_percentage=100,
                message=message,
                target_version=(
                    target_version
                ),
                active_version=(
                    active_version
                ),
                job_status="FAILED",
                self_test="FAILED",
                rollback_performed=(
                    rollback_performed
                ),
            )

            self.jobs.publish_device_state_event(
                previous_state="UPDATING",
                current_state="MONITORING",
                reason=(
                    "OTA_UPDATE_FAILED; "
                    "rollbackPerformed="
                    f"{rollback_performed}; "
                    f"{message}"
                ),
            )


def main() -> None:
    """CLI entry point."""

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )

    project_root = (
        Path.cwd()
        .resolve()
    )

    supervisor = (
        ManagedDeviceSupervisor(
            project_root
        )
    )

    supervisor.run()


if __name__ == "__main__":
    main()