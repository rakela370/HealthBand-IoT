"""Top-level HealthBand simulator application."""

import asyncio
import logging

from device_simulator.core.device_controller import DeviceController
from device_simulator.core.event_bus import EventBus
from device_simulator.utils.logging_config import configure_logging


logger = logging.getLogger(__name__)


class HealthBandApplication:
    """Creates and runs the HealthBand simulator application."""

    def __init__(self) -> None:
        configure_logging()

        self.event_bus = EventBus()

        self.device_controller = DeviceController(
            device_id="healthband-device-001",
            software_version="1.0.0",
            event_bus=self.event_bus,
        )

        self.event_bus.subscribe(
            DeviceController.STATE_CHANGED_EVENT,
            self._on_state_changed,
        )

    async def run(self) -> None:
        """Run the simulator until the process is interrupted."""

        await self.device_controller.start()

        logger.info(
            "HealthBand is running."
        )
        logger.info(
            "Press CTRL+C to stop the simulator."
        )

        try:
            while True:
                await asyncio.sleep(1.0)

        finally:
            await self.device_controller.shutdown()

    def _on_state_changed(
        self,
        payload: dict[str, object],
    ) -> None:
        """Receive local state change events from the EventBus."""

        logger.debug(
            "State event received: %s",
            payload,
        )