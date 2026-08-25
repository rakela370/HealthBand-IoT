"""REST API for HealthBand Device Shadow configuration."""

import asyncio
from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)

from control_backend.models.configuration_models import (
    ConfigurationUpdateRequest,
)


router = APIRouter(
    prefix="/api/devices",
    tags=[
        "Configuration"
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


@router.get(
    "/{device_id}/configuration"
)
async def get_configuration(
    device_id: str,
    request: Request,
) -> dict[str, Any]:
    """Return complete classic Shadow document."""

    ensure_device(
        request,
        device_id,
    )

    try:
        return (
            await asyncio.to_thread(
                request.app.state
                .shadow_service
                .get_shadow,
                device_id,
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to retrieve Device Shadow: "
                f"{exc}"
            ),
        ) from exc


@router.put(
    "/{device_id}/configuration"
)
async def update_configuration(
    device_id: str,
    update: ConfigurationUpdateRequest,
    request: Request,
) -> dict[str, Any]:
    """Update desired Device Shadow configuration."""

    ensure_device(
        request,
        device_id,
    )

    desired = (
        update.model_dump(
            exclude_none=True
        )
    )

    try:
        return (
            await asyncio.to_thread(
                request.app.state
                .shadow_service
                .update_desired,
                device_id,
                desired,
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to update Device Shadow: "
                f"{exc}"
            ),
        ) from exc