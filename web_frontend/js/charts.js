import {
    byId,
    formatTimestamp
} from "./utils.js";


export class HistoryCharts {

    constructor(
        api
    ) {

        this.api =
            api;

        this.period =
            "1h";

        this.charts = {};
    }


    async load(
        period = this.period
    ) {

        this.period =
            period;

        const status =
            byId(
                "history-status"
            );

        status.textContent =
            "Učitavanje podataka iz DynamoDB...";


        const longPeriod =
            [
                "7d",
                "30d"
            ].includes(
                period
            );


        const [
            dataResponse,
            alertsResponse
        ] = await Promise.all(
            [
                longPeriod
                    ? this.api
                        .getAnalytics(
                            period
                        )
                    : this.api
                        .getTelemetry(
                            period
                        ),

                this.api
                    .getAlerts(
                        period
                    )
            ]
        );


        const items =
            dataResponse.items
            ?? [];

        const alerts =
            alertsResponse.items
            ?? [];


        if (
            longPeriod
        ) {
            this._renderAnalytics(
                items,
                alerts
            );
        }

        else {
            this._renderTelemetry(
                items,
                alerts
            );
        }


        status.textContent =
            `${items.length} data points | `
            + `${alerts.length} alerts | `
            + `period ${period}`;
    }


    _renderTelemetry(
        items,
        alerts
    ) {

        const labels =
            items.map(
                item =>
                    this._shortTime(
                        item.timestamp
                    )
            );


        const heartRate =
            items.map(
                item =>
                    item.measurements
                    ?.heartRateBpm
                    ?? null
            );


        const temperature =
            items.map(
                item =>
                    item.measurements
                    ?.skinTemperature
                    ?? null
            );


        const steps =
            items.map(
                item =>
                    item.measurements
                    ?.totalDailySteps
                    ?? null
            );


        const battery =
            items.map(
                item =>
                    item.measurements
                    ?.batteryPercentage
                    ?? null
            );


        const spo2 =
            items.map(
                item =>
                    item.measurements
                    ?.oxygenSaturationPercentage
                    ?? null
            );


        const calories =
            items.map(
                item =>
                    item.measurements
                    ?.caloriesBurnedToday
                    ?? null
            );


        const temperatureUnit =
            items.find(
                item =>
                    item.measurements
                    ?.temperatureUnit
            )
            ?.measurements
            ?.temperatureUnit
            ?? "CELSIUS";


        this._line(
            "heart-rate",
            labels,
            heartRate,
            "BPM",
            "Heart Rate"
        );


        this._line(
            "temperature",
            labels,
            temperature,
            temperatureUnit
                === "FAHRENHEIT"
                ? "°F"
                : "°C",
            "Skin Temperature"
        );


        this._line(
            "steps",
            labels,
            steps,
            "steps",
            "Daily Steps"
        );


        this._line(
            "battery",
            labels,
            battery,
            "%",
            "Battery"
        );


        this._renderAlerts(
            alerts
        );


        const hasSpo2 =
            spo2.some(
                value =>
                    value !== null
                    && value !== undefined
            );

        byId(
            "spo2-chart-card"
        )?.classList.toggle(
            "hidden",
            !hasSpo2
        );

        if (
            hasSpo2
        ) {

            this._line(
                "spo2",
                labels,
                spo2,
                "%",
                "SpO₂"
            );
        }

        else {
            this._destroy(
                "spo2"
            );
        }


        const hasCalories =
            calories.some(
                value =>
                    value !== null
                    && value !== undefined
            );

        byId(
            "calories-chart-card"
        )?.classList.toggle(
            "hidden",
            !hasCalories
        );

        if (
            hasCalories
        ) {

            this._line(
                "calories",
                labels,
                calories,
                "kcal",
                "Estimated Calories Today"
            );
        }

        else {
            this._destroy(
                "calories"
            );
        }
    }


    _renderAnalytics(
        items,
        alerts
    ) {

        const labels =
            items.map(
                item =>
                    this._shortTime(
                        item.windowEnd
                    )
            );


        const heartRate =
            items.map(
                item =>
                    item.analytics
                    ?.heartRate
                    ?.averageBpm
                    ?? null
            );


        const temperature =
            items.map(
                item =>
                    item.analytics
                    ?.skinTemperature
                    ?.averageCelsius
                    ?? null
            );


        const steps =
            items.map(
                item =>
                    item.analytics
                    ?.steps
                    ?.total
                    ?? null
            );


        const battery =
            items.map(
                item =>
                    item.analytics
                    ?.battery
                    ?.averagePercentage
                    ?? item.analytics
                    ?.battery
                    ?.average
                    ?? null
            );


        const spo2 =
            items.map(
                item =>
                    item.analytics
                    ?.spo2
                    ?.averagePercentage
                    ?? item.analytics
                    ?.spo2
                    ?.average
                    ?? null
            );


        const dailyCalories =
            this._dailyCalories(
                items
            );


        this._line(
            "heart-rate",
            labels,
            heartRate,
            "BPM",
            "Average Heart Rate"
        );


        this._line(
            "temperature",
            labels,
            temperature,
            "°C",
            "Average Skin Temperature"
        );


        this._line(
            "steps",
            labels,
            steps,
            "steps/window",
            "Steps"
        );


        this._line(
            "battery",
            labels,
            battery,
            "%",
            "Average Battery"
        );


        this._renderAlerts(
            alerts
        );


        const hasSpo2 =
            spo2.some(
                value =>
                    value !== null
                    && value !== undefined
            );

        byId(
            "spo2-chart-card"
        )?.classList.toggle(
            "hidden",
            !hasSpo2
        );

        if (
            hasSpo2
        ) {

            this._line(
                "spo2",
                labels,
                spo2,
                "%",
                "Average SpO₂"
            );
        }

        else {
            this._destroy(
                "spo2"
            );
        }


        const hasCalories =
            dailyCalories.values.length
            > 0;

        byId(
            "calories-chart-card"
        )?.classList.toggle(
            "hidden",
            !hasCalories
        );

        if (
            hasCalories
        ) {

            this._bar(
                "calories",
                dailyCalories.labels,
                dailyCalories.values,
                "kcal",
                "Estimated Daily Calories"
            );
        }

        else {
            this._destroy(
                "calories"
            );
        }
    }


    _dailyCalories(
        items
    ) {

        const totalsByDate =
            new Map();


        for (
            const item
            of items
        ) {

            const value =
                item.analytics
                ?.calories
                ?.dailyTotalKcal;

            const date =
                new Date(
                    item.windowEnd
                );


            if (
                value === undefined
                || value === null
                || Number.isNaN(
                    date.getTime()
                )
            ) {
                continue;
            }


            const label =
                date.toLocaleDateString(
                    "bs-BA",
                    {
                        day: "2-digit",
                        month: "2-digit",
                        timeZone:
                            "Europe/Sarajevo"
                    }
                );

            const numeric =
                Number(
                    value
                );


            if (
                !Number.isFinite(
                    numeric
                )
            ) {
                continue;
            }


            const previous =
                totalsByDate.get(
                    label
                );

            if (
                previous === undefined
                || numeric > previous
            ) {

                totalsByDate.set(
                    label,
                    numeric
                );
            }
        }


        return {
            labels: [
                ...totalsByDate.keys()
            ],
            values: [
                ...totalsByDate.values()
            ]
        };
    }


    _renderAlerts(
        alerts
    ) {

        const labels =
            alerts.map(
                alert =>
                    this._shortTime(
                        alert.timestamp
                    )
            );


        const values =
            alerts.map(
                () => 1
            );


        this._bar(
            "alerts",
            labels,
            values,
            "alert",
            "Alerts"
        );
    }


    _line(
        id,
        labels,
        values,
        unit,
        label
    ) {

        this._destroy(
            id
        );

        const canvas =
            byId(
                `${id}-chart`
            );

        if (!canvas) {
            return;
        }


        this.charts[
            id
        ] = new Chart(
            canvas,
            {
                type: "line",

                data: {
                    labels,

                    datasets: [
                        {
                            label,

                            data:
                                values,

                            borderColor:
                                "#58d6c7",

                            backgroundColor:
                                "rgba(88, 214, 199, 0.12)",

                            borderWidth: 2,

                            pointRadius:
                                labels.length > 150
                                    ? 0
                                    : 2,

                            pointHoverRadius: 4,

                            tension: 0.25,

                            spanGaps: true
                        }
                    ]
                },

                options:
                    this._options(
                        unit
                    )
            }
        );
    }


    _bar(
        id,
        labels,
        values,
        unit,
        label
    ) {

        this._destroy(
            id
        );

        const canvas =
            byId(
                `${id}-chart`
            );

        if (!canvas) {
            return;
        }


        this.charts[
            id
        ] = new Chart(
            canvas,
            {
                type: "bar",

                data: {
                    labels,

                    datasets: [
                        {
                            label,

                            data:
                                values,

                            backgroundColor:
                                "rgba(255, 113, 133, 0.55)",

                            borderColor:
                                "#ff7185",

                            borderWidth: 1
                        }
                    ]
                },

                options:
                    this._options(
                        unit
                    )
            }
        );
    }


    _options(
        unit
    ) {

        return {

            responsive: true,

            maintainAspectRatio:
                false,

            animation: {
                duration: 350
            },

            interaction: {
                intersect: false,
                mode: "index"
            },

            scales: {

                x: {
                    ticks: {
                        color:
                            "#708797",

                        maxTicksLimit:
                            10
                    },

                    grid: {
                        color:
                            "rgba(255,255,255,0.04)"
                    }
                },

                y: {
                    ticks: {
                        color:
                            "#708797",

                        callback:
                            value =>
                                `${value} ${unit}`
                    },

                    grid: {
                        color:
                            "rgba(255,255,255,0.05)"
                    }
                }
            },

            plugins: {

                legend: {
                    labels: {
                        color:
                            "#a8bac7"
                    }
                }
            }
        };
    }


    _destroy(
        id
    ) {

        if (
            this.charts[
                id
            ]
        ) {

            this.charts[
                id
            ].destroy();

            delete this.charts[
                id
            ];
        }
    }


    _shortTime(
        value
    ) {

        const date =
            new Date(
                value
            );

        if (
            Number.isNaN(
                date.getTime()
            )
        ) {
            return formatTimestamp(
                value
            );
        }


        if (
            [
                "7d",
                "30d"
            ].includes(
                this.period
            )
        ) {

            return date.toLocaleString(
                "bs-BA",
                {
                    day: "2-digit",
                    month: "2-digit",
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false
                }
            );
        }


        return date.toLocaleTimeString(
            "bs-BA",
            {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: false
            }
        );
    }
}