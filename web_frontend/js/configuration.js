import {
    badgeKindForStatus,
    byId,
    setText,
    showToast
} from "./utils.js";


const CONFIG_KEYS = [
    "measurementIntervalSec",
    "telemetryIntervalSec",
    "analyticsWindowSec",
    "healthReportIntervalSec",
    "temperatureUnit",
    "thresholds",
    "alerts",
    "offlineQueueMaximumItems",
    "activeUserProfile",
    "analyticsEnabled",
    "spo2AlertsEnabled",
    "spo2MinimumThreshold",
    "spo2MeasurementEnabled"
];


export class ConfigurationView {

    constructor(
        api
    ) {

        this.api =
            api;

        this.spo2Supported =
            false;

        this.form =
            byId(
                "configuration-form"
            );


        this.form.addEventListener(
            "submit",
            event => {
                event.preventDefault();

                this.save();
            }
        );


        byId(
            "configuration-refresh"
        ).addEventListener(
            "click",
            () => {
                this.load();
            }
        );
    }


    async load() {

        setText(
            "configuration-form-message",
            "Loading Device Shadow..."
        );


        try {

            const shadow =
                await this.api
                .getConfiguration();

            this.render(
                shadow
            );

            setText(
                "configuration-form-message",
                "Shadow loaded."
            );

        }

        catch (error) {

            setText(
                "configuration-form-message",
                `Error: ${error.message}`
            );

            throw error;
        }
    }


    async save() {

        const desired =
            this._readForm();


        setText(
            "configuration-form-message",
            "Updating desired state..."
        );


        try {

            await this.api
                .updateConfiguration(
                    desired
                );

            showToast(
                "Desired configuration sent to Device Shadow."
            );

            setText(
                "configuration-form-message",
                "Čeka se primjena konfiguracije."
            );


            for (
                let attempt = 0;
                attempt < 8;
                attempt += 1
            ) {

                await new Promise(
                    resolve =>
                        window.setTimeout(
                            resolve,
                            1000
                        )
                );


                const shadow =
                    await this.api
                        .getConfiguration();

                this.render(
                    shadow
                );


                if (
                    this._isSynchronized(
                        shadow
                    )
                ) {
                    break;
                }
            }

        }

        catch (error) {

            setText(
                "configuration-form-message",
                `Error: ${error.message}`
            );

            showToast(
                `Configuration failed: ${error.message}`
            );
        }
    }


    render(
        shadow
    ) {

        const state =
            shadow.state
            ?? {};

        const desired =
            state.desired
            ?? {};

        const reported =
            state.reported
            ?? {};


        byId(
            "configuration-desired-json"
        ).textContent =
            JSON.stringify(
                desired,
                null,
                2
            );


        byId(
            "configuration-reported-json"
        ).textContent =
            JSON.stringify(
                reported,
                null,
                2
            );


        setText(
            "configuration-shadow-version",
            shadow.version
            ?? "—"
        );


        const deviceResult =
            reported
            .configurationStatus
            ?.status
            ?? "—";

        setText(
            "configuration-device-result",
            deviceResult
        );


        const synchronized =
            this._isSynchronized(
                shadow
            );


        setText(
            "configuration-sync-status",
            synchronized
                ? "SYNCED"
                : "PENDING"
        );


        const syncElement =
            byId(
                "configuration-sync-status"
            );

        syncElement.style.color =
            synchronized
                ? "var(--success)"
                : "var(--warning)";


        if (
            synchronized
        ) {

            setText(
                "configuration-form-message",
                "Desired i reported vrijednosti su sinhronizovane."
            );
        }

        else {

            const status =
                reported
                .configurationStatus;

            if (
                status?.status
                === "REJECTED"
            ) {

                const errors =
                    status.errors
                    ?? [];

                setText(
                    "configuration-form-message",
                    `Configuration rejected: ${errors.join("; ")}`
                );
            }

            else {

                setText(
                    "configuration-form-message",
                    "Čeka se primjena konfiguracije."
                );
            }
        }


        this.spo2Supported =
            this._supportsSpo2(
                reported
            );

        byId(
            "config-spo2-section"
        )?.classList.toggle(
            "hidden",
            !this.spo2Supported
        );


        this._fillForm(
            this._effectiveConfig(
                reported,
                desired
            )
        );
    }


    _fillForm(
        config
    ) {

        if (!config) {
            return;
        }


        this._setInput(
            "config-measurement",
            config.measurementIntervalSec
        );

        this._setInput(
            "config-telemetry",
            config.telemetryIntervalSec
        );

        this._setInput(
            "config-analytics-window",
            config.analyticsWindowSec
        );

        this._setInput(
            "config-health-interval",
            config.healthReportIntervalSec
        );

        this._setInput(
            "config-temperature-unit",
            config.temperatureUnit
        );

        this._setInput(
            "config-offline-queue",
            config.offlineQueueMaximumItems
        );

        this._setInput(
            "config-user-profile",
            config.activeUserProfile
        );


        const thresholds =
            config.thresholds
            ?? {};

        this._setInput(
            "config-heart-min",
            thresholds
            .heartRateMinimumBpm
        );

        this._setInput(
            "config-heart-max",
            thresholds
            .heartRateMaximumRestingBpm
        );

        this._setInput(
            "config-temp-min",
            thresholds
            .skinTemperatureMinimumC
        );

        this._setInput(
            "config-temp-max",
            thresholds
            .skinTemperatureMaximumC
        );

        this._setInput(
            "config-battery-low",
            thresholds
            .lowBatteryPercentage
        );


        const alerts =
            config.alerts
            ?? {};

        this._setCheckbox(
            "config-alerts-enabled",
            alerts.enabled
        );

        this._setCheckbox(
            "config-heart-alerts",
            alerts.heartRate
        );

        this._setCheckbox(
            "config-temperature-alerts",
            alerts.temperature
        );

        this._setCheckbox(
            "config-battery-alerts",
            alerts.battery
        );

        this._setCheckbox(
            "config-sensor-alerts",
            alerts.sensorFailure
        );

        this._setCheckbox(
            "config-analytics-enabled",
            config.analyticsEnabled
        );


        if (
            this.spo2Supported
        ) {

            this._setInput(
                "config-spo2-minimum",
                config.spo2MinimumThreshold
            );

            this._setCheckbox(
                "config-spo2-enabled",
                config.spo2MeasurementEnabled
            );

            this._setCheckbox(
                "config-spo2-alerts",
                config.spo2AlertsEnabled
            );
        }
    }


    _readForm() {

        const desired = {

            measurementIntervalSec:
                Number(
                    byId(
                        "config-measurement"
                    ).value
                ),

            telemetryIntervalSec:
                Number(
                    byId(
                        "config-telemetry"
                    ).value
                ),

            analyticsWindowSec:
                Number(
                    byId(
                        "config-analytics-window"
                    ).value
                ),

            healthReportIntervalSec:
                Number(
                    byId(
                        "config-health-interval"
                    ).value
                ),

            temperatureUnit:
                byId(
                    "config-temperature-unit"
                ).value,

            thresholds: {

                heartRateMinimumBpm:
                    Number(
                        byId(
                            "config-heart-min"
                        ).value
                    ),

                heartRateMaximumRestingBpm:
                    Number(
                        byId(
                            "config-heart-max"
                        ).value
                    ),

                skinTemperatureMinimumC:
                    Number(
                        byId(
                            "config-temp-min"
                        ).value
                    ),

                skinTemperatureMaximumC:
                    Number(
                        byId(
                            "config-temp-max"
                        ).value
                    ),

                lowBatteryPercentage:
                    Number(
                        byId(
                            "config-battery-low"
                        ).value
                    )
            },

            alerts: {

                enabled:
                    byId(
                        "config-alerts-enabled"
                    ).checked,

                heartRate:
                    byId(
                        "config-heart-alerts"
                    ).checked,

                temperature:
                    byId(
                        "config-temperature-alerts"
                    ).checked,

                battery:
                    byId(
                        "config-battery-alerts"
                    ).checked,

                sensorFailure:
                    byId(
                        "config-sensor-alerts"
                    ).checked
            },

            offlineQueueMaximumItems:
                Number(
                    byId(
                        "config-offline-queue"
                    ).value
                ),

            activeUserProfile:
                byId(
                    "config-user-profile"
                ).value.trim(),

            analyticsEnabled:
                byId(
                    "config-analytics-enabled"
                ).checked
        };


        if (
            this.spo2Supported
        ) {

            desired.spo2MinimumThreshold =
                Number(
                    byId(
                        "config-spo2-minimum"
                    ).value
                );

            desired.spo2MeasurementEnabled =
                byId(
                    "config-spo2-enabled"
                ).checked;

            desired.spo2AlertsEnabled =
                byId(
                    "config-spo2-alerts"
                ).checked;
        }


        return desired;
    }


    _supportsSpo2(
        reported
    ) {

        const capabilities =
            reported.capabilities
            ?? [];


        if (
            Array.isArray(
                capabilities
            )
            && capabilities.includes(
                "SPO2_MONITORING"
            )
        ) {
            return true;
        }


        const version =
            String(
                reported.softwareVersion
                ?? ""
            );

        const major =
            Number(
                version.split(
                    "."
                )[0]
            );


        return (
            major >= 2
            || reported.spo2MeasurementEnabled
                !== undefined
            || reported.spo2MinimumThreshold
                !== undefined
        );
    }


    _effectiveConfig(
        reported,
        desired
    ) {

        const hasDesired =
            Object.keys(
                desired
            ).length > 0;


        if (
            !hasDesired
        ) {
            return reported;
        }


        return {
            ...reported,
            ...desired,

            thresholds: {
                ...(
                    reported.thresholds
                    ?? {}
                ),
                ...(
                    desired.thresholds
                    ?? {}
                )
            },

            alerts: {
                ...(
                    reported.alerts
                    ?? {}
                ),
                ...(
                    desired.alerts
                    ?? {}
                )
            }
        };
    }


    _isSynchronized(
        shadow
    ) {

        const desired =
            shadow.state
            ?.desired
            ?? {};

        const reported =
            shadow.state
            ?.reported
            ?? {};


        for (
            const key
            of CONFIG_KEYS
        ) {

            if (
                desired[
                    key
                ]
                === undefined
            ) {
                continue;
            }


            if (
                JSON.stringify(
                    desired[
                        key
                    ]
                )
                !==
                JSON.stringify(
                    reported[
                        key
                    ]
                )
            ) {
                return false;
            }
        }

        return true;
    }


    _setInput(
        id,
        value
    ) {

        if (
            value === undefined
            || value === null
        ) {
            return;
        }

        byId(
            id
        ).value =
            value;
    }


    _setCheckbox(
        id,
        value
    ) {

        if (
            value === undefined
            || value === null
        ) {
            return;
        }

        byId(
            id
        ).checked =
            Boolean(
                value
            );
    }
}