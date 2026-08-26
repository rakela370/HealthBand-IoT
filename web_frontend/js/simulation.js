import {
    byId,
    formatNumber,
    formatTime,
    setText
} from "./utils.js";


export class SimulationView {

    updateTelemetry(
        telemetry
    ) {

        const measurements =
            telemetry.measurements
            ?? {};

        const bpm =
            Number(
                measurements
                .heartRateBpm
            );

        if (
            Number.isFinite(
                bpm
            )
            && bpm > 0
        ) {

            setText(
                "watch-heart-rate",
                Math.round(
                    bpm
                )
            );

            /*
             * Required HealthBand relation:
             *
             * heartbeat interval ≈ 60000 / bpm
             */
            const heartbeatIntervalMs =
                60000 / bpm;

            const safeDuration =
                Math.max(
                    280,
                    Math.min(
                        2000,
                        heartbeatIntervalMs
                    )
                );

            byId(
                "watch-heart"
            )?.style.setProperty(
                "--heart-duration",
                `${safeDuration}ms`
            );
        }


        setText(
            "watch-steps",
            measurements
            .totalDailySteps
            ?? "—"
        );


        setText(
            "watch-battery",
            `${formatNumber(
                measurements
                .batteryPercentage,
                0
            )} %`
        );


        const activity =
            telemetry.activityLevel
            ?? measurements.activityLevel
            ?? "—";

        setText(
            "watch-activity",
            activity
        );

        setText(
            "simulation-scenario",
            telemetry.scenario
            ?? "—"
        );

        setText(
            "simulation-device-state",
            telemetry.deviceState
            ?? "—"
        );

        setText(
            "simulation-time",
            formatTime(
                telemetry.timestamp
            )
        );


        const battery =
            Number(
                measurements
                .batteryPercentage
            );

        if (
            Number.isFinite(
                battery
            )
        ) {

            const normalized =
                Math.max(
                    0,
                    Math.min(
                        100,
                        battery
                    )
                );

            byId(
                "simulation-battery-fill"
            ).style.width =
                `${normalized}%`;

            setText(
                "simulation-battery-label",
                `${normalized.toFixed(1)} %`
            );
        }


        this._renderActivity(
            telemetry.scenario,
            activity
        );


        const spo2 =
            measurements
            .oxygenSaturationPercentage;

        if (
            spo2 !== undefined
            && spo2 !== null
        ) {

            byId(
                "watch-spo2-row"
            )?.classList.remove(
                "hidden"
            );

            setText(
                "watch-spo2",
                formatNumber(
                    spo2,
                    1
                )
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
                "simulation-device-state",
                event.currentState
                ?? "—"
            );
        }
    }


    _renderActivity(
        scenario,
        activity
    ) {

        const visualMap = {

            SLEEPING: {
                symbol: "☾",
                name: "Sleeping",
                description:
                    "Low activity and stable simulated vital parameters."
            },

            RESTING: {
                symbol: "◉",
                name: "Resting",
                description:
                    "The simulated user is awake and resting."
            },

            WALKING: {
                symbol: "↗",
                name: "Walking",
                description:
                    "Steps increase while activity remains light or moderate."
            },

            RUNNING: {
                symbol: "≫",
                name: "Running",
                description:
                    "High activity with progressively increasing heart rate."
            },

            EXERCISING: {
                symbol: "◆",
                name: "Exercising",
                description:
                    "General high-intensity exercise simulation."
            },

            RECOVERY: {
                symbol: "↺",
                name: "Recovery",
                description:
                    "Heart rate gradually returns toward resting values."
            },

            STRESS_EVENT: {
                symbol: "!",
                name: "Stress Event",
                description:
                    "Technical simulation used to test alerts and analytics."
            },

            SENSOR_FAILURE: {
                symbol: "×",
                name: "Sensor Failure",
                description:
                    "One sensor is currently being simulated as failed."
            },

            LOW_BATTERY: {
                symbol: "↓",
                name: "Low Battery",
                description:
                    "Low battery scenario is active."
            },

            NETWORK_OUTAGE: {
                symbol: "⌁",
                name: "Network Outage",
                description:
                    "Local sensing continues while cloud connectivity is unavailable."
            }
        };


        const selected =
            visualMap[
                scenario
            ]
            ?? {
                symbol: "◉",
                name:
                    activity
                    ?? "Unknown",
                description:
                    "Realtime HealthBand activity."
            };


        setText(
            "activity-symbol",
            selected.symbol
        );

        setText(
            "activity-name",
            selected.name
        );

        setText(
            "activity-description",
            selected.description
        );
    }
}