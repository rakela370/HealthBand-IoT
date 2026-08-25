"""Tests for realtime backend state cache."""

import pytest

from control_backend.services.realtime_state_store import (
    RealtimeStateStore,
)


@pytest.mark.asyncio
async def test_latest_telemetry_is_stored() -> None:
    store = (
        RealtimeStateStore()
    )

    await store.update(
        "device-1",
        "telemetry",
        {
            "heartRateBpm": 80
        },
    )

    telemetry = (
        await store.get_latest(
            "device-1",
            "telemetry",
        )
    )

    assert (
        telemetry is not None
    )

    assert (
        telemetry[
            "heartRateBpm"
        ]
        == 80
    )


@pytest.mark.asyncio
async def test_command_response_is_indexed_by_command_id() -> None:
    store = (
        RealtimeStateStore()
    )

    await store.update(
        "device-1",
        "command_response",
        {
            "commandId": "cmd-1",
            "status": "SUCCEEDED",
        },
    )

    result = (
        await store.get_command(
            "device-1",
            "cmd-1",
        )
    )

    assert (
        result is not None
    )

    assert (
        result[
            "status"
        ]
        == "SUCCEEDED"
    )


@pytest.mark.asyncio
async def test_unknown_device_returns_empty_snapshot() -> None:
    store = (
        RealtimeStateStore()
    )

    snapshot = (
        await store.snapshot(
            "missing-device"
        )
    )

    assert snapshot == {}