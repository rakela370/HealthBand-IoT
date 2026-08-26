export class HealthBandWebSocket {

    constructor({
        url,
        onMessage,
        onStateChange
    }) {

        this.url =
            url;

        this.onMessage =
            onMessage;

        this.onStateChange =
            onStateChange;

        this.socket =
            null;

        this.reconnectTimer =
            null;

        this.closedManually =
            false;
    }


    connect() {

        this.closedManually =
            false;

        this._setState(
            "CONNECTING"
        );

        try {

            this.socket =
                new WebSocket(
                    this.url
                );

        }

        catch (error) {

            this._setState(
                "DISCONNECTED"
            );

            this._scheduleReconnect();

            return;
        }


        this.socket.onopen =
            () => {

                this._setState(
                    "CONNECTED"
                );
            };


        this.socket.onmessage =
            event => {

                try {

                    const payload =
                        JSON.parse(
                            event.data
                        );

                    this.onMessage?.(
                        payload
                    );

                }

                catch (error) {

                    console.error(
                        "Invalid WebSocket payload.",
                        error
                    );
                }
            };


        this.socket.onerror =
            () => {

                this._setState(
                    "ERROR"
                );
            };


        this.socket.onclose =
            () => {

                this._setState(
                    "DISCONNECTED"
                );

                if (
                    !this.closedManually
                ) {
                    this._scheduleReconnect();
                }
            };
    }


    close() {

        this.closedManually =
            true;

        window.clearTimeout(
            this.reconnectTimer
        );

        this.socket?.close();
    }


    _scheduleReconnect() {

        window.clearTimeout(
            this.reconnectTimer
        );

        this.reconnectTimer =
            window.setTimeout(
                () => {
                    this.connect();
                },
                2000
            );
    }


    _setState(
        state
    ) {

        this.onStateChange?.(
            state
        );
    }
}