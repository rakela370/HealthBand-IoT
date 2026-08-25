"""REST API for HealthBand commands."""

import asyncio
from typing import Any
from uuid import uuid4

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)

from control_backend.models.command_models import (
    CommandCreateRequest,
)


router = APIRouter(
    prefix="/api/devices",
    tags=[
        "Commands"
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


@router.post(
    "/{device_id}/commands",
    status_code=202,
)
async def send_command(
    device_id: str,
    command: CommandCreateRequest,
    request: Request,
) -> dict[str, Any]:
    """Publish one command to AWS IoT Core."""

    ensure_device(
        request,
        device_id,
    )

    command_id = str(
        uuid4()
    )

    try:
        payload = (
            await asyncio.to_thread(
                request.app.state
                .iot_data_client
                .publish_command,
                device_id,
                command_id,
                command.type.value,
                command.parameters,
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to publish HealthBand command: "
                f"{exc}"
            ),
        ) from exc

    await (
        request.app.state
        .realtime_store
        .register_command_submission(
            device_id=(
                device_id
            ),
            command_id=(
                command_id
            ),
            command_type=(
                command.type.value
            ),
            parameters=(
                command.parameters
            ),
        )
    )

    return {
        "accepted": True,
        "commandId": (
            command_id
        ),
        "request": (
            payload
        ),
    }


@router.get(
    "/{device_id}/commands/{command_id}"
)
async def get_command_status(
    device_id: str,
    command_id: str,
    request: Request,
) -> dict[str, Any]:
    """Return latest known status of one command."""

    ensure_device(
        request,
        device_id,
    )

    realtime = (
        await request.app.state
        .realtime_store
        .get_command(
            device_id,
            command_id,
        )
    )

    if realtime is not None:
        return realtime

    persisted = (
        await asyncio.to_thread(
            request.app.state
            .dynamodb_service
            .get_command_status,
            device_id,
            command_id,
        )
    )

    if persisted is None:
        raise HTTPException(
            status_code=404,
            detail="Command not found.",
        )

    return persisted