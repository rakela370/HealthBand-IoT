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
from control_backend.services.history_downsampling import (
    downsample_analytics_history,
)
from control_backend.services.history_series import (
    build_history_series,
)


router = APIRouter(
    prefix="/api/devices",
    tags=[
        "History"
    ],
)




def normalize_telemetry_temperature_history(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return telemetry history with temperature canonically expressed in °C.

    Realtime/dashboard telemetry still uses the configured display unit. This
    normalization is only for historical chart data, whose axis is treated as
    Celsius. It also repairs already-stored Fahrenheit rows when their
    temperatureUnit metadata is present.
    """

    normalized: list[dict[str, Any]] = []

    for item in items:
        copied = dict(item)
        raw_measurements = item.get("measurements")

        if not isinstance(raw_measurements, dict):
            normalized.append(copied)
            continue

        measurements = dict(raw_measurements)
        canonical = measurements.get("skinTemperatureCelsius")

        value_celsius: float | None = None

        if isinstance(canonical, (int, float)) and not isinstance(canonical, bool):
            value_celsius = float(canonical)
        else:
            displayed = measurements.get("skinTemperature")
            if isinstance(displayed, (int, float)) and not isinstance(displayed, bool):
                value = float(displayed)
                unit = str(measurements.get("temperatureUnit", "CELSIUS")).upper()
                if unit == "FAHRENHEIT":
                    value_celsius = (value - 32.0) * 5.0 / 9.0
                else:
                    value_celsius = value

        if value_celsius is not None:
            rounded = round(value_celsius, 2)
            measurements["skinTemperatureCelsius"] = rounded
            measurements["skinTemperature"] = rounded
            measurements["temperatureUnit"] = "CELSIUS"

        copied["measurements"] = measurements
        normalized.append(copied)

    return normalized

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
        default=5000,
        ge=1,
        le=5000,
    ),
) -> dict[str, Any]:
    """Return raw telemetry.

    The device can publish telemetry as frequently as once per second.
    A one-hour history window can therefore contain up to 3,600 rows.
    The previous 1,000-row default silently truncated the newest part of
    the selected hour, so the default now covers the complete supported
    one-hour raw-telemetry window.
    """

    ensure_device(
        request,
        device_id,
    )

    response = await query_history(
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

    response["items"] = normalize_telemetry_temperature_history(
        response["items"]
    )
    return response


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
        default=300000,
        ge=1,
        le=300000,
    ),
) -> dict[str, Any]:
    """Return aggregate analytics for longer history windows.

    The query limit covers 30 days at the default 10-second analytics
    interval. The response is then reduced to at most 1,200 display points
    while preserving min/max values and the real requested time range.
    """

    ensure_device(
        request,
        device_id,
    )

    response = await query_history(
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

    source_items = response["items"]
    response["sourceCount"] = len(source_items)
    response["items"] = downsample_analytics_history(
        source_items,
        response["from"],
        response["to"],
        max_points=1200,
    )
    response["count"] = len(response["items"])
    response["downsampled"] = (
        response["count"] < response["sourceCount"]
    )
    return response




@router.get(
    "/{device_id}/history-series"
)
async def get_history_series(
    device_id: str,
    request: Request,
    period: str = Query(default="1h"),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
) -> dict[str, Any]:
    """Return one normalized history series for all chart periods.

    Recent raw telemetry is always included so the History page remains useful
    even when local analytics has been disabled.  For 24h/7d/30d, analytics
    rows are also loaded to fill older seeded/aggregate history.  Overlapping
    analytics is suppressed in favour of the more detailed raw telemetry.
    """

    ensure_device(request, device_id)

    try:
        start_time, end_time = resolve_time_range(
            period=period,
            start=start,
            end=end,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    start_iso = start_time.isoformat()
    end_iso = end_time.isoformat()

    telemetry_limit = {
        "15m": 20_000,
        "1h": 50_000,
        "24h": 100_000,
        "7d": 100_000,
        "30d": 100_000,
    }.get(period, 100_000)

    analytics_limit = {
        "15m": 0,
        "1h": 0,
        "24h": 50_000,
        "7d": 150_000,
        "30d": 300_000,
    }.get(period, 0)

    telemetry_task = asyncio.to_thread(
        request.app.state.dynamodb_service.get_telemetry_recent,
        device_id,
        start_iso,
        end_iso,
        telemetry_limit,
    )

    if analytics_limit > 0:
        analytics_task = asyncio.to_thread(
            request.app.state.dynamodb_service.get_analytics,
            device_id,
            start_iso,
            end_iso,
            analytics_limit,
        )
        telemetry_items, analytics_items = await asyncio.gather(
            telemetry_task,
            analytics_task,
        )
    else:
        telemetry_items = await telemetry_task
        analytics_items = []

    points = build_history_series(
        telemetry_items=telemetry_items,
        analytics_items=analytics_items,
        start_iso=start_iso,
        end_iso=end_iso,
        period=period,
    )

    return {
        "deviceId": device_id,
        "from": start_iso,
        "to": end_iso,
        "period": period,
        "count": len(points),
        "rawTelemetryCount": len(telemetry_items),
        "analyticsCount": len(analytics_items),
        "items": points,
    }


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
        default=20000,
        ge=1,
        le=20000,
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