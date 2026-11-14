"""Cross-release persistence regression for the v1 -> v2 OTA path."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap


def _run_python(
    *,
    project_root: Path,
    pythonpath_first: Path,
    code: str,
    env_extra: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(pythonpath_first) + (
        os.pathsep + existing if existing else ""
    )
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
    )


def test_v1_runtime_state_is_restored_by_v2_without_reset(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    v1_payload = project_root / "releases" / "1.0.0" / "payload"
    database_path = tmp_path / "healthband.db"
    expected_path = tmp_path / "expected.json"

    v1_code = textwrap.dedent(
        r'''
        import asyncio
        import json
        import os
        from pathlib import Path

        from device_simulator.core.device_controller import DeviceController
        from device_simulator.core.event_bus import EventBus
        from device_simulator.core.scheduler import Scheduler
        from device_simulator.simulation.scenario import SimulationScenario
        from device_simulator.storage.local_database import LocalDatabase
        from device_simulator.storage.offline_queue import OfflineQueue

        async def main():
            db = LocalDatabase(Path(os.environ["HB_DB"]))
            controller = DeviceController(
                software_version="1.0.0",
                event_bus=EventBus(),
                scheduler=Scheduler(),
                random_seed=4,
                mqtt_client=None,
                offline_queue=OfflineQueue(database=db, maximum_items=1000),
            )
            controller.change_scenario(SimulationScenario.RUNNING)
            for _ in range(30):
                await controller.read_sensors_now()

            battery = controller.sensor_manager.get_sensor("battery")
            battery.set_percentage(70.0)
            controller._persist_runtime_state()
            state = controller.sensor_manager.export_runtime_state()
            Path(os.environ["HB_EXPECTED"]).write_text(
                json.dumps(
                    {
                        "heartRateBpm": state["heartRateBpm"],
                        "skinTemperatureCelsius": state["skinTemperatureCelsius"],
                        "totalDailySteps": state["totalDailySteps"],
                        "fractionalSteps": state["fractionalSteps"],
                        "cadenceStepsPerMinute": state["cadenceStepsPerMinute"],
                        "batteryPercentage": state["batteryPercentage"],
                        "charging": state["charging"],
                    }
                ),
                encoding="utf-8",
            )

        asyncio.run(main())
        '''
    )
    result = _run_python(
        project_root=project_root,
        pythonpath_first=v1_payload,
        code=v1_code,
        env_extra={
            "HB_DB": str(database_path),
            "HB_EXPECTED": str(expected_path),
        },
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    assert expected["totalDailySteps"] > 0
    assert expected["batteryPercentage"] == 70.0

    v2_code = textwrap.dedent(
        r'''
        import json
        import os
        from pathlib import Path

        from device_simulator.core.device_controller import DeviceController
        from device_simulator.core.event_bus import EventBus
        from device_simulator.core.scheduler import Scheduler
        from device_simulator.simulation.scenario import SimulationScenario
        from device_simulator.storage.local_database import LocalDatabase
        from device_simulator.storage.offline_queue import OfflineQueue

        expected = json.loads(Path(os.environ["HB_EXPECTED"]).read_text(encoding="utf-8"))
        db = LocalDatabase(Path(os.environ["HB_DB"]))
        controller = DeviceController(
            software_version="2.0.0",
            event_bus=EventBus(),
            scheduler=Scheduler(),
            random_seed=8,
            mqtt_client=None,
            offline_queue=OfflineQueue(database=db, maximum_items=1000),
        )
        state = controller.sensor_manager.export_runtime_state()

        assert controller.current_scenario == SimulationScenario.RUNNING
        assert controller.sensor_manager.has_sensor("spo2")
        assert controller.calorie_estimator is not None
        assert state["totalDailySteps"] == expected["totalDailySteps"]
        assert state["fractionalSteps"] == expected["fractionalSteps"]
        assert state["cadenceStepsPerMinute"] == expected["cadenceStepsPerMinute"]
        assert state["heartRateBpm"] == expected["heartRateBpm"]
        assert state["skinTemperatureCelsius"] == expected["skinTemperatureCelsius"]
        assert state["batteryPercentage"] == 70.0
        assert state["charging"] is False
        '''
    )
    result = _run_python(
        project_root=project_root,
        pythonpath_first=project_root,
        code=v2_code,
        env_extra={
            "HB_DB": str(database_path),
            "HB_EXPECTED": str(expected_path),
        },
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
