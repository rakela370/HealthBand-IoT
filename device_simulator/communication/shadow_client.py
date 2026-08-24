"""AWS IoT Device Shadow communication for HealthBand."""

import logging
from dataclasses import dataclass
from queue import Empty, Queue
from threading import Lock
from typing import Any
from uuid import uuid4

from awscrt import mqtt
from awsiot import iotshadow


logger = logging.getLogger(__name__)


class ShadowOperationRejected(RuntimeError):
    """Raised when AWS IoT rejects a Shadow request."""

    def __init__(
        self,
        code: int | None,
        message: str,
    ) -> None:
        self.code = (
            code
        )

        super().__init__(
            message
        )


@dataclass(frozen=True, slots=True)
class ShadowDelta:
    """One desired/reported delta received from AWS IoT."""

    state: dict[str, Any]
    version: int | None


class ShadowClient:
    """Use AWS IoT Device SDK v2 for classic Device Shadow."""

    def __init__(
        self,
        thing_name: str,
        mqtt_connection: Any,
    ) -> None:
        self.thing_name = (
            thing_name
        )

        self._client = (
            iotshadow.IotShadowClient(
                mqtt_connection
            )
        )

        self._delta_queue: Queue[
            ShadowDelta
        ] = Queue()

        self._pending_get: dict[
            str,
            Queue[Any],
        ] = {}

        self._pending_update: dict[
            str,
            Queue[Any],
        ] = {}

        self._lock = (
            Lock()
        )

        self._started = (
            False
        )

    def start(
        self,
    ) -> None:
        """Establish initial Shadow subscriptions."""

        if self._started:
            return

        self._subscribe_all()

        self._started = (
            True
        )

        logger.info(
            "Device Shadow subscriptions established "
            "for thing '%s'.",
            self.thing_name,
        )

    def resubscribe(
        self,
    ) -> None:
        """Restore Shadow subscriptions after manual MQTT reconnect."""

        self._subscribe_all()

        self._started = (
            True
        )

        logger.info(
            "Device Shadow subscriptions restored "
            "for thing '%s'.",
            self.thing_name,
        )

    def get_shadow(
        self,
        timeout_sec: float = 10.0,
    ) -> iotshadow.GetShadowResponse:
        """Retrieve current classic Shadow document."""

        self._ensure_started()

        token = str(
            uuid4()
        )

        response_queue: Queue[
            Any
        ] = Queue(
            maxsize=1
        )

        with self._lock:
            self._pending_get[
                token
            ] = response_queue

        try:
            future = (
                self._client.publish_get_shadow(
                    request=(
                        iotshadow.GetShadowRequest(
                            thing_name=(
                                self.thing_name
                            ),
                            client_token=token,
                        )
                    ),
                    qos=(
                        mqtt.QoS.AT_LEAST_ONCE
                    ),
                )
            )

            future.result(
                timeout=timeout_sec
            )

            response = (
                response_queue.get(
                    timeout=timeout_sec
                )
            )

        except Empty as exc:
            raise TimeoutError(
                "Timed out waiting for "
                "GetShadow response."
            ) from exc

        finally:
            with self._lock:
                self._pending_get.pop(
                    token,
                    None,
                )

        if isinstance(
            response,
            Exception,
        ):
            raise response

        return response

    def update_reported(
        self,
        reported: dict[str, Any],
        timeout_sec: float = 10.0,
    ) -> iotshadow.UpdateShadowResponse:
        """Update reported state and wait for AWS acceptance."""

        self._ensure_started()

        token = str(
            uuid4()
        )

        response_queue: Queue[
            Any
        ] = Queue(
            maxsize=1
        )

        with self._lock:
            self._pending_update[
                token
            ] = response_queue

        try:
            request = (
                iotshadow.UpdateShadowRequest(
                    thing_name=(
                        self.thing_name
                    ),
                    client_token=token,
                    state=(
                        iotshadow.ShadowState(
                            reported=reported
                        )
                    ),
                )
            )

            future = (
                self._client.publish_update_shadow(
                    request=request,
                    qos=(
                        mqtt.QoS.AT_LEAST_ONCE
                    ),
                )
            )

            future.result(
                timeout=timeout_sec
            )

            response = (
                response_queue.get(
                    timeout=timeout_sec
                )
            )

        except Empty as exc:
            raise TimeoutError(
                "Timed out waiting for "
                "UpdateShadow response."
            ) from exc

        finally:
            with self._lock:
                self._pending_update.pop(
                    token,
                    None,
                )

        if isinstance(
            response,
            Exception,
        ):
            raise response

        return response

    def drain_deltas(
        self,
        maximum_items: int = 100,
    ) -> list[ShadowDelta]:
        """Return currently queued Shadow deltas."""

        deltas: list[
            ShadowDelta
        ] = []

        while (
            len(
                deltas
            )
            < maximum_items
        ):
            try:
                deltas.append(
                    self._delta_queue.get_nowait()
                )

            except Empty:
                break

        return deltas

    def _subscribe_all(
        self,
    ) -> None:
        """Subscribe to all classic Shadow topics required by device."""

        qos = (
            mqtt.QoS.AT_LEAST_ONCE
        )

        subscriptions = [
            self._client.subscribe_to_shadow_delta_updated_events(
                request=(
                    iotshadow.ShadowDeltaUpdatedSubscriptionRequest(
                        thing_name=(
                            self.thing_name
                        )
                    )
                ),
                qos=qos,
                callback=self._on_delta,
            ),
            self._client.subscribe_to_get_shadow_accepted(
                request=(
                    iotshadow.GetShadowSubscriptionRequest(
                        thing_name=(
                            self.thing_name
                        )
                    )
                ),
                qos=qos,
                callback=(
                    self._on_get_accepted
                ),
            ),
            self._client.subscribe_to_get_shadow_rejected(
                request=(
                    iotshadow.GetShadowSubscriptionRequest(
                        thing_name=(
                            self.thing_name
                        )
                    )
                ),
                qos=qos,
                callback=(
                    self._on_get_rejected
                ),
            ),
            self._client.subscribe_to_update_shadow_accepted(
                request=(
                    iotshadow.UpdateShadowSubscriptionRequest(
                        thing_name=(
                            self.thing_name
                        )
                    )
                ),
                qos=qos,
                callback=(
                    self._on_update_accepted
                ),
            ),
            self._client.subscribe_to_update_shadow_rejected(
                request=(
                    iotshadow.UpdateShadowSubscriptionRequest(
                        thing_name=(
                            self.thing_name
                        )
                    )
                ),
                qos=qos,
                callback=(
                    self._on_update_rejected
                ),
            ),
        ]

        for (
            future,
            _,
        ) in subscriptions:
            future.result(
                timeout=10
            )

    def _ensure_started(
        self,
    ) -> None:
        if not self._started:
            raise RuntimeError(
                "ShadowClient.start() must be called first."
            )

    def _on_delta(
        self,
        event: iotshadow.ShadowDeltaUpdatedEvent,
    ) -> None:
        state = (
            event.state
            if isinstance(
                event.state,
                dict,
            )
            else {}
        )

        self._delta_queue.put(
            ShadowDelta(
                state=dict(
                    state
                ),
                version=(
                    event.version
                ),
            )
        )

        logger.info(
            "Device Shadow delta queued | "
            "version=%s | state=%s",
            event.version,
            state,
        )

    def _on_get_accepted(
        self,
        response: iotshadow.GetShadowResponse,
    ) -> None:
        self._resolve_pending(
            pending=(
                self._pending_get
            ),
            token=(
                response.client_token
            ),
            value=response,
        )

    def _on_get_rejected(
        self,
        response: iotshadow.ErrorResponse,
    ) -> None:
        self._resolve_pending(
            pending=(
                self._pending_get
            ),
            token=(
                response.client_token
            ),
            value=(
                ShadowOperationRejected(
                    code=(
                        response.code
                    ),
                    message=(
                        response.message
                        or "GetShadow rejected."
                    ),
                )
            ),
        )

    def _on_update_accepted(
        self,
        response: iotshadow.UpdateShadowResponse,
    ) -> None:
        self._resolve_pending(
            pending=(
                self._pending_update
            ),
            token=(
                response.client_token
            ),
            value=response,
        )

    def _on_update_rejected(
        self,
        response: iotshadow.ErrorResponse,
    ) -> None:
        self._resolve_pending(
            pending=(
                self._pending_update
            ),
            token=(
                response.client_token
            ),
            value=(
                ShadowOperationRejected(
                    code=(
                        response.code
                    ),
                    message=(
                        response.message
                        or "UpdateShadow rejected."
                    ),
                )
            ),
        )

    def _resolve_pending(
        self,
        pending: dict[
            str,
            Queue[Any],
        ],
        token: str | None,
        value: Any,
    ) -> None:
        if token is None:
            return

        with self._lock:
            response_queue = (
                pending.get(
                    token
                )
            )

        if response_queue is None:
            return

        try:
            response_queue.put_nowait(
                value
            )

        except Exception:
            logger.exception(
                "Unable to deliver Device Shadow response."
            )