import {
    byId,
    formatNumber,
    formatTime,
    setText
} from "./utils.js";


export class SimulationView {

    constructor() {

        this.currentWatchPage = 0;
        this.version2Active = false;

        this._buildWatchUi();
        this._bindWatchNavigation();
        this._setWatchPage(0);
    }


    _buildWatchUi() {

        const stage =
            document.querySelector(
                "#page-simulation .watch-stage"
            );


        if (
            !stage
        ) {

            return;
        }


        stage.innerHTML = `
            <div class="watch-strap watch-strap-top"></div>

            <div
                id="watch-page-navigation"
                class="watch-page-navigation hidden"
            >
                <button
                    id="watch-prev-screen"
                    class="watch-page-arrow hidden"
                    type="button"
                    aria-label="Prethodni ekran narukvice"
                    title="Prethodni ekran"
                >‹</button>

                <button
                    id="watch-next-screen"
                    class="watch-page-arrow"
                    type="button"
                    aria-label="Sljedeći ekran narukvice"
                    title="Sljedeći ekran"
                >›</button>
            </div>

            <div class="watch-body">
                <div
                    id="watch-screen"
                    class="watch-screen"
                >

                    <div class="watch-top-row">

                        <span>
                            HealthBand
                        </span>

                        <span
                            id="watch-battery-group"
                            class="watch-battery-group"
                        >

                            <span id="watch-battery">
                                — %
                            </span>

                            <span
                                id="watch-charging-indicator"
                                class="watch-charging-indicator hidden"
                                aria-label="Uređaj se puni"
                                title="Charging"
                            >
                                <svg
                                    viewBox="0 0 20 20"
                                    width="14"
                                    height="14"
                                    aria-hidden="true"
                                >
                                    <path
                                        d="M11.4 1.5 4.8 10h4.4l-.7 8.5 6.7-9.4h-4.4l.6-7.6Z"
                                    ></path>
                                </svg>
                            </span>

                        </span>

                    </div>


                    <div
                        class="watch-page watch-page-primary"
                    >

                        <div
                            id="watch-heart"
                            class="watch-heart"
                        >
                            ♥
                        </div>

                        <div
                            id="watch-heart-rate"
                            class="watch-heart-rate"
                        >
                            —
                        </div>

                        <div class="watch-unit">
                            BPM
                        </div>


                        <div
                            id="watch-v1-bottom-grid"
                            class="watch-bottom-grid"
                        >

                            <div>

                                <span class="watch-small-label">
                                    Steps
                                </span>

                                <strong id="watch-steps">
                                    —
                                </strong>

                            </div>


                            <div>

                                <span class="watch-small-label">
                                    Activity
                                </span>

                                <strong id="watch-activity">
                                    —
                                </strong>

                            </div>

                        </div>


                        <div
                            id="watch-v2-bottom-grid"
                            class="watch-v2-bottom-grid hidden"
                        >

                            <div class="watch-v2-left-stack">

                                <div class="watch-v2-mini-card">

                                    <span class="watch-small-label">
                                        Steps
                                    </span>

                                    <strong id="watch-v2-steps">
                                        —
                                    </strong>

                                </div>


                                <div
                                    id="watch-spo2-row"
                                    class="watch-v2-mini-card watch-v2-spo2"
                                >

                                    <span class="watch-small-label">
                                        SpO₂
                                    </span>

                                    <strong>

                                        <span id="watch-spo2">
                                            —
                                        </span>

                                        <small>
                                            %
                                        </small>

                                    </strong>

                                </div>

                            </div>


                            <div class="watch-v2-activity-card">

                                <span class="watch-small-label">
                                    Activity
                                </span>

                                <strong id="watch-v2-activity">
                                    —
                                </strong>

                                <span
                                    class="watch-v2-activity-dot"
                                ></span>

                            </div>

                        </div>

                    </div>


                    <div
                        class="watch-page watch-page-secondary"
                    >

                        <div class="watch-secondary-title">
                            Activity today
                        </div>


                        <div
                            id="watch-calories-row"
                            class="watch-calorie-card"
                        >

                            <div class="watch-calorie-content">

                                <svg
                                    class="watch-calorie-icon"
                                    viewBox="0 0 48 48"
                                    width="24"
                                    height="24"
                                    aria-hidden="true"
                                >
                                    <path
                                        d="M27.8 4.5c1.2 8.1-5.4 10.8-5.4 16.2 0 2.7 1.7 4.3 3.8 4.3 3.4 0 5.7-3.2 4.8-8.2 5.9 4.1 9.2 9.5 9.2 15.2 0 7.1-6.7 12-16 12S8 39 8 31.1c0-6.5 4.2-12.2 10.8-17.1-.4 5.5 1.8 8.4 4.2 8.4 4 0 2-8.9 4.8-17.9Z"
                                    ></path>
                                </svg>

                                <strong id="watch-calories">
                                    —
                                </strong>

                                <span>
                                    kcal today
                                </span>

                            </div>

                        </div>


                        <div class="watch-secondary-steps-card">

                            <div class="watch-step-icon">

                                <svg
                                    viewBox="0 0 48 48"
                                    width="30"
                                    height="30"
                                    aria-hidden="true"
                                >

                                    <ellipse
                                        cx="17"
                                        cy="29"
                                        rx="6"
                                        ry="10"
                                        transform="rotate(-18 17 29)"
                                    ></ellipse>

                                    <circle
                                        cx="11"
                                        cy="14"
                                        r="2.4"
                                    ></circle>

                                    <circle
                                        cx="16"
                                        cy="11"
                                        r="2.2"
                                    ></circle>

                                    <circle
                                        cx="21"
                                        cy="12"
                                        r="2"
                                    ></circle>

                                    <ellipse
                                        cx="32"
                                        cy="24"
                                        rx="5.5"
                                        ry="9"
                                        transform="rotate(20 32 24)"
                                    ></ellipse>

                                    <circle
                                        cx="27"
                                        cy="9"
                                        r="2.1"
                                    ></circle>

                                    <circle
                                        cx="32"
                                        cy="7"
                                        r="2"
                                    ></circle>

                                    <circle
                                        cx="37"
                                        cy="9"
                                        r="1.8"
                                    ></circle>

                                </svg>

                            </div>


                            <div>

                                <span class="watch-small-label">
                                    Steps today
                                </span>

                                <strong id="watch-secondary-steps">
                                    —
                                </strong>

                            </div>

                        </div>

                    </div>


                    <div
                        id="watch-page-dots"
                        class="watch-page-dots hidden"
                        aria-hidden="true"
                    >

                        <span
                            id="watch-page-dot-1"
                            class="watch-page-dot active"
                        ></span>

                        <span
                            id="watch-page-dot-2"
                            class="watch-page-dot"
                        ></span>

                    </div>

                </div>
            </div>

            <div class="watch-strap watch-strap-bottom"></div>
        `;
    }


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


        const steps =
            measurements
            .totalDailySteps
            ?? "—";


        setText(
            "watch-steps",
            steps
        );


        setText(
            "watch-v2-steps",
            steps
        );


        setText(
            "watch-secondary-steps",
            steps
        );


        const batteryPercentage =
            Number(
                measurements
                .batteryPercentage
            );


        if (
            Number.isFinite(
                batteryPercentage
            )
        ) {

            const normalizedBattery =
                Math.max(
                    0,
                    Math.min(
                        100,
                        batteryPercentage
                    )
                );


            setText(
                "watch-battery",
                `${formatNumber(
                    normalizedBattery,
                    0
                )} %`
            );


            const batteryFill =
                byId(
                    "simulation-battery-fill"
                );


            if (
                batteryFill
            ) {

                batteryFill.style.width =
                    `${normalizedBattery}%`;
            }


            setText(
                "simulation-battery-label",
                `${normalizedBattery.toFixed(1)} %`
            );
        }


        const chargingValue =
            measurements
            .charging;


        const charging =
            chargingValue === true
            || String(
                chargingValue
                ?? ""
            ).toLowerCase()
            === "true";


        this._renderChargingState(
            charging
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
            "watch-v2-activity",
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


        this._renderActivity(
            telemetry.scenario,
            activity
        );


        const spo2 =
            measurements
            .oxygenSaturationPercentage;


        const caloriesToday =
            measurements
            .caloriesBurnedToday;


        const version2 =
            this._isVersion2Telemetry(
                telemetry,
                spo2,
                caloriesToday
            );


        this._setVersionMode(
            version2
        );


        if (
            version2
        ) {

            setText(
                "watch-spo2",
                formatNumber(
                    spo2,
                    1
                )
            );


            setText(
                "watch-calories",
                formatNumber(
                    caloriesToday,
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


    _bindWatchNavigation() {

        byId(
            "watch-prev-screen"
        )?.addEventListener(
            "click",
            () => {

                this._setWatchPage(
                    0
                );
            }
        );


        byId(
            "watch-next-screen"
        )?.addEventListener(
            "click",
            () => {

                this._setWatchPage(
                    1
                );
            }
        );
    }


    _setVersionMode(
        version2
    ) {

        const normalized =
            Boolean(
                version2
            );


        this.version2Active =
            normalized;


        byId(
            "watch-v1-bottom-grid"
        )?.classList.toggle(
            "hidden",
            normalized
        );


        byId(
            "watch-v2-bottom-grid"
        )?.classList.toggle(
            "hidden",
            !normalized
        );


        byId(
            "watch-page-navigation"
        )?.classList.toggle(
            "hidden",
            !normalized
        );


        byId(
            "watch-page-dots"
        )?.classList.toggle(
            "hidden",
            !normalized
        );


        if (
            !normalized
        ) {

            this._setWatchPage(
                0
            );
        }

        else {

            this._syncWatchNavigation();
        }
    }


    _setWatchPage(
        page
    ) {

        const normalized =
            page === 1
            ? 1
            : 0;


        this.currentWatchPage =
            normalized;


        byId(
            "watch-screen"
        )?.classList.toggle(
            "show-secondary",
            normalized === 1
        );


        byId(
            "watch-page-dot-1"
        )?.classList.toggle(
            "active",
            normalized === 0
        );


        byId(
            "watch-page-dot-2"
        )?.classList.toggle(
            "active",
            normalized === 1
        );


        this._syncWatchNavigation();
    }


    _syncWatchNavigation() {

        if (
            !this.version2Active
        ) {

            return;
        }


        byId(
            "watch-prev-screen"
        )?.classList.toggle(
            "hidden",
            this.currentWatchPage === 0
        );


        byId(
            "watch-next-screen"
        )?.classList.toggle(
            "hidden",
            this.currentWatchPage === 1
        );
    }


    _renderChargingState(
        charging
    ) {

        byId(
            "watch-charging-indicator"
        )?.classList.toggle(
            "hidden",
            !charging
        );


        byId(
            "watch-battery-group"
        )?.classList.toggle(
            "is-charging",
            charging
        );
    }


    _isVersion2Telemetry(
        telemetry,
        spo2,
        caloriesToday
    ) {

        const version =
            String(
                telemetry
                ?.softwareVersion
                ?? ""
            )
            .trim();


        const major =
            Number(
                version
                .split(
                    "."
                )[0]
            );


        if (
            Number.isFinite(
                major
            )
            && major >= 2
        ) {

            return true;
        }


        return (
            spo2 !== undefined
            && spo2 !== null
        ) || (
            caloriesToday !== undefined
            && caloriesToday !== null
        );
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