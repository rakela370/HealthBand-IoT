"""Rollback orchestration for failed HealthBand OTA updates."""

from pathlib import Path

from device_simulator.ota.release_manager import (
    ReleaseManager,
)


class RollbackManager:
    """Create backup and restore a previously installed release."""

    def __init__(
        self,
        release_manager: ReleaseManager,
    ) -> None:

        self.release_manager = (
            release_manager
        )


    def backup_active_release(
        self,
    ) -> tuple[
        str,
        Path,
    ]:
        """Back up currently active release."""

        version = (
            self.release_manager
            .get_active_version()
        )


        backup = (
            self.release_manager
            .create_backup(
                version
            )
        )


        return (
            version,
            backup,
        )


    def rollback_to(
        self,
        version: str,
        reason: str,
    ) -> dict:
        """Switch active release back to previous version."""

        return (
            self.release_manager
            .activate(
                version,
                rollback_performed=True,
                rollback_reason=(
                    reason
                ),
            )
        )