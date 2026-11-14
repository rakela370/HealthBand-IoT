"""Regression tests for release-version-aware OTA packaging."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from scripts.build_release import DEFAULT_CAPABILITIES, build_release


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_release(
    archive: Path,
    manifest_path: Path,
    sha_path: Path,
    tmp_path: Path,
) -> tuple[dict, set[str]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_outer_hash = sha_path.read_text(encoding="utf-8").split()[0]
    assert _sha256(archive) == expected_outer_hash

    extract_root = tmp_path / (archive.stem + "-extract")
    with zipfile.ZipFile(archive, "r") as zf:
        names = set(zf.namelist())
        zf.extractall(extract_root)

    embedded = json.loads((extract_root / "manifest.json").read_text(encoding="utf-8"))
    assert embedded == manifest

    for relative, expected in manifest["files"].items():
        assert _sha256(extract_root / relative) == expected

    result = subprocess.run(
        [sys.executable, str(extract_root / "self_test.py")],
        cwd=extract_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "SELF_TEST_OK" in result.stdout
    return manifest, names


def test_builder_keeps_v1_baseline_and_v2_features_separate(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    output = tmp_path / "artifacts"

    v1 = build_release(
        source_root=project_root,
        version="1.0.0",
        minimum_current_version="1.0.0",
        capabilities=list(DEFAULT_CAPABILITIES),
        output_root=output,
    )
    v1_manifest, v1_names = _verify_release(*v1, tmp_path)
    assert "SPO2_MONITORING" not in v1_manifest["capabilities"]
    assert "CALORIE_ESTIMATION" not in v1_manifest["capabilities"]
    assert "payload/device_simulator/sensors/spo2_sensor.py" not in v1_names
    assert "payload/device_simulator/analytics/calorie_estimator.py" not in v1_names

    v2 = build_release(
        source_root=project_root,
        version="2.0.0",
        minimum_current_version="1.0.0",
        capabilities=list(DEFAULT_CAPABILITIES)
        + ["SPO2_MONITORING", "CALORIE_ESTIMATION"],
        output_root=output,
    )
    v2_manifest, v2_names = _verify_release(*v2, tmp_path)
    assert "SPO2_MONITORING" in v2_manifest["capabilities"]
    assert "CALORIE_ESTIMATION" in v2_manifest["capabilities"]
    assert "payload/device_simulator/sensors/spo2_sensor.py" in v2_names
    assert "payload/device_simulator/analytics/calorie_estimator.py" in v2_names
