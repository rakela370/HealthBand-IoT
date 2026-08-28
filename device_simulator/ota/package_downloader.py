"""OTA package downloader."""

from pathlib import Path
import shutil
from urllib.parse import urlparse
from urllib.request import urlopen


class PackageDownloadError(
    RuntimeError
):
    """Raised when an OTA package cannot be obtained."""


class PackageDownloader:
    """
    Obtain OTA package locally or over HTTP(S).

    Module 10 primarily uses local files.
    Module 12 will use time-limited S3 HTTPS URLs.
    """

    def __init__(
        self,
        download_directory: Path | str,
        maximum_size_bytes: int = (
            100
            * 1024
            * 1024
        ),
    ) -> None:

        self.download_directory = (
            Path(
                download_directory
            )
            .resolve()
        )


        self.maximum_size_bytes = int(
            maximum_size_bytes
        )


        self.download_directory.mkdir(
            parents=True,
            exist_ok=True,
        )


    def download(
        self,
        source: str,
        destination_name: str | None = None,
    ) -> Path:
        """Copy local package or download HTTP(S) package."""

        parsed = (
            urlparse(
                source
            )
        )


        if (
            parsed.scheme
            in {
                "http",
                "https",
            }
        ):

            name = (
                destination_name
                or Path(
                    parsed.path
                ).name
                or "healthband-update.zip"
            )


            destination = (
                self.download_directory
                / name
            )


            self._download_http(
                source,
                destination,
            )


            return (
                destination
            )


        local_path = (
            Path(
                source
            )
            .expanduser()
            .resolve()
        )


        if (
            not local_path
            .is_file()
        ):
            raise PackageDownloadError(
                f"OTA package does not exist: "
                f"{local_path}"
            )


        if (
            local_path.stat().st_size
            >
            self.maximum_size_bytes
        ):
            raise PackageDownloadError(
                "OTA package exceeds configured "
                "maximum size."
            )


        destination = (
            self.download_directory
            / (
                destination_name
                or local_path.name
            )
        ).resolve()


        if (
            destination
            != local_path
        ):
            shutil.copy2(
                local_path,
                destination,
            )


        return (
            destination
        )


    def _download_http(
        self,
        source: str,
        destination: Path,
    ) -> None:
        """Stream HTTP package while enforcing size limit."""

        try:

            with urlopen(
                source,
                timeout=30,
            ) as response:

                content_length = (
                    response.headers.get(
                        "Content-Length"
                    )
                )


                if (
                    content_length
                    and int(
                        content_length
                    )
                    >
                    self.maximum_size_bytes
                ):
                    raise PackageDownloadError(
                        "OTA package exceeds "
                        "configured maximum size."
                    )


                written = 0


                with destination.open(
                    "wb"
                ) as output:

                    while True:

                        chunk = (
                            response.read(
                                64
                                * 1024
                            )
                        )


                        if (
                            not chunk
                        ):
                            break


                        written += (
                            len(
                                chunk
                            )
                        )


                        if (
                            written
                            >
                            self.maximum_size_bytes
                        ):
                            raise PackageDownloadError(
                                "OTA package exceeded "
                                "maximum size while "
                                "downloading."
                            )


                        output.write(
                            chunk
                        )


        except PackageDownloadError:

            destination.unlink(
                missing_ok=True
            )

            raise


        except Exception as exc:

            destination.unlink(
                missing_ok=True
            )

            raise PackageDownloadError(
                f"Unable to download OTA package: "
                f"{exc}"
            ) from exc