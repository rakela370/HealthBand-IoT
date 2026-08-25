"""Tests for backend AWS IoT Data operations."""

import json
from typing import Any

from control_backend.aws.iot_data_client import (
    IotDataClient,
)
from control_backend.aws.shadow_service import (
    ShadowService,
)


class FakeStreamingBody:
    """Small boto3 StreamingBody replacement."""

    def __init__(
        self,
        payload: dict[str, Any],
    ) -> None:
        self.payload = (
            payload
        )

    def read(
        self,
    ) -> bytes:
        return (
            json.dumps(
                self.payload
            ).encode(
                "utf-8"
            )
        )


class FakeIotDataClient:
    """In-memory IoT Data Plane fake."""

    def __init__(
        self,
    ) -> None:
        self.publish_calls: list[
            dict[str, Any]
        ] = []

        self.shadow_updates: list[
            dict[str, Any]
        ] = []

    def publish(
        self,
        **kwargs: Any,
    ) -> None:
        self.publish_calls.append(
            kwargs
        )

    def update_thing_shadow(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.shadow_updates.append(
            kwargs
        )

        return {
            "payload": FakeStreamingBody(
                {
                    "state": {
                        "desired": {
                            "measurementIntervalSec": 4
                        }
                    }
                }
            )
        }


def test_command_is_published_to_correct_topic() -> None:
    fake = (
        FakeIotDataClient()
    )

    client = (
        IotDataClient(
            fake
        )
    )

    client.publish_command(
        device_id=(
            "healthband-device-001"
        ),
        command_id="cmd-1",
        command_type=(
            "REQUEST_DEVICE_HEALTH"
        ),
        parameters={},
    )

    call = (
        fake.publish_calls[0]
    )

    assert (
        call[
            "topic"
        ]
        == (
            "healthband/"
            "healthband-device-001/"
            "commands/request"
        )
    )

    assert (
        call[
            "qos"
        ]
        == 1
    )


def test_shadow_update_writes_desired_state() -> None:
    fake = (
        FakeIotDataClient()
    )

    service = (
        ShadowService(
            fake
        )
    )

    service.update_desired(
        "healthband-device-001",
        {
            "measurementIntervalSec": 4
        },
    )

    raw_payload = (
        fake.shadow_updates[0][
            "payload"
        ]
    )

    decoded = (
        json.loads(
            raw_payload.decode(
                "utf-8"
            )
        )
    )

    assert (
        decoded[
            "state"
        ][
            "desired"
        ][
            "measurementIntervalSec"
        ]
        == 4
    )