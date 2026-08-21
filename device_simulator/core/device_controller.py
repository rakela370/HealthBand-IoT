"""Central controller for the simulated HealthBand device."""

import asyncio
import logging

from device_simulator.core.device_state import (
    DeviceState,
)
from device_simulator.core.event_bus import (
    EventBus,
)
from device_simulator.core.scheduler import (
    Scheduler,
)
from device_simulator.core.state_machine import (
    InvalidStateTransitionError,
    StateMachine,
    StateTransition,
)
from device_simulator.sensors.sensor_manager import (
    SensorManager,
    SensorSnapshot,
)
from device_simulator.simulation.scenario import (
    SimulationScenario,
)
from device_simulator.simulation.scenario_engine import (
    ScenarioEngine,
)
from device_simulator.simulation.user_profile import (
    UserProfile,
)


logger = logging.getLogger(__name__)


class DeviceController:
    """Coordinates the main lifecycle of the HealthBand device."""

    STATE_CHANGED_EVENT = "device.state.changed"

    SENSOR_SNAPSHOT_EVENT = (
        "device.sensors.snapshot"
    )

    # This is intentionally hardcoded during Module 2.
    # Device Shadow configuration will replace it later.
    MEASUREMENT_INTERVAL_SEC = 2.0

    def __init__(
        self,
        device_id: str = "healthband-device-001",
        software_version: str = "1.0.0",
        event_bus: EventBus | None = None,
        scheduler: Scheduler | None = None,
        user_profile: UserProfile | None = None,
        random_seed: int | None = None,
    ) -> None:
        self.device_id = device_id
        self.software_version = software_version

        self.event_bus = event_bus or EventBus()
        self.scheduler = scheduler or Scheduler()

        self.state_machine = StateMachine()

        self.user_profile = (
            user_profile or UserProfile()
        )

        self.scenario_engine = ScenarioEngine(
            self.user_profile
        )

        self.sensor_manager = SensorManager(
            user_profile=self.user_profile,
            random_seed=random_seed,
        )

        self.latest_snapshot: (
            SensorSnapshot | None
        ) = None

        self._started = False

    @property
    def current_state(self) -> DeviceState:
        """Return the current logical device state."""

        return self.state_machine.current_state

    @property
    def current_scenario(
        self,
    ) -> SimulationScenario:
        """Return the active simulation scenario."""

        return (
            self.scenario_engine.current_scenario
        )

    async def start(self) -> None:
        """Start the HealthBand lifecycle."""

        if self._started:
            raise RuntimeError(
                "HealthBand device is already started."
            )

        self._started = True

        logger.info(
            "Starting HealthBand device '%s', "
            "software version %s.",
            self.device_id,
            self.software_version,
        )

        logger.info(
            "Initial device state: %s.",
            self.current_state.value,
        )

        await self._transition_to(
            DeviceState.SELF_TEST,
            "Boot sequence started.",
        )

        await self._run_core_self_test()

        await self._transition_to(
            DeviceState.CONNECTING,
            "Core self-test completed successfully.",
        )

        await (
            self._complete_module1_connection_stage()
        )

        await self._transition_to(
            DeviceState.MONITORING,
            "Module 2 local monitoring mode started.",
        )

        # Produce the first measurement immediately.
        await self._read_sensors()

        self.scheduler.add_periodic_job(
            name="sensor-reading",
            interval_sec=(
                self.MEASUREMENT_INTERVAL_SEC
            ),
            callback=self._read_sensors,
        )

        self.scheduler.add_periodic_job(
            name="core-status",
            interval_sec=5.0,
            callback=self._log_core_status,
        )

        await self.scheduler.start()

        logger.info(
            "HealthBand core and simulated sensors "
            "started successfully."
        )

    async def shutdown(self) -> None:
        """Perform controlled HealthBand shutdown."""

        logger.info(
            "Controlled HealthBand shutdown requested."
        )

        await self.scheduler.stop()

        if (
            self.current_state
            != DeviceState.SHUTTING_DOWN
        ):
            try:
                await self._transition_to(
                    DeviceState.SHUTTING_DOWN,
                    "Controlled application shutdown.",
                )

            except InvalidStateTransitionError:
                logger.exception(
                    "Unable to enter "
                    "SHUTTING_DOWN state."
                )
                raise

        self._started = False

        logger.info(
            "HealthBand shutdown completed."
        )

    def change_scenario(
        self,
        scenario: SimulationScenario,
        failed_sensor_name: str | None = None,
    ) -> None:
        """Change active simulation scenario."""

        previous_scenario = (
            self.scenario_engine.current_scenario
        )

        self.scenario_engine.set_scenario(
            scenario=scenario,
            failed_sensor_name=(
                failed_sensor_name
            ),
        )

        logger.info(
            "Simulation scenario changed: "
            "%s -> %s.",
            previous_scenario.value,
            scenario.value,
        )

    async def read_sensors_now(
        self,
    ) -> SensorSnapshot:
        """Immediately perform a sensor measurement cycle."""

        return await self._read_sensors()

    async def _run_core_self_test(
        self,
    ) -> None:
        """
        Execute the Module 2 core self-test.

        Database, certificates and cloud connectivity are
        intentionally checked in later modules.
        """

        logger.info(
            "Running Module 2 core self-test."
        )

        checks = {
            "state_machine": (
                self.state_machine is not None
            ),
            "event_bus": (
                self.event_bus is not None
            ),
            "scheduler": (
                self.scheduler is not None
            ),
            "scenario_engine": (
                self.scenario_engine is not None
            ),
            "sensor_manager": (
                self.sensor_manager is not None
            ),
            "device_id": bool(
                self.device_id.strip()
            ),
            "software_version": bool(
                self.software_version.strip()
            ),
        }

        failed_checks = [
            name
            for name, passed
            in checks.items()
            if not passed
        ]

        await asyncio.sleep(0.1)

        if failed_checks:
            await self._transition_to(
                DeviceState.ERROR,
                "Core self-test failed.",
            )

            raise RuntimeError(
                "Core self-test failed: "
                + ", ".join(failed_checks)
            )

        logger.info(
            "Module 2 core self-test passed."
        )

    async def _complete_module1_connection_stage(
        self,
    ) -> None:
        """
        Represent CONNECTING during local development.

        Real AWS IoT Core connectivity is intentionally
        implemented later in the AWS communication module.
        """

        logger.info(
            "CONNECTING state entered."
        )

        logger.info(
            "AWS IoT connection is intentionally "
            "deferred until the AWS communication "
            "module."
        )

        await asyncio.sleep(0.2)

    async def _read_sensors(
        self,
    ) -> SensorSnapshot:
        """Perform one complete sensor sampling cycle."""

        context = (
            self.scenario_engine.get_context()
        )

        snapshot = (
            self.sensor_manager.read_all(
                context=context,
                elapsed_sec=(
                    self.MEASUREMENT_INTERVAL_SEC
                ),
            )
        )

        self.latest_snapshot = snapshot

        logger.info(
            "Sensor snapshot | "
            "scenario=%s | "
            "activity=%s | "
            "measurements=%s | "
            "status=%s",
            snapshot.scenario,
            snapshot.activity_level,
            snapshot.measurements,
            snapshot.sensor_status,
        )

        self.event_bus.publish(
            self.SENSOR_SNAPSHOT_EVENT,
            {
                "deviceId": self.device_id,
                "userId": (
                    self.user_profile.user_id
                ),
                "softwareVersion": (
                    self.software_version
                ),
                "scenario": snapshot.scenario,
                "activityLevel": (
                    snapshot.activity_level
                ),
                "measurements": (
                    snapshot.measurements
                ),
                "sensorStatus": (
                    snapshot.sensor_status
                ),
                "timestamp": (
                    snapshot.timestamp.isoformat()
                ),
                "simulated": True,
            },
        )

        return snapshot

    async def _transition_to(
        self,
        new_state: DeviceState,
        reason: str,
    ) -> StateTransition:
        """Perform and publish a device state transition."""

        transition = (
            self.state_machine.transition_to(
                new_state=new_state,
                reason=reason,
            )
        )

        logger.info(
            "Device state changed: %s -> %s "
            "| reason=%s",
            transition.previous_state.value,
            transition.current_state.value,
            transition.reason,
        )

        self.event_bus.publish(
            self.STATE_CHANGED_EVENT,
            {
                "deviceId": self.device_id,
                "softwareVersion": (
                    self.software_version
                ),
                "previousState": (
                    transition.previous_state.value
                ),
                "currentState": (
                    transition.current_state.value
                ),
                "reason": (
                    transition.reason
                ),
                "timestamp": (
                    transition.timestamp.isoformat()
                ),
            },
        )

        return transition

    async def _log_core_status(
        self,
    ) -> None:
        """Write a periodic local status message."""

        logger.info(
            "Core status | "
            "device=%s | "
            "version=%s | "
            "state=%s | "
            "scenario=%s",
            self.device_id,
            self.software_version,
            self.current_state.value,
            self.current_scenario.value,
        )