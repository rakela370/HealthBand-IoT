"""AWS IoT Jobs MQTT client used by the stable HealthBand OTA supervisor."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from queue import Empty, Queue
from threading import Event, Lock
from typing import Any
from uuid import uuid4

from awscrt import mqtt

from device_simulator.communication.connection_manager import (
    ConnectionManager,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AwsJobExecution:
    """One AWS IoT Job execution returned by StartNextPendingJobExecution."""

    job_id: str
    version_number: int
    status: str
    job_document: dict[str, Any]


class AwsIotJobsClient:
    """Minimal raw-MQTT AWS IoT Jobs client for one HealthBand Thing."""

    def __init__(
        self,
        connection_manager: ConnectionManager,
        thing_name: str,
    ) -> None:
        self.connection_manager = connection_manager
        self.thing_name = thing_name

        self._executions: Queue[AwsJobExecution] = Queue()
        self._notification_event = Event()

        self._presence_lock = Lock()
        self._latest_presence: dict[str, Any] | None = None

        root = f"$aws/things/{thing_name}/jobs"

        self.notify_next_topic = f"{root}/notify-next"
        self.start_next_topic = f"{root}/start-next"
        self.start_next_accepted_topic = (
            f"{root}/start-next/accepted"
        )
        self.start_next_rejected_topic = (
            f"{root}/start-next/rejected"
        )

        self.presence_topic = (
            f"healthband/{thing_name}/presence"
        )

        self.ota_status_topic = (
            f"healthband/{thing_name}/ota/status"
        )

        self.events_topic = (
            f"healthband/{thing_name}/events"
        )

    @property
    def is_connected(self) -> bool:
        return (
            self.connection_manager
            .is_connected
        )

    def start(self) -> None:
        """Connect and subscribe to AWS IoT Jobs topics."""

        self.connection_manager.connect()

        connection = (
            self.connection_manager
            .mqtt_connection
        )

        subscriptions = (
            (
                self.notify_next_topic,
                self._on_notify_next,
            ),
            (
                self.start_next_accepted_topic,
                self._on_start_next_accepted,
            ),
            (
                self.start_next_rejected_topic,
                self._on_start_next_rejected,
            ),
            (
                self.presence_topic,
                self._on_presence,
            ),
        )

        for topic, callback in subscriptions:
            future, _ = connection.subscribe(
                topic=topic,
                qos=mqtt.QoS.AT_LEAST_ONCE,
                callback=callback,
            )

            future.result(
                timeout=10
            )

            logger.info(
                "OTA supervisor subscribed | topic=%s",
                topic,
            )

        self._notification_event.set()

    def stop(self) -> None:
        """Disconnect OTA supervisor."""

        self.connection_manager.disconnect()

    def request_next(self) -> None:
        """Request the next pending AWS IoT Job."""

        payload = {
            "clientToken": str(
                uuid4()
            ),
            "statusDetails": {
                "phase": "QUEUED",
                "progress": "0",
            },
        }

        self._publish_raw(
            self.start_next_topic,
            payload,
        )

    def drain_executions(
        self,
    ) -> list[AwsJobExecution]:
        """Return pending executions received from AWS."""

        result: list[
            AwsJobExecution
        ] = []

        while True:
            try:
                result.append(
                    self._executions
                    .get_nowait()
                )

            except Empty:
                break

        return result

    def consume_notification(
        self,
    ) -> bool:
        """Check whether AWS changed the next pending job."""

        if (
            not self
            ._notification_event
            .is_set()
        ):
            return False

        self._notification_event.clear()

        return True

    def update_execution(
        self,
        job_id: str,
        status: str,
        status_details: (
            dict[str, Any] | None
        ) = None,
    ) -> None:
        """Report AWS IoT Job execution progress."""

        normalized_details = {
            str(key): str(value)
            for key, value
            in (
                status_details
                or {}
            ).items()
        }

        payload: dict[
            str,
            Any,
        ] = {
            "status": status,
            "clientToken": str(
                uuid4()
            ),
        }

        if normalized_details:
            payload[
                "statusDetails"
            ] = (
                normalized_details
            )

        topic = (
            f"$aws/things/"
            f"{self.thing_name}/jobs/"
            f"{job_id}/update"
        )

        self._publish_raw(
            topic,
            payload,
        )

    def publish_ota_status(
        self,
        *,
        job_id: str | None,
        phase: str,
        progress_percentage: int,
        message: str,
        target_version: str | None,
        active_version: str | None,
        job_status: str,
        self_test: str = "NOT_RUN",
        rollback_performed: bool = False,
    ) -> None:
        """Publish browser-friendly OTA status."""

        payload = {
            "schemaVersion": 1,
            "messageId": str(
                uuid4()
            ),
            "deviceId": (
                self.thing_name
            ),
            "jobId": job_id,
            "phase": phase,
            "progressPercentage": max(
                0,
                min(
                    100,
                    int(
                        progress_percentage
                    ),
                ),
            ),
            "message": message,
            "targetVersion": (
                target_version
            ),
            "activeVersion": (
                active_version
            ),
            "jobStatus": (
                job_status
            ),
            "selfTest": (
                self_test
            ),
            "rollbackPerformed": bool(
                rollback_performed
            ),
            "timestamp": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "simulated": True,
        }

        self._publish_raw(
            self.ota_status_topic,
            payload,
        )

    def publish_device_state_event(
        self,
        *,
        previous_state: str,
        current_state: str,
        reason: str,
    ) -> None:
        """Publish state transition while replacing a release."""

        payload = {
            "schemaVersion": 1,
            "messageId": str(
                uuid4()
            ),
            "deviceId": (
                self.thing_name
            ),
            "eventType": (
                "DEVICE_STATE_CHANGED"
            ),
            "previousState": (
                previous_state
            ),
            "currentState": (
                current_state
            ),
            "reason": reason,
            "timestamp": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "simulated": True,
        }

        self._publish_raw(
            self.events_topic,
            payload,
        )

    def clear_presence(
        self,
    ) -> None:
        """Remove stale presence before release restart."""

        with self._presence_lock:
            self._latest_presence = None

    def latest_presence(
        self,
    ) -> dict[str, Any] | None:
        """Return most recent device presence."""

        with self._presence_lock:
            if (
                self._latest_presence
                is None
            ):
                return None

            return dict(
                self._latest_presence
            )

    @staticmethod
    def parse_start_next_response(
        data: dict[str, Any],
    ) -> AwsJobExecution | None:
        """Parse StartNextPendingJobExecution response."""

        execution = data.get(
            "execution"
        )

        if execution is None:
            return None

        if not isinstance(
            execution,
            dict,
        ):
            raise ValueError(
                "AWS Jobs execution "
                "must be a JSON object."
            )

        job_id = str(
            execution.get(
                "jobId",
                "",
            )
        ).strip()

        status = str(
            execution.get(
                "status",
                "",
            )
        ).strip()

        job_document = (
            execution.get(
                "jobDocument"
            )
        )

        if not job_id:
            raise ValueError(
                "AWS Jobs execution "
                "does not contain jobId."
            )

        if not isinstance(
            job_document,
            dict,
        ):
            raise ValueError(
                "AWS Jobs execution "
                "does not contain jobDocument."
            )

        try:
            version_number = int(
                execution.get(
                    "versionNumber",
                    0,
                )
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "AWS Jobs versionNumber "
                "must be an integer."
            ) from exc

        return AwsJobExecution(
            job_id=job_id,
            version_number=(
                version_number
            ),
            status=status,
            job_document=dict(
                job_document
            ),
        )

    def _on_notify_next(
        self,
        topic: str,
        payload: bytes,
        **kwargs: Any,
    ) -> None:
        del topic
        del payload
        del kwargs

        self._notification_event.set()

    def _on_start_next_accepted(
        self,
        topic: str,
        payload: bytes,
        **kwargs: Any,
    ) -> None:
        del topic
        del kwargs

        try:
            data = (
                self._decode_object(
                    payload
                )
            )

            execution = (
                self
                .parse_start_next_response(
                    data
                )
            )

            if execution is not None:
                self._executions.put(
                    execution
                )

        except Exception:
            logger.exception(
                "Unable to parse AWS IoT "
                "Jobs start-next response."
            )

    def _on_start_next_rejected(
        self,
        topic: str,
        payload: bytes,
        **kwargs: Any,
    ) -> None:
        del topic
        del kwargs

        try:
            data = (
                self._decode_object(
                    payload
                )
            )

        except Exception:
            logger.exception(
                "Malformed AWS IoT Jobs "
                "rejected response."
            )

            return

        logger.error(
            "AWS IoT Jobs start-next rejected: %s",
            data,
        )

    def _on_presence(
        self,
        topic: str,
        payload: bytes,
        **kwargs: Any,
    ) -> None:
        del topic
        del kwargs

        try:
            data = (
                self._decode_object(
                    payload
                )
            )

        except Exception:
            logger.exception(
                "Malformed HealthBand "
                "presence payload."
            )

            return

        with self._presence_lock:
            self._latest_presence = (
                data
            )

    def _publish_raw(
        self,
        topic: str,
        payload: dict[str, Any],
    ) -> None:
        if (
            not self
            .connection_manager
            .is_connected
        ):
            raise RuntimeError(
                "OTA supervisor is not "
                "connected to AWS IoT Core."
            )

        future, _ = (
            self.connection_manager
            .mqtt_connection
            .publish(
                topic=topic,
                payload=json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(
                        ",",
                        ":",
                    ),
                ),
                qos=(
                    mqtt.QoS
                    .AT_LEAST_ONCE
                ),
            )
        )

        future.result(
            timeout=10
        )

    @staticmethod
    def _decode_object(
        payload: bytes,
    ) -> dict[str, Any]:
        decoded = json.loads(
            payload.decode(
                "utf-8"
            )
        )

        if not isinstance(
            decoded,
            dict,
        ):
            raise ValueError(
                "MQTT payload must "
                "be a JSON object."
            )

        return decoded