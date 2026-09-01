"""Run HealthBand as a desktop application.

The existing architecture remains unchanged:

    simulated device
        -> AWS IoT Core
        -> FastAPI backend
        -> existing web frontend
        -> desktop WebView

The WebView only replaces the visible browser window.

Usage:
    python -m scripts.run_healthband_desktop
    python -m scripts.run_healthband_desktop --reset-v1
    python -m scripts.run_healthband_desktop --windowed
    python -m scripts.run_healthband_desktop --stop
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.request import (
    urlopen,
)

from scripts.reset_demo_to_v1 import (
    DemoResetError,
    reset_demo_to_v1,
)


HOST = (
    "127.0.0.1"
)

PORT = (
    8000
)

APP_URL = (
    f"http://{HOST}:{PORT}"
)

DEVICE_ID = (
    "healthband-device-001"
)

DEVICE_API_URL = (
    f"{APP_URL}/api/devices/{DEVICE_ID}"
)

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

RUNTIME_ROOT = (
    PROJECT_ROOT
    / "runtime"
)

PROCESS_STATE_FILE = (
    RUNTIME_ROOT
    / "healthband_desktop_processes.json"
)

BACKEND_LOG_FILE = (
    RUNTIME_ROOT
    / "healthband_desktop_backend.log"
)

DEVICE_LOG_FILE = (
    RUNTIME_ROOT
    / "healthband_desktop_device.log"
)

BACKEND_TIMEOUT_SECONDS = (
    120.0
)

DEVICE_TIMEOUT_SECONDS = (
    120.0
)


class DesktopLauncherError(
    RuntimeError
):
    """HealthBand desktop launcher failed."""


def parse_args() -> argparse.Namespace:
    """Read command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Run HealthBand inside a desktop "
            "application window."
        )
    )

    parser.add_argument(
        "--reset-v1",
        action="store_true",
        help=(
            "Reset the local demo to HealthBand "
            "1.0.0 before startup."
        ),
    )

    parser.add_argument(
        "--windowed",
        action="store_true",
        help=(
            "Open HealthBand in a normal desktop "
            "window instead of fullscreen."
        ),
    )

    parser.add_argument(
        "--stop",
        action="store_true",
        help=(
            "Stop HealthBand processes previously "
            "started by this launcher."
        ),
    )

    return (
        parser.parse_args()
    )


def ensure_runtime_directory() -> None:
    """Ensure the local runtime directory exists."""

    RUNTIME_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )


def ensure_webview_available() -> None:
    """Fail before startup if pywebview is unavailable."""

    try:

        import webview  # noqa: F401

    except ModuleNotFoundError as exc:

        raise DesktopLauncherError(
            "pywebview is not installed.\n\n"
            "Install it once with:\n"
            ".\\.venv\\Scripts\\python.exe "
            "-m pip install pywebview"
        ) from exc


def port_is_in_use() -> bool:
    """Return True if something already listens on port 8000."""

    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as probe:

        probe.settimeout(
            0.3
        )

        return (
            probe.connect_ex(
                (
                    HOST,
                    PORT,
                )
            )
            == 0
        )


def creation_flags() -> int:
    """Return Windows child-process flags."""

    if (
        os.name
        == "nt"
    ):

        return (
            subprocess
            .CREATE_NEW_PROCESS_GROUP
        )

    return (
        0
    )


def open_log_file(
    path: Path,
):
    """Open a process log in append mode."""

    ensure_runtime_directory()

    return path.open(
        "a",
        encoding="utf-8",
        buffering=1,
    )


def start_process(
    arguments: list[
        str
    ],
    log_path: Path,
) -> tuple[
    subprocess.Popen[Any],
    Any,
]:
    """Start one HealthBand child process."""

    log_handle = (
        open_log_file(
            log_path
        )
    )

    process = (
        subprocess.Popen(
            arguments,
            cwd=(
                PROJECT_ROOT
            ),
            stdout=(
                log_handle
            ),
            stderr=(
                subprocess.STDOUT
            ),
            text=True,
            creationflags=(
                creation_flags()
            ),
        )
    )

    return (
        process,
        log_handle,
    )


def tail_log(
    path: Path,
    maximum_lines: int = 25,
) -> str:
    """Return last lines of a process log."""

    if not path.is_file():

        return (
            "(log file does not exist)"
        )

    try:

        lines = (
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
            .splitlines()
        )

    except OSError as exc:

        return (
            "Unable to read log: "
            f"{exc}"
        )

    if not lines:

        return (
            "(log file is empty)"
        )

    return "\n".join(
        lines[
            -maximum_lines:
        ]
    )


def start_backend() -> tuple[
    subprocess.Popen[Any],
    Any,
]:
    """Start FastAPI without --reload."""

    if port_is_in_use():

        raise DesktopLauncherError(
            f"Port {PORT} is already in use.\n\n"
            "Ugasi stari Uvicorn/HealthBand proces "
            "prije pokretanja desktop aplikacije."
        )

    BACKEND_LOG_FILE.unlink(
        missing_ok=True
    )

    print()

    print(
        "Starting HealthBand FastAPI backend..."
    )

    return start_process(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "control_backend.main:app",
            "--host",
            HOST,
            "--port",
            str(
                PORT
            ),
        ],
        BACKEND_LOG_FILE,
    )


def wait_for_backend(
    backend_process: subprocess.Popen[Any],
) -> None:
    """Wait until FastAPI responds with HTTP 200."""

    print(
        "Waiting for FastAPI backend..."
    )

    deadline = (
        time.monotonic()
        + BACKEND_TIMEOUT_SECONDS
    )

    while (
        time.monotonic()
        < deadline
    ):

        return_code = (
            backend_process.poll()
        )

        if (
            return_code
            is not None
        ):

            raise DesktopLauncherError(
                "FastAPI backend stopped during startup.\n"
                f"Exit code: {return_code}\n\n"
                "Backend log:\n"
                f"{tail_log(BACKEND_LOG_FILE)}"
            )

        try:

            with urlopen(
                APP_URL,
                timeout=2.0,
            ) as response:

                if (
                    response.status
                    == 200
                ):

                    print(
                        "FastAPI backend: READY"
                    )

                    return

        except (
            HTTPError,
            URLError,
            TimeoutError,
            OSError,
        ):

            pass

        time.sleep(
            0.5
        )

    raise DesktopLauncherError(
        "FastAPI backend did not become ready "
        f"within {BACKEND_TIMEOUT_SECONDS:.0f} seconds.\n\n"
        "Backend log:\n"
        f"{tail_log(BACKEND_LOG_FILE)}"
    )


def start_device() -> tuple[
    subprocess.Popen[Any],
    Any,
]:
    """Start managed simulated device and OTA supervisor."""

    DEVICE_LOG_FILE.unlink(
        missing_ok=True
    )

    print()

    print(
        "Starting HealthBand managed device..."
    )

    (
        process,
        log_handle,
    ) = start_process(
        [
            sys.executable,
            "-m",
            "scripts.run_managed_device",
        ],
        DEVICE_LOG_FILE,
    )

    time.sleep(
        1.0
    )

    if (
        process.poll()
        is not None
    ):

        raise DesktopLauncherError(
            "HealthBand managed device stopped "
            "during startup.\n\n"
            "Device log:\n"
            f"{tail_log(DEVICE_LOG_FILE)}"
        )

    return (
        process,
        log_handle,
    )


def device_payload_is_ready(
    payload: Any,
) -> bool:
    """Return True when backend contains live telemetry."""

    if not isinstance(
        payload,
        dict,
    ):

        return (
            False
        )

    latest_telemetry = (
        payload.get(
            "latestTelemetry"
        )
    )

    if isinstance(
        latest_telemetry,
        dict,
    ):

        if (
            latest_telemetry.get(
                "softwareVersion"
            )
        ):

            return (
                True
            )

        measurements = (
            latest_telemetry.get(
                "measurements"
            )
        )

        if (
            isinstance(
                measurements,
                dict,
            )
            and measurements
        ):

            return (
                True
            )

    if (
        payload.get(
            "softwareVersion"
        )
    ):

        return (
            True
        )

    return (
        False
    )


def wait_for_device(
    device_process: subprocess.Popen[Any],
) -> None:
    """Wait until the managed device has published live data."""

    print(
        "Waiting for HealthBand device..."
    )

    deadline = (
        time.monotonic()
        + DEVICE_TIMEOUT_SECONDS
    )

    while (
        time.monotonic()
        < deadline
    ):

        return_code = (
            device_process.poll()
        )

        if (
            return_code
            is not None
        ):

            raise DesktopLauncherError(
                "HealthBand managed device stopped "
                "during startup.\n"
                f"Exit code: {return_code}\n\n"
                "Device log:\n"
                f"{tail_log(DEVICE_LOG_FILE)}"
            )

        try:

            with urlopen(
                DEVICE_API_URL,
                timeout=2.0,
            ) as response:

                if (
                    200
                    <= response.status
                    < 300
                ):

                    raw = (
                        response.read()
                        .decode(
                            "utf-8"
                        )
                    )

                    payload = (
                        json.loads(
                            raw
                        )
                    )

                    if (
                        device_payload_is_ready(
                            payload
                        )
                    ):

                        print(
                            "HealthBand device: READY"
                        )

                        return

        except (
            HTTPError,
            URLError,
            TimeoutError,
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):

            pass

        time.sleep(
            0.75
        )

    print()

    print(
        "WARNING: Device readiness was not "
        "confirmed through REST within "
        f"{DEVICE_TIMEOUT_SECONDS:.0f} seconds."
    )

    print(
        "The managed device is still running, "
        "so the desktop application will open."
    )

    print()


def write_process_state(
    backend_process: subprocess.Popen[Any],
    device_process: subprocess.Popen[Any],
) -> None:
    """Remember launcher-owned processes."""

    ensure_runtime_directory()

    state = {

        "launcherPid":
            os.getpid(),

        "backendPid":
            backend_process.pid,

        "devicePid":
            device_process.pid,
    }

    PROCESS_STATE_FILE.write_text(
        json.dumps(
            state,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def remove_process_state() -> None:
    """Remove recorded desktop process state."""

    PROCESS_STATE_FILE.unlink(
        missing_ok=True
    )


def kill_pid_tree(
    pid: int,
) -> None:
    """Terminate one process tree."""

    if (
        pid
        <= 0
    ):

        return

    if (
        os.name
        == "nt"
    ):

        subprocess.run(
            [
                "taskkill",
                "/PID",
                str(
                    pid
                ),
                "/T",
                "/F",
            ],
            stdout=(
                subprocess.DEVNULL
            ),
            stderr=(
                subprocess.DEVNULL
            ),
            check=False,
        )

        return

    try:

        os.kill(
            pid,
            15,
        )

    except OSError:

        pass


def stop_process(
    process: subprocess.Popen[Any] | None,
) -> None:
    """Stop a launcher-owned process if alive."""

    if (
        process
        is None
    ):

        return

    if (
        process.poll()
        is not None
    ):

        return

    kill_pid_tree(
        process.pid
    )


def stop_recorded_processes(
    quiet: bool = False,
) -> None:
    """Stop child processes recorded by previous launcher run."""

    if not PROCESS_STATE_FILE.is_file():

        if not quiet:

            print(
                "No recorded HealthBand desktop "
                "processes were found."
            )

        return

    try:

        state = json.loads(
            PROCESS_STATE_FILE.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:

        remove_process_state()

        raise DesktopLauncherError(
            "Unable to read previous HealthBand "
            "desktop process state."
        ) from exc

    for key in (
        "devicePid",
        "backendPid",
    ):

        try:

            pid = int(
                state.get(
                    key,
                    0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            pid = (
                0
            )

        kill_pid_tree(
            pid
        )

    remove_process_state()

    if not quiet:

        print(
            "Recorded HealthBand processes stopped."
        )


def open_desktop_window(
    fullscreen: bool,
) -> None:
    """Open frontend inside native pywebview."""

    import webview

    print()

    print(
        "========================================"
    )

    print(
        " HealthBand Desktop"
    )

    print(
        "========================================"
    )

    print()

    print(
        "Opening HealthBand application..."
    )

    print(
        "ALT + F4 closes HealthBand."
    )

    print()

    webview.create_window(
        title="HealthBand",
        url=APP_URL,
        width=1440,
        height=900,
        resizable=True,
        fullscreen=fullscreen,
        background_color="#071018",
    )

    webview.start()


def close_log_handle(
    handle: Any,
) -> None:
    """Close one child-process log handle."""

    if (
        handle
        is None
    ):

        return

    try:

        handle.close()

    except OSError:

        pass


def run_application(
    fullscreen: bool,
) -> None:
    """Start complete HealthBand desktop environment."""

    backend_process: (
        subprocess.Popen[Any]
        | None
    ) = None

    device_process: (
        subprocess.Popen[Any]
        | None
    ) = None

    backend_log_handle: Any = (
        None
    )

    device_log_handle: Any = (
        None
    )

    try:

        ensure_webview_available()

        (
            backend_process,
            backend_log_handle,
        ) = start_backend()

        wait_for_backend(
            backend_process
        )

        (
            device_process,
            device_log_handle,
        ) = start_device()

        write_process_state(
            backend_process,
            device_process,
        )

        wait_for_device(
            device_process
        )

        open_desktop_window(
            fullscreen=(
                fullscreen
            )
        )

    finally:

        print()

        print(
            "Closing HealthBand..."
        )

        stop_process(
            device_process
        )

        stop_process(
            backend_process
        )

        close_log_handle(
            device_log_handle
        )

        close_log_handle(
            backend_log_handle
        )

        remove_process_state()

        print(
            "HealthBand stopped."
        )


def main() -> None:
    """Command-line entry point."""

    args = (
        parse_args()
    )

    try:

        if args.stop:

            stop_recorded_processes()

            return

        ensure_webview_available()

        if args.reset_v1:

            stop_recorded_processes(
                quiet=True
            )

            time.sleep(
                0.5
            )

            reset_demo_to_v1()

        run_application(
            fullscreen=(
                not args.windowed
            )
        )

    except KeyboardInterrupt:

        print()

        print(
            "HealthBand interrupted by user."
        )

    except (
        DesktopLauncherError,
        DemoResetError,
    ) as exc:

        print()

        print(
            "HEALTHBAND STARTUP ERROR"
        )

        print(
            "------------------------"
        )

        print(
            str(
                exc
            )
        )

        print()

        raise SystemExit(
            1
        ) from exc


if __name__ == "__main__":

    main()