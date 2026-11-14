export class ApiClient {

    constructor({
        baseUrl =
            "http://127.0.0.1:8000",

        deviceId =
            "healthband-device-001"
    } = {}) {

        this.baseUrl =
            baseUrl.replace(
                /\/$/,
                ""
            );

        this.deviceId =
            deviceId;
    }


    async request(
        path,
        options = {}
    ) {

        const controller =
            new AbortController();

        const timeout =
            window.setTimeout(
                () => {
                    controller.abort();
                },
                15000
            );

        try {

            const response =
                await fetch(
                    `${this.baseUrl}${path}`,
                    {
                        ...options,

                        headers: {
                            "Content-Type":
                                "application/json",

                            ...(
                                options.headers
                                ?? {}
                            )
                        },

                        signal:
                            controller.signal
                    }
                );

            const contentType =
                response.headers.get(
                    "content-type"
                ) ?? "";

            let body = null;

            if (
                contentType.includes(
                    "application/json"
                )
            ) {
                body =
                    await response.json();
            }

            else {
                body =
                    await response.text();
            }

            if (!response.ok) {

                const detail =
                    body?.detail
                    ?? body
                    ?? response.statusText;

                throw new Error(
                    String(
                        detail
                    )
                );
            }

            return body;
        }

        finally {

            window.clearTimeout(
                timeout
            );
        }
    }


    getBackendHealth() {

        return this.request(
            "/api/backend/health"
        );
    }


    getDevice() {

        return this.request(
            `/api/devices/${this.deviceId}`
        );
    }


    getState() {

        return this.request(
            `/api/devices/${this.deviceId}/state`
        );
    }


    getHealth() {

        return this.request(
            `/api/devices/${this.deviceId}/health`
        );
    }


    getConfiguration() {

        return this.request(
            `/api/devices/${this.deviceId}/configuration`
        );
    }


    updateConfiguration(
        desired
    ) {

        return this.request(
            `/api/devices/${this.deviceId}/configuration`,
            {
                method: "PUT",

                body:
                    JSON.stringify(
                        desired
                    )
            }
        );
    }


    sendCommand(
        type,
        parameters = {}
    ) {

        return this.request(
            `/api/devices/${this.deviceId}/commands`,
            {
                method: "POST",

                body:
                    JSON.stringify(
                        {
                            type,
                            parameters
                        }
                    )
            }
        );
    }


    getCommand(
        commandId
    ) {

        return this.request(
            `/api/devices/${this.deviceId}/commands/${commandId}`
        );
    }


    getHistorySeries(
        period = "1h"
    ) {

        return this.request(
            `/api/devices/${this.deviceId}/history-series?period=${encodeURIComponent(period)}`
        );
    }


    getTelemetry(
        period = "1h"
    ) {

        return this.request(
            `/api/devices/${this.deviceId}/telemetry?period=${encodeURIComponent(period)}`
        );
    }


    getAnalytics(
        period = "30d"
    ) {

        return this.request(
            `/api/devices/${this.deviceId}/analytics?period=${encodeURIComponent(period)}`
        );
    }


    getAlerts(
        period = "24h"
    ) {

        return this.request(
            `/api/devices/${this.deviceId}/alerts?period=${encodeURIComponent(period)}`
        );
    }


    getEvents(
        period = "24h"
    ) {

        return this.request(
            `/api/devices/${this.deviceId}/events?period=${encodeURIComponent(period)}`
        );
    }


    getCommandResponses(
        period = "24h"
    ) {

        return this.request(
            `/api/devices/${this.deviceId}/command-responses?period=${encodeURIComponent(period)}`
        );
    }


    getReleases() {

        return this.request(
            "/api/releases"
        );
    }


    getOtaState() {

        return this.request(
            `/api/devices/${this.deviceId}/ota`
        );
    }


    startOta(
        targetVersion,
        force = false
    ) {

        return this.request(
            `/api/devices/${this.deviceId}/ota`,
            {
                method: "POST",

                body:
                    JSON.stringify(
                        {
                            targetVersion,
                            force
                        }
                    )
            }
        );
    }


    websocketUrl() {

        const wsBase =
            this.baseUrl
            .replace(
                /^http:/,
                "ws:"
            )
            .replace(
                /^https:/,
                "wss:"
            );

        return (
            `${wsBase}/ws/devices/${this.deviceId}`
        );
    }
}