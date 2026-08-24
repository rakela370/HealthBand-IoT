"""Registry that maps HealthBand commands to executors."""

from collections.abc import Awaitable, Callable
from typing import Any

from device_simulator.commands.command import (
    Command,
    CommandType,
)


CommandExecutor = Callable[
    [
        Command,
    ],
    Awaitable[
        tuple[
            str,
            dict[str, Any],
        ]
    ],
]


class CommandRegistry:
    """Register and dispatch command executors."""

    def __init__(
        self,
    ) -> None:
        self._executors: dict[
            CommandType,
            CommandExecutor,
        ] = {}

    def register(
        self,
        command_type: CommandType,
        executor: CommandExecutor,
    ) -> None:
        """Register one command executor."""

        if (
            command_type
            in self._executors
        ):
            raise ValueError(
                f"Executor already registered "
                f"for {command_type.value}."
            )

        self._executors[
            command_type
        ] = executor

    async def execute(
        self,
        command: Command,
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        """Execute one registered command."""

        executor = (
            self._executors.get(
                command.type
            )
        )

        if executor is None:
            raise RuntimeError(
                "No executor registered for "
                f"{command.type.value}."
            )

        return await executor(
            command
        )