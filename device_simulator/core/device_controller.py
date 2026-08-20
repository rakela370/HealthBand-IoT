"""Central controller for the simulated HealthBand device."""

import asyncio
import logging
from typing import Optional

from device_simulator.core.device_state import DeviceState
from device_simulator.core.event_bus import EventBus
from device_simulator.core.scheduler import Scheduler
from device_simulator.core.state_machine import StateMachine, StateTransition

logger = logging.getLogger(__name__)


class DeviceController:
    STATE_CHANGED_EVENT = "device.state_changed"

    def __init__(
        self,
        device_id: str = "healthband-device-001",
        software_version: str = "1.0.0",
        event_bus: Optional[EventBus] = None,
        scheduler: Optional[Scheduler] = None,
    ) -> None:
        self.device_id = device_id
        self.software_version = software_version
        self.event_bus = event_bus or EventBus()
        self.scheduler = scheduler or Scheduler()
        self.state_machine = StateMachine()

        self.scheduler.add_job(
            name="core_status_tick",
            interval_sec=5.0,
            callback=self._log_core_status,
        )

    @property
    def current_state(self) -> DeviceState:
        return self.state_machine.current_state

    async def start(self) -> None:
        logger.info(
            "Starting HealthBand device controller | id=%s | version=%s",
            self.device_id,
            self.software_version,
        )

        await self._transition_to(DeviceState.SELF_TEST, "Executing startup self-tests.")
        await self._run_self_test()

        await self._transition_to(DeviceState.CONNECTING, "Initializing connectivity stage.")
        await self._complete_module1_connection_stage()

        await self._transition_to(DeviceState.MONITORING, "Core startup sequence complete.")
        await self.scheduler.start()

    async def shutdown(self) -> None:
        if self.current_state == DeviceState.SHUTTING_DOWN:
            return

        logger.info("Initiating controlled device shutdown.")
        await self.scheduler.stop()
        await self._transition_to(DeviceState.SHUTTING_DOWN, "User requested shutdown (SIGINT/CTRL+C).")
        logger.info("Device controller successfully shut down.")

    async def _run_self_test(self) -> None:
        checks = {
            "device_id": bool(self.device_id.strip()),
            "software_version": bool(self.software_version.strip()),
        }
        failed_checks = [name for name, passed in checks.items() if not passed]

        await asyncio.sleep(0.1)

        if failed_checks:
            await self._transition_to(DeviceState.ERROR, "Core self-test failed.")
            raise RuntimeError("Core self-test failed: " + ", ".join(failed_checks))

        logger.info("Module 1 core self-test passed.")

    async def _complete_module1_connection_stage(self) -> None:
        logger.info("CONNECTING state entered.")
        logger.info("AWS IoT connection is intentionally deferred until the AWS communication module.")
        await asyncio.sleep(0.2)

    async def _transition_to(self, new_state: DeviceState, reason: str) -> StateTransition:
        transition = self.state_machine.transition_to(new_state=new_state, reason=reason)

        logger.info(
            "Device state changed: %s -> %s | reason=%s",
            transition.previous_state.value,
            transition.current_state.value,
            transition.reason,
        )

        self.event_bus.publish(
            self.STATE_CHANGED_EVENT,
            {
                "deviceId": self.device_id,
                "softwareVersion": self.software_version,
                "previousState": transition.previous_state.value,
                "currentState": transition.current_state.value,
                "reason": transition.reason,
                "timestamp": transition.timestamp.isoformat(),
            },
        )
        return transition

    async def _log_core_status(self) -> None:
        logger.info(
            "Core status | device=%s | version=%s | state=%s",
            self.device_id,
            self.software_version,
            self.current_state.value,
        )
