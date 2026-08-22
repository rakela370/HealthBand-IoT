"""Unit tests for MQTT message serialization."""

import pytest

from device_simulator.communication.message_serializer import (
    MessageSerializationError,
    deserialize_message,
    serialize_message,
)


def test_serializer_adds_common_envelope_fields() -> None:
    serialized = serialize_message(
        {
            "deviceId": "test-device",
            "value": 42,
        }
    )

    parsed = deserialize_message(
        serialized
    )

    assert parsed[
        "schemaVersion"
    ] == 1

    assert parsed[
        "messageId"
    ]

    assert parsed[
        "timestamp"
    ]

    assert (
        parsed["simulated"]
        is True
    )

    assert parsed[
        "value"
    ] == 42


def test_existing_message_id_is_preserved() -> None:
    serialized = serialize_message(
        {
            "messageId": "fixed-id",
            "value": 1,
        }
    )

    parsed = deserialize_message(
        serialized
    )

    assert (
        parsed["messageId"]
        == "fixed-id"
    )


def test_non_object_json_is_rejected() -> None:
    with pytest.raises(
        MessageSerializationError
    ):
        deserialize_message(
            "[1, 2, 3]"
        )