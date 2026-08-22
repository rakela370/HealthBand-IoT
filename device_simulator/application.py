"""Top-level HealthBand simulator application."""

import asyncio
import logging

from device_simulator.communication.connection_manager import (
    AwsIotConnectionSettings,
)
from device_simulator.communication.mqtt_client import (
    MqttClient,
)
from device_simulator.core.device_controller import (
    DeviceController,
)
from device_simulator.core.device_state import (
    DeviceState,
)
from device_simulator.core.event_bus import (
    EventBus,
)
from device_simulator.utils.logging_config import (
    configure_logging,
)


logger = logging.getLogger(__name__)


class HealthBandApplication:
    """Create and run the HealthBand simulator."""

    def __init__(self) -> None:
        configure_logging()

        self.event_bus = (
            EventBus()
        )

        mqtt_settings = (
            AwsIotConnectionSettings.from_environment()
        )

        self.mqtt_client = (
            MqttClient(
                settings=mqtt_settings
            )
        )

        self.device_controller = (
            DeviceController(
                device_id=(
                    mqtt_settings.client_id
                ),
                software_version="1.0.0",
                event_bus=self.event_bus,
                mqtt_client=self.mqtt_client,
            )
        )

        self.event_bus.subscribe(
            DeviceController.STATE_CHANGED_EVENT,
            self._on_state_changed,
        )

    async def run(self) -> None:
        """Run simulator until interrupted."""

        try:
            await self.device_controller.start()

            logger.info(
                "HealthBand is running."
            )

            logger.info(
                "Press CTRL+C to stop the simulator."
            )

            while True:
                await asyncio.sleep(
                    1.0
                )

        finally:
            if (
                self.device_controller.current_state
                != DeviceState.SHUTTING_DOWN
            ):
                await self.device_controller.shutdown()

    def _on_state_changed(
        self,
        payload: dict[str, object],
    ) -> None:
        """Receive local state-change events."""

        logger.debug(
            "State event received: %s",
            payload,
        )