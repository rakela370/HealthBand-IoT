import {
    badgeKindForStatus,
    byId,
    formatBytes,
    formatNumber,
    setText,
    showToast
} from "./utils.js";


export class DeviceHealthView {

    constructor(
        api
    ) {

        this.api =
            api;


        byId(
            "health-refresh"
        ).addEventListener(
            "click",
            () => {
                this.load();
            }
        );
    }


    async load() {

        try {

            const health =
                await this.api
                    .getHealth();

            this.render(
                health
            );

        }

        catch (error) {

            showToast(
                `Device Health: ${error.message}`
            );
        }
    }


    render(
        health
    ) {

        setText(
            "health-overall",
            health.deviceStatus
            ?? "—"
        );

        setText(
            "health-mqtt",
            health.mqttConnected
                === true
                ? "CONNECTED"
                : "DISCONNECTED"
        );

        setText(
            "health-uptime",
            this._duration(
                health.uptimeSec
            )
        );

        setText(
            "health-battery",
            health.batteryPercentage
            !== null
            && health.batteryPercentage
            !== undefined
                ? `${formatNumber(
                    health.batteryPercentage,
                    1
                )} %`
                : "—"
        );

        setText(
            "health-cpu",
            health.resources
            ?.processCpuPercentage
            !== undefined
                ? `${formatNumber(
                    health.resources
                    .processCpuPercentage,
                    1
                )} %`
                : "—"
        );

        setText(
            "health-memory",
            health.resources
            ?.processMemoryMb
            !== undefined
                ? `${formatNumber(
                    health.resources
                    .processMemoryMb,
                    1
                )} MB`
                : "—"
        );

        setText(
            "health-database",
            formatBytes(
                health
                .localDatabaseSizeBytes
            )
        );

        setText(
            "health-queue",
            health.offlineQueueSize
            ?? "—"
        );

        setText(
            "health-reconnects",
            health.reconnectAttempts
            ?? "—"
        );

        setText(
            "health-send-failures",
            health.mqttSendFailures
            ?? "—"
        );

        setText(
            "health-version",
            health.softwareVersion
            ?? "—"
        );

        setText(
            "health-last-error",
            health.lastError
            ?? "None"
        );


        this._renderSensors(
            health.sensors
            ?? {}
        );

        this._renderCapabilities(
            health.capabilities
            ?? []
        );
    }


    _renderSensors(
        sensors
    ) {

        const container =
            byId(
                "health-sensors"
            );

        container.innerHTML = "";


        for (
            const [
                name,
                status
            ]
            of Object.entries(
                sensors
            )
        ) {

            const row =
                document.createElement(
                    "div"
                );

            row.className =
                "health-list-row";


            const label =
                document.createElement(
                    "span"
                );

            label.textContent =
                name;


            const badge =
                document.createElement(
                    "span"
                );

            badge.className =
                `status-badge status-${badgeKindForStatus(status)}`;

            badge.textContent =
                status;


            row.appendChild(
                label
            );

            row.appendChild(
                badge
            );

            container.appendChild(
                row
            );
        }
    }


    _renderCapabilities(
        capabilities
    ) {

        const container =
            byId(
                "health-capabilities"
            );

        container.innerHTML = "";


        for (
            const capability
            of capabilities
        ) {

            const tag =
                document.createElement(
                    "span"
                );

            tag.className =
                "tag";

            tag.textContent =
                capability;

            container.appendChild(
                tag
            );
        }
    }


    _duration(
        seconds
    ) {

        const total =
            Number(
                seconds
            );

        if (
            !Number.isFinite(
                total
            )
        ) {
            return "—";
        }


        const hours =
            Math.floor(
                total / 3600
            );

        const minutes =
            Math.floor(
                (
                    total % 3600
                ) / 60
            );

        const remaining =
            Math.floor(
                total % 60
            );


        return (
            `${hours}h `
            + `${minutes}m `
            + `${remaining}s`
        );
    }
}