"""REST endpoints for HealthBand OTA releases and AWS IoT Jobs."""

from typing import Any

from botocore.exceptions import (
    ClientError,
)
from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    status,
)

from control_backend.aws.ota_service import (
    OtaReleaseNotFoundError,
    OtaServiceConfigurationError,
)
from control_backend.models.ota_models import (
    OtaStartRequest,
)


router = APIRouter(
    tags=[
        "OTA"
    ],
)


def _validate_device(
    request: Request,
    device_id: str,
) -> None:
    expected = (
        request.app.state
        .settings
        .device_id
    )

    if (
        device_id
        != expected
    ):
        raise HTTPException(
            status_code=(
                status
                .HTTP_404_NOT_FOUND
            ),
            detail=(
                "Unknown HealthBand "
                f"device '{device_id}'."
            ),
        )


async def _current_version(
    request: Request,
    device_id: str,
) -> str | None:
    store = (
        request.app.state
        .realtime_store
    )

    for event_type in (
        "telemetry",
        "health",
        "presence",
    ):
        payload = (
            await store
            .get_latest(
                device_id,
                event_type,
            )
        )

        if payload:
            version = str(
                payload.get(
                    "softwareVersion",
                    "",
                )
            ).strip()

            if version:
                return version

    return (
        request.app.state
        .ota_service
        .active_version_from_disk()
    )


@router.get(
    "/api/releases",
)
async def list_releases(
    request: Request,
) -> dict[str, Any]:
    """Return local releases and their private-S3 availability."""

    try:
        releases = (
            request.app.state
            .ota_service
            .list_releases()
        )

    except ClientError as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_502_BAD_GATEWAY
            ),
            detail=(
                "Unable to inspect "
                "HealthBand OTA objects "
                "in AWS S3: "
                + str(
                    exc.response
                    .get(
                        "Error",
                        {},
                    )
                    .get(
                        "Code",
                        "AWS_ERROR",
                    )
                )
            ),
        ) from exc

    return {
        "items": releases,
    }


@router.get(
    "/api/devices/{device_id}/ota",
)
async def get_ota_state(
    request: Request,
    device_id: str,
) -> dict[str, Any]:
    """Return current version, progress, latest Job and releases."""

    _validate_device(
        request,
        device_id,
    )

    current_version = (
        await _current_version(
            request,
            device_id,
        )
    )

    progress = (
        await request.app.state
        .realtime_store
        .get_latest(
            device_id,
            "ota",
        )
    )

    try:
        latest_job = (
            request.app.state
            .ota_service
            .latest_job_execution(
                device_id
            )
        )

        releases = (
            request.app.state
            .ota_service
            .list_releases()
        )

    except ClientError as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_502_BAD_GATEWAY
            ),
            detail=(
                "Unable to read AWS "
                "IoT Jobs OTA state: "
                + str(
                    exc.response
                    .get(
                        "Error",
                        {},
                    )
                    .get(
                        "Code",
                        "AWS_ERROR",
                    )
                )
            ),
        ) from exc

    return {
        "deviceId":
            device_id,

        "currentVersion":
            current_version,

        "latestProgress":
            progress,

        "latestJob":
            latest_job,

        "releases":
            releases,
    }


@router.post(
    "/api/devices/{device_id}/ota",
    status_code=(
        status
        .HTTP_201_CREATED
    ),
)
async def start_ota(
    request: Request,
    device_id: str,
    body: OtaStartRequest,
) -> dict[str, Any]:
    """Create an AWS IoT Job for the selected HealthBand release."""

    _validate_device(
        request,
        device_id,
    )

    service = (
        request.app.state
        .ota_service
    )

    target_version = (
        body.target_version
        .strip()
    )

    current_version = (
        await _current_version(
            request,
            device_id,
        )
    )

    if (
        current_version
        and not body.force
    ):
        try:
            if (
                service.parse_version(
                    target_version
                )
                <= service.parse_version(
                    current_version
                )
            ):
                raise HTTPException(
                    status_code=(
                        status
                        .HTTP_409_CONFLICT
                    ),
                    detail=(
                        "Target version "
                        f"{target_version} "
                        "must be newer than "
                        "active version "
                        f"{current_version}."
                    ),
                )

        except ValueError as exc:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
                detail=str(
                    exc
                ),
            ) from exc

    try:
        return service.start_job(
            device_id=(
                device_id
            ),
            version=(
                target_version
            ),
        )

    except (
        OtaReleaseNotFoundError
    ) as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_404_NOT_FOUND
            ),
            detail=str(
                exc
            ),
        ) from exc

    except (
        OtaServiceConfigurationError
    ) as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=str(
                exc
            ),
        ) from exc

    except ClientError as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_502_BAD_GATEWAY
            ),
            detail=(
                "AWS IoT Job "
                "creation failed: "
                + str(
                    exc.response
                    .get(
                        "Error",
                        {},
                    )
                    .get(
                        "Code",
                        "AWS_ERROR",
                    )
                )
            ),
        ) from exc