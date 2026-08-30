import {
    badgeKindForStatus,
    byId,
    formatNumber,
    formatTime,
    setBadge,
    setText
} from "./utils.js";


export class DashboardView {

    constructor(
        api
    ) {

        this.api =
            api;

        this.previous = {};

        this.latestTelemetry =
            null;

        this.latestHealth =
            null;
    }


    async load() {

        const device =
            await this.api.getDevice();

        this.updateDevice(
            device
        );

        if (
            device.latestTelemetry
        ) {
            this.updateTelemetry(
                device.latestTelemetry
            );
        }

        if (
            device.latestHealth
        ) {
            this.updateHealth(
                device.latestHealth
            );
        }

        if (
            device.latestAlert
        ) {
            this.updateAlert(
                device.latestAlert
            );
        }
    }


    updateDevice(
        device
    ) {

        setText(
            "dashboard-device-state",
            device.deviceState
            ?? "UNKNOWN"
        );

        setText(
            "dashboard-software-version",
            device.softwareVersion
            ?? "—"
        );

        setText(
            "dashboard-scenario",
            device.scenario
            ?? "—"
        );

        setText(
            "dashboard-mqtt",
            device.mqttConnected
                === true
                ? "CONNECTED"
                : (
                    device.mqttConnected
                        === false
                        ? "DISCONNECTED"
                        : "UNKNOWN"
                )
        );

        this.setOnline(
            Boolean(
                device.online
            )
        );
    }


    updateTelemetry(
        telemetry
    ) {

        this.latestTelemetry =
            telemetry;

        const measurements =
            telemetry.measurements
            ?? {};

        const statuses =
            telemetry.sensorStatus
            ?? {};

        const timestamp =
            telemetry.timestamp;

        setText(
            "dashboard-last-update",
            `Last telemetry: ${formatTime(timestamp)}`
        );

        setText(
            "dashboard-device-state",
            telemetry.deviceState
            ?? "—"
        );

        setText(
            "dashboard-software-version",
            telemetry.softwareVersion
            ?? "—"
        );

        setText(
            "dashboard-scenario",
            telemetry.scenario
            ?? "—"
        );

        const activity =
            telemetry.activityLevel
            ?? measurements.activityLevel
            ?? "—";

        setText(
            "dashboard-activity",
            activity
        );

        setText(
            "dashboard-activity-description",
            this._activityDescription(
                telemetry.scenario,
                activity
            )
        );


        this._renderSensor({
            prefix: "heart",
            cardId:
                "sensor-heart-card",

            value:
                measurements
                .heartRateBpm,

            previousKey:
                "heartRate",

            decimals: 0,

            status:
                statuses.heart_rate
                ?? statuses.heartRate
                ?? "UNKNOWN",

            timestamp,

            tolerance: 1
        });


        this._renderSensor({
            prefix:
                "temperature",

            cardId:
                "sensor-temperature-card",

            value:
                measurements
                .skinTemperature,

            previousKey:
                "temperature",

            decimals: 2,

            status:
                statuses.skin_temperature
                ?? statuses.skinTemperature
                ?? "UNKNOWN",

            timestamp,

            tolerance: 0.03
        });


        setText(
            "sensor-temperature-unit",
            measurements.temperatureUnit
                === "FAHRENHEIT"
                ? "°F"
                : (
                    measurements
                    .temperatureUnit
                    === "CELSIUS"
                        ? "°C"
                        : "—"
                )
        );


        this._renderSensor({
            prefix: "steps",
            cardId:
                "sensor-steps-card",

            value:
                measurements
                .totalDailySteps,

            previousKey:
                "steps",

            decimals: 0,

            status:
                statuses.step_counter
                ?? statuses.stepCounter
                ?? "UNKNOWN",

            timestamp,

            tolerance: 0
        });


        this._renderSensor({
            prefix: "battery",
            cardId:
                "sensor-battery-card",

            value:
                measurements
                .batteryPercentage,

            previousKey:
                "battery",

            decimals: 1,

            status:
                statuses.battery
                ?? "UNKNOWN",

            timestamp,

            tolerance: 0.02
        });


        const spo2 =
            measurements
            .oxygenSaturationPercentage;

        const spo2Status =
            statuses.spo2;

        if (
            spo2 !== undefined
            || spo2Status !== undefined
        ) {

            byId(
                "sensor-spo2-card"
            )?.classList.remove(
                "hidden"
            );

            this._renderSensor({
                prefix: "spo2",
                cardId:
                    "sensor-spo2-card",

                value: spo2,

                previousKey:
                    "spo2",

                decimals: 1,

                status:
                    spo2Status
                    ?? "UNKNOWN",

                timestamp,

                tolerance: 0.1
            });
        }


        const caloriesToday =
            measurements
            .caloriesBurnedToday;

        if (
            caloriesToday !== undefined
            && caloriesToday !== null
        ) {

            byId(
                "sensor-calories-card"
            )?.classList.remove(
                "hidden"
            );

            this._renderSensor({
                prefix: "calories",
                cardId:
                    "sensor-calories-card",

                value:
                    caloriesToday,

                previousKey:
                    "calories",

                decimals: 2,

                status:
                    "ESTIMATED",

                timestamp,

                tolerance: 0.01
            });
        }
    }


    updateHealth(
        health
    ) {

        this.latestHealth =
            health;

        setText(
            "dashboard-mqtt",
            health.mqttConnected
                === true
                ? "CONNECTED"
                : "DISCONNECTED"
        );

        if (
            health.deviceState
        ) {
            setText(
                "dashboard-device-state",
                health.deviceState
            );
        }
    }


    updatePresence(
        presence
    ) {

        this.setOnline(
            presence?.status
            === "ONLINE"
        );

        if (
            presence?.deviceState
        ) {

            setText(
                "dashboard-device-state",
                presence.deviceState
            );
        }
    }


    updateEvent(
        event
    ) {

        if (
            event?.eventType
            === "DEVICE_STATE_CHANGED"
        ) {

            setText(
                "dashboard-device-state",
                event.currentState
                ?? "—"
            );

            if (
                event.currentState
                === "OFFLINE"
            ) {
                this.setOnline(
                    false
                );
            }
        }
    }


    updateAlert(
        alert
    ) {

        setText(
            "dashboard-alert-title",
            alert.type
            ?? "Alert"
        );

        setText(
            "dashboard-alert-message",
            alert.message
            ?? "Warning received."
        );

        const severity =
            alert.severity
            ?? "WARNING";

        setBadge(
            "dashboard-alert-severity",
            severity,
            badgeKindForStatus(
                severity
            )
        );
    }


    setOnline(
        online
    ) {

        setBadge(
            "global-online-status",
            online
                ? "ONLINE"
                : "OFFLINE",
            online
                ? "ok"
                : "danger"
        );
    }


    _renderSensor({
        prefix,
        cardId,
        value,
        previousKey,
        decimals,
        status,
        timestamp,
        tolerance
    }) {

        const normalizedStatus =
            String(
                status
                ?? "UNKNOWN"
            ).toUpperCase();

        const failed =
            [
                "FAILED",
                "DISABLED"
            ].includes(
                normalizedStatus
            );

        const card =
            byId(
                cardId
            );

        card?.classList.toggle(
            "failed",
            failed
        );

        setBadge(
            `sensor-${prefix}-status`,
            normalizedStatus,
            badgeKindForStatus(
                normalizedStatus
            )
        );

        if (
            failed
            || value === undefined
            || value === null
        ) {

            setText(
                `sensor-${prefix}-value`,
                "NEMA PODATAKA"
            );

            setText(
                `sensor-${prefix}-trend`,
                "—"
            );

        }

        else {

            setText(
                `sensor-${prefix}-value`,
                formatNumber(
                    value,
                    decimals
                )
            );

            setText(
                `sensor-${prefix}-trend`,
                this._trend(
                    previousKey,
                    Number(
                        value
                    ),
                    tolerance
                )
            );
        }

        setText(
            `sensor-${prefix}-time`,
            formatTime(
                timestamp
            )
        );
    }


    _trend(
        key,
        current,
        tolerance
    ) {

        const previous =
            this.previous[
                key
            ];

        this.previous[
            key
        ] = current;

        if (
            previous === undefined
            || !Number.isFinite(
                previous
            )
            || !Number.isFinite(
                current
            )
        ) {
            return "→ first reading";
        }

        const difference =
            current
            - previous;

        if (
            Math.abs(
                difference
            )
            <= tolerance
        ) {
            return "→ stable";
        }

        return (
            difference > 0
                ? "↑ rising"
                : "↓ falling"
        );
    }


    _activityDescription(
        scenario,
        activity
    ) {

        const descriptions = {

            SLEEPING:
                "Simulated sleeping state with low activity.",

            RESTING:
                "User is awake and resting.",

            WALKING:
                "Walking scenario with increasing steps.",

            RUNNING:
                "High-intensity running simulation.",

            EXERCISING:
                "General exercise simulation.",

            RECOVERY:
                "Recovery following physical activity.",

            STRESS_EVENT:
                "Technical stress-event simulation.",

            SENSOR_FAILURE:
                "A simulated sensor fault is active.",

            LOW_BATTERY:
                "Low-battery simulation is active.",

            NETWORK_OUTAGE:
                "Device is operating without cloud connectivity."
        };

        return (
            descriptions[
                scenario
            ]
            ?? `Activity level: ${activity ?? "UNKNOWN"}`
        );
    }
}