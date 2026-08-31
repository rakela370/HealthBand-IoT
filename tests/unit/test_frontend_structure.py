"""Structural tests for the HealthBand web frontend."""

from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

FRONTEND = (
    ROOT
    / "web_frontend"
)


def read(
    relative_path: str,
) -> str:
    """Read one frontend source file."""

    return (
        FRONTEND
        .joinpath(
            relative_path
        )
        .read_text(
            encoding="utf-8"
        )
    )


def test_main_frontend_files_exist() -> None:
    required = [
        "index.html",
        "css/variables.css",
        "css/layout.css",
        "css/components.css",
        "css/animations.css",
        "css/ota.css",
        "js/api.js",
        "js/websocket.js",
        "js/dashboard.js",
        "js/simulation.js",
        "js/charts.js",
        "js/configuration.js",
        "js/commands.js",
        "js/device_health.js",
        "js/event_log.js",
        "js/ota.js",
        "js/app.js",
        "assets/vendor/chart.umd.min.js",
    ]

    for relative_path in required:
        assert (
            FRONTEND
            .joinpath(
                relative_path
            )
            .is_file()
        ), relative_path


def test_frontend_contains_required_navigation() -> None:
    html = (
        read(
            "index.html"
        )
    )

    required_labels = [
        "Dashboard",
        "Live Simulation",
        "History",
        "Configuration",
        "Commands",
        "Device Health",
        "OTA Update",
        "Event Log",
    ]

    for label in required_labels:
        assert (
            label
            in html
        )


def test_frontend_contains_required_disclaimer() -> None:
    html = (
        read(
            "index.html"
        )
    )

    assert (
        "Svi prikazani podaci su simulirani."
        in html
    )

    assert (
        "Sistem nije medicinski uređaj."
        in html
    )


def test_heart_animation_uses_bpm_relation() -> None:
    source = (
        read(
            "js/simulation.js"
        )
    )

    assert (
        "60000 / bpm"
        in source
    )


def test_frontend_contains_no_aws_credentials() -> None:
    source = "\n".join(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
        for path
        in FRONTEND.rglob(
            "*"
        )
        if (
            path.is_file()
            and path.suffix
            in {
                ".html",
                ".js",
                ".css",
            }
        )
    )

    forbidden = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "private.pem.key",
        "backend.private.key",
    ]

    for value in forbidden:
        assert (
            value
            not in source
        )


def test_version2_frontend_hooks_are_present() -> None:
    html = (
        read(
            "index.html"
        )
    )

    dashboard = (
        read(
            "js/dashboard.js"
        )
    )

    simulation = (
        read(
            "js/simulation.js"
        )
    )

    charts = (
        read(
            "js/charts.js"
        )
    )

    configuration = (
        read(
            "js/configuration.js"
        )
    )

    required_ids = [
        "sensor-spo2-card",
        "watch-spo2-row",
        "spo2-chart-card",
        "sensor-calories-card",
        "watch-calories-row",
        "calories-chart-card",
        "config-spo2-section",
        "config-spo2-minimum",
        "config-spo2-enabled",
        "config-spo2-alerts",
    ]

    for value in required_ids:
        assert (
            value
            in html
        )

    assert (
        "oxygenSaturationPercentage"
        in dashboard
    )

    assert (
        "caloriesBurnedToday"
        in dashboard
    )

    assert (
        "caloriesBurnedToday"
        in simulation
    )

    assert (
        "dailyTotalKcal"
        in charts
    )

    assert (
        "SPO2_MONITORING"
        in configuration
    )


def test_module12_ota_frontend_is_fully_wired() -> None:
    html = (
        read(
            "index.html"
        )
    )

    api = (
        read(
            "js/api.js"
        )
    )

    app = (
        read(
            "js/app.js"
        )
    )

    ota = (
        read(
            "js/ota.js"
        )
    )

    required_ids = [
        "ota-refresh",
        "ota-current-version",
        "ota-job-status",
        "ota-target-version",
        "ota-release-list",
        "ota-selected-version",
        "ota-install-button",
        "ota-progress-phase",
        "ota-progress-percent",
        "ota-progress-fill",
        "ota-progress-steps",
        "ota-job-id",
        "ota-self-test",
        "ota-rollback",
        "ota-status-message",
        "ota-job-log",
    ]

    for value in required_ids:
        assert (
            value
            in html
        )

    assert (
        "css/ota.css"
        in html
    )

    assert (
        "getOtaState"
        in api
    )

    assert (
        "startOta"
        in api
    )

    assert (
        "targetVersion"
        in api
    )

    assert (
        'case "ota"'
        in app
    )

    assert (
        "ota.handleRealtime"
        in app
    )

    assert (
        "await ota.load()"
        in app
    )

    assert (
        "AWS IoT Job"
        in ota
    )

    assert (
        "ROLLING_BACK"
        in ota
    )

    assert (
        "SELF_TEST"
        in ota
    )

    assert (
        "COMPLETED"
        in ota
    )


def test_module12_placeholder_is_not_present() -> None:
    html = (
        read(
            "index.html"
        )
    )

    forbidden = [
        "OTA frontend is prepared",
        "No release available yet",
        (
            "AWS IoT Jobs biće implementirani "
            "u narednim modulima"
        ),
    ]

    for value in forbidden:
        assert (
            value
            not in html
        )