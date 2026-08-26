import {
    badgeKindForStatus,
    byId,
    formatTime,
    showToast
} from "./utils.js";


const SENSOR_COMMANDS =
    new Set(
        [
            "CALIBRATE_SENSOR",
            "SIMULATE_SENSOR_FAILURE",
            "RESTORE_SENSOR"
        ]
    );


export class CommandsView {

    constructor(
        api
    ) {

        this.api =
            api;

        this.commands =
            new Map();

        this.typeSelect =
            byId(
                "command-type"
            );

        this.form =
            byId(
                "command-form"
            );


        this.typeSelect
            .addEventListener(
                "change",
                () => {
                    this._renderParameters();
                }
            );


        this.form
            .addEventListener(
                "submit",
                event => {

                    event.preventDefault();

                    this.send();
                }
            );


        this._renderParameters();
    }


    async send() {

        const type =
            this.typeSelect.value;

        const parameters =
            this._parametersFor(
                type
            );


        const message =
            byId(
                "command-form-message"
            );

        message.textContent =
            "Publishing command...";


        try {

            const response =
                await this.api
                    .sendCommand(
                        type,
                        parameters
                    );


            const commandId =
                response.commandId;


            this.commands.set(
                commandId,
                {
                    commandId,
                    type,
                    parameters,
                    timestamp:
                        response.request
                        ?.requestedAt
                        ?? new Date()
                            .toISOString(),

                    status:
                        "PUBLISHED",

                    message:
                        "Command published to AWS IoT Core."
                }
            );


            this.render();

            message.textContent =
                `Command sent: ${commandId}`;

            showToast(
                `${type} published.`
            );

        }

        catch (error) {

            message.textContent =
                `Error: ${error.message}`;

            showToast(
                `Command failed: ${error.message}`
            );
        }
    }


    handleRealtimeResult(
        payload
    ) {

        const commandId =
            payload.commandId;

        if (!commandId) {
            return;
        }


        const previous =
            this.commands.get(
                commandId
            )
            ?? {
                commandId,

                type:
                    payload.type
                    ?? "UNKNOWN",

                parameters: {},

                timestamp:
                    payload.timestamp
                    ?? new Date()
                        .toISOString()
            };


        this.commands.set(
            commandId,
            {
                ...previous,

                type:
                    payload.type
                    ?? previous.type,

                status:
                    payload.status
                    ?? previous.status,

                message:
                    payload.message
                    ?? previous.message,

                details:
                    payload.details,

                errorCode:
                    payload.errorCode,

                timestamp:
                    payload.timestamp
                    ?? previous.timestamp
            }
        );


        this.render();
    }


    render() {

        const body =
            byId(
                "command-table-body"
            );

        body.innerHTML = "";


        const commands =
            Array.from(
                this.commands.values()
            )
            .sort(
                (
                    left,
                    right
                ) =>
                    new Date(
                        right.timestamp
                    )
                    -
                    new Date(
                        left.timestamp
                    )
            )
            .slice(
                0,
                20
            );


        if (!commands.length) {

            const row =
                document.createElement(
                    "tr"
                );

            const cell =
                document.createElement(
                    "td"
                );

            cell.colSpan = 5;

            cell.className =
                "empty-cell";

            cell.textContent =
                "Još nema poslatih komandi.";

            row.appendChild(
                cell
            );

            body.appendChild(
                row
            );

            return;
        }


        for (
            const command
            of commands
        ) {

            const row =
                document.createElement(
                    "tr"
                );


            row.appendChild(
                this._cell(
                    command.type
                )
            );


            const idCell =
                this._cell(
                    command.commandId
                );

            idCell.title =
                command.commandId;

            row.appendChild(
                idCell
            );


            row.appendChild(
                this._cell(
                    formatTime(
                        command.timestamp
                    )
                )
            );


            const statusCell =
                document.createElement(
                    "td"
                );

            const badge =
                document.createElement(
                    "span"
                );

            badge.className =
                `status-badge status-${badgeKindForStatus(command.status)}`;

            badge.textContent =
                command.status
                ?? "UNKNOWN";

            statusCell.appendChild(
                badge
            );

            row.appendChild(
                statusCell
            );


            const result =
                command.message
                ?? command.errorCode
                ?? "—";

            row.appendChild(
                this._cell(
                    result
                )
            );


            body.appendChild(
                row
            );
        }
    }


    _renderParameters() {

        const type =
            this.typeSelect.value;


        byId(
            "scenario-parameter"
        ).classList.toggle(
            "hidden",
            type
            !== "CHANGE_SIMULATION_SCENARIO"
        );


        byId(
            "sensor-parameter"
        ).classList.toggle(
            "hidden",
            !SENSOR_COMMANDS.has(
                type
            )
        );


        byId(
            "outage-parameter"
        ).classList.toggle(
            "hidden",
            type
            !== "SIMULATE_NETWORK_OUTAGE"
        );
    }


    _parametersFor(
        type
    ) {

        if (
            type
            === "CHANGE_SIMULATION_SCENARIO"
        ) {

            return {
                scenario:
                    byId(
                        "command-scenario"
                    ).value
            };
        }


        if (
            SENSOR_COMMANDS.has(
                type
            )
        ) {

            return {
                sensorName:
                    byId(
                        "command-sensor"
                    ).value
            };
        }


        if (
            type
            === "SIMULATE_NETWORK_OUTAGE"
        ) {

            return {
                durationSec:
                    Number(
                        byId(
                            "command-outage-duration"
                        ).value
                    )
            };
        }


        return {};
    }


    _cell(
        value
    ) {

        const cell =
            document.createElement(
                "td"
            );

        cell.textContent =
            String(
                value
                ?? "—"
            );

        return cell;
    }
}