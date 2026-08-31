import {
    byId,
    formatBytes,
    formatTimestamp,
    setText,
    showToast
} from "./utils.js";


const PHASE_ORDER = [
    "QUEUED",
    "DOWNLOADING",
    "VERIFYING",
    "VALIDATING",
    "BACKING_UP",
    "EXTRACTING",
    "PRE_INSTALL_CHECK",
    "INSTALLING",
    "ACTIVATING",
    "SELF_TEST",
    "RESTARTING",
    "COMPLETED"
];


const PHASE_LABELS = {
    QUEUED:
        "Queued",

    DOWNLOADING:
        "Download",

    VERIFYING:
        "SHA-256",

    VALIDATING:
        "Manifest",

    BACKING_UP:
        "Backup",

    EXTRACTING:
        "Extract",

    PRE_INSTALL_CHECK:
        "Pre-check",

    INSTALLING:
        "Install",

    ACTIVATING:
        "Activate",

    SELF_TEST:
        "Self-test",

    RESTARTING:
        "Restart",

    COMPLETED:
        "Completed"
};


export class OtaView {

    constructor(
        api
    ) {

        this.api =
            api;

        this.currentVersion =
            null;

        this.releases =
            [];

        this.selectedVersion =
            null;

        this.latestProgress =
            null;

        this.latestJob =
            null;

        this.installing =
            false;

        this.bound =
            false;

        this._bind();

        this._renderPhaseSteps(
            "IDLE"
        );
    }


    async load() {

        this._setStatusMessage(
            "Provjeravam OTA stanje i dostupne release pakete..."
        );

        try {

            const state =
                await this.api
                    .getOtaState();

            this._applyState(
                state
            );

            if (
                !this.latestProgress
            ) {

                this._setStatusMessage(
                    this._idleMessage()
                );
            }

            return state;
        }

        catch (error) {

            this._setStatusMessage(
                `OTA stanje nije dostupno: ${error.message}`,
                "error"
            );

            throw error;
        }
    }


    updateVersion(
        softwareVersion
    ) {

        const version =
            String(
                softwareVersion
                ?? ""
            ).trim();

        if (!version) {
            return;
        }

        const changed =
            this.currentVersion
            !== version;

        this.currentVersion =
            version;

        setText(
            "ota-current-version",
            version
        );

        if (
            changed
            && this.releases.length
        ) {

            this._selectBestRelease();

            this._renderReleases();

            this._renderSelectedRelease();
        }
    }


    handleRealtime(
        data
    ) {

        if (
            !data
            || typeof data !== "object"
        ) {
            return;
        }

        this.latestProgress =
            data;

        if (
            data.activeVersion
        ) {

            this.updateVersion(
                data.activeVersion
            );
        }

        if (
            data.targetVersion
        ) {

            setText(
                "ota-target-version",
                data.targetVersion
            );
        }

        if (
            data.jobStatus
        ) {

            setText(
                "ota-job-status",
                data.jobStatus
            );
        }

        if (
            data.jobId
        ) {

            setText(
                "ota-job-id",
                data.jobId
            );
        }

        setText(
            "ota-self-test",
            data.selfTest
            ?? "NOT_RUN"
        );

        setText(
            "ota-rollback",
            data.rollbackPerformed
            ? "YES"
            : "NO"
        );

        this._renderProgress(
            data
        );

        this._appendLog(
            data
        );

        const phase =
            String(
                data.phase
                ?? ""
            ).toUpperCase();

        if (
            phase === "COMPLETED"
        ) {

            this.installing =
                false;

            this._setStatusMessage(
                data.message
                ?? "OTA update completed successfully.",
                "success"
            );

            this._refreshInstallButton();

            window.setTimeout(
                () => {

                    this.load()
                        .catch(
                            error => {

                                console.warn(
                                    "OTA state refresh after completion:",
                                    error
                                );
                            }
                        );
                },
                1200
            );

            return;
        }

        if (
            phase === "FAILED"
        ) {

            this.installing =
                false;

            this._setStatusMessage(
                data.message
                ?? "OTA update failed.",
                "error"
            );

            this._refreshInstallButton();

            return;
        }

        if (
            phase === "ROLLING_BACK"
        ) {

            this._setStatusMessage(
                data.message
                ?? "OTA rollback is in progress.",
                "error"
            );

            return;
        }

        this._setStatusMessage(
            data.message
            ?? `OTA phase: ${phase || "IN_PROGRESS"}`
        );
    }


    _bind() {

        if (
            this.bound
        ) {
            return;
        }

        const refresh =
            byId(
                "ota-refresh"
            );

        const install =
            byId(
                "ota-install-button"
            );

        refresh?.addEventListener(
            "click",
            async () => {

                refresh.disabled =
                    true;

                try {

                    await this.load();
                }

                catch (error) {

                    showToast(
                        `OTA: ${error.message}`
                    );
                }

                finally {

                    refresh.disabled =
                        false;
                }
            }
        );

        install?.addEventListener(
            "click",
            () => {

                this._installSelected()
                    .catch(
                        error => {

                            showToast(
                                `OTA: ${error.message}`
                            );
                        }
                    );
            }
        );

        this.bound =
            true;
    }


    _applyState(
        state
    ) {

        this.releases =
            Array.isArray(
                state?.releases
            )
            ? state.releases
            : [];

        this.latestProgress =
            state?.latestProgress
            ?? null;

        this.latestJob =
            state?.latestJob
            ?? null;

        if (
            state?.currentVersion
        ) {

            this.updateVersion(
                state.currentVersion
            );
        }

        else {

            setText(
                "ota-current-version",
                "—"
            );
        }

        this._selectBestRelease();

        this._renderReleases();

        this._renderSelectedRelease();

        this._renderLatestJob();

        if (
            this.latestProgress
        ) {

            this.handleRealtime(
                this.latestProgress
            );
        }

        else {

            this._renderProgress(
                {
                    phase:
                        "IDLE",

                    progressPercentage:
                        0,

                    jobStatus:
                        this.latestJob?.status
                        ?? "IDLE",

                    selfTest:
                        this._jobStatusDetail(
                            "selfTest"
                        )
                        ?? "NOT_RUN",

                    rollbackPerformed:
                        this._jobStatusDetail(
                            "rollbackPerformed"
                        )
                        === "true"
                }
            );
        }
    }


    _selectBestRelease() {

        const usable =
            this.releases
            .filter(
                release => (
                    release.uploaded
                    && this._isNewer(
                        release.version,
                        this.currentVersion
                    )
                )
            )
            .sort(
                (
                    left,
                    right
                ) => (

                    this._compareVersions(
                        right.version,
                        left.version
                    )
                )
            );

        const currentSelection =
            usable.find(
                release => (
                    release.version
                    === this.selectedVersion
                )
            );

        if (
            currentSelection
        ) {
            return;
        }

        this.selectedVersion =
            usable[0]?.version
            ?? null;
    }


    _renderReleases() {

        const container =
            byId(
                "ota-release-list"
            );

        if (!container) {
            return;
        }

        container.replaceChildren();

        if (
            !this.releases.length
        ) {

            const empty =
                document.createElement(
                    "div"
                );

            empty.className =
                "empty-cell";

            empty.textContent =
                "Nema lokalnih OTA release paketa.";

            container.appendChild(
                empty
            );

            return;
        }

        const releases =
            [
                ...this.releases
            ]
            .sort(
                (
                    left,
                    right
                ) => (

                    this._compareVersions(
                        right.version,
                        left.version
                    )
                )
            );

        releases.forEach(
            release => {

                const row =
                    document.createElement(
                        "div"
                    );

                row.className =
                    "ota-release-row";

                if (
                    release.version
                    === this.selectedVersion
                ) {

                    row.classList.add(
                        "selected"
                    );
                }

                const info =
                    document.createElement(
                        "div"
                    );

                info.className =
                    "ota-release-info";

                const title =
                    document.createElement(
                        "strong"
                    );

                title.textContent =
                    `HealthBand ${release.version}`;

                const meta =
                    document.createElement(
                        "span"
                    );

                const uploadState =
                    release.uploaded
                    ? "S3 ready"
                    : "not uploaded";

                meta.textContent =
                    `${formatBytes(release.sizeBytes)} · ${uploadState}`;

                info.append(
                    title,
                    meta
                );


                const actions =
                    document.createElement(
                        "div"
                    );

                actions.className =
                    "ota-release-actions";


                const badge =
                    document.createElement(
                        "span"
                    );

                badge.className =
                    release.uploaded
                    ? "status-badge status-ok"
                    : "status-badge status-warning";

                badge.textContent =
                    release.uploaded
                    ? "AVAILABLE"
                    : "LOCAL ONLY";


                const selectButton =
                    document.createElement(
                        "button"
                    );

                selectButton.type =
                    "button";

                selectButton.className =
                    "button button-secondary";

                const newer =
                    this._isNewer(
                        release.version,
                        this.currentVersion
                    );

                selectButton.disabled =
                    !release.uploaded
                    || !newer
                    || this.installing;

                selectButton.textContent =
                    release.version
                    === this.selectedVersion
                    ? "Selected"
                    : (
                        newer
                        ? "Select"
                        : "Installed / older"
                    );

                selectButton.addEventListener(
                    "click",
                    () => {

                        this.selectedVersion =
                            release.version;

                        this._renderReleases();

                        this._renderSelectedRelease();
                    }
                );

                actions.append(
                    badge,
                    selectButton
                );

                row.append(
                    info,
                    actions
                );

                container.appendChild(
                    row
                );
            }
        );
    }


    _renderSelectedRelease() {

        const release =
            this.releases.find(
                item => (
                    item.version
                    === this.selectedVersion
                )
            );

        setText(
            "ota-selected-version",
            release?.version
            ?? "—"
        );

        const meta =
            byId(
                "ota-selected-meta"
            );

        const features =
            byId(
                "ota-selected-features"
            );

        if (
            meta
        ) {

            meta.textContent =
                release
                ? (
                    `${formatBytes(release.sizeBytes)} · `
                    + `SHA-256 ${String(release.sha256).slice(0, 16)}…`
                )
                : (
                    "Izaberi noviju verziju "
                    + "dostupnu u privatnom S3 bucketu."
                );
        }

        if (
            features
        ) {

            features.replaceChildren();

            const values =
                release?.features?.length
                ? release.features
                : (
                    release?.capabilities
                    ?? []
                );

            values.forEach(
                value => {

                    const tag =
                        document.createElement(
                            "span"
                        );

                    tag.className =
                        "ota-feature-tag";

                    tag.textContent =
                        value;

                    features.appendChild(
                        tag
                    );
                }
            );
        }

        this._refreshInstallButton();
    }


    _renderLatestJob() {

        const job =
            this.latestJob
            ?? {};

        setText(
            "ota-job-id",
            job.jobId
            ?? "—"
        );

        setText(
            "ota-job-status",
            job.status
            ?? "IDLE"
        );

        const details =
            job.statusDetails
            ?? {};

        if (
            details.targetVersion
        ) {

            setText(
                "ota-target-version",
                details.targetVersion
            );
        }

        setText(
            "ota-self-test",
            details.selfTest
            ?? "NOT_RUN"
        );

        setText(
            "ota-rollback",
            String(
                details.rollbackPerformed
                ?? "false"
            ).toLowerCase()
            === "true"
            ? "YES"
            : "NO"
        );
    }


    _renderProgress(
        progress
    ) {

        const phase =
            String(
                progress?.phase
                ?? "IDLE"
            ).toUpperCase();

        const numeric =
            Number(
                progress?.progressPercentage
                ?? 0
            );

        const percentage =
            Number.isFinite(
                numeric
            )
            ? Math.max(
                0,
                Math.min(
                    100,
                    numeric
                )
            )
            : 0;

        setText(
            "ota-progress-phase",
            phase
        );

        setText(
            "ota-progress-percent",
            `${Math.round(percentage)}%`
        );

        const fill =
            byId(
                "ota-progress-fill"
            );

        if (
            fill
        ) {

            fill.style.width =
                `${percentage}%`;
        }

        this._renderPhaseSteps(
            phase
        );
    }


    _renderPhaseSteps(
        phase
    ) {

        const container =
            byId(
                "ota-progress-steps"
            );

        if (
            !container
        ) {
            return;
        }

        container.replaceChildren();

        const normalized =
            String(
                phase
                ?? "IDLE"
            ).toUpperCase();

        const currentIndex =
            PHASE_ORDER.indexOf(
                normalized
            );

        PHASE_ORDER.forEach(
            (
                value,
                index
            ) => {

                const step =
                    document.createElement(
                        "div"
                    );

                step.className =
                    "ota-progress-step";

                if (
                    normalized === "FAILED"
                    || normalized === "ROLLING_BACK"
                ) {

                    if (
                        value === "COMPLETED"
                    ) {

                        step.classList.add(
                            "failed"
                        );
                    }
                }

                else if (
                    currentIndex >= 0
                    && index < currentIndex
                ) {

                    step.classList.add(
                        "completed"
                    );
                }

                else if (
                    index === currentIndex
                ) {

                    step.classList.add(
                        normalized === "COMPLETED"
                        ? "completed"
                        : "active"
                    );
                }


                const title =
                    document.createElement(
                        "strong"
                    );

                title.textContent =
                    PHASE_LABELS[
                        value
                    ];


                const valueText =
                    document.createElement(
                        "span"
                    );

                if (
                    index < currentIndex
                    || normalized === "COMPLETED"
                ) {

                    valueText.textContent =
                        "Completed";
                }

                else if (
                    index === currentIndex
                ) {

                    valueText.textContent =
                        "In progress";
                }

                else {

                    valueText.textContent =
                        "Waiting";
                }

                step.append(
                    title,
                    valueText
                );

                container.appendChild(
                    step
                );
            }
        );
    }


    async _installSelected() {

        const release =
            this.releases.find(
                item => (
                    item.version
                    === this.selectedVersion
                )
            );

        if (
            !release
        ) {

            throw new Error(
                "Nije izabran OTA release."
            );
        }

        if (
            !release.uploaded
        ) {

            throw new Error(
                `HealthBand ${release.version} `
                + "nije uploadovan u privatni S3 bucket."
            );
        }

        if (
            !this._isNewer(
                release.version,
                this.currentVersion
            )
        ) {

            throw new Error(
                `Verzija ${release.version} nije novija `
                + `od aktivne verzije ${this.currentVersion ?? "—"}.`
            );
        }

        const confirmed =
            window.confirm(
                "Pokrenuti OTA nadogradnju "
                + `HealthBand ${this.currentVersion ?? "—"} `
                + `→ ${release.version}?`
            );

        if (
            !confirmed
        ) {
            return;
        }

        this.installing =
            true;

        this._refreshInstallButton();

        this._setStatusMessage(
            `Kreiram AWS IoT Job za HealthBand ${release.version}...`
        );

        try {

            const response =
                await this.api
                    .startOta(
                        release.version
                    );

            setText(
                "ota-target-version",
                response.targetVersion
                ?? release.version
            );

            setText(
                "ota-job-id",
                response.jobId
                ?? "—"
            );

            setText(
                "ota-job-status",
                response.status
                ?? "QUEUED"
            );

            this._renderProgress(
                {
                    phase:
                        "QUEUED",

                    progressPercentage:
                        0
                }
            );

            this._appendLog(
                {
                    timestamp:
                        new Date()
                        .toISOString(),

                    phase:
                        "QUEUED",

                    message:
                        `AWS IoT Job ${response.jobId ?? ""} `
                        + `created for ${release.version}.`
                }
            );

            this._setStatusMessage(
                "AWS IoT Job je kreiran. "
                + "Čeka se OTA supervisor uređaja...",
                "success"
            );
        }

        catch (error) {

            this.installing =
                false;

            this._refreshInstallButton();

            this._setStatusMessage(
                `OTA nije pokrenut: ${error.message}`,
                "error"
            );

            throw error;
        }
    }


    _refreshInstallButton() {

        const button =
            byId(
                "ota-install-button"
            );

        if (
            !button
        ) {
            return;
        }

        const release =
            this.releases.find(
                item => (
                    item.version
                    === this.selectedVersion
                )
            );

        const canInstall =
            Boolean(
                release?.uploaded
                && this._isNewer(
                    release.version,
                    this.currentVersion
                )
                && !this.installing
            );

        button.disabled =
            !canInstall;

        if (
            this.installing
        ) {

            button.textContent =
                "OTA in progress...";
        }

        else if (
            release
        ) {

            button.textContent =
                `Install HealthBand ${release.version}`;
        }

        else {

            button.textContent =
                "No newer uploaded release";
        }
    }


    _appendLog(
        progress
    ) {

        const log =
            byId(
                "ota-job-log"
            );

        if (
            !log
        ) {
            return;
        }

        if (
            log.dataset.empty
            === "true"
        ) {

            log.textContent =
                "";

            log.dataset.empty =
                "false";
        }

        const line =
            document.createElement(
                "div"
            );

        line.textContent =
            `[${formatTimestamp(
                progress.timestamp
                ?? new Date().toISOString()
            )}] `
            + `${progress.phase ?? "OTA"} · `
            + `${progress.message ?? "Status update"}`;

        log.appendChild(
            line
        );

        while (
            log.children.length
            > 80
        ) {

            log.firstElementChild
                ?.remove();
        }

        log.scrollTop =
            log.scrollHeight;
    }


    _setStatusMessage(
        message,
        kind = "neutral"
    ) {

        const element =
            byId(
                "ota-status-message"
            );

        if (
            !element
        ) {
            return;
        }

        element.textContent =
            message;

        element.className =
            "ota-status-message";

        if (
            kind === "success"
            || kind === "error"
        ) {

            element.classList.add(
                kind
            );
        }
    }


    _idleMessage() {

        const available =
            this.releases.filter(
                release => (
                    release.uploaded
                    && this._isNewer(
                        release.version,
                        this.currentVersion
                    )
                )
            );

        if (
            available.length
        ) {

            return (
                "Dostupna je novija OTA verzija: "
                + available
                    .map(
                        release =>
                            release.version
                    )
                    .join(
                        ", "
                    )
                + "."
            );
        }

        return (
            "Nema novije verzije koja je "
            + "spremna u privatnom S3 OTA bucketu."
        );
    }


    _jobStatusDetail(
        key
    ) {

        return (
            this.latestJob
            ?.statusDetails
            ?.[key]
            ?? null
        );
    }


    _isNewer(
        candidate,
        current
    ) {

        if (
            !candidate
        ) {
            return false;
        }

        if (
            !current
        ) {
            return true;
        }

        return (
            this._compareVersions(
                candidate,
                current
            ) > 0
        );
    }


    _compareVersions(
        left,
        right
    ) {

        const parse =
            value => (

                String(
                    value
                    ?? "0.0.0"
                )
                .split(
                    "."
                )
                .map(
                    part => (
                        Number(
                            part
                        ) || 0
                    )
                )
            );

        const a =
            parse(
                left
            );

        const b =
            parse(
                right
            );

        for (
            let index = 0;
            index < Math.max(
                a.length,
                b.length,
                3
            );
            index += 1
        ) {

            const difference =
                (a[index] ?? 0)
                - (b[index] ?? 0);

            if (
                difference !== 0
            ) {

                return difference;
            }
        }

        return 0;
    }
}