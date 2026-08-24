"""Execution and deduplication of HealthBand commands."""

from collections import OrderedDict
from dataclasses import replace
from datetime import datetime, timezone

from device_simulator.commands.command import (
    Command,
    CommandResult,
    CommandStatus,
)
from device_simulator.commands.command_registry import (
    CommandRegistry,
)


class CommandHandler:
    """Execute validated commands exactly once."""

    def __init__(
        self,
        registry: CommandRegistry,
        maximum_recent_commands: int = 100,
    ) -> None:
        if maximum_recent_commands <= 0:
            raise ValueError(
                "maximum_recent_commands "
                "must be positive."
            )

        self.registry = (
            registry
        )

        self.maximum_recent_commands = (
            maximum_recent_commands
        )

        self._recent: OrderedDict[
            str,
            CommandResult,
        ] = OrderedDict()

    def get_cached_result(
        self,
        command_id: str,
    ) -> CommandResult | None:
        """Return previous result for an already processed command."""

        previous = (
            self._recent.get(
                command_id
            )
        )

        if previous is None:
            return None

        self._recent.move_to_end(
            command_id
        )

        return replace(
            previous,
            duplicate=True,
            timestamp=datetime.now(
                timezone.utc
            ),
        )

    async def execute(
        self,
        command: Command,
    ) -> CommandResult:
        """Execute command once and remember its final result."""

        previous = (
            self.get_cached_result(
                command.command_id
            )
        )

        if previous is not None:
            return previous

        try:
            message, details = (
                await self.registry.execute(
                    command
                )
            )

            result = CommandResult(
                command_id=(
                    command.command_id
                ),
                device_id=(
                    command.device_id
                ),
                command_type=(
                    command.type.value
                ),
                status=(
                    CommandStatus.SUCCEEDED
                ),
                message=message,
                details=details,
                timestamp=datetime.now(
                    timezone.utc
                ),
            )

        except Exception as exc:
            result = CommandResult(
                command_id=(
                    command.command_id
                ),
                device_id=(
                    command.device_id
                ),
                command_type=(
                    command.type.value
                ),
                status=(
                    CommandStatus.FAILED
                ),
                message=str(
                    exc
                ),
                error_code=(
                    "COMMAND_EXECUTION_FAILED"
                ),
                timestamp=datetime.now(
                    timezone.utc
                ),
            )

        self._recent[
            command.command_id
        ] = result

        while (
            len(
                self._recent
            )
            > self.maximum_recent_commands
        ):
            self._recent.popitem(
                last=False
            )

        return result