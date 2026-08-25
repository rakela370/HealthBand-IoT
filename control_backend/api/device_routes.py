"""REST routes for HealthBand device state."""

import asyncio
from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)


router = APIRouter(
    prefix="/api/devices",
    tags=[
        "Devices"
    ],
)


def ensure_device(
    request: Request,
    device_id: str,
) -> None:
    """Reject unknown HealthBand device identifiers."""

    if (
        device_id
        != request.app.state.settings.device_id
    ):
        raise HTTPException(
            status_code=404,
            detail="HealthBand device not found.",
        )


async def build_summary(
    request: Request,
    device_id: str,
) -> dict[str, Any]:
    """Build REST representation from realtime + persisted state."""

    store = (
        request.app.state
        .realtime_store
    )

    snapshot = (
        await store.snapshot(
            device_id
        )
    )

    telemetry = (
        snapshot.get(
            "telemetry"
        )
    )

    if telemetry is None:
        telemetry = (
            await asyncio.to_thread(
                request.app.state
                .dynamodb_service
                .get_latest_telemetry,
                device_id,
            )
        )

    presence = (
        snapshot.get(
            "presence"
        )
    )

    health = (
        snapshot.get(
            "health"
        )
    )

    online = (
        isinstance(
            presence,
            dict,
        )
        and presence.get(
            "status"
        )
        == "ONLINE"
    )

    return {
        "deviceId": (
            device_id
        ),
        "online": (
            online
        ),
        "deviceState": (
            (
                health or {}
            ).get(
                "deviceState"
            )
            or (
                telemetry or {}
            ).get(
                "deviceState"
            )
        ),
        "softwareVersion": (
            (
                telemetry or {}
            ).get(
                "softwareVersion"
            )
        ),
        "scenario": (
            (
                telemetry or {}
            ).get(
                "scenario"
            )
        ),
        "mqttConnected": (
            (
                health or {}
            ).get(
                "mqttConnected"
            )
        ),
        "latestTelemetry": (
            telemetry
        ),
        "latestHealth": (
            health
        ),
        "latestAlert": (
            snapshot.get(
                "alert"
            )
        ),
    }


@router.get("")
async def list_devices(
    request: Request,
) -> list[dict[str, Any]]:
    """Return configured HealthBand devices."""

    device_id = (
        request.app.state
        .settings
        .device_id
    )

    return [
        await build_summary(
            request,
            device_id,
        )
    ]


@router.get(
    "/{device_id}"
)
async def get_device(
    device_id: str,
    request: Request,
) -> dict[str, Any]:
    """Return one HealthBand summary."""

    ensure_device(
        request,
        device_id,
    )

    return await build_summary(
        request,
        device_id,
    )


@router.get(
    "/{device_id}/state"
)
async def get_device_state(
    device_id: str,
    request: Request,
) -> dict[str, Any]:
    """Return current logical and connectivity state."""

    ensure_device(
        request,
        device_id,
    )

    summary = (
        await build_summary(
            request,
            device_id,
        )
    )

    return {
        "deviceId": (
            device_id
        ),
        "online": (
            summary[
                "online"
            ]
        ),
        "deviceState": (
            summary[
                "deviceState"
            ]
        ),
        "softwareVersion": (
            summary[
                "softwareVersion"
            ]
        ),
        "scenario": (
            summary[
                "scenario"
            ]
        ),
        "mqttConnected": (
            summary[
                "mqttConnected"
            ]
        ),
    }


@router.get(
    "/{device_id}/health"
)
async def get_device_health(
    device_id: str,
    request: Request,
) -> dict[str, Any]:
    """Return latest realtime technical health report."""

    ensure_device(
        request,
        device_id,
    )

    health = (
        await request.app.state
        .realtime_store
        .get_latest(
            device_id,
            "health",
        )
    )

    if health is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No realtime HealthBand health "
                "report has been received yet."
            ),
        )

    return health