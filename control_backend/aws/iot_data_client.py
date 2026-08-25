"""AWS IoT Data Plane operations used for commands."""

import json
from datetime import datetime, timezone
from typing import Any


class IotDataClient:
    """Publish one-shot commands to HealthBand through AWS IoT Core."""

    def __init__(
        self,
        boto3_client: Any,
    ) -> None:
        self._client = (
            boto3_client
        )

    def publish_command(
        self,
        device_id: str,
        command_id: str,
        command_type: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Publish command request using QoS 1."""

        payload = {
            "schemaVersion": 1,
            "commandId": (
                command_id
            ),
            "deviceId": (
                device_id
            ),
            "type": (
                command_type
            ),
            "parameters": (
                parameters
            ),
            "requestedAt": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }

        topic = (
            f"healthband/{device_id}/commands/request"
        )

        self._client.publish(
            topic=topic,
            qos=1,
            payload=(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode(
                    "utf-8"
                )
            ),
        )

        return payload