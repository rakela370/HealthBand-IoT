"""Tests for command execution and deduplication."""

from datetime import datetime, timezone

import pytest

from device_simulator.commands.command import (
    Command,
    CommandStatus,
    CommandType,
)
from device_simulator.commands.command_handler import (
    CommandHandler,
)
from device_simulator.commands.command_registry import (
    CommandRegistry,
)


@pytest.mark.asyncio
async def test_duplicate_command_is_not_executed_twice() -> None:
    registry = CommandRegistry()

    executions = 0

    async def executor(
        command: Command,
    ) -> tuple[
        str,
        dict[str, object],
    ]:
        nonlocal executions

        del command

        executions += 1

        return (
            "Done.",
            {
                "executions": executions
            },
        )

    registry.register(
        CommandType.CLEAR_ALERTS,
        executor,
    )

    handler = CommandHandler(
        registry
    )

    command = Command(
        command_id="duplicate-1",
        device_id="test-device",
        type=CommandType.CLEAR_ALERTS,
        parameters={},
        received_at=datetime.now(
            timezone.utc
        ),
    )

    first = (
        await handler.execute(
            command
        )
    )

    second = (
        await handler.execute(
            command
        )
    )

    assert (
        first.status
        == CommandStatus.SUCCEEDED
    )

    assert (
        second.status
        == CommandStatus.SUCCEEDED
    )

    assert second.duplicate is True

    assert executions == 1


@pytest.mark.asyncio
async def test_executor_exception_returns_failed_result() -> None:
    registry = CommandRegistry()

    async def executor(
        command: Command,
    ) -> tuple[
        str,
        dict[str, object],
    ]:
        del command

        raise RuntimeError(
            "Expected test failure."
        )

    registry.register(
        CommandType.CLEAR_ALERTS,
        executor,
    )

    handler = CommandHandler(
        registry
    )

    command = Command(
        command_id="fail-1",
        device_id="test-device",
        type=CommandType.CLEAR_ALERTS,
        parameters={},
        received_at=datetime.now(
            timezone.utc
        ),
    )

    result = (
        await handler.execute(
            command
        )
    )

    assert (
        result.status
        == CommandStatus.FAILED
    )