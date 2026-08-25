"""Device Shadow operations for the HealthBand backend."""

import json
from typing import Any


class ShadowService:
    """Read and update HealthBand classic Device Shadow."""

    def __init__(
        self,
        boto3_client: Any,
    ) -> None:
        self._client = (
            boto3_client
        )

    def get_shadow(
        self,
        device_id: str,
    ) -> dict[str, Any]:
        """Retrieve complete classic Shadow document."""

        response = (
            self._client
            .get_thing_shadow(
                thingName=(
                    device_id
                )
            )
        )

        raw = (
            response[
                "payload"
            ].read()
        )

        return json.loads(
            raw.decode(
                "utf-8"
            )
        )

    def update_desired(
        self,
        device_id: str,
        desired: dict[str, Any],
    ) -> dict[str, Any]:
        """Update only the desired part of classic Shadow."""

        request = {
            "state": {
                "desired": (
                    desired
                )
            }
        }

        response = (
            self._client
            .update_thing_shadow(
                thingName=(
                    device_id
                ),
                payload=(
                    json.dumps(
                        request,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode(
                        "utf-8"
                    )
                ),
            )
        )

        raw = (
            response[
                "payload"
            ].read()
        )

        return json.loads(
            raw.decode(
                "utf-8"
            )
        )