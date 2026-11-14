"""End-to-end regression for the v1 offline watch data path.

This test uses the exact installed 1.0.0 payload in a child process and the
root FastAPI local-telemetry bridge in the parent process. It protects the
specific diploma-demo failure where the watch froze after NETWORK_OUTAGE.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import sys
import textwrap
from typing import Any

import pytest

from control_backend.services.local_device_bridge import LocalDeviceTelemetryBridge
from control_backend.services.realtime_state_store import RealtimeStateStore


class RecordingBroadcaster:
    """Collect realtime broadcasts exactly where the existing frontend listens."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str, dict[str, Any]]] = []

    async def broadcast(
        self,
        device_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        self.messages.append((device_id, event_type, dict(data)))


@pytest.mark.asyncio
async def test_installed_v1_offline_readings_reach_existing_realtime_channel(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    payload = project_root / "releases" / "1.0.0" / "payload"
    database_path = tmp_path / "healthband.db"

    child_code = textwrap.dedent(
        r'''
        import asyncio
        import os
        from pathlib import Path
        from typing import Any

        from device_simulator.communication.mqtt_client import IncomingMqttMessage
        from device_simulator.core.device_controller import DeviceController
        from device_simulator.core.event_bus import EventBus
        from device_simulator.core.scheduler import Scheduler
        from device_simulator.simulation.scenario import SimulationScenario
        from device_simulator.storage.local_database import LocalDatabase
        from device_simulator.storage.offline_queue import OfflineQueue


        class FakeMqttClient:
            def __init__(self) -> None:
                self.connected = False
                self.incoming = []

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
                random_seed=17,
                mqtt_client=mqtt,
                offline_queue=queue,
            )
            await controller.start()
            controller.change_scenario(SimulationScenario.RUNNING)

            # Establish an in-progress running state first.
            for _ in range(8):
                await controller.read_sensors_now()

            mqtt.incoming.append(
                IncomingMqttMessage(
                    topic=controller.mqtt_topics.commands_request,
                    payload={
                        "schemaVersion": 1,
                        "commandId": "v1-offline-watch-e2e",
                        "deviceId": controller.device_id,
                        "type": "SIMULATE_NETWORK_OUTAGE",
                        "parameters": {"durationSec": 40},
                    },
                    duplicate=False,
                    retained=False,
                )
            )
            await controller.process_mqtt_messages_now()

            # Generate multiple real local readings while AWS/MQTT is down.
            for _ in range(14):
                await controller.read_sensors_now()
                await controller._publish_latest_telemetry(force=True)
                await asyncio.sleep(0.07)

            await controller.shutdown()


        asyncio.run(main())
        '''
    )

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(payload) + (os.pathsep + existing if existing else "")
    env["HB_TEST_DB"] = str(database_path)

    process = subprocess.Popen(
        [sys.executable, "-c", child_code],
        cwd=project_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    broadcaster = RecordingBroadcaster()
    bridge = LocalDeviceTelemetryBridge(
        device_id="healthband-device-001",
        database_path=database_path,
        realtime_store=RealtimeStateStore(),
        broadcaster=broadcaster,  # type: ignore[arg-type]
        poll_interval_sec=0.02,
        maximum_age_sec=30.0,
    )

    deadline = asyncio.get_running_loop().time() + 8.0
    while process.poll() is None and asyncio.get_running_loop().time() < deadline:
        await bridge.poll_once()
        await asyncio.sleep(0.02)

    # Drain a final state if the child completed between polls.
    await bridge.poll_once()

    stdout, stderr = process.communicate(timeout=5)
    assert process.returncode == 0, stdout + "\n" + stderr

    offline = [
        data
        for _, event_type, data in broadcaster.messages
        if event_type == "telemetry" and data.get("deviceState") == "OFFLINE"
    ]

    assert len(offline) >= 3
    assert all(sample.get("scenario") == "RUNNING" for sample in offline)
    assert all(sample.get("activityLevel") == "HIGH" for sample in offline)

    first_measurements = offline[0]["measurements"]
    last_measurements = offline[-1]["measurements"]

    assert float(last_measurements["heartRateBpm"]) > float(
        first_measurements["heartRateBpm"]
    )
    assert int(last_measurements["totalDailySteps"]) > int(
        first_measurements["totalDailySteps"]
    )
    assert float(last_measurements["batteryPercentage"]) < float(
        first_measurements["batteryPercentage"]
    )
