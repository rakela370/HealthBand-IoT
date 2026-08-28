"""Integrity and archive verification for HealthBand OTA packages."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import zipfile

from device_simulator.ota.manifest import (
    OtaManifest,
)


class PackageVerificationError(
    RuntimeError
):
    """Raised when an OTA package fails validation."""


@dataclass(
    frozen=True,
    slots=True,
)
class VerifiedPackage:
    """Metadata returned after successful archive verification."""

    archive_path: Path

    archive_sha256: str

    archive_size_bytes: int

    manifest: OtaManifest


class PackageVerifier:
    """
    Verify:

    * complete archive SHA-256;
    * archive size;
    * ZIP safety;
    * manifest;
    * hashes of files inside package.
    """

    MANIFEST_NAME = (
        "manifest.json"
    )


    @staticmethod
    def calculate_sha256(
        path: Path | str,
    ) -> str:
        """Calculate SHA-256 of a file."""

        file_path = (
            Path(
                path
            )
        )


        digest = (
            hashlib.sha256()
        )


        with file_path.open(
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


    def verify_archive(
        self,
        archive_path: Path | str,
        expected_sha256: str,
        expected_size_bytes: int | None = None,
    ) -> VerifiedPackage:
        """Verify archive before extraction."""

        archive = (
            Path(
                archive_path
            )
            .resolve()
        )


        if (
            not archive
            .is_file()
        ):
            raise PackageVerificationError(
                f"OTA archive does not exist: "
                f"{archive}"
            )


        actual_size = (
            archive.stat().st_size
        )


        if (
            expected_size_bytes
            is not None
            and actual_size
            != int(
                expected_size_bytes
            )
        ):
            raise PackageVerificationError(
                "OTA package size verification failed."
            )


        actual_sha256 = (
            self.calculate_sha256(
                archive
            )
        )


        if (
            actual_sha256.lower()
            !=
            expected_sha256
            .strip()
            .lower()
        ):
            raise PackageVerificationError(
                "OTA package SHA-256 "
                "verification failed."
            )


        try:

            with zipfile.ZipFile(
                archive,
                "r",
            ) as package:

                names = (
                    package.namelist()
                )


                if (
                    self.MANIFEST_NAME
                    not in names
                ):
                    raise PackageVerificationError(
                        "OTA package does not "
                        "contain manifest.json."
                    )


                for name in names:

                    self._validate_member_name(
                        name
                    )


                raw_manifest = (
                    package.read(
                        self.MANIFEST_NAME
                    )
                )


        except PackageVerificationError:

            raise


        except Exception as exc:

            raise PackageVerificationError(
                f"Invalid OTA archive: {exc}"
            ) from exc


        try:

            manifest_data = (
                json.loads(
                    raw_manifest.decode(
                        "utf-8"
                    )
                )
            )


            manifest = (
                OtaManifest.from_dict(
                    manifest_data
                )
            )


        except Exception as exc:

            raise PackageVerificationError(
                f"Invalid OTA manifest: {exc}"
            ) from exc


        if (
            manifest.artifact
            != archive.name
        ):
            raise PackageVerificationError(
                "Manifest artifact name does not "
                "match ZIP filename."
            )


        return VerifiedPackage(
            archive_path=(
                archive
            ),
            archive_sha256=(
                actual_sha256
            ),
            archive_size_bytes=(
                actual_size
            ),
            manifest=(
                manifest
            ),
        )


    def extract_and_verify(
        self,
        verified_package: VerifiedPackage,
        destination: Path | str,
    ) -> Path:
        """
        Safely extract archive and verify every file
        declared by the manifest.
        """

        destination_path = (
            Path(
                destination
            )
            .resolve()
        )


        if (
            destination_path
            .exists()
        ):
            shutil.rmtree(
                destination_path
            )


        destination_path.mkdir(
            parents=True,
            exist_ok=True,
        )


        try:

            with zipfile.ZipFile(
                verified_package
                .archive_path,
                "r",
            ) as package:

                for member in (
                    package.infolist()
                ):

                    self._validate_member_name(
                        member.filename
                    )


                    target = (
                        destination_path
                        / member.filename
                    ).resolve()


                    if (
                        target
                        != destination_path
                        and destination_path
                        not in target.parents
                    ):
                        raise PackageVerificationError(
                            "OTA archive contains "
                            "an unsafe path."
                        )


                    package.extract(
                        member,
                        destination_path,
                    )


        except Exception:

            shutil.rmtree(
                destination_path,
                ignore_errors=True,
            )

            raise


        for (
            relative_path,
            expected_digest,
        ) in (
            verified_package
            .manifest
            .files
            .items()
        ):

            file_path = (
                destination_path
                / relative_path
            ).resolve()


            if (
                file_path
                != destination_path
                and destination_path
                not in file_path.parents
            ):
                raise PackageVerificationError(
                    "Manifest references file "
                    "outside extraction directory."
                )


            if (
                not file_path
                .is_file()
            ):
                raise PackageVerificationError(
                    f"Manifest file is missing: "
                    f"{relative_path}"
                )


            actual_digest = (
                self.calculate_sha256(
                    file_path
                )
            )


            if (
                actual_digest
                != expected_digest
            ):
                raise PackageVerificationError(
                    f"Payload SHA-256 mismatch: "
                    f"{relative_path}"
                )


        entry_point = (
            destination_path
            /
            verified_package
            .manifest
            .entry_point
        ).resolve()


        if (
            not entry_point
            .is_file()
        ):
            raise PackageVerificationError(
                "Manifest entryPoint does not "
                "exist inside package."
            )


        return (
            destination_path
        )


    @staticmethod
    def _validate_member_name(
        member_name: str,
    ) -> None:
        """Prevent ZIP-slip/path traversal attacks."""

        normalized = (
            member_name.replace(
                "\\",
                "/",
            )
        )


        path = (
            PurePosixPath(
                normalized
            )
        )


        if (
            path.is_absolute()
            or ".."
            in path.parts
        ):
            raise PackageVerificationError(
                f"Unsafe OTA archive member: "
                f"{member_name}"
            )