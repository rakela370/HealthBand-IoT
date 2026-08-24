"""Central controller for the simulated HealthBand device."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from device_simulator.alerts.alert import (
    Alert,
    AlertSeverity,
    AlertType,
)
from device_simulator.alerts.alert_manager import (
    AlertManager,
)
from device_simulator.analytics.analytics_manager import (
    AnalyticsManager,
    AnalyticsResult,
)
from device_simulator.commands.command import (
    Command,
    CommandResult,
    CommandStatus,
    CommandType,
)
from device_simulator.commands.command_handler import (
    CommandHandler,
)
from device_simulator.commands.command_registry import (
    CommandRegistry,
)
from device_simulator.commands.command_validator import (
    CommandValidationError,
    CommandValidator,
)
from device_simulator.communication.mqtt_client import (
    MqttClient,
)
from device_simulator.communication.mqtt_topics import (
    MqttTopics,
)
from device_simulator.communication.shadow_client import (
    ShadowClient,
    ShadowOperationRejected,
)
from device_simulator.configuration.configuration_manager import (
    ConfigurationApplyResult,
    ConfigurationManager,
)
from device_simulator.configuration.device_config import (
    DeviceConfig,
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
from device_simulator.sensors.battery_model import (
    BatteryModel,
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
    """Coordinate the complete HealthBand device lifecycle."""

    STATE_CHANGED_EVENT = "device.state.changed"
    SENSOR_SNAPSHOT_EVENT = "device.sensors.snapshot"
    ANALYTICS_EVENT = "device.analytics.completed"
    ALERT_EVENT = "device.alert.generated"
    DEVICE_HEALTH_EVENT = "device.health.report"
    CONFIGURATION_EVENT = "device.configuration.changed"

    COMMAND_POLL_INTERVAL_SEC = 0.5
    SHADOW_POLL_INTERVAL_SEC = 0.5
    PRESENCE_INTERVAL_SEC = 10.0

    def __init__(
        self,
        device_id: str = "healthband-device-001",
        software_version: str = "1.0.0",
        event_bus: EventBus | None = None,
        scheduler: Scheduler | None = None,
        user_profile: UserProfile | None = None,
        random_seed: int | None = None,
        mqtt_client: MqttClient | None = None,
        shadow_client: ShadowClient | None = None,
        configuration_manager: (
            ConfigurationManager | None
        ) = None,
    ) -> None:
        self.device_id = (
            device_id
        )

        self.software_version = (
            software_version
        )

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

        self.configuration_manager = (
            configuration_manager
            or ConfigurationManager()
        )

        config = (
            self.configuration_manager.current
        )

        self.analytics_manager = (
            AnalyticsManager(
                device_id=self.device_id,
                software_version=(
                    self.software_version
                ),
                window_sec=(
                    config.analytics_window_sec
                ),
            )
        )

        self.alert_manager = (
            AlertManager(
                device_id=self.device_id,
                heart_rate_minimum_threshold=(
                    config.heart_rate_minimum_bpm
                ),
                heart_rate_maximum_resting_threshold=(
                    config.heart_rate_maximum_resting_bpm
                ),
                skin_temperature_minimum_threshold=(
                    config.skin_temperature_minimum_c
                ),
                skin_temperature_maximum_threshold=(
                    config.skin_temperature_maximum_c
                ),
                low_battery_threshold_percentage=(
                    config.low_battery_percentage
                ),
            )
        )

        self.device_health_monitor = (
            DeviceHealthMonitor(
                device_id=self.device_id,
                software_version=(
                    self.software_version
                ),
                low_battery_threshold=(
                    config.low_battery_percentage
                ),
            )
        )

        self.mqtt_client = (
            mqtt_client
        )

        self.shadow_client = (
            shadow_client
        )

        self.mqtt_topics = (
            MqttTopics(
                device_id=self.device_id
            )
        )

        self.command_validator = (
            CommandValidator(
                device_id=self.device_id
            )
        )

        self.command_registry = (
            CommandRegistry()
        )

        self._register_commands()

        self.command_handler = (
            CommandHandler(
                registry=(
                    self.command_registry
                )
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

        self._monitoring_enabled = (
            True
        )

        self._started = False

        self._last_rejected_delta_signature: (
            str | None
        ) = None

    @property
    def current_state(
        self,
    ) -> DeviceState:
        return (
            self.state_machine.current_state
        )

    @property
    def current_scenario(
        self,
    ) -> SimulationScenario:
        return (
            self.scenario_engine.current_scenario
        )

    @property
    def current_config(
        self,
    ) -> DeviceConfig:
        return (
            self.configuration_manager.current
        )

    async def start(
        self,
    ) -> None:
        """Start the HealthBand device."""

        if self._started:
            raise RuntimeError(
                "HealthBand device is already started."
            )

        self._started = (
            True
        )

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
            "AWS IoT connection stage completed.",
        )

        await self._publish_presence(
            "ONLINE"
        )

        await self._read_sensors(
            force=True
        )

        await self._publish_latest_telemetry(
            force=True
        )

        await self._create_health_report()

        config = (
            self.current_config
        )

        self.scheduler.add_periodic_job(
            name="sensor-reading",
            interval_sec=(
                config.measurement_interval_sec
            ),
            callback=self._scheduled_sensor_read,
        )

        self.scheduler.add_periodic_job(
            name="telemetry-publish",
            interval_sec=(
                config.telemetry_interval_sec
            ),
            callback=(
                self._publish_latest_telemetry
            ),
        )

        self.scheduler.add_periodic_job(
            name="device-health",
            interval_sec=(
                config.health_report_interval_sec
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

        if self.shadow_client is not None:
            self.scheduler.add_periodic_job(
                name="shadow-delta-poll",
                interval_sec=(
                    self.SHADOW_POLL_INTERVAL_SEC
                ),
                callback=(
                    self._process_shadow_deltas
                ),
            )

        await self.scheduler.start()

        logger.info(
            "HealthBand Module 5 started successfully."
        )

    async def shutdown(
        self,
    ) -> None:
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
            "OFFLINE"
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

        self._started = (
            False
        )

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
            self.current_scenario
        )

        self.scenario_engine.set_scenario(
            scenario=scenario,
            failed_sensor_name=(
                failed_sensor_name
            ),
        )

        logger.info(
            "Simulation scenario changed: %s -> %s.",
            previous.value,
            scenario.value,
        )

    async def read_sensors_now(
        self,
    ) -> SensorSnapshot:
        """Force an immediate sensor measurement."""

        snapshot = (
            await self._read_sensors(
                force=True
            )
        )

        if snapshot is None:
            raise RuntimeError(
                "Immediate sensor reading failed."
            )

        return snapshot

    async def create_health_report_now(
        self,
    ) -> DeviceHealthReport:
        return (
            await self._create_health_report()
        )

    async def process_mqtt_messages_now(
        self,
    ) -> None:
        await self._process_incoming_commands()

    async def apply_configuration_delta_now(
        self,
        delta: dict[str, Any],
    ) -> bool:
        """Apply configuration directly; useful for testing."""

        result = (
            await self._apply_configuration_delta(
                delta=delta,
                source="LOCAL_TEST",
            )
        )

        return (
            result.applied
        )

    async def _run_core_self_test(
        self,
    ) -> None:
        logger.info(
            "Running Module 5 core self-test."
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
                self.device_health_monitor is not None
            ),
            "configuration_manager": (
                self.configuration_manager is not None
            ),
            "command_handler": (
                self.command_handler is not None
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
                + ", ".join(
                    failed
                )
            )

        logger.info(
            "Module 5 core self-test passed."
        )

    async def _connect_to_cloud(
        self,
    ) -> None:
        if self.mqtt_client is None:
            logger.info(
                "No MQTT client supplied. "
                "Running in local test mode."
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
                "HealthBand connected to AWS IoT Core."
            )

            if self.shadow_client is not None:
                await asyncio.to_thread(
                    self.shadow_client.start
                )

                await self._synchronize_shadow_on_startup()

        except Exception as exc:
            self.device_health_monitor.record_fault(
                f"AWS_IOT_CONNECTION_FAILED: {exc}"
            )

            logger.exception(
                "Unable to initialize "
                "AWS IoT communication."
            )

            await self._transition_to(
                DeviceState.ERROR,
                "AWS IoT initialization failed.",
            )

            raise

    async def _synchronize_shadow_on_startup(
        self,
    ) -> None:
        """Get existing Shadow and create/update reported state."""

        if self.shadow_client is None:
            return

        try:
            response = (
                await asyncio.to_thread(
                    self.shadow_client.get_shadow
                )
            )

            delta: dict[
                str,
                Any,
            ] = {}

            if (
                response.state is not None
                and isinstance(
                    response.state.delta,
                    dict,
                )
            ):
                delta = dict(
                    response.state.delta
                )

            if delta:
                logger.info(
                    "Applying startup Shadow delta: %s",
                    delta,
                )

                await self._apply_configuration_delta(
                    delta=delta,
                    source="SHADOW_STARTUP",
                )

            else:
                await self._report_configuration_applied(
                    message=(
                        "Current local configuration "
                        "reported on startup."
                    )
                )

        except ShadowOperationRejected as exc:
            if exc.code == 404:
                logger.info(
                    "No existing Device Shadow. "
                    "Creating initial reported state."
                )

                await self._report_configuration_applied(
                    message=(
                        "Initial configuration reported."
                    )
                )

            else:
                raise

    async def _scheduled_sensor_read(
        self,
    ) -> None:
        await self._read_sensors(
            force=False
        )

    async def _read_sensors(
        self,
        force: bool,
    ) -> SensorSnapshot | None:
        if (
            not self._monitoring_enabled
            and not force
        ):
            return self.latest_snapshot

        context = (
            self.scenario_engine.get_context()
        )

        snapshot = (
            self.sensor_manager.read_all(
                context=context,
                elapsed_sec=(
                    self.current_config
                    .measurement_interval_sec
                ),
            )
        )

        self.latest_snapshot = (
            snapshot
        )

        logger.info(
            "Sensor snapshot | "
            "scenario=%s | activity=%s | "
            "measurements=%s | status=%s",
            snapshot.scenario,
            snapshot.activity_level,
            snapshot.measurements,
            snapshot.sensor_status,
        )

        self.event_bus.publish(
            self.SENSOR_SNAPSHOT_EVENT,
            {
                "deviceId": self.device_id,
                "measurements": (
                    snapshot.measurements
                ),
                "sensorStatus": (
                    snapshot.sensor_status
                ),
                "scenario": (
                    snapshot.scenario
                ),
                "activityLevel": (
                    snapshot.activity_level
                ),
                "timestamp": (
                    snapshot.timestamp.isoformat()
                ),
            },
        )

        alerts: list[
            Alert
        ] = []

        if self.current_config.alerts_enabled:
            alerts = (
                self.alert_manager.evaluate_snapshot(
                    snapshot
                )
            )

            alerts = [
                alert
                for alert in alerts
                if self._is_alert_enabled(
                    alert
                )
            ]

        for alert in alerts:
            await self._publish_alert(
                alert
            )

        if self.current_config.analytics_enabled:
            analytics_result = (
                self.analytics_manager.add_snapshot(
                    snapshot=snapshot,
                    elapsed_sec=(
                        self.current_config
                        .measurement_interval_sec
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

                payload = (
                    analytics_result.to_dict()
                )

                self.event_bus.publish(
                    self.ANALYTICS_EVENT,
                    payload,
                )

                await self._publish_mqtt(
                    topic=(
                        self.mqtt_topics.analytics
                    ),
                    payload=payload,
                    qos=1,
                )

        return snapshot

    async def _publish_latest_telemetry(
        self,
        force: bool = False,
    ) -> None:
        if (
            not self._monitoring_enabled
            and not force
        ):
            return

        if self.latest_snapshot is None:
            return

        payload = (
            self._build_telemetry_payload(
                self.latest_snapshot
            )
        )

        await self._publish_mqtt(
            topic=self.mqtt_topics.telemetry,
            payload=payload,
            qos=0,
        )

    def _build_telemetry_payload(
        self,
        snapshot: SensorSnapshot,
    ) -> dict[str, Any]:
        """Build external telemetry using configured unit."""

        measurements = dict(
            snapshot.measurements
        )

        temperature_celsius = (
            measurements.pop(
                "skinTemperatureCelsius",
                None,
            )
        )

        if temperature_celsius is not None:
            measurements[
                "skinTemperature"
            ] = (
                self.current_config
                .convert_temperature_from_celsius(
                    float(
                        temperature_celsius
                    )
                )
            )

            measurements[
                "temperatureUnit"
            ] = (
                self.current_config
                .temperature_unit.value
            )

        return {
            "deviceId": (
                self.device_id
            ),
            "userId": (
                self.current_config
                .active_user_profile
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
                measurements
            ),
            "sensorStatus": (
                snapshot.sensor_status
            ),
            "timestamp": (
                snapshot.timestamp.isoformat()
            ),
            "simulated": True,
        }

    def _is_alert_enabled(
        self,
        alert: Alert,
    ) -> bool:
        config = (
            self.current_config
        )

        if alert.type in {
            AlertType.HEART_RATE_BELOW_THRESHOLD,
            AlertType.HEART_RATE_ABOVE_RESTING_THRESHOLD,
        }:
            return (
                config.heart_rate_alerts_enabled
            )

        if alert.type in {
            AlertType.TEMPERATURE_BELOW_THRESHOLD,
            AlertType.TEMPERATURE_ABOVE_THRESHOLD,
        }:
            return (
                config.temperature_alerts_enabled
            )

        if (
            alert.type
            == AlertType.LOW_BATTERY
        ):
            return (
                config.battery_alerts_enabled
            )

        if alert.type in {
            AlertType.SENSOR_FAILED,
            AlertType.SENSOR_NO_DATA,
            AlertType.SENSOR_INVALID_VALUE,
        }:
            return (
                config.sensor_failure_alerts_enabled
            )

        return True

    async def _publish_alert(
        self,
        alert: Alert,
    ) -> None:
        logger.warning(
            "Alert generated | type=%s | "
            "severity=%s | scenario=%s | "
            "measured=%s",
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
            self.mqtt_topics.alerts,
            payload,
            1,
        )

    async def _create_health_report(
        self,
    ) -> DeviceHealthReport:
        statuses = (
            self.sensor_manager.sensor_statuses()
        )

        battery_percentage: (
            float | None
        ) = None

        if self.latest_snapshot is not None:
            value = (
                self.latest_snapshot
                .measurements
                .get(
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
                sensor_statuses=statuses,
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
            "Device health | status=%s | "
            "state=%s | mqtt=%s | battery=%s",
            report.device_status.value,
            report.device_state.value,
            report.mqtt_connected,
            report.battery_percentage,
        )

        payload = (
            report.to_dict()
        )

        self.event_bus.publish(
            self.DEVICE_HEALTH_EVENT,
            payload,
        )

        await self._publish_mqtt(
            self.mqtt_topics.health,
            payload,
            1,
        )

        return report

    async def _process_incoming_commands(
        self,
    ) -> None:
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
                continue

            try:
                command = (
                    self.command_validator.validate(
                        message.payload
                    )
                )

            except CommandValidationError as exc:
                raw_id = (
                    message.payload.get(
                        "commandId"
                    )
                )

                command_id = (
                    raw_id
                    if isinstance(
                        raw_id,
                        str,
                    )
                    else (
                        "rejected-"
                        + str(
                            uuid4()
                        )
                    )
                )

                raw_type = (
                    message.payload.get(
                        "type",
                        message.payload.get(
                            "command",
                            "UNKNOWN",
                        ),
                    )
                )

                rejected = (
                    CommandResult(
                        command_id=command_id,
                        device_id=self.device_id,
                        command_type=str(
                            raw_type
                        ),
                        status=(
                            CommandStatus.REJECTED
                        ),
                        message=str(
                            exc
                        ),
                        error_code=(
                            "COMMAND_VALIDATION_FAILED"
                        ),
                        timestamp=datetime.now(
                            timezone.utc
                        ),
                    )
                )

                await self._publish_command_result(
                    rejected
                )

                continue

            cached = (
                self.command_handler
                .get_cached_result(
                    command.command_id
                )
            )

            if cached is not None:
                logger.info(
                    "Duplicate command received | "
                    "commandId=%s",
                    command.command_id,
                )

                await self._publish_command_result(
                    cached
                )

                continue

            await self._publish_command_result(
                self._transient_command_result(
                    command,
                    CommandStatus.RECEIVED,
                    "Command received.",
                )
            )

            await self._publish_command_result(
                self._transient_command_result(
                    command,
                    CommandStatus.IN_PROGRESS,
                    "Command execution started.",
                )
            )

            result = (
                await self.command_handler.execute(
                    command
                )
            )

            await self._publish_command_result(
                result
            )

    def _transient_command_result(
        self,
        command: Command,
        status: CommandStatus,
        message: str,
    ) -> CommandResult:
        return CommandResult(
            command_id=(
                command.command_id
            ),
            device_id=(
                command.device_id
            ),
            command_type=(
                command.type.value
            ),
            status=status,
            message=message,
            timestamp=datetime.now(
                timezone.utc
            ),
        )

    async def _publish_command_result(
        self,
        result: CommandResult,
    ) -> None:
        logger.info(
            "Command result | commandId=%s | "
            "type=%s | status=%s | duplicate=%s",
            result.command_id,
            result.command_type,
            result.status.value,
            result.duplicate,
        )

        await self._publish_mqtt(
            topic=(
                self.mqtt_topics.commands_response
            ),
            payload=(
                result.to_dict()
            ),
            qos=1,
        )

    def _register_commands(
        self,
    ) -> None:
        registrations = {
            CommandType.START_MONITORING:
                self._command_start_monitoring,

            CommandType.STOP_MONITORING:
                self._command_stop_monitoring,

            CommandType.RESTART_DEVICE:
                self._command_restart_device,

            CommandType.ENTER_MAINTENANCE:
                self._command_enter_maintenance,

            CommandType.EXIT_MAINTENANCE:
                self._command_exit_maintenance,

            CommandType.START_CHARGING:
                self._command_start_charging,

            CommandType.STOP_CHARGING:
                self._command_stop_charging,

            CommandType.CALIBRATE_SENSOR:
                self._command_calibrate_sensor,

            CommandType.REQUEST_IMMEDIATE_MEASUREMENT:
                self._command_request_measurement,

            CommandType.REQUEST_DEVICE_HEALTH:
                self._command_request_device_health,

            CommandType.CLEAR_ALERTS:
                self._command_clear_alerts,

            CommandType.CHANGE_SIMULATION_SCENARIO:
                self._command_change_scenario,

            CommandType.SIMULATE_SENSOR_FAILURE:
                self._command_simulate_sensor_failure,

            CommandType.RESTORE_SENSOR:
                self._command_restore_sensor,

            CommandType.SIMULATE_NETWORK_OUTAGE:
                self._command_simulate_network_outage,

            CommandType.RESTORE_NETWORK:
                self._command_restore_network,
        }

        for (
            command_type,
            executor,
        ) in registrations.items():
            self.command_registry.register(
                command_type,
                executor,
            )

    async def _command_start_monitoring(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        del command

        self._monitoring_enabled = True

        if (
            self.current_state
            == DeviceState.MAINTENANCE
        ):
            await self._transition_to(
                DeviceState.MONITORING,
                "START_MONITORING command.",
            )

        return (
            "Monitoring started.",
            {
                "monitoringEnabled": True,
            },
        )

    async def _command_stop_monitoring(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        del command

        self._monitoring_enabled = False

        return (
            "Periodic sensor monitoring stopped.",
            {
                "monitoringEnabled": False,
            },
        )

    async def _command_restart_device(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        del command

        await self._transition_to(
            DeviceState.RESTARTING,
            "RESTART_DEVICE command.",
        )

        await self._transition_to(
            DeviceState.BOOTING,
            "Simulated restart.",
        )

        await self._transition_to(
            DeviceState.SELF_TEST,
            "Restart self-test.",
        )

        await self._run_core_self_test()

        await self._transition_to(
            DeviceState.CONNECTING,
            "Restart self-test passed.",
        )

        await self._transition_to(
            DeviceState.MONITORING,
            "Simulated restart completed.",
        )

        return (
            "Simulated device restart completed.",
            {
                "deviceState": (
                    self.current_state.value
                ),
            },
        )

    async def _command_enter_maintenance(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        del command

        if (
            self.current_state
            != DeviceState.MAINTENANCE
        ):
            await self._transition_to(
                DeviceState.MAINTENANCE,
                "ENTER_MAINTENANCE command.",
            )

        self._monitoring_enabled = False

        return (
            "Maintenance mode entered.",
            {
                "deviceState": (
                    self.current_state.value
                ),
            },
        )

    async def _command_exit_maintenance(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        del command

        if (
            self.current_state
            == DeviceState.MAINTENANCE
        ):
            await self._transition_to(
                DeviceState.MONITORING,
                "EXIT_MAINTENANCE command.",
            )

        self._monitoring_enabled = True

        return (
            "Maintenance mode exited.",
            {
                "deviceState": (
                    self.current_state.value
                ),
            },
        )

    async def _command_start_charging(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        del command

        battery = (
            self.sensor_manager.get_sensor(
                "battery"
            )
        )

        if not isinstance(
            battery,
            BatteryModel,
        ):
            raise RuntimeError(
                "Battery model unavailable."
            )

        battery.start_charging()

        return (
            "Charging started.",
            {
                "charging": True,
            },
        )

    async def _command_stop_charging(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        del command

        battery = (
            self.sensor_manager.get_sensor(
                "battery"
            )
        )

        if not isinstance(
            battery,
            BatteryModel,
        ):
            raise RuntimeError(
                "Battery model unavailable."
            )

        battery.stop_charging()

        return (
            "Charging stopped.",
            {
                "charging": False,
            },
        )

    async def _command_calibrate_sensor(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        sensor_name = (
            command.parameters[
                "sensorName"
            ]
        )

        sensor = (
            self.sensor_manager.get_sensor(
                sensor_name
            )
        )

        sensor.calibrate()

        return (
            f"Sensor '{sensor_name}' calibrated.",
            {
                "sensorName": sensor_name,
                "sensorStatus": (
                    sensor.status.value
                ),
            },
        )

    async def _command_request_measurement(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        del command

        snapshot = (
            await self.read_sensors_now()
        )

        await self._publish_latest_telemetry(
            force=True
        )

        return (
            "Immediate measurement completed.",
            {
                "measurements": (
                    self._build_telemetry_payload(
                        snapshot
                    )[
                        "measurements"
                    ]
                ),
            },
        )

    async def _command_request_device_health(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        del command

        report = (
            await self._create_health_report()
        )

        return (
            "Device health report generated.",
            {
                "deviceHealth": (
                    report.to_dict()
                ),
            },
        )

    async def _command_clear_alerts(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        del command

        self.alert_manager.clear()

        return (
            "Alert evaluation state cleared.",
            {},
        )

    async def _command_change_scenario(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        scenario = (
            SimulationScenario(
                command.parameters[
                    "scenario"
                ]
            )
        )

        self.change_scenario(
            scenario
        )

        return (
            f"Simulation scenario changed "
            f"to {scenario.value}.",
            {
                "scenario": (
                    scenario.value
                ),
            },
        )

    async def _command_simulate_sensor_failure(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        sensor_name = (
            command.parameters[
                "sensorName"
            ]
        )

        self.change_scenario(
            SimulationScenario.SENSOR_FAILURE,
            failed_sensor_name=(
                sensor_name
            ),
        )

        return (
            f"Sensor failure simulated "
            f"for '{sensor_name}'.",
            {
                "sensorName": sensor_name,
                "scenario": (
                    self.current_scenario.value
                ),
            },
        )

    async def _command_restore_sensor(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        sensor_name = (
            command.parameters[
                "sensorName"
            ]
        )

        self.sensor_manager.restore_sensor(
            sensor_name
        )

        if (
            self.current_scenario
            == SimulationScenario.SENSOR_FAILURE
        ):
            self.change_scenario(
                SimulationScenario.RESTING
            )

        return (
            f"Sensor '{sensor_name}' restored.",
            {
                "sensorName": sensor_name,
                "sensorStatus": (
                    self.sensor_manager
                    .get_sensor(
                        sensor_name
                    )
                    .status.value
                ),
            },
        )

    async def _command_simulate_network_outage(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        del command

        self.change_scenario(
            SimulationScenario.NETWORK_OUTAGE
        )

        return (
            "NETWORK_OUTAGE simulation scenario activated. "
            "Transport disconnection and offline queue behavior "
            "are implemented in Module 6.",
            {
                "scenario": (
                    self.current_scenario.value
                ),
            },
        )

    async def _command_restore_network(
        self,
        command: Command,
    ) -> tuple[str, dict[str, Any]]:
        del command

        if (
            self.current_scenario
            == SimulationScenario.NETWORK_OUTAGE
        ):
            self.change_scenario(
                SimulationScenario.RESTING
            )

        return (
            "Network simulation state restored.",
            {
                "scenario": (
                    self.current_scenario.value
                ),
            },
        )

    async def _process_shadow_deltas(
        self,
    ) -> None:
        if self.shadow_client is None:
            return

        deltas = (
            self.shadow_client.drain_deltas()
        )

        for delta in deltas:
            await self._apply_configuration_delta(
                delta=(
                    delta.state
                ),
                source=(
                    f"SHADOW_DELTA_V{delta.version}"
                ),
            )

    async def _apply_configuration_delta(
        self,
        delta: dict[str, Any],
        source: str,
    ) -> ConfigurationApplyResult:
        result = (
            self.configuration_manager.apply_delta(
                delta
            )
        )

        if not result.applied:
            signature = json.dumps(
                delta,
                sort_keys=True,
                default=str,
            )

            logger.warning(
                "Configuration rejected | "
                "source=%s | errors=%s",
                source,
                result.errors,
            )

            if (
                signature
                != self._last_rejected_delta_signature
            ):
                self._last_rejected_delta_signature = (
                    signature
                )

                await self._publish_configuration_event(
                    status="REJECTED",
                    source=source,
                    errors=list(
                        result.errors
                    ),
                )

                await self._report_configuration_rejected(
                    errors=list(
                        result.errors
                    )
                )

            return result

        self._last_rejected_delta_signature = (
            None
        )

        self._apply_runtime_configuration(
            result.config
        )

        logger.info(
            "Configuration applied | "
            "source=%s | config=%s",
            source,
            result.config.to_shadow_dict(),
        )

        await self._publish_configuration_event(
            status="APPLIED",
            source=source,
            errors=[],
        )

        await self._report_configuration_applied(
            message=(
                "Desired configuration validated "
                "and applied."
            )
        )

        return result

    def _apply_runtime_configuration(
        self,
        config: DeviceConfig,
    ) -> None:
        """Apply configuration to running modules."""

        self.alert_manager.heart_rate_minimum_threshold = (
            config.heart_rate_minimum_bpm
        )

        self.alert_manager.heart_rate_maximum_resting_threshold = (
            config.heart_rate_maximum_resting_bpm
        )

        self.alert_manager.skin_temperature_minimum_threshold = (
            config.skin_temperature_minimum_c
        )

        self.alert_manager.skin_temperature_maximum_threshold = (
            config.skin_temperature_maximum_c
        )

        self.alert_manager.low_battery_threshold_percentage = (
            config.low_battery_percentage
        )

        self.device_health_monitor.low_battery_threshold = (
            config.low_battery_percentage
        )

        self.analytics_manager = (
            AnalyticsManager(
                device_id=self.device_id,
                software_version=(
                    self.software_version
                ),
                window_sec=(
                    config.analytics_window_sec
                ),
            )
        )

        self.scheduler.update_periodic_job_interval(
            "sensor-reading",
            config.measurement_interval_sec,
        )

        self.scheduler.update_periodic_job_interval(
            "telemetry-publish",
            config.telemetry_interval_sec,
        )

        self.scheduler.update_periodic_job_interval(
            "device-health",
            config.health_report_interval_sec,
        )

    async def _publish_configuration_event(
        self,
        status: str,
        source: str,
        errors: list[str],
    ) -> None:
        payload = {
            "deviceId": (
                self.device_id
            ),
            "eventType": (
                "CONFIGURATION_CHANGED"
            ),
            "status": status,
            "source": source,
            "errors": errors,
            "timestamp": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }

        self.event_bus.publish(
            self.CONFIGURATION_EVENT,
            payload,
        )

        await self._publish_mqtt(
            self.mqtt_topics.events,
            payload,
            1,
        )

    async def _report_configuration_applied(
        self,
        message: str,
    ) -> None:
        if self.shadow_client is None:
            return

        reported = (
            self.current_config.to_shadow_dict()
        )

        reported[
            "softwareVersion"
        ] = self.software_version

        reported[
            "capabilities"
        ] = list(
            self.device_health_monitor
            .VERSION_1_CAPABILITIES
        )

        reported[
            "configurationStatus"
        ] = {
            "status": "APPLIED",
            "message": message,
            "timestamp": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }

        await asyncio.to_thread(
            self.shadow_client.update_reported,
            reported,
        )

    async def _report_configuration_rejected(
        self,
        errors: list[str],
    ) -> None:
        if self.shadow_client is None:
            return

        reported = {
            "configurationStatus": {
                "status": "REJECTED",
                "errors": errors,
                "timestamp": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
        }

        try:
            await asyncio.to_thread(
                self.shadow_client.update_reported,
                reported,
            )

        except Exception:
            logger.exception(
                "Unable to report rejected "
                "configuration to Device Shadow."
            )

    async def _transition_to(
        self,
        new_state: DeviceState,
        reason: str,
    ) -> StateTransition:
        transition = (
            self.state_machine.transition_to(
                new_state=new_state,
                reason=reason,
            )
        )

        logger.info(
            "Device state changed: %s -> %s | reason=%s",
            transition.previous_state.value,
            transition.current_state.value,
            transition.reason,
        )

        payload = {
            "deviceId": (
                self.device_id
            ),
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
            self.mqtt_topics.events,
            payload,
            1,
        )

        return transition

    async def _publish_presence(
        self,
        status: str,
    ) -> None:
        await self._publish_mqtt(
            self.mqtt_topics.presence,
            {
                "deviceId": self.device_id,
                "status": status,
                "deviceState": (
                    self.current_state.value
                ),
                "softwareVersion": (
                    self.software_version
                ),
            },
            1,
        )

    async def _publish_presence_heartbeat(
        self,
    ) -> None:
        await self._publish_presence(
            "ONLINE"
        )

    async def _publish_mqtt(
        self,
        topic: str,
        payload: dict[str, Any],
        qos: int,
    ) -> bool:
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
        mqtt_connected: (
            bool | None
        ) = None

        if self.mqtt_client is not None:
            mqtt_connected = (
                self.mqtt_client.is_connected
            )

        logger.info(
            "Core status | device=%s | "
            "version=%s | state=%s | "
            "scenario=%s | mqtt=%s | "
            "measurementInterval=%s | "
            "telemetryInterval=%s | "
            "temperatureUnit=%s",
            self.device_id,
            self.software_version,
            self.current_state.value,
            self.current_scenario.value,
            mqtt_connected,
            self.current_config.measurement_interval_sec,
            self.current_config.telemetry_interval_sec,
            self.current_config.temperature_unit.value,
        )