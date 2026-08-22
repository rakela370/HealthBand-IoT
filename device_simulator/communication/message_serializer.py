"""JSON serialization helpers for HealthBand MQTT messages."""

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class MessageSerializationError(ValueError):
    """Raised when an MQTT message cannot be serialized or parsed."""


def prepare_message(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Add common HealthBand envelope fields.

    Existing values are preserved.
    """

    message = dict(payload)

    message.setdefault(
        "schemaVersion",
        1,
    )

    message.setdefault(
        "messageId",
        str(uuid4()),
    )

    message.setdefault(
        "timestamp",
        datetime.now(
            timezone.utc
        ).isoformat(),
    )

    message.setdefault(
        "simulated",
        True,
    )

    return message


def serialize_message(
    payload: Mapping[str, Any],
) -> str:
    """Serialize one HealthBand MQTT payload to JSON."""

    message = prepare_message(
        payload
    )

    try:
        return json.dumps(
            message,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise MessageSerializationError(
            "Unable to serialize MQTT message."
        ) from exc


def deserialize_message(
    payload: bytes | bytearray | str,
) -> dict[str, Any]:
    """Parse one MQTT JSON payload."""

    try:
        if isinstance(
            payload,
            (bytes, bytearray),
        ):
            text = bytes(
                payload
            ).decode("utf-8")
        else:
            text = payload

        result = json.loads(
            text
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise MessageSerializationError(
            "Invalid MQTT JSON payload."
        ) from exc

    if not isinstance(
        result,
        dict,
    ):
        raise MessageSerializationError(
            "MQTT payload must contain a JSON object."
        )

    return result