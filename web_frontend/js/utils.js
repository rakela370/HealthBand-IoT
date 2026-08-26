export function byId(id) {
    return document.getElementById(id);
}


export function formatTimestamp(value) {

    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleString(
        "bs-BA",
        {
            hour12: false
        }
    );
}


export function formatTime(value) {

    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "—";
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


export function formatNumber(
    value,
    decimals = 0
) {

    const numeric = Number(value);

    if (!Number.isFinite(numeric)) {
        return "—";
    }

    return numeric.toFixed(decimals);
}


export function formatBytes(bytes) {

    const numeric = Number(bytes);

    if (!Number.isFinite(numeric)) {
        return "—";
    }

    if (numeric < 1024) {
        return `${numeric} B`;
    }

    if (numeric < 1024 * 1024) {
        return `${(
            numeric / 1024
        ).toFixed(1)} KB`;
    }

    return `${(
        numeric / 1024 / 1024
    ).toFixed(2)} MB`;
}


export function setText(
    id,
    value
) {

    const element = byId(id);

    if (element) {
        element.textContent =
            value ?? "—";
    }
}


export function setBadge(
    id,
    value,
    kind = "neutral"
) {

    const element = byId(id);

    if (!element) {
        return;
    }

    element.textContent =
        value ?? "—";

    element.className =
        `status-badge status-${kind}`;
}


export function badgeKindForStatus(status) {

    const normalized =
        String(
            status ?? ""
        ).toUpperCase();

    if (
        [
            "OK",
            "ONLINE",
            "HEALTHY",
            "MONITORING",
            "SUCCEEDED",
            "APPLIED"
        ].includes(
            normalized
        )
    ) {
        return "ok";
    }

    if (
        [
            "WARNING",
            "DEGRADED",
            "LOW_BATTERY",
            "CALIBRATING",
            "IN_PROGRESS",
            "RECEIVED",
            "PUBLISHED",
            "CONNECTING"
        ].includes(
            normalized
        )
    ) {
        return "warning";
    }

    if (
        [
            "FAILED",
            "ERROR",
            "UNHEALTHY",
            "OFFLINE",
            "REJECTED",
            "DISABLED"
        ].includes(
            normalized
        )
    ) {
        return "danger";
    }

    return "neutral";
}


export function showToast(
    message
) {

    const container =
        byId(
            "toast-container"
        );

    if (!container) {
        return;
    }

    const toast =
        document.createElement(
            "div"
        );

    toast.className =
        "toast";

    toast.textContent =
        String(
            message
        );

    container.appendChild(
        toast
    );

    window.setTimeout(
        () => {
            toast.remove();
        },
        4500
    );
}


export function showGlobalError(
    message
) {

    const element =
        byId(
            "global-error"
        );

    if (!element) {
        return;
    }

    if (!message) {

        element.classList.add(
            "hidden"
        );

        element.textContent = "";

        return;
    }

    element.textContent =
        String(
            message
        );

    element.classList.remove(
        "hidden"
    );
}