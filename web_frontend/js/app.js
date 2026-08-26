import {
    ApiClient
} from "./api.js";

import {
    HealthBandWebSocket
} from "./websocket.js";

import {
    DashboardView
} from "./dashboard.js";

import {
    SimulationView
} from "./simulation.js";

import {
    HistoryCharts
} from "./charts.js";

import {
    ConfigurationView
} from "./configuration.js";

import {
    CommandsView
} from "./commands.js";

import {
    DeviceHealthView
} from "./device_health.js";

import {
    EventLogView
} from "./event_log.js";

import {
    OtaView
} from "./ota.js";

import {
    byId,
    showGlobalError,
    showToast
} from "./utils.js";


const DEVICE_ID =
    "healthband-device-001";


const api =
    new ApiClient(
        {
            baseUrl:
                "http://127.0.0.1:8000",

            deviceId:
                DEVICE_ID
        }
    );


const dashboard =
    new DashboardView(
        api
    );


const simulation =
    new SimulationView();


const history =
    new HistoryCharts(
        api
    );


const configuration =
    new ConfigurationView(
        api
    );


const commands =
    new CommandsView(
        api
    );


const deviceHealth =
    new DeviceHealthView(
        api
    );


const eventLog =
    new EventLogView(
        api
    );


const ota =
    new OtaView();


let historyLoaded =
    false;


function handleRealtime(
    type,
    data
) {

    switch (
        type
    ) {

        case "telemetry":

            dashboard
                .updateTelemetry(
                    data
                );

            simulation
                .updateTelemetry(
                    data
                );

            ota.updateVersion(
                data.softwareVersion
            );

            break;


        case "health":

            dashboard
                .updateHealth(
                    data
                );

            deviceHealth
                .render(
                    data
                );

            ota.updateVersion(
                data.softwareVersion
            );

            break;


        case "presence":

            dashboard
                .updatePresence(
                    data
                );

            break;


        case "alert":

            dashboard
                .updateAlert(
                    data
                );

            eventLog
                .addRealtime(
                    "ALERT",
                    data
                );

            showToast(
                `${data.type ?? "Alert"}: `
                + `${data.message ?? ""}`
            );

            break;


        case "event":

            dashboard
                .updateEvent(
                    data
                );

            simulation
                .updateEvent(
                    data
                );

            eventLog
                .addRealtime(
                    "EVENT",
                    data
                );

            break;


        case "command_response":

            commands
                .handleRealtimeResult(
                    data
                );

            eventLog
                .addRealtime(
                    "COMMAND_RESPONSE",
                    data
                );

            break;


        case "analytics":

            break;


        default:

            console.debug(
                "Unhandled realtime type:",
                type
            );
    }
}


function handleWebSocketMessage(
    message
) {

    if (
        message.type
        === "initial_snapshot"
    ) {

        const snapshot =
            message.data
            ?? {};


        for (
            const [
                type,
                data
            ]
            of Object.entries(
                snapshot
            )
        ) {

            handleRealtime(
                type,
                data
            );
        }

        return;
    }


    handleRealtime(
        message.type,
        message.data
        ?? {}
    );
}


function handleWebSocketState(
    state
) {

    const dot =
        byId(
            "websocket-dot"
        );

    const label =
        byId(
            "websocket-label"
        );


    if (
        state
        === "CONNECTED"
    ) {

        dot.className =
            "status-dot status-dot-online";

        label.textContent =
            "Backend realtime connected";

        showGlobalError(
            null
        );

        return;
    }


    dot.className =
        "status-dot status-dot-offline";


    if (
        state
        === "CONNECTING"
    ) {

        label.textContent =
            "Connecting realtime...";

        return;
    }


    label.textContent =
        "Backend realtime disconnected";
}


const websocket =
    new HealthBandWebSocket(
        {
            url:
                api.websocketUrl(),

            onMessage:
                handleWebSocketMessage,

            onStateChange:
                handleWebSocketState
        }
    );


const pageTitles = {

    dashboard:
        "Dashboard",

    simulation:
        "Live Simulation",

    history:
        "History",

    configuration:
        "Configuration",

    commands:
        "Commands",

    health:
        "Device Health",

    ota:
        "OTA Update",

    events:
        "Event Log"
};


async function navigate(
    page
) {

    document
        .querySelectorAll(
            ".nav-item"
        )
        .forEach(
            button => {

                button.classList.toggle(
                    "active",
                    button.dataset.page
                    === page
                );
            }
        );


    document
        .querySelectorAll(
            ".page-section"
        )
        .forEach(
            section => {

                section.classList.toggle(
                    "active",
                    section.id
                    === `page-${page}`
                );
            }
        );


    byId(
        "page-title"
    ).textContent =
        pageTitles[
            page
        ]
        ?? "HealthBand";


    try {

        if (
            page
            === "history"
            && !historyLoaded
        ) {

            await history.load(
                history.period
            );

            historyLoaded =
                true;
        }


        if (
            page
            === "configuration"
        ) {

            await configuration.load();
        }


        if (
            page
            === "health"
        ) {

            await deviceHealth.load();
        }


        if (
            page
            === "events"
        ) {

            await eventLog.load();
        }

    }

    catch (error) {

        showToast(
            error.message
        );
    }
}


function configureNavigation() {

    document
        .querySelectorAll(
            ".nav-item"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    () => {

                        navigate(
                            button.dataset.page
                        );
                    }
                );
            }
        );


    document
        .querySelectorAll(
            ".period-button"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "click",
                    async () => {

                        document
                            .querySelectorAll(
                                ".period-button"
                            )
                            .forEach(
                                item =>
                                    item.classList.remove(
                                        "active"
                                    )
                            );


                        button.classList.add(
                            "active"
                        );


                        try {

                            await history.load(
                                button.dataset.period
                            );

                            historyLoaded =
                                true;

                        }

                        catch (error) {

                            showToast(
                                `History: ${error.message}`
                            );
                        }
                    }
                );
            }
        );
}


async function initialLoad() {

    configureNavigation();


    try {

        const backend =
            await api
                .getBackendHealth();


        if (
            backend.status
            !== "OK"
        ) {

            throw new Error(
                "FastAPI backend is not healthy."
            );
        }


        showGlobalError(
            null
        );

    }

    catch (error) {

        showGlobalError(
            "FastAPI backend nije dostupan na "
            + "http://127.0.0.1:8000. "
            + error.message
        );
    }


    const initialTasks = [

        dashboard
            .load()
            .catch(
                error => {
                    console.warn(
                        "Dashboard initial load:",
                        error
                    );
                }
            ),

        configuration
            .load()
            .catch(
                error => {
                    console.warn(
                        "Configuration initial load:",
                        error
                    );
                }
            ),

        deviceHealth
            .load()
            .catch(
                error => {
                    console.warn(
                        "Device health initial load:",
                        error
                    );
                }
            ),

        eventLog
            .load()
            .catch(
                error => {
                    console.warn(
                        "Event log initial load:",
                        error
                    );
                }
            )
    ];


    await Promise.allSettled(
        initialTasks
    );


    const device =
        dashboard.latestTelemetry;

    if (
        device?.softwareVersion
    ) {

        ota.updateVersion(
            device.softwareVersion
        );
    }


    websocket.connect();
}


window.addEventListener(
    "beforeunload",
    () => {

        websocket.close();
    }
);


initialLoad();