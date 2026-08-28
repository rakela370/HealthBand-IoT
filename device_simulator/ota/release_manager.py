"""Installed HealthBand release management."""

from datetime import (
    datetime,
    timezone,
)
import json
from pathlib import Path
import shutil
from typing import Any
from uuid import uuid4

from device_simulator.ota.manifest import (
    OtaManifest,
)


class ReleaseManagerError(
    RuntimeError
):
    """Raised when release storage cannot be managed."""


class ReleaseManager:
    """
    Manage immutable installed release directories.

    Runtime release selection is controlled by:

        releases/active_release.json
    """

    def __init__(
        self,
        releases_root: Path | str = "releases",
    ) -> None:

        self.releases_root = (
            Path(
                releases_root
            )
            .resolve()
        )


        self.backups_root = (
            self.releases_root
            / "backups"
        )


        self.active_release_file = (
            self.releases_root
            / "active_release.json"
        )


        self.releases_root.mkdir(
            parents=True,
            exist_ok=True,
        )


        self.backups_root.mkdir(
            parents=True,
            exist_ok=True,
        )


    def installed_release_path(
        self,
        version: str,
    ) -> Path:
        """Return directory of installed release."""

        return (
            self.releases_root
            / version
        )


    def install_from_staging(
        self,
        staging_root: Path | str,
        manifest: OtaManifest,
        replace_existing: bool = False,
    ) -> Path:
        """Install a previously verified staged release."""

        source = (
            Path(
                staging_root
            )
            .resolve()
        )


        payload = (
            source
            / "payload"
        )


        if (
            not payload
            .is_dir()
        ):
            raise ReleaseManagerError(
                "Staged package does not contain "
                "payload directory."
            )


        target = (
            self.installed_release_path(
                manifest.version
            )
        )


        if (
            target.exists()
        ):

            if (
                not replace_existing
            ):
                raise ReleaseManagerError(
                    f"Release {manifest.version} "
                    "is already installed."
                )


            shutil.rmtree(
                target
            )


        temporary = (
            self.releases_root
            /
            (
                f".install-"
                f"{manifest.version}-"
                f"{uuid4().hex}"
            )
        )


        try:

            temporary.mkdir(
                parents=True,
                exist_ok=False,
            )


            shutil.copytree(
                payload,
                temporary
                / "payload",
            )


            for name in (
                "manifest.json",
                "release_info.json",
                "self_test.py",
            ):

                source_file = (
                    source
                    / name
                )


                if (
                    source_file
                    .is_file()
                ):
                    shutil.copy2(
                        source_file,
                        temporary
                        / name,
                    )


            temporary.replace(
                target
            )


        except Exception:

            shutil.rmtree(
                temporary,
                ignore_errors=True,
            )

            raise


        return (
            target
        )


    def initialize_active_release(
        self,
        version: str,
    ) -> dict[
        str,
        Any,
    ]:
        """Create initial active_release.json."""

        if (
            self.active_release_file
            .exists()
        ):
            raise ReleaseManagerError(
                "active_release.json already exists."
            )


        self._require_installed(
            version
        )


        state = {

            "activeVersion":
                version,

            "previousVersion":
                None,

            "activatedAt":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "rollbackPerformed":
                False,

            "rollbackReason":
                None,
        }


        self._write_state(
            state
        )


        return (
            state
        )


    def activate(
        self,
        version: str,
        *,
        rollback_performed: bool = False,
        rollback_reason: str | None = None,
    ) -> dict[
        str,
        Any,
    ]:
        """Atomically switch active HealthBand release."""

        self._require_installed(
            version
        )


        current = (
            self.read_active_state()
        )


        previous_version = (

            current.get(
                "activeVersion"
            )

            if current
            else None
        )


        state = {

            "activeVersion":
                version,

            "previousVersion":
                previous_version,

            "activatedAt":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "rollbackPerformed":
                rollback_performed,

            "rollbackReason":
                rollback_reason,
        }


        self._write_state(
            state
        )


        return (
            state
        )


    def read_active_state(
        self,
    ) -> dict[
        str,
        Any,
    ] | None:
        """Read active release state."""

        if (
            not self.active_release_file
            .is_file()
        ):
            return (
                None
            )


        try:

            data = (
                json.loads(
                    self.active_release_file
                    .read_text(
                        encoding="utf-8"
                    )
                )
            )


        except Exception as exc:

            raise ReleaseManagerError(
                f"Unable to read active "
                f"release state: {exc}"
            ) from exc


        if (
            not isinstance(
                data,
                dict,
            )
            or not data.get(
                "activeVersion"
            )
        ):
            raise ReleaseManagerError(
                "active_release.json is invalid."
            )


        return (
            data
        )


    def get_active_version(
        self,
    ) -> str:
        """Return active version."""

        state = (
            self.read_active_state()
        )


        if (
            state is None
        ):
            raise ReleaseManagerError(
                "No active HealthBand release "
                "is configured."
            )


        return str(
            state[
                "activeVersion"
            ]
        )


    def create_backup(
        self,
        version: str,
    ) -> Path:
        """Create explicit backup of an installed release."""

        source = (
            self.installed_release_path(
                version
            )
        )


        if (
            not source
            .is_dir()
        ):
            raise ReleaseManagerError(
                f"Cannot back up missing "
                f"release {version}."
            )


        stamp = (
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y%m%dT%H%M%SZ"
            )
        )


        destination = (
            self.backups_root
            /
            (
                f"{version}-"
                f"{stamp}-"
                f"{uuid4().hex[:8]}"
            )
        )


        shutil.copytree(
            source,
            destination,
        )


        return (
            destination
        )


    def release_payload_root(
        self,
        version: str,
    ) -> Path:
        """Return Python import root for installed release."""

        payload = (
            self.installed_release_path(
                version
            )
            / "payload"
        )


        if (
            not payload
            .is_dir()
        ):
            raise ReleaseManagerError(
                f"Installed release {version} "
                "has no payload directory."
            )


        return (
            payload
        )


    def _require_installed(
        self,
        version: str,
    ) -> None:

        if (
            not self
            .installed_release_path(
                version
            )
            .is_dir()
        ):
            raise ReleaseManagerError(
                f"Release {version} "
                "is not installed."
            )


    def _write_state(
        self,
        state: dict[
            str,
            Any,
        ],
    ) -> None:
        """Atomically write active_release.json."""

        temporary = (
            self.active_release_file
            .with_suffix(
                ".json.tmp"
            )
        )


        temporary.write_text(
            json.dumps(
                state,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )


        temporary.replace(
            self.active_release_file
        )