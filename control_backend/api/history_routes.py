"""REST API for HealthBand historical DynamoDB data."""

import asyncio
from collections.abc import Callable
from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Request,
)

from control_backend.services.time_range import (
    resolve_time_range,
)


router = APIRouter(
    prefix="/api/devices",
    tags=[
        "History"
    ],
)


def ensure_device(
    request: Request,
    device_id: str,
) -> None:
    if (
        device_id
        != request.app.state.settings.device_id
    ):
        raise HTTPException(
            status_code=404,
            detail="HealthBand device not found.",
        )


async def query_history(
    request: Request,
    device_id: str,
    method: Callable[..., list[dict[str, Any]]],
    period: str,
    start: str | None,
    end: str | None,
    limit: int,
) -> dict[str, Any]:
    """Resolve period and execute blocking DynamoDB query."""

    try:
        start_time, end_time = (
            resolve_time_range(
                period=period,
                start=start,
                end=end,
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(
                exc
            ),
        ) from exc

    start_iso = (
        start_time.isoformat()
    )

    end_iso = (
        end_time.isoformat()
    )

    items = (
        await asyncio.to_thread(
            method,
            device_id,
            start_iso,
            end_iso,
            limit,
        )
    )

    return {
        "deviceId": device_id,
        "from": start_iso,
        "to": end_iso,
        "count": len(
            items
        ),
        "items": items,
    }


@router.get(
    "/{device_id}/telemetry"
)
async def get_telemetry(
    device_id: str,
    request: Request,
    period: str = Query(
        default="1h"
    ),
    start: str | None = Query(
        default=None
    ),
    end: str | None = Query(
        default=None
    ),
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000,
    ),
) -> dict[str, Any]:
    """Return raw telemetry."""

    ensure_device(
        request,
        device_id,
    )

    return await query_history(
        request,
        device_id,
        request.app.state
        .dynamodb_service
        .get_telemetry,
        period,
        start,
        end,
        limit,
    )


@router.get(
    "/{device_id}/analytics"
)
async def get_analytics(
    device_id: str,
    request: Request,
    period: str = Query(
        default="30d"
    ),
    start: str | None = Query(
        default=None
    ),
    end: str | None = Query(
        default=None
    ),
    limit: int = Query(
        default=2000,
        ge=1,
        le=5000,
    ),
) -> dict[str, Any]:
    """Return aggregate analytics."""

    ensure_device(
        request,
        device_id,
    )

    return await query_history(
        request,
        device_id,
        request.app.state
        .dynamodb_service
        .get_analytics,
        period,
        start,
        end,
        limit,
    )


@router.get(
    "/{device_id}/alerts"
)
async def get_alerts(
    device_id: str,
    request: Request,
    period: str = Query(
        default="24h"
    ),
    start: str | None = Query(
        default=None
    ),
    end: str | None = Query(
        default=None
    ),
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000,
    ),
) -> dict[str, Any]:
    """Return persisted alerts."""

    ensure_device(
        request,
        device_id,
    )

    return await query_history(
        request,
        device_id,
        request.app.state
        .dynamodb_service
        .get_alerts,
        period,
        start,
        end,
        limit,
    )


@router.get(
    "/{device_id}/events"
)
async def get_events(
    device_id: str,
    request: Request,
    period: str = Query(
        default="24h"
    ),
    start: str | None = Query(
        default=None
    ),
    end: str | None = Query(
        default=None
    ),
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000,
    ),
) -> dict[str, Any]:
    """Return persisted HealthBand events."""

    ensure_device(
        request,
        device_id,
    )

    return await query_history(
        request,
        device_id,
        request.app.state
        .dynamodb_service
        .get_events,
        period,
        start,
        end,
        limit,
    )


@router.get(
    "/{device_id}/command-responses"
)
async def get_command_responses(
    device_id: str,
    request: Request,
    period: str = Query(
        default="24h"
    ),
    start: str | None = Query(
        default=None
    ),
    end: str | None = Query(
        default=None
    ),
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000,
    ),
) -> dict[str, Any]:
    """Return persisted command lifecycle responses."""

    ensure_device(
        request,
        device_id,
    )

    return await query_history(
        request,
        device_id,
        request.app.state
        .dynamodb_service
        .get_command_responses,
        period,
        start,
        end,
        limit,
    )