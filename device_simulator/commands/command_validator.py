"""Validation of MQTT commands received by HealthBand."""

from datetime import datetime, timezone
from typing import Any

from device_simulator.commands.command import (
    Command,
    CommandType,
)
from device_simulator.simulation.scenario import (
    SimulationScenario,
)


class CommandValidationError(ValueError):
    """Raised when an incoming command is invalid."""


class CommandValidator:
    """Parse and validate incoming command payloads."""

    _SENSORS = {
        "heart_rate",
        "skin_temperature",
        "step_counter",
        "battery",
        "spo2",
    }

    def __init__(
        self,
        device_id: str,
    ) -> None:
        self.device_id = (
            device_id
        )

    def validate(
        self,
        payload: dict[str, Any],
    ) -> Command:
        """Validate one incoming MQTT command."""

        if not isinstance(
            payload,
            dict,
        ):
            raise CommandValidationError(
                "Command payload must be an object."
            )

        schema_version = (
            payload.get(
                "schemaVersion",
                1,
            )
        )

        if schema_version != 1:
            raise CommandValidationError(
                "Unsupported command schemaVersion."
            )

        command_id = (
            payload.get(
                "commandId"
            )
        )

        if (
            not isinstance(
                command_id,
                str,
            )
            or not command_id.strip()
        ):
            raise CommandValidationError(
                "commandId is required."
            )

        incoming_device_id = (
            payload.get(
                "deviceId"
            )
        )

        if (
            incoming_device_id
            is not None
            and incoming_device_id
            != self.device_id
        ):
            raise CommandValidationError(
                "Command targets another device."
            )

        type_value = (
            payload.get(
                "type"
            )
        )

        if type_value is None:
            type_value = (
                payload.get(
                    "command"
                )
            )

        try:
            command_type = (
                CommandType(
                    type_value
                )
            )

        except (
            ValueError,
            TypeError,
        ) as exc:
            raise CommandValidationError(
                f"Unknown command type: {type_value!r}"
            ) from exc

        parameters = (
            payload.get(
                "parameters",
                {},
            )
        )

        if not isinstance(
            parameters,
            dict,
        ):
            raise CommandValidationError(
                "parameters must be an object."
            )

        self._validate_parameters(
            command_type,
            parameters,
        )

        return Command(
            command_id=(
                command_id.strip()
            ),
            device_id=(
                self.device_id
            ),
            type=(
                command_type
            ),
            parameters=dict(
                parameters
            ),
            received_at=(
                datetime.now(
                    timezone.utc
                )
            ),
        )

    def _validate_parameters(
        self,
        command_type: CommandType,
        parameters: dict[str, Any],
    ) -> None:
        """Validate command-specific parameters."""

        if (
            command_type
            == CommandType.CHANGE_SIMULATION_SCENARIO
        ):
            scenario = (
                parameters.get(
                    "scenario"
                )
            )

            try:
                SimulationScenario(
                    scenario
                )

            except (
                ValueError,
                TypeError,
            ) as exc:
                raise CommandValidationError(
                    "CHANGE_SIMULATION_SCENARIO "
                    "requires a valid 'scenario'."
                ) from exc

        if command_type in {
            CommandType.CALIBRATE_SENSOR,
            CommandType.SIMULATE_SENSOR_FAILURE,
            CommandType.RESTORE_SENSOR,
        }:
            sensor_name = (
                parameters.get(
                    "sensorName"
                )
            )

            if sensor_name not in self._SENSORS:
                raise CommandValidationError(
                    "A valid 'sensorName' is required. "
                    "Allowed values: "
                    + ", ".join(
                        sorted(
                            self._SENSORS
                        )
                    )
                )

        if (
            command_type
            == CommandType.SIMULATE_NETWORK_OUTAGE
        ):
            duration = (
                parameters.get(
                    "durationSec",
                    15,
                )
            )

            if (
                isinstance(
                    duration,
                    bool,
                )
                or not isinstance(
                    duration,
                    (int, float),
                )
            ):
                raise CommandValidationError(
                    "durationSec must be numeric."
                )

            numeric_duration = float(
                duration
            )

            if not (
                5.0
                <= numeric_duration
                <= 300.0
            ):
                raise CommandValidationError(
                    "durationSec must be between "
                    "5 and 300 seconds."
                )