"""Launch HealthBand from releases/active_release.json."""

import json
from pathlib import Path
import runpy
import sys


def resolve_active_payload(
    releases_root: Path | str = "releases",
) -> tuple[
    str,
    Path,
]:
    """Resolve active version and Python payload root."""

    root = (
        Path(
            releases_root
        )
        .resolve()
    )


    state_file = (
        root
        / "active_release.json"
    )


    if (
        not state_file
        .is_file()
    ):
        raise RuntimeError(
            "No releases/active_release.json "
            "found. Run bootstrap_release first."
        )


    data = (
        json.loads(
            state_file.read_text(
                encoding="utf-8"
            )
        )
    )


    version = str(
        data.get(
            "activeVersion",
            "",
        )
    ).strip()


    if (
        not version
    ):
        raise RuntimeError(
            "active_release.json does not "
            "contain activeVersion."
        )


    payload = (
        root
        / version
        / "payload"
    )


    entry = (
        payload
        / "device_simulator"
        / "main.py"
    )


    if (
        not entry
        .is_file()
    ):
        raise RuntimeError(
            f"Active release {version} "
            f"is incomplete: {entry}"
        )


    return (
        version,
        payload,
    )


def main() -> None:
    """Start active installed HealthBand release."""

    (
        version,
        payload,
    ) = (
        resolve_active_payload()
    )


    print(
        (
            "Starting HealthBand "
            f"active release {version}"
        )
    )


    sys.path.insert(
        0,
        str(
            payload
        ),
    )


    for module_name in list(
        sys.modules
    ):

        if (
            module_name
            == "device_simulator"
            or module_name.startswith(
                "device_simulator."
            )
        ):

            del sys.modules[
                module_name
            ]


    runpy.run_module(
        "device_simulator.main",
        run_name="__main__",
    )


if __name__ == "__main__":
    main()