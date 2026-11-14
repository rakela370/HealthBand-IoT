"""Regression tests against the exact payload launched by Start-HealthBand-v1.cmd."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap


def test_installed_v1_payload_keeps_running_during_network_outage(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    payload = project_root / "releases" / "1.0.0" / "payload"
    database_path = tmp_path / "healthband.db"

    code = textwrap.dedent(
        r'''
        import asyncio
        import json
        import os
        from pathlib import Path
        from typing import Any

        from device_simulator.communication.mqtt_client import IncomingMqttMessage
        from device_simulator.core.device_controller import DeviceController
        from device_simulator.core.device_state import DeviceState
        from device_simulator.core.event_bus import EventBus
        from device_simulator.core.scheduler import Scheduler
        from device_simulator.simulation.scenario import SimulationScenario
        from device_simulator.storage.local_database import LocalDatabase
        from device_simulator.storage.offline_queue import OfflineQueue


        class FakeMqttClient:
            def __init__(self) -> None:
                self.connected = False
                self.incoming = []
                self.published = []

            @property
            def is_connected(self) -> bool:
                return self.connected

            def connect(self) -> None:
                self.connected = True

            def disconnect(self) -> None:
                self.connected = False

            def subscribe(self, topic: str, qos: int = 1) -> None:
                pass

            def resubscribe_all(self) -> None:
                pass

            def publish(self, topic: str, payload: dict[str, Any], qos: int) -> str:
                if not self.connected:
                    raise ConnectionError("MQTT disconnected")
                self.published.append((topic, dict(payload), qos))
                return str(payload.get("messageId", "fake"))

            def drain_incoming_messages(self, maximum_items: int = 100):
                result = self.incoming[:maximum_items]
                del self.incoming[:maximum_items]
                return result


        async def main() -> None:
            db = LocalDatabase(Path(os.environ["HB_TEST_DB"]))
            queue = OfflineQueue(database=db, maximum_items=1000)
            mqtt = FakeMqttClient()
            controller = DeviceController(
                event_bus=EventBus(),
                scheduler=Scheduler(),
                random_seed=7,
                mqtt_client=mqtt,
                offline_queue=queue,
            )
            await controller.start()
            controller.change_scenario(SimulationScenario.RUNNING)

            for _ in range(6):
                await controller.read_sensors_now()

            before = controller.latest_snapshot
            assert before is not None
            before_hr = float(before.measurements["heartRateBpm"])
            before_steps = int(before.measurements["totalDailySteps"])
            before_battery = float(before.measurements["batteryPercentage"])

            mqtt.incoming.append(
                IncomingMqttMessage(
                    topic=controller.mqtt_topics.commands_request,
                    payload={
                        "schemaVersion": 1,
                        "commandId": "v1-outage-regression",
                        "deviceId": controller.device_id,
                        "type": "SIMULATE_NETWORK_OUTAGE",
                        "parameters": {"durationSec": 40},
                    },
                    duplicate=False,
                    retained=False,
                )
            )
            await controller.process_mqtt_messages_now()

            assert controller.current_state == DeviceState.OFFLINE
            assert controller.current_scenario == SimulationScenario.RUNNING
            assert mqtt.connected is False

            for _ in range(20):
                await controller.read_sensors_now()
                await controller._publish_latest_telemetry(force=True)

            after = controller.latest_snapshot
            assert after is not None
            assert after.scenario == "RUNNING"
            assert after.activity_level == "HIGH"
            assert float(after.measurements["heartRateBpm"]) > before_hr
            assert int(after.measurements["totalDailySteps"]) > before_steps
            assert float(after.measurements["batteryPercentage"]) < before_battery
            assert queue.size() > 0

            raw = db.get_state(controller.RUNTIME_STATE_KEY)
            assert raw is not None
            state = json.loads(raw)
            assert state["physiologicalScenario"] == "RUNNING"
            assert state["latestTelemetry"]["deviceState"] == "OFFLINE"
            assert state["latestTelemetry"]["scenario"] == "RUNNING"

            # The installed v1 command path must restore a failed sensor
            # without changing RUNNING and without the next read failing it
            # again.
            from types import SimpleNamespace
            await controller._command_simulate_sensor_failure(
                SimpleNamespace(parameters={"sensorName": "heart_rate"})
            )
            failed = await controller.read_sensors_now()
            assert failed.scenario == "RUNNING"
            assert failed.sensor_status["heart_rate"] == "FAILED"
            assert "heartRateBpm" not in failed.measurements

            await controller._command_restore_sensor(
                SimpleNamespace(parameters={"sensorName": "heart_rate"})
            )
            restored_reading = await controller.read_sensors_now()
            assert restored_reading.scenario == "RUNNING"
            assert restored_reading.sensor_status["heart_rate"] == "OK"
            assert "heartRateBpm" in restored_reading.measurements

            # Expire the outage and execute the exact automatic reconnect path
            # used by the installed v1 device. Queued offline messages must be
            # flushed without changing the user's physical activity.
            controller._simulated_outage_until = 0.0
            await controller._connection_watch_tick()
            assert mqtt.connected is True
            assert controller.current_state == DeviceState.MONITORING
            assert controller.current_scenario == SimulationScenario.RUNNING
            assert queue.size() == 0

            persisted_after_reconnect = db.get_state(controller.RUNTIME_STATE_KEY)
            assert persisted_after_reconnect is not None
            reconnect_state = json.loads(persisted_after_reconnect)
            assert reconnect_state["deviceState"] == "MONITORING"
            assert reconnect_state["physiologicalScenario"] == "RUNNING"

            # Capture the newest state after the failure/restore/reconnect
            # operations above.
            # Those reads legitimately advance steps/battery/HR, so restart
            # persistence must be compared with the state immediately before
            # process replacement rather than the earlier outage snapshot.
            expected_runtime_state = controller.sensor_manager.export_runtime_state()

            # Simulate process replacement (restart / OTA activation) on the
            # same runtime database. Core local state must survive exactly.
            restored = DeviceController(
                event_bus=EventBus(),
                scheduler=Scheduler(),
                random_seed=99,
                mqtt_client=None,
                offline_queue=OfflineQueue(database=db, maximum_items=1000),
            )
            restored_state = restored.sensor_manager.export_runtime_state()
            assert restored.current_scenario == SimulationScenario.RUNNING
            assert restored_state["totalDailySteps"] == expected_runtime_state["totalDailySteps"]
            assert restored_state["batteryPercentage"] == expected_runtime_state["batteryPercentage"]
            assert restored_state["heartRateBpm"] == expected_runtime_state["heartRateBpm"]

            await controller.shutdown()

        asyncio.run(main())
        '''
    )

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(payload) + (os.pathsep + existing if existing else "")
    env["HB_TEST_DB"] = str(database_path)

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=project_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
