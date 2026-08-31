"""FastAPI entry point for the HealthBand control backend."""

import asyncio
import logging
from contextlib import (
    asynccontextmanager,
)
from pathlib import (
    Path,
)
from typing import (
    AsyncIterator,
)

import boto3
from fastapi import (
    FastAPI,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from fastapi.responses import (
    FileResponse,
)
from fastapi.staticfiles import (
    StaticFiles,
)

from control_backend.api.command_routes import (
    router as command_router,
)
from control_backend.api.configuration_routes import (
    router as configuration_router,
)
from control_backend.api.device_routes import (
    router as device_router,
)
from control_backend.api.history_routes import (
    router as history_router,
)
from control_backend.api.ota_routes import (
    router as ota_router,
)
from control_backend.aws.dynamodb_service import (
    DynamoDbService,
)
from control_backend.aws.iot_data_client import (
    IotDataClient,
)
from control_backend.aws.mqtt_subscriber import (
    BackendMqttSubscriber,
)
from control_backend.aws.ota_service import (
    OtaService,
)
from control_backend.aws.shadow_service import (
    ShadowService,
)
from control_backend.services.realtime_state_store import (
    RealtimeStateStore,
)
from control_backend.settings import (
    BackendSettings,
)
from control_backend.websocket.connection_manager import (
    WebSocketConnectionManager,
)
from control_backend.websocket.event_broadcaster import (
    EventBroadcaster,
)


logger = logging.getLogger(
    __name__
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

FRONTEND_DIR = (
    PROJECT_ROOT
    / "web_frontend"
)

FRONTEND_INDEX = (
    FRONTEND_DIR
    / "index.html"
)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    """Initialize AWS and realtime backend services."""

    settings = (
        BackendSettings()
    )

    logging.basicConfig(
        level=getattr(
            logging,
            settings
            .log_level
            .upper(),
            logging.INFO,
        ),
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )

    session_kwargs = {
        "region_name": (
            settings.aws_region
        )
    }

    if (
        settings.profile_name
        is not None
    ):
        session_kwargs[
            "profile_name"
        ] = (
            settings.profile_name
        )

    aws_session = boto3.Session(
        **session_kwargs
    )

    dynamodb_resource = (
        aws_session.resource(
            "dynamodb"
        )
    )

    iot_data_boto_client = (
        aws_session.client(
            "iot-data",
            endpoint_url=(
                "https://"
                + settings
                .aws_iot_endpoint
            ),
        )
    )

    s3_client = (
        aws_session.client(
            "s3"
        )
    )

    iot_management_client = (
        aws_session.client(
            "iot"
        )
    )

    sts_client = (
        aws_session.client(
            "sts"
        )
    )

    dynamodb_service = (
        DynamoDbService(
            dynamodb_resource=(
                dynamodb_resource
            ),
            telemetry_table=(
                settings.telemetry_table
            ),
            analytics_table=(
                settings.analytics_table
            ),
            events_table=(
                settings.events_table
            ),
        )
    )

    iot_data_client = (
        IotDataClient(
            iot_data_boto_client
        )
    )

    shadow_service = (
        ShadowService(
            iot_data_boto_client
        )
    )

    ota_service = (
        OtaService(
            settings=settings,
            s3_client=(
                s3_client
            ),
            iot_client=(
                iot_management_client
            ),
            sts_client=(
                sts_client
            ),
        )
    )

    realtime_store = (
        RealtimeStateStore()
    )

    websocket_manager = (
        WebSocketConnectionManager()
    )

    broadcaster = (
        EventBroadcaster(
            websocket_manager
        )
    )

    async def handle_realtime_message(
        device_id: str,
        event_type: str,
        payload: dict,
    ) -> None:
        await realtime_store.update(
            device_id=device_id,
            event_type=event_type,
            payload=payload,
        )

        await broadcaster.broadcast(
            device_id=device_id,
            event_type=event_type,
            data=payload,
        )

    mqtt_subscriber = (
        BackendMqttSubscriber(
            settings=settings,
            handler=(
                handle_realtime_message
            ),
        )
    )

    app.state.settings = settings

    app.state.dynamodb_service = (
        dynamodb_service
    )

    app.state.iot_data_client = (
        iot_data_client
    )

    app.state.shadow_service = (
        shadow_service
    )

    app.state.ota_service = (
        ota_service
    )

    app.state.realtime_store = (
        realtime_store
    )

    app.state.websocket_manager = (
        websocket_manager
    )

    app.state.event_broadcaster = (
        broadcaster
    )

    app.state.mqtt_subscriber = (
        mqtt_subscriber
    )

    if (
        settings
        .backend_mqtt_enabled
    ):
        loop = (
            asyncio
            .get_running_loop()
        )

        await asyncio.to_thread(
            mqtt_subscriber.start,
            loop,
        )

    logger.info(
        "HealthBand FastAPI "
        "backend started."
    )

    try:
        yield

    finally:
        if (
            settings
            .backend_mqtt_enabled
        ):
            try:
                await asyncio.to_thread(
                    mqtt_subscriber.stop
                )

            except Exception:
                logger.exception(
                    "Error while stopping "
                    "backend MQTT subscriber."
                )

        logger.info(
            "HealthBand FastAPI "
            "backend stopped."
        )


app = FastAPI(
    title=(
        "HealthBand Control API"
    ),
    version="1.1.0",
    description=(
        "Backend API for the "
        "simulated HealthBand "
        "IoT diploma project."
    ),
    lifespan=lifespan,
)


settings_for_cors = (
    BackendSettings()
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        settings_for_cors
        .cors_origin_list
    ),
    allow_credentials=True,
    allow_methods=[
        "*"
    ],
    allow_headers=[
        "*"
    ],
)


app.include_router(
    device_router
)

app.include_router(
    configuration_router
)

app.include_router(
    command_router
)

app.include_router(
    history_router
)

app.include_router(
    ota_router
)


if not FRONTEND_DIR.is_dir():
    raise RuntimeError(
        "HealthBand frontend directory "
        f"does not exist: {FRONTEND_DIR}"
    )


if not FRONTEND_INDEX.is_file():
    raise RuntimeError(
        "HealthBand frontend index.html "
        f"does not exist: {FRONTEND_INDEX}"
    )


app.mount(
    "/css",
    StaticFiles(
        directory=(
            FRONTEND_DIR
            / "css"
        )
    ),
    name="frontend-css",
)


app.mount(
    "/js",
    StaticFiles(
        directory=(
            FRONTEND_DIR
            / "js"
        )
    ),
    name="frontend-js",
)


app.mount(
    "/assets",
    StaticFiles(
        directory=(
            FRONTEND_DIR
            / "assets"
        )
    ),
    name="frontend-assets",
)


@app.get(
    "/",
    include_in_schema=False,
)
async def frontend_index() -> FileResponse:
    """Serve the HealthBand web dashboard."""

    return FileResponse(
        FRONTEND_INDEX
    )


@app.get(
    "/api/backend/health",
    tags=[
        "Backend"
    ],
)
async def backend_health(
    request: Request,
) -> dict[str, object]:
    """Return backend technical status."""

    subscriber = (
        request.app.state
        .mqtt_subscriber
    )

    return {
        "status":
            "OK",

        "service":
            "HealthBand Control Backend",

        "mqttSubscriberEnabled":
            request.app.state
            .settings
            .backend_mqtt_enabled,

        "mqttSubscriberConnected":
            subscriber
            .is_connected,

        "deviceId":
            request.app.state
            .settings
            .device_id,
    }


@app.websocket(
    "/ws/devices/{device_id}"
)
async def device_websocket(
    websocket: WebSocket,
    device_id: str,
) -> None:
    """Stream realtime HealthBand updates to browser."""

    settings = (
        websocket.app.state
        .settings
    )

    if (
        device_id
        != settings.device_id
    ):
        await websocket.close(
            code=1008
        )

        return

    manager = (
        websocket.app.state
        .websocket_manager
    )

    store = (
        websocket.app.state
        .realtime_store
    )

    await manager.connect(
        device_id,
        websocket,
    )

    try:
        snapshot = (
            await store.snapshot(
                device_id
            )
        )

        await websocket.send_json(
            {
                "type":
                    "initial_snapshot",

                "deviceId":
                    device_id,

                "data":
                    snapshot,
            }
        )

        while True:
            message = (
                await websocket
                .receive_text()
            )

            if (
                message
                .strip()
                .lower()
                == "ping"
            ):
                await websocket.send_json(
                    {
                        "type": "pong"
                    }
                )

    except WebSocketDisconnect:
        pass

    finally:
        await manager.disconnect(
            device_id,
            websocket,
        )