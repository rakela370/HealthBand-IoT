"""Regression tests for Event Log command history support."""

from pathlib import Path

from control_backend.aws.dynamodb_service import (
    DynamoDbService,
)


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


def test_dynamodb_service_queries_command_responses() -> None:
    service = object.__new__(
        DynamoDbService
    )

    captured: dict[
        str,
        object,
    ] = {}

    def fake_query_events(
        device_id: str,
        start_iso: str,
        end_iso: str,
        record_type: str,
        limit: int,
    ) -> list[dict]:
        captured[
            "device_id"
        ] = device_id

        captured[
            "record_type"
        ] = record_type

        captured[
            "limit"
        ] = limit

        return []

    service._query_events = (  # type: ignore[method-assign]
        fake_query_events
    )

    result = (
        service
        .get_command_responses(
            device_id="device-1",
            start_iso=(
                "2026-08-26T00:00:00+00:00"
            ),
            end_iso=(
                "2026-08-27T00:00:00+00:00"
            ),
            limit=123,
        )
    )

    assert result == []

    assert (
        captured[
            "device_id"
        ]
        == "device-1"
    )

    assert (
        captured[
            "record_type"
        ]
        == "COMMAND_RESPONSE"
    )

    assert (
        captured[
            "limit"
        ]
        == 123
    )


def test_frontend_event_log_loads_command_history() -> None:
    api_source = (
        ROOT
        / "web_frontend"
        / "js"
        / "api.js"
    ).read_text(
        encoding="utf-8"
    )

    event_log_source = (
        ROOT
        / "web_frontend"
        / "js"
        / "event_log.js"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "getCommandResponses"
        in api_source
    )

    assert (
        "getCommandResponses"
        in event_log_source
    )

    assert (
        "COMMAND_RESPONSE"
        in event_log_source
    )