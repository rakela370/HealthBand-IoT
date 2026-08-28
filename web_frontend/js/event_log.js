import {
    badgeKindForStatus,
    byId,
    formatTimestamp,
    showToast
} from "./utils.js";


export class EventLogView {

    constructor(
        api
    ) {

        this.api =
            api;

        this.items = [];

        this.filter =
            "ALL";


        byId(
            "event-filter"
        ).addEventListener(
            "change",
            event => {

                this.filter =
                    event.target.value;

                this.render();
            }
        );


        byId(
            "event-refresh"
        ).addEventListener(
            "click",
            () => {
                this.load();
            }
        );
    }


    async load() {

        try {

            const [
                events,
                alerts,
                commandResponses
            ] = await Promise.all(
                [
                    this.api
                        .getEvents(
                            "24h"
                        ),

                    this.api
                        .getAlerts(
                            "24h"
                        ),

                    this.api
                        .getCommandResponses(
                            "24h"
                        )
                ]
            );


            const historicalItems = [

                ...(
                    events.items
                    ?? []
                ).map(
                    item => ({
                        category:
                            "EVENT",

                        timestamp:
                            item.timestamp
                            ?? this._timestampFromKey(
                                item.timestampEventId
                            ),

                        payload:
                            item
                    })
                ),


                ...(
                    alerts.items
                    ?? []
                ).map(
                    item => ({
                        category:
                            "ALERT",

                        timestamp:
                            item.timestamp
                            ?? this._timestampFromKey(
                                item.timestampEventId
                            ),

                        payload:
                            item
                    })
                ),


                ...(
                    commandResponses.items
                    ?? []
                ).map(
                    item => ({
                        category:
                            "COMMAND_RESPONSE",

                        timestamp:
                            item.timestamp
                            ?? this._timestampFromKey(
                                item.timestampEventId
                            ),

                        payload:
                            item
                    })
                )
            ];


            /*
             * Merge persisted DynamoDB history with realtime
             * messages already received during the current
             * browser session.
             *
             * This prevents navigation/Refresh from deleting
             * realtime command responses.
             */
            const merged =
                new Map();


            for (
                const item
                of [
                    ...historicalItems,
                    ...this.items
                ]
            ) {

                merged.set(
                    this._identity(
                        item
                    ),
                    item
                );
            }


            this.items =
                Array.from(
                    merged.values()
                );


            this._sort();

            this.render();

        }

        catch (error) {

            showToast(
                `Event Log: ${error.message}`
            );
        }
    }


    addRealtime(
        category,
        payload
    ) {

        const normalized =
            String(
                category
            ).toUpperCase();


        const mapped =
            normalized
            === "COMMAND_RESPONSE"
                ? "COMMAND_RESPONSE"
                : (
                    normalized
                    === "ALERT"
                        ? "ALERT"
                        : "EVENT"
                );


        const item = {

            category:
                mapped,

            timestamp:
                payload.timestamp
                ?? new Date()
                    .toISOString(),

            payload
        };


        const identity =
            this._identity(
                item
            );


        this.items =
            this.items.filter(
                existing =>
                    this._identity(
                        existing
                    )
                    !== identity
            );


        this.items.unshift(
            item
        );


        this.items =
            this.items.slice(
                0,
                500
            );


        this._sort();

        this.render();
    }


    render() {

        const container =
            byId(
                "event-log"
            );

        container.innerHTML = "";


        const visible =
            this.items.filter(
                item =>
                    this.filter
                    === "ALL"
                    || item.category
                    === this.filter
            );


        if (!visible.length) {

            const empty =
                document.createElement(
                    "div"
                );

            empty.className =
                "empty-cell";

            empty.textContent =
                "Nema događaja za izabrani filter.";

            container.appendChild(
                empty
            );

            return;
        }


        for (
            const item
            of visible.slice(
                0,
                200
            )
        ) {

            container.appendChild(
                this._renderItem(
                    item
                )
            );
        }
    }


    _renderItem(
        item
    ) {

        const row =
            document.createElement(
                "div"
            );

        row.className =
            "event-item";


        const time =
            document.createElement(
                "div"
            );

        time.className =
            "event-time";

        time.textContent =
            formatTimestamp(
                item.timestamp
            );


        const category =
            document.createElement(
                "div"
            );

        const badge =
            document.createElement(
                "span"
            );

        badge.className =
            `status-badge status-${this._categoryKind(item)}`;

        badge.textContent =
            this._categoryLabel(
                item
            );

        category.appendChild(
            badge
        );


        const message =
            document.createElement(
                "div"
            );

        message.className =
            "event-message";

        message.textContent =
            this._description(
                item
            );


        row.appendChild(
            time
        );

        row.appendChild(
            category
        );

        row.appendChild(
            message
        );


        return row;
    }


    _description(
        item
    ) {

        const payload =
            item.payload
            ?? {};


        if (
            item.category
            === "ALERT"
        ) {

            return (
                `${payload.type ?? "ALERT"} — `
                + `${payload.message ?? ""}`
            );
        }


        if (
            item.category
            === "COMMAND_RESPONSE"
        ) {

            const commandType =
                payload.type
                ?? payload.commandType
                ?? "COMMAND";


            const status =
                payload.status
                ?? "UNKNOWN";


            const message =
                payload.message
                ?? "";


            const commandId =
                payload.commandId
                ?? "unknown-command";


            return (
                `${commandType} — `
                + `${status} — `
                + `${message} `
                + `[${commandId}]`
            );
        }


        if (
            payload.eventType
            === "DEVICE_STATE_CHANGED"
        ) {

            return (
                `${payload.previousState ?? "?"} → `
                + `${payload.currentState ?? "?"} — `
                + `${payload.reason ?? ""}`
            );
        }


        if (
            payload.eventType
            === "CONFIGURATION_CHANGED"
        ) {

            return (
                `Configuration ${payload.status ?? ""} — `
                + `${payload.source ?? ""}`
            );
        }


        if (
            payload.eventType
            === "OFFLINE_SYNC_COMPLETED"
        ) {

            return (
                `Offline synchronization: `
                + `${payload.sent ?? 0} sent, `
                + `${payload.remaining ?? 0} remaining`
            );
        }


        return (
            payload.eventType
            ?? payload.message
            ?? JSON.stringify(
                payload
            )
        );
    }


    _categoryLabel(
        item
    ) {

        if (
            item.category
            === "COMMAND_RESPONSE"
        ) {

            return (
                item.payload
                ?.status
                ?? "COMMAND"
            );
        }


        return item.category;
    }


    _categoryKind(
        item
    ) {

        if (
            item.category
            === "ALERT"
        ) {

            return badgeKindForStatus(
                item.payload
                ?.severity
                ?? "WARNING"
            );
        }


        if (
            item.category
            === "COMMAND_RESPONSE"
        ) {

            return badgeKindForStatus(
                item.payload
                ?.status
            );
        }


        return "neutral";
    }


    _identity(
        item
    ) {

        const payload =
            item.payload
            ?? {};


        if (
            payload.messageId
        ) {

            return (
                `message:${payload.messageId}`
            );
        }


        if (
            payload.timestampEventId
        ) {

            return (
                `event:${payload.timestampEventId}`
            );
        }


        if (
            item.category
            === "COMMAND_RESPONSE"
        ) {

            return (
                "command:"
                + `${payload.commandId ?? "unknown"}:`
                + `${payload.status ?? "unknown"}:`
                + `${item.timestamp ?? "unknown"}`
            );
        }


        return (
            `${item.category}:`
            + `${item.timestamp ?? "unknown"}:`
            + `${payload.eventType ?? payload.type ?? "unknown"}`
        );
    }


    _timestampFromKey(
        key
    ) {

        if (!key) {
            return null;
        }

        return String(
            key
        ).slice(
            0,
            25
        );
    }


    _sort() {

        this.items.sort(
            (
                left,
                right
            ) =>
                new Date(
                    right.timestamp
                    ?? 0
                )
                -
                new Date(
                    left.timestamp
                    ?? 0
                )
        );
    }
}