"""Central controller for the simulated HealthBand device."""

import asyncio
import logging
from typing import Any

from device_simulator.alerts.alert import (
    Alert,
    AlertSeverity,
)
from device_simulator.alerts.alert_manager import (
    AlertManager,
)
from device_simulator.analytics.analytics_manager import (
    AnalyticsManager,
    AnalyticsResult,
)
from device_simulator.communication.mqtt_client import (
    MqttClient,
)
from device_simulator.communication.mqtt_topics import (
    MqttTopics,
)
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
from device_simulator.device_health.device_health_monitor import (
    DeviceHealthMonitor,
    DeviceHealthReport,
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
    """Coordinate the main lifecycle of the HealthBand device."""

    STATE_CHANGED_EVENT = (
        "device.state.changed"
    )

    SENSOR_SNAPSHOT_EVENT = (
        "device.sensors.snapshot"
    )

    ANALYTICS_EVENT = (
        "device.analytics.completed"
    )

    ALERT_EVENT = (
        "device.alert.generated"
    )

    DEVICE_HEALTH_EVENT = (
        "device.health.report"
    )

    MEASUREMENT_INTERVAL_SEC = 2.0
    ANALYTICS_WINDOW_SEC = 10.0
    HEALTH_REPORT_INTERVAL_SEC = 5.0
    PRESENCE_INTERVAL_SEC = 10.0
    COMMAND_POLL_INTERVAL_SEC = 0.5

    def __init__(
        self,
        device_id: str = "healthband-device-001",
        software_version: str = "1.0.0",
        event_bus: EventBus | None = None,
        scheduler: Scheduler | None = None,
        user_profile: UserProfile | None = None,
        random_seed: int | None = None,
        mqtt_client: MqttClient | None = None,
    ) -> None:
        self.device_id = device_id
        self.software_version = software_version

        self.event_bus = (
            event_bus or EventBus()
        )

        self.scheduler = (
            scheduler or Scheduler()
        )

        self.state_machine = (
            StateMachine()
        )

        self.user_profile = (
            user_profile or UserProfile()
        )

        self.scenario_engine = (
            ScenarioEngine(
                self.user_profile
            )
        )

        self.sensor_manager = (
            SensorManager(
                user_profile=(
                    self.user_profile
                ),
                random_seed=random_seed,
            )
        )

        self.analytics_manager = (
            AnalyticsManager(
                device_id=self.device_id,
                software_version=(
                    self.software_version
                ),
                window_sec=(
                    self.ANALYTICS_WINDOW_SEC
                ),
            )
        )

        self.alert_manager = (
            AlertManager(
                device_id=self.device_id
            )
        )

        self.device_health_monitor = (
            DeviceHealthMonitor(
                device_id=self.device_id,
                software_version=(
                    self.software_version
                ),
            )
        )

        self.mqtt_client = (
            mqtt_client
        )

        self.mqtt_topics = (
            MqttTopics(
                device_id=self.device_id
            )
        )

        self.latest_snapshot: (
            SensorSnapshot | None
        ) = None

        self.latest_analytics: (
            AnalyticsResult | None
        ) = None

        self.latest_health_report: (
            DeviceHealthReport | None
        ) = None

        self._started = False

    @property
    def current_state(
        self,
    ) -> DeviceState:
        """Return current device state."""

        return (
            self.state_machine.current_state
        )

    @property
    def current_scenario(
        self,
    ) -> SimulationScenario:
        """Return active simulation scenario."""

        return (
            self.scenario_engine.current_scenario
        )

    async def start(self) -> None:
        """Start HealthBand."""

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

        await self._connect_to_cloud()

        await self._transition_to(
            DeviceState.MONITORING,
            "AWS IoT connection established.",
        )

        await self._publish_presence(
            status="ONLINE"
        )

        await self._read_sensors()

        await self._create_health_report()

        self.scheduler.add_periodic_job(
            name="sensor-reading",
            interval_sec=(
                self.MEASUREMENT_INTERVAL_SEC
            ),
            callback=self._read_sensors,
        )

        self.scheduler.add_periodic_job(
            name="device-health",
            interval_sec=(
                self.HEALTH_REPORT_INTERVAL_SEC
            ),
            callback=(
                self._create_health_report
            ),
        )

        self.scheduler.add_periodic_job(
            name="core-status",
            interval_sec=5.0,
            callback=self._log_core_status,
        )

        if self.mqtt_client is not None:
            self.scheduler.add_periodic_job(
                name="mqtt-command-poll",
                interval_sec=(
                    self.COMMAND_POLL_INTERVAL_SEC
                ),
                callback=(
                    self._process_incoming_commands
                ),
            )

            self.scheduler.add_periodic_job(
                name="presence-heartbeat",
                interval_sec=(
                    self.PRESENCE_INTERVAL_SEC
                ),
                callback=(
                    self._publish_presence_heartbeat
                ),
            )

        await self.scheduler.start()

        logger.info(
            "HealthBand Module 4 started successfully."
        )

    async def shutdown(self) -> None:
        """Perform controlled shutdown."""

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

        await self._publish_presence(
            status="OFFLINE"
        )

        if self.mqtt_client is not None:
            try:
                await asyncio.to_thread(
                    self.mqtt_client.disconnect
                )

            except Exception:
                logger.exception(
                    "Error while disconnecting "
                    "from AWS IoT Core."
                )

        self._started = False

        logger.info(
            "HealthBand shutdown completed."
        )

    def change_scenario(
        self,
        scenario: SimulationScenario,
        failed_sensor_name: str | None = None,
    ) -> None:
        """Change simulation scenario."""

        previous = (
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
            previous.value,
            scenario.value,
        )

    async def read_sensors_now(
        self,
    ) -> SensorSnapshot:
        """Immediately execute one sampling cycle."""

        return await self._read_sensors()

    async def create_health_report_now(
        self,
    ) -> DeviceHealthReport:
        """Immediately create a health report."""

        return await self._create_health_report()

    async def process_mqtt_messages_now(
        self,
    ) -> None:
        """Immediately process queued inbound MQTT messages."""

        await self._process_incoming_commands()

    async def _run_core_self_test(
        self,
    ) -> None:
        """Run local Module 4 self-test."""

        logger.info(
            "Running Module 4 core self-test."
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
            "analytics_manager": (
                self.analytics_manager is not None
            ),
            "alert_manager": (
                self.alert_manager is not None
            ),
            "device_health_monitor": (
                self.device_health_monitor
                is not None
            ),
            "mqtt_topics": (
                self.mqtt_topics is not None
            ),
            "device_id": bool(
                self.device_id.strip()
            ),
            "software_version": bool(
                self.software_version.strip()
            ),
        }

        failed = [
            name
            for name, passed
            in checks.items()
            if not passed
        ]

        await asyncio.sleep(
            0.1
        )

        if failed:
            await self._transition_to(
                DeviceState.ERROR,
                "Core self-test failed.",
            )

            raise RuntimeError(
                "Core self-test failed: "
                + ", ".join(failed)
            )

        logger.info(
            "Module 4 core self-test passed."
        )

    async def _connect_to_cloud(
        self,
    ) -> None:
        """Connect and subscribe to AWS IoT Core."""

        if self.mqtt_client is None:
            logger.info(
                "No MQTT client supplied. "
                "Running in local test mode."
            )

            await asyncio.sleep(
                0.2
            )

            return

        try:
            await asyncio.to_thread(
                self.mqtt_client.connect
            )

            await asyncio.to_thread(
                self.mqtt_client.subscribe,
                self.mqtt_topics.commands_request,
                1,
            )

            logger.info(
                "HealthBand is connected to "
                "AWS IoT Core and ready for commands."
            )

        except Exception as exc:
            self.device_health_monitor.record_fault(
                f"AWS_IOT_CONNECTION_FAILED: {exc}"
            )

            logger.exception(
                "Unable to connect HealthBand "
                "to AWS IoT Core."
            )

            await self._transition_to(
                DeviceState.ERROR,
                "AWS IoT connection failed.",
            )

            raise

    async def _read_sensors(
        self,
    ) -> SensorSnapshot:
        """Read sensors, evaluate alerts and run analytics."""

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

        self.latest_snapshot = (
            snapshot
        )

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

        telemetry_payload = {
            "deviceId": self.device_id,
            "userId": (
                self.user_profile.user_id
            ),
            "softwareVersion": (
                self.software_version
            ),
            "scenario": (
                snapshot.scenario
            ),
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
        }

        self.event_bus.publish(
            self.SENSOR_SNAPSHOT_EVENT,
            telemetry_payload,
        )

        await self._publish_mqtt(
            topic=(
                self.mqtt_topics.telemetry
            ),
            payload=telemetry_payload,
            qos=0,
        )

        alerts = (
            self.alert_manager.evaluate_snapshot(
                snapshot
            )
        )

        for alert in alerts:
            await self._publish_alert(
                alert
            )

        analytics_result = (
            self.analytics_manager.add_snapshot(
                snapshot=snapshot,
                elapsed_sec=(
                    self.MEASUREMENT_INTERVAL_SEC
                ),
                alerts_generated=len(
                    alerts
                ),
            )
        )

        if analytics_result is not None:
            self.latest_analytics = (
                analytics_result
            )

            logger.info(
                "Analytics completed | %s",
                analytics_result.analytics,
            )

            analytics_payload = (
                analytics_result.to_dict()
            )

            self.event_bus.publish(
                self.ANALYTICS_EVENT,
                analytics_payload,
            )

            await self._publish_mqtt(
                topic=(
                    self.mqtt_topics.analytics
                ),
                payload=analytics_payload,
                qos=1,
            )

        return snapshot

    async def _publish_alert(
        self,
        alert: Alert,
    ) -> None:
        """Log and publish one alert."""

        logger.warning(
            "Alert generated | "
            "type=%s | severity=%s | "
            "scenario=%s | measured=%s",
            alert.type.value,
            alert.severity.value,
            alert.scenario,
            alert.measured_value,
        )

        if (
            alert.severity
            == AlertSeverity.HIGH
        ):
            self.device_health_monitor.record_fault(
                alert.type.value
            )

        payload = (
            alert.to_dict()
        )

        self.event_bus.publish(
            self.ALERT_EVENT,
            payload,
        )

        await self._publish_mqtt(
            topic=(
                self.mqtt_topics.alerts
            ),
            payload=payload,
            qos=1,
        )

    async def _create_health_report(
        self,
    ) -> DeviceHealthReport:
        """Create technical device-health report."""

        sensor_statuses = (
            self.sensor_manager.sensor_statuses()
        )

        battery_percentage: (
            float | None
        ) = None

        if (
            self.latest_snapshot
            is not None
        ):
            value = (
                self.latest_snapshot.measurements.get(
                    "batteryPercentage"
                )
            )

            if value is not None:
                battery_percentage = float(
                    value
                )

        mqtt_connected: (
            bool | None
        ) = None

        if self.mqtt_client is not None:
            mqtt_connected = (
                self.mqtt_client.is_connected
            )

        report = (
            self.device_health_monitor.create_report(
                device_state=(
                    self.current_state
                ),
                sensor_statuses=(
                    sensor_statuses
                ),
                battery_percentage=(
                    battery_percentage
                ),
                mqtt_connected=(
                    mqtt_connected
                ),
                offline_queue_size=0,
            )
        )

        self.latest_health_report = (
            report
        )

        logger.info(
            "Device health | "
            "status=%s | "
            "state=%s | "
            "mqtt=%s | "
            "battery=%s | "
            "sensors=%s",
            report.device_status.value,
            report.device_state.value,
            report.mqtt_connected,
            report.battery_percentage,
            report.sensors,
        )

        payload = (
            report.to_dict()
        )

        self.event_bus.publish(
            self.DEVICE_HEALTH_EVENT,
            payload,
        )

        await self._publish_mqtt(
            topic=(
                self.mqtt_topics.health
            ),
            payload=payload,
            qos=1,
        )

        return report

    async def _transition_to(
        self,
        new_state: DeviceState,
        reason: str,
    ) -> StateTransition:
        """Perform and publish a state transition."""

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

        payload = {
            "deviceId": self.device_id,
            "softwareVersion": (
                self.software_version
            ),
            "eventType": (
                "DEVICE_STATE_CHANGED"
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
        }

        self.event_bus.publish(
            self.STATE_CHANGED_EVENT,
            payload,
        )

        await self._publish_mqtt(
            topic=(
                self.mqtt_topics.events
            ),
            payload=payload,
            qos=1,
        )

        return transition

    async def _process_incoming_commands(
        self,
    ) -> None:
        """
        Process commands received from AWS IoT Core.

        Module 4 proves bidirectional MQTT communication.
        Full command validation, dispatch, idempotency and execution
        are implemented in the command module.
        """

        if self.mqtt_client is None:
            return

        messages = (
            self.mqtt_client
            .drain_incoming_messages()
        )

        for message in messages:
            if (
                message.topic
                != self.mqtt_topics.commands_request
            ):
                logger.warning(
                    "Ignoring unexpected MQTT topic: %s",
                    message.topic,
                )
                continue

            command_id = (
                message.payload.get(
                    "commandId"
                )
            )

            command = (
                message.payload.get(
                    "command"
                )
            )

            if (
                not isinstance(
                    command_id,
                    str,
                )
                or not command_id.strip()
                or not isinstance(
                    command,
                    str,
                )
                or not command.strip()
            ):
                logger.warning(
                    "Rejected malformed Module 4 "
                    "test command: %s",
                    message.payload,
                )
                continue

            logger.info(
                "MQTT command received | "
                "commandId=%s | command=%s",
                command_id,
                command,
            )

            response = {
                "deviceId": self.device_id,
                "commandId": command_id,
                "command": command,
                "status": "RECEIVED",
                "message": (
                    "Command received by HealthBand. "
                    "Full command execution is implemented "
                    "in Module 5."
                ),
            }

            await self._publish_mqtt(
                topic=(
                    self.mqtt_topics.commands_response
                ),
                payload=response,
                qos=1,
            )

    async def _publish_presence(
        self,
        status: str,
    ) -> None:
        """Publish online/offline presence."""

        payload = {
            "deviceId": self.device_id,
            "status": status,
            "deviceState": (
                self.current_state.value
            ),
            "softwareVersion": (
                self.software_version
            ),
        }

        await self._publish_mqtt(
            topic=(
                self.mqtt_topics.presence
            ),
            payload=payload,
            qos=1,
        )

    async def _publish_presence_heartbeat(
        self,
    ) -> None:
        """Periodically publish online presence."""

        await self._publish_presence(
            status="ONLINE"
        )

    async def _publish_mqtt(
        self,
        topic: str,
        payload: dict[str, Any],
        qos: int,
    ) -> bool:
        """Safely publish one message when MQTT is available."""

        if (
            self.mqtt_client is None
            or not self.mqtt_client.is_connected
        ):
            return False

        try:
            await asyncio.to_thread(
                self.mqtt_client.publish,
                topic,
                payload,
                qos,
            )

            return True

        except Exception as exc:
            logger.error(
                "MQTT publish failed | "
                "topic=%s | error=%s",
                topic,
                exc,
            )

            self.device_health_monitor.record_fault(
                f"MQTT_PUBLISH_FAILED: {topic}: {exc}"
            )

            return False

    async def _log_core_status(
        self,
    ) -> None:
        """Log periodic controller status."""

        mqtt_connected: (
            bool | None
        ) = None

        if self.mqtt_client is not None:
            mqtt_connected = (
                self.mqtt_client.is_connected
            )

        logger.info(
            "Core status | "
            "device=%s | "
            "version=%s | "
            "state=%s | "
            "scenario=%s | "
            "mqtt=%s",
            self.device_id,
            self.software_version,
            self.current_state.value,
            self.current_scenario.value,
            mqtt_connected,
        )