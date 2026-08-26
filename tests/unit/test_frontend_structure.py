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
        "js/api.js",
        "js/websocket.js",
        "js/dashboard.js",
        "js/simulation.js",
        "js/charts.js",
        "js/configuration.js",
        "js/commands.js",
        "js/device_health.js",
        "js/event_log.js",
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