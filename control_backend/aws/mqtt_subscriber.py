"""Dedicated AWS IoT MQTT subscriber for FastAPI realtime data."""

import asyncio
import json
import logging
from collections.abc import (
    Awaitable,
    Callable,
)
from typing import Any

from awscrt import mqtt
from awsiot import mqtt_connection_builder

from control_backend.settings import (
    BackendSettings,
)


logger = logging.getLogger(
    __name__
)


RealtimeHandler = Callable[
    [
        str,
        str,
        dict[str, Any],
    ],
    Awaitable[None],
]


class BackendMqttSubscriber:
    """Receive HealthBand MQTT traffic using a separate X.509 identity."""

    def __init__(
        self,
        settings: BackendSettings,
        handler: RealtimeHandler,
    ) -> None:
        self.settings = (
            settings
        )

        self.handler = (
            handler
        )

        self._loop: (
            asyncio.AbstractEventLoop
            | None
        ) = None

        self._connection: Any = None

        self._connected = (
            False
        )

        device_id = (
            settings.device_id
        )

        self._topics: dict[
            str,
            tuple[
                str,
                int,
            ],
        ] = {
            (
                f"healthband/{device_id}/telemetry"
            ): (
                "telemetry",
                0,
            ),

            (
                f"healthband/{device_id}/analytics"
            ): (
                "analytics",
                1,
            ),

            (
                f"healthband/{device_id}/alerts"
            ): (
                "alert",
                1,
            ),

            (
                f"healthband/{device_id}/health"
            ): (
                "health",
                1,
            ),

            (
                f"healthband/{device_id}/events"
            ): (
                "event",
                1,
            ),

            (
                f"healthband/{device_id}/commands/response"
            ): (
                "command_response",
                1,
            ),

            (
                f"healthband/{device_id}/presence"
            ): (
                "presence",
                1,
            ),
        }

    @property
    def is_connected(
        self,
    ) -> bool:
        """Return MQTT subscriber connection state."""

        return (
            self._connected
        )

    def start(
        self,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Connect and subscribe to HealthBand realtime topics."""

        if self._connected:
            return

        self._loop = (
            loop
        )

        certificate = (
            self.settings.resolve_path(
                self.settings
                .backend_iot_cert_path
            )
        )

        private_key = (
            self.settings.resolve_path(
                self.settings
                .backend_iot_private_key_path
            )
        )

        root_ca = (
            self.settings.resolve_path(
                self.settings
                .backend_root_ca_path
            )
        )

        for path in (
            certificate,
            private_key,
            root_ca,
        ):
            if not path.is_file():
                raise FileNotFoundError(
                    f"Backend MQTT file does not exist: {path}"
                )

        self._connection = (
            mqtt_connection_builder
            .mtls_from_path(
                endpoint=(
                    self.settings
                    .aws_iot_endpoint
                ),
                cert_filepath=(
                    str(
                        certificate
                    )
                ),
                pri_key_filepath=(
                    str(
                        private_key
                    )
                ),
                ca_filepath=(
                    str(
                        root_ca
                    )
                ),
                client_id=(
                    self.settings
                    .backend_mqtt_client_id
                ),
                clean_session=False,
                keep_alive_secs=30,
                reconnect_min_timeout_secs=1,
                reconnect_max_timeout_secs=32,
                on_connection_interrupted=(
                    self._on_connection_interrupted
                ),
                on_connection_resumed=(
                    self._on_connection_resumed
                ),
            )
        )

        logger.info(
            "Connecting backend MQTT subscriber "
            "to AWS IoT Core."
        )

        self._connection.connect().result(
            timeout=15
        )

        self._connected = (
            True
        )

        for (
            topic,
            (
                _,
                qos,
            ),
        ) in self._topics.items():

            future, _ = (
                self._connection.subscribe(
                    topic=topic,
                    qos=self._to_qos(
                        qos
                    ),
                    callback=(
                        self._on_message
                    ),
                )
            )

            future.result(
                timeout=10
            )

            logger.info(
                "Backend MQTT subscribed | topic=%s",
                topic,
            )

        logger.info(
            "Backend MQTT subscriber is ready."
        )

    def stop(
        self,
    ) -> None:
        """Disconnect backend subscriber."""

        if (
            self._connection is None
            or not self._connected
        ):
            return

        self._connection.disconnect().result(
            timeout=10
        )

        self._connected = (
            False
        )

        logger.info(
            "Backend MQTT subscriber disconnected."
        )

    def _on_message(
        self,
        topic: str,
        payload: bytes,
        dup: bool,
        qos: mqtt.QoS,
        retain: bool,
        **kwargs: Any,
    ) -> None:
        """Forward AWS MQTT callback to FastAPI asyncio loop."""

        del dup
        del qos
        del retain
        del kwargs

        if self._loop is None:
            return

        topic_info = (
            self._topics.get(
                topic
            )
        )

        if topic_info is None:
            return

        event_type, _ = (
            topic_info
        )

        try:
            decoded = (
                json.loads(
                    payload.decode(
                        "utf-8"
                    )
                )
            )

            if not isinstance(
                decoded,
                dict,
            ):
                raise ValueError(
                    "MQTT payload must be JSON object."
                )

        except Exception:
            logger.exception(
                "Backend rejected malformed MQTT "
                "message on topic %s.",
                topic,
            )

            return

        future = (
            asyncio.run_coroutine_threadsafe(
                self.handler(
                    self.settings.device_id,
                    event_type,
                    decoded,
                ),
                self._loop,
            )
        )

        def log_callback(
            completed: Any,
        ) -> None:
            try:
                completed.result()

            except Exception:
                logger.exception(
                    "Realtime MQTT handler failed."
                )

        future.add_done_callback(
            log_callback
        )

    def _on_connection_interrupted(
        self,
        connection: Any,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        del connection
        del kwargs

        self._connected = (
            False
        )

        logger.warning(
            "Backend MQTT connection interrupted: %s",
            error,
        )

    def _on_connection_resumed(
        self,
        connection: Any,
        return_code: mqtt.ConnectReturnCode,
        session_present: bool,
        **kwargs: Any,
    ) -> None:
        del kwargs

        self._connected = (
            return_code
            == mqtt.ConnectReturnCode.ACCEPTED
        )

        logger.info(
            "Backend MQTT connection resumed | "
            "sessionPresent=%s",
            session_present,
        )

        if (
            self._connected
            and not session_present
        ):
            future, _ = (
                connection
                .resubscribe_existing_topics()
            )

            future.add_done_callback(
                lambda completed: (
                    completed.result()
                )
            )

    @staticmethod
    def _to_qos(
        qos: int,
    ) -> mqtt.QoS:
        if qos == 0:
            return (
                mqtt.QoS.AT_MOST_ONCE
            )

        return (
            mqtt.QoS.AT_LEAST_ONCE
        )