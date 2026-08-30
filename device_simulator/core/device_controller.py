"""Central controller for the simulated HealthBand device."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
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
from device_simulator.analytics.calorie_estimator import (
    CalorieEstimator,
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
from device_simulator.communication.message_serializer import (
    prepare_message,
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
from device_simulator.storage.local_database import (
    LocalDatabase,
)
from device_simulator.storage.offline_queue import (
    OfflineMessageType,
    OfflineQueue,
)
from device_simulator.storage.synchronization_manager import (
    SynchronizationManager,
    SynchronizationResult,
)
from device_simulator.utils.versioning import (
    is_at_least,
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
    CONNECTION_WATCH_INTERVAL_SEC = 1.0

    RECONNECT_RETRY_INTERVAL_SEC = 5.0

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
        offline_queue: OfflineQueue | None = None,
        synchronization_manager: (
            SynchronizationManager | None
        ) = None,
    ) -> None:
        self.device_id = (
            device_id
        )

        self.software_version = (
            software_version
        )

        self.event_bus = (
            event_bus
            or EventBus()
        )

        self.scheduler = (
            scheduler
            or Scheduler()
        )

        self.state_machine = (
            StateMachine()
        )

        self.user_profile = (
            user_profile
            or UserProfile()
        )

        self.scenario_engine = (
            ScenarioEngine(
                self.user_profile
            )
        )

        self.configuration_manager = (
            configuration_manager
            or ConfigurationManager(
                software_version=(
                    self.software_version
                )
            )
        )

        config = (
            self.configuration_manager.current
        )

        self.sensor_manager = (
            SensorManager(
                user_profile=(
                    self.user_profile
                ),
                random_seed=(
                    random_seed
                ),
                software_version=(
                    self.software_version
                ),
                spo2_measurement_enabled=(
                    config.spo2_measurement_enabled
                ),
            )
        )

        self.analytics_manager = (
            AnalyticsManager(
                device_id=(
                    self.device_id
                ),
                software_version=(
                    self.software_version
                ),
                window_sec=(
                    config.analytics_window_sec
                ),
                spo2_minimum_threshold=(
                    config.spo2_minimum_threshold
                    if config.spo2_minimum_threshold
                    is not None
                    else 92.0
                ),
                spo2_enabled=(
                    config.spo2_measurement_enabled
                ),
            )
        )

        self.alert_manager = (
            AlertManager(
                device_id=(
                    self.device_id
                ),
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
                spo2_minimum_threshold=(
                    config.spo2_minimum_threshold
                    if config.spo2_minimum_threshold
                    is not None
                    else 92.0
                ),
            )
        )

        self.device_health_monitor = (
            DeviceHealthMonitor(
                device_id=(
                    self.device_id
                ),
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
                device_id=(
                    self.device_id
                )
            )
        )

        if offline_queue is None:
            database = (
                LocalDatabase(
                    Path.cwd()
                    / "runtime"
                    / "healthband.db"
                )
            )

            self.offline_queue = (
                OfflineQueue(
                    database=database,
                    maximum_items=(
                        config.offline_queue_maximum_items
                    ),
                )
            )

        else:
            self.offline_queue = (
                offline_queue
            )

        self.calorie_estimator: (
            CalorieEstimator | None
        ) = None

        if is_at_least(
            self.software_version,
            "2.0.0",
        ):
            self.calorie_estimator = (
                CalorieEstimator(
                    user_profile=(
                        self.user_profile
                    ),
                    database=(
                        self.offline_queue.database
                    ),
                )
            )

        if (
            synchronization_manager
            is not None
        ):
            self.synchronization_manager = (
                synchronization_manager
            )

        elif self.mqtt_client is not None:
            self.synchronization_manager = (
                SynchronizationManager(
                    offline_queue=(
                        self.offline_queue
                    ),
                    mqtt_client=(
                        self.mqtt_client
                    ),
                )
            )

        else:
            self.synchronization_manager = (
                None
            )

        self.command_validator = (
            CommandValidator(
                device_id=(
                    self.device_id
                )
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

        self._started = (
            False
        )

        self._last_rejected_delta_signature: (
            str | None
        ) = None

        self._simulated_outage_until: (
            float | None
        ) = None

        self._manual_reconnect_needed = (
            False
        )

        self._next_manual_reconnect_at = (
            0.0
        )

        self._scenario_before_network_outage: (
            SimulationScenario | None
        ) = None

        self._offline_queue_near_limit_alerted = (
            False
        )

        self._reconnect_attempts = (
            0
        )

        self._mqtt_send_failures = (
            0
        )

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
        """Start HealthBand."""

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

        await self._synchronize_offline_queue(
            reason="STARTUP"
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
            callback=(
                self._scheduled_sensor_read
            ),
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
            callback=(
                self._log_core_status
            ),
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

            self.scheduler.add_periodic_job(
                name="connection-watch",
                interval_sec=(
                    self.CONNECTION_WATCH_INTERVAL_SEC
                ),
                callback=(
                    self._connection_watch_tick
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
            "HealthBand Module 6 started successfully."
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
                    "Unable to enter SHUTTING_DOWN state."
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
            scenario=(
                scenario
            ),
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
        """Force immediate sensor reading."""

        snapshot = (
            await self._read_sensors(
                force=True
            )
        )

        if snapshot is None:
            raise RuntimeError(
                "Immediate sensor reading failed."
            )

        return (
            snapshot
        )

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
        result = (
            await self._apply_configuration_delta(
                delta=delta,
                source="LOCAL_TEST",
            )
        )

        return (
            result.applied
        )

    async def synchronize_offline_queue_now(
        self,
    ) -> SynchronizationResult | None:
        """Force one queue synchronization pass."""

        return (
            await self._synchronize_offline_queue(
                reason="MANUAL_TEST"
            )
        )

    async def _run_core_self_test(
        self,
    ) -> None:
        """Run Module 6 self-test."""

        logger.info(
            "Running Module 6 core self-test."
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
            "configuration_manager": (
                self.configuration_manager
                is not None
            ),
            "command_handler": (
                self.command_handler
                is not None
            ),
            "offline_queue": (
                self.offline_queue
                is not None
            ),
            "local_database": (
                self.offline_queue
                .database
                .ping()
            ),
            "device_id": bool(
                self.device_id.strip()
            ),
            "software_version": bool(
                self.software_version.strip()
            ),
        }

        if is_at_least(
            self.software_version,
            "2.0.0",
        ):
            checks[
                "spo2_sensor"
            ] = self.sensor_manager.has_sensor(
                "spo2"
            )

            checks[
                "calorie_estimator"
            ] = (
                self.calorie_estimator
                is not None
            )

        failed = [
            name
            for (
                name,
                passed,
            )
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
            "Module 6 core self-test passed."
        )

    async def _connect_to_cloud(
        self,
    ) -> None:
        """Initial AWS connection."""

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

                await (
                    self._synchronize_shadow_on_startup()
                )

        except Exception as exc:
            self.device_health_monitor.record_fault(
                f"AWS_IOT_CONNECTION_FAILED: {exc}"
            )

            logger.exception(
                "Unable to initialize AWS IoT communication."
            )

            await self._transition_to(
                DeviceState.ERROR,
                "AWS IoT initialization failed.",
            )

            raise

    async def _synchronize_shadow_on_startup(
        self,
    ) -> None:
        """Retrieve Shadow and reconcile desired/reported config."""

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

                await (
                    self._apply_configuration_delta(
                        delta=delta,
                        source=(
                            "SHADOW_STARTUP"
                        ),
                    )
                )

            else:
                await (
                    self._report_configuration_applied(
                        message=(
                            "Current local configuration "
                            "reported on startup."
                        )
                    )
                )

        except ShadowOperationRejected as exc:
            if exc.code == 404:
                logger.info(
                    "No existing Device Shadow. "
                    "Creating initial reported state."
                )

                await (
                    self._report_configuration_applied(
                        message=(
                            "Initial configuration reported."
                        )
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
        """
        Read sensors even when OFFLINE.

        Network state deliberately does not stop local measurements.
        """

        if (
            not self._monitoring_enabled
            and not force
        ):
            return (
                self.latest_snapshot
            )

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

        if self.calorie_estimator is not None:
            calorie_values = (
                self.calorie_estimator
                .estimate_interval(
                    measurements=(
                        snapshot.measurements
                    ),
                    activity_level=(
                        snapshot.activity_level
                    ),
                    scenario=(
                        snapshot.scenario
                    ),
                    elapsed_sec=(
                        self.current_config
                        .measurement_interval_sec
                    ),
                    timestamp=(
                        snapshot.timestamp
                    ),
                )
            )

            snapshot.measurements.update(
                calorie_values
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

        self.event_bus.publish(
            self.SENSOR_SNAPSHOT_EVENT,
            {
                "deviceId": (
                    self.device_id
                ),
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

        if (
            self.current_config
            .alerts_enabled
        ):
            alerts = (
                self.alert_manager
                .evaluate_snapshot(
                    snapshot
                )
            )

            alerts = [
                alert
                for alert
                in alerts
                if self._is_alert_enabled(
                    alert
                )
            ]

        for alert in alerts:
            await self._publish_alert(
                alert
            )

        if (
            self.current_config
            .analytics_enabled
        ):
            analytics_result = (
                self.analytics_manager
                .add_snapshot(
                    snapshot=snapshot,
                    elapsed_sec=(
                        self.current_config
                        .measurement_interval_sec
                    ),
                    alerts_generated=(
                        len(
                            alerts
                        )
                    ),
                )
            )

            if (
                analytics_result
                is not None
            ):
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
                    message_type=(
                        OfflineMessageType.ANALYTICS
                    ),
                )

        return (
            snapshot
        )

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
            topic=(
                self.mqtt_topics.telemetry
            ),
            payload=payload,
            qos=0,
            message_type=(
                OfflineMessageType.TELEMETRY
            ),
        )

    def _build_telemetry_payload(
        self,
        snapshot: SensorSnapshot,
    ) -> dict[str, Any]:
        """Build externally visible telemetry."""

        measurements = dict(
            snapshot.measurements
        )

        temperature_celsius = (
            measurements.pop(
                "skinTemperatureCelsius",
                None,
            )
        )

        if (
            temperature_celsius
            is not None
        ):
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
            "schemaVersion": (
                2
                if is_at_least(
                    self.software_version,
                    "2.0.0",
                )
                else 1
            ),
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
            "deviceState": (
                self.current_state.value
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
                config
                .heart_rate_alerts_enabled
            )

        if alert.type in {
            AlertType.TEMPERATURE_BELOW_THRESHOLD,
            AlertType.TEMPERATURE_ABOVE_THRESHOLD,
        }:
            return (
                config
                .temperature_alerts_enabled
            )

        if (
            alert.type
            == AlertType.LOW_BATTERY
        ):
            return (
                config
                .battery_alerts_enabled
            )

        if alert.type in {
            AlertType.SENSOR_FAILED,
            AlertType.SENSOR_NO_DATA,
            AlertType.SENSOR_INVALID_VALUE,
        }:
            return (
                config
                .sensor_failure_alerts_enabled
            )

        if alert.type in {
            AlertType.SPO2_BELOW_THRESHOLD,
            AlertType.SPO2_SENSOR_FAILED,
        }:
            return bool(
                config.spo2_alerts_enabled
            )

        return (
            True
        )

    async def _publish_alert(
        self,
        alert: Alert,
    ) -> None:
        logger.warning(
            "Alert generated | "
            "type=%s | "
            "severity=%s | "
            "scenario=%s | "
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
            topic=(
                self.mqtt_topics.alerts
            ),
            payload=payload,
            qos=1,
            message_type=(
                OfflineMessageType.ALERT
            ),
        )

    async def _emit_system_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        measured_value: Any = None,
        configured_threshold: Any = None,
    ) -> None:
        """Create a non-sensor technical alert."""

        alert = Alert(
            alert_id=(
                f"alert-{uuid4()}"
            ),
            device_id=(
                self.device_id
            ),
            type=(
                alert_type
            ),
            severity=(
                severity
            ),
            timestamp=(
                datetime.now(
                    timezone.utc
                )
            ),
            scenario=(
                self.current_scenario.value
            ),
            activity_level=(
                self.latest_snapshot.activity_level
                if (
                    self.latest_snapshot
                    is not None
                )
                else "UNKNOWN"
            ),
            measured_value=(
                measured_value
            ),
            configured_threshold=(
                configured_threshold
            ),
            message=(
                message
            ),
        )

        await self._publish_alert(
            alert
        )

    async def _create_health_report(
        self,
    ) -> DeviceHealthReport:
        statuses = (
            self.sensor_manager
            .sensor_statuses()
        )

        battery_percentage: (
            float | None
        ) = None

        if (
            self.latest_snapshot
            is not None
        ):
            value = (
                self.latest_snapshot
                .measurements
                .get(
                    "batteryPercentage"
                )
            )

            if value is not None:
                battery_percentage = (
                    float(
                        value
                    )
                )

        mqtt_connected: (
            bool | None
        ) = None

        if (
            self.mqtt_client
            is not None
        ):
            mqtt_connected = (
                self.mqtt_client
                .is_connected
            )

        queue_size = (
            self._health_queue_size()
        )

        report = (
            self.device_health_monitor
            .create_report(
                device_state=(
                    self.current_state
                ),
                sensor_statuses=(
                    statuses
                ),
                battery_percentage=(
                    battery_percentage
                ),
                mqtt_connected=(
                    mqtt_connected
                ),
                offline_queue_size=(
                    queue_size
                ),
                local_database_size_bytes=(
                    self.offline_queue
                    .database_size_bytes
                ),
                reconnect_attempts=(
                    self._reconnect_attempts
                ),
                mqtt_send_failures=(
                    self._mqtt_send_failures
                ),
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
            "offlineQueue=%s",
            report.device_status.value,
            report.device_state.value,
            report.mqtt_connected,
            report.battery_percentage,
            report.offline_queue_size,
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
            message_type=(
                OfflineMessageType.HEALTH
            ),
        )

        return (
            report
        )

    def _health_queue_size(
        self,
    ) -> int:
        """
        Local-only unit tests do not represent an offline cloud device.

        Therefore queue size contributes to technical health only when
        a real/fake MQTT client is configured.
        """

        if self.mqtt_client is None:
            return (
                0
            )

        return (
            self.offline_queue.size()
        )

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
                != self.mqtt_topics
                .commands_request
            ):
                continue

            try:
                command = (
                    self.command_validator
                    .validate(
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
                        command_id=(
                            command_id
                        ),
                        device_id=(
                            self.device_id
                        ),
                        command_type=(
                            str(
                                raw_type
                            )
                        ),
                        status=(
                            CommandStatus.REJECTED
                        ),
                        message=(
                            str(
                                exc
                            )
                        ),
                        error_code=(
                            "COMMAND_VALIDATION_FAILED"
                        ),
                        timestamp=(
                            datetime.now(
                                timezone.utc
                            )
                        ),
                    )
                )

                await (
                    self._publish_command_result(
                        rejected
                    )
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

                await (
                    self._publish_command_result(
                        cached
                    )
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
                await self.command_handler
                .execute(
                    command
                )
            )

            await self._publish_command_result(
                result
            )

            if (
                command.type
                == CommandType.SIMULATE_NETWORK_OUTAGE
                and result.status
                == CommandStatus.SUCCEEDED
            ):
                duration = float(
                    command.parameters.get(
                        "durationSec",
                        15.0,
                    )
                )

                await (
                    self._begin_simulated_network_outage(
                        duration_sec=(
                            duration
                        )
                    )
                )

    def _transient_command_result(
        self,
        command: Command,
        status: CommandStatus,
        message: str,
    ) -> CommandResult:
        return (
            CommandResult(
                command_id=(
                    command.command_id
                ),
                device_id=(
                    command.device_id
                ),
                command_type=(
                    command.type.value
                ),
                status=(
                    status
                ),
                message=(
                    message
                ),
                timestamp=(
                    datetime.now(
                        timezone.utc
                    )
                ),
            )
        )

    async def _publish_command_result(
        self,
        result: CommandResult,
    ) -> None:
        logger.info(
            "Command result | "
            "commandId=%s | "
            "type=%s | "
            "status=%s | "
            "duplicate=%s",
            result.command_id,
            result.command_type,
            result.status.value,
            result.duplicate,
        )

        await self._publish_mqtt(
            topic=(
                self.mqtt_topics
                .commands_response
            ),
            payload=(
                result.to_dict()
            ),
            qos=1,
            message_type=(
                OfflineMessageType
                .COMMAND_RESPONSE
            ),
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
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        del command

        self._monitoring_enabled = (
            True
        )

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
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        del command

        self._monitoring_enabled = (
            False
        )

        return (
            "Periodic sensor monitoring stopped.",
            {
                "monitoringEnabled": False,
            },
        )

    async def _command_restart_device(
        self,
        command: Command,
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
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
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        del command

        if (
            self.current_state
            != DeviceState.MAINTENANCE
        ):
            await self._transition_to(
                DeviceState.MAINTENANCE,
                "ENTER_MAINTENANCE command.",
            )

        self._monitoring_enabled = (
            False
        )

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
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        del command

        if (
            self.current_state
            == DeviceState.MAINTENANCE
        ):
            await self._transition_to(
                DeviceState.MONITORING,
                "EXIT_MAINTENANCE command.",
            )

        self._monitoring_enabled = (
            True
        )

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
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        del command

        battery = (
            self.sensor_manager
            .get_sensor(
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
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        del command

        battery = (
            self.sensor_manager
            .get_sensor(
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
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        sensor_name = (
            command.parameters[
                "sensorName"
            ]
        )

        sensor = (
            self.sensor_manager
            .get_sensor(
                sensor_name
            )
        )

        sensor.calibrate()

        return (
            f"Sensor '{sensor_name}' calibrated.",
            {
                "sensorName": (
                    sensor_name
                ),
                "sensorStatus": (
                    sensor.status.value
                ),
            },
        )

    async def _command_request_measurement(
        self,
        command: Command,
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
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
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
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
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        del command

        self.alert_manager.clear()

        return (
            "Alert evaluation state cleared.",
            {},
        )

    async def _command_change_scenario(
        self,
        command: Command,
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
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
            "Simulation scenario changed "
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
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
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
            "Sensor failure simulated "
            f"for '{sensor_name}'.",
            {
                "sensorName": (
                    sensor_name
                ),
                "scenario": (
                    self.current_scenario.value
                ),
            },
        )

    async def _command_restore_sensor(
        self,
        command: Command,
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
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
                "sensorName": (
                    sensor_name
                ),
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
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        duration = float(
            command.parameters.get(
                "durationSec",
                15.0,
            )
        )

        if (
            self.current_scenario
            != SimulationScenario.NETWORK_OUTAGE
        ):
            self._scenario_before_network_outage = (
                self.current_scenario
            )

        self.change_scenario(
            SimulationScenario.NETWORK_OUTAGE
        )

        return (
            "Simulated network outage scheduled.",
            {
                "scenario": (
                    SimulationScenario
                    .NETWORK_OUTAGE
                    .value
                ),
                "durationSec": (
                    duration
                ),
                "automaticReconnect": (
                    True
                ),
            },
        )

    async def _command_restore_network(
        self,
        command: Command,
    ) -> tuple[
        str,
        dict[str, Any],
    ]:
        del command

        self._simulated_outage_until = (
            None
        )

        self._next_manual_reconnect_at = (
            0.0
        )

        if (
            self.current_scenario
            == SimulationScenario.NETWORK_OUTAGE
        ):
            self._restore_pre_outage_scenario()

        return (
            "Network restoration requested.",
            {
                "automaticReconnect": True,
            },
        )

    async def _begin_simulated_network_outage(
        self,
        duration_sec: float,
    ) -> None:
        """Perform an actual graceful MQTT disconnect for simulation."""

        if self.mqtt_client is None:
            return

        self._simulated_outage_until = (
            monotonic()
            + duration_sec
        )

        self._manual_reconnect_needed = (
            True
        )

        logger.warning(
            "Starting simulated network outage | "
            "durationSec=%s",
            duration_sec,
        )

        if (
            self.current_state
            != DeviceState.OFFLINE
        ):
            await self._transition_to(
                DeviceState.OFFLINE,
                "Simulated network outage started.",
            )

        await asyncio.to_thread(
            self.mqtt_client.disconnect
        )

        await self._emit_system_alert(
            alert_type=(
                AlertType.MQTT_DISCONNECTED
            ),
            severity=(
                AlertSeverity.WARNING
            ),
            message=(
                "MQTT connection to AWS IoT Core "
                "is unavailable."
            ),
        )

        logger.warning(
            "HealthBand is OFFLINE. "
            "Local sensing and analytics continue."
        )

    async def _connection_watch_tick(
        self,
    ) -> None:
        """Monitor MQTT connectivity and coordinate recovery."""

        if self.mqtt_client is None:
            return

        now = (
            monotonic()
        )

        if self._manual_reconnect_needed:
            if (
                self._simulated_outage_until
                is not None
                and now
                < self._simulated_outage_until
            ):
                return

            if (
                now
                >= self._next_manual_reconnect_at
            ):
                await (
                    self._attempt_manual_reconnect()
                )

            return

        if not self.mqtt_client.is_connected:
            if (
                self.current_state
                not in {
                    DeviceState.OFFLINE,
                    DeviceState.CONNECTING,
                    DeviceState.ERROR,
                    DeviceState.SHUTTING_DOWN,
                }
            ):
                await (
                    self._enter_offline_after_transport_loss()
                )

            return

        if (
            self.current_state
            == DeviceState.OFFLINE
        ):
            await (
                self._complete_automatic_reconnection()
            )

    async def _enter_offline_after_transport_loss(
        self,
    ) -> None:
        """React to an unexpected connection interruption."""

        if (
            self.current_scenario
            != SimulationScenario.NETWORK_OUTAGE
        ):
            self._scenario_before_network_outage = (
                self.current_scenario
            )

            self.change_scenario(
                SimulationScenario.NETWORK_OUTAGE
            )

        try:
            await self._transition_to(
                DeviceState.OFFLINE,
                "MQTT connection to AWS IoT Core lost.",
            )

        except InvalidStateTransitionError:
            logger.warning(
                "Unable to enter OFFLINE from state %s.",
                self.current_state.value,
            )

        await self._emit_system_alert(
            alert_type=(
                AlertType.MQTT_DISCONNECTED
            ),
            severity=(
                AlertSeverity.WARNING
            ),
            message=(
                "MQTT connection to AWS IoT Core "
                "was interrupted."
            ),
        )

    async def _attempt_manual_reconnect(
        self,
    ) -> None:
        """Reconnect after an intentional simulated outage."""

        if self.mqtt_client is None:
            return

        self._reconnect_attempts += 1

        self._next_manual_reconnect_at = (
            monotonic()
            + self.RECONNECT_RETRY_INTERVAL_SEC
        )

        logger.info(
            "Attempting MQTT reconnect | attempt=%s",
            self._reconnect_attempts,
        )

        try:
            if (
                self.current_state
                == DeviceState.OFFLINE
            ):
                await self._transition_to(
                    DeviceState.CONNECTING,
                    "Attempting AWS IoT reconnect.",
                )

            await asyncio.to_thread(
                self.mqtt_client.connect
            )

            await asyncio.to_thread(
                self.mqtt_client.resubscribe_all
            )

            if (
                self.shadow_client
                is not None
            ):
                await asyncio.to_thread(
                    self.shadow_client.resubscribe
                )

                await (
                    self._synchronize_shadow_on_startup()
                )

            self._manual_reconnect_needed = (
                False
            )

            self._simulated_outage_until = (
                None
            )

            await self._finish_reconnection(
                reason=(
                    "AWS IoT reconnect completed."
                )
            )

        except Exception as exc:
            logger.warning(
                "MQTT reconnect attempt failed | "
                "error=%s",
                exc,
            )

            self.device_health_monitor.record_fault(
                f"MQTT_RECONNECT_FAILED: {exc}"
            )

            if (
                self.current_state
                == DeviceState.CONNECTING
            ):
                await self._transition_to(
                    DeviceState.OFFLINE,
                    "AWS IoT reconnect failed.",
                )

    async def _complete_automatic_reconnection(
        self,
    ) -> None:
        """Handle reconnect completed internally by AWS SDK."""

        self._reconnect_attempts += 1

        logger.info(
            "MQTT connection is available again."
        )

        try:
            if (
                self.current_state
                == DeviceState.OFFLINE
            ):
                await self._transition_to(
                    DeviceState.CONNECTING,
                    "MQTT connection resumed.",
                )

            await asyncio.to_thread(
                self.mqtt_client.resubscribe_all
            )

            if (
                self.shadow_client
                is not None
            ):
                await asyncio.to_thread(
                    self.shadow_client.resubscribe
                )

                await (
                    self._synchronize_shadow_on_startup()
                )

            await self._finish_reconnection(
                reason=(
                    "MQTT connection automatically resumed."
                )
            )

        except Exception as exc:
            logger.exception(
                "Post-reconnect initialization failed."
            )

            self.device_health_monitor.record_fault(
                f"POST_RECONNECT_FAILED: {exc}"
            )

    async def _finish_reconnection(
        self,
        reason: str,
    ) -> None:
        """Complete state restoration and offline synchronization."""

        if (
            self.current_state
            == DeviceState.CONNECTING
        ):
            await self._transition_to(
                DeviceState.MONITORING,
                reason,
            )

        self._restore_pre_outage_scenario()

        await self._publish_presence(
            "ONLINE"
        )

        await self._synchronize_offline_queue(
            reason="RECONNECT"
        )

        await self._create_health_report()

        logger.info(
            "HealthBand returned ONLINE."
        )

    def _restore_pre_outage_scenario(
        self,
    ) -> None:
        """Restore scenario active before network interruption."""

        scenario = (
            self._scenario_before_network_outage
            or SimulationScenario.RESTING
        )

        if (
            self.current_scenario
            == SimulationScenario.NETWORK_OUTAGE
        ):
            self.change_scenario(
                scenario
            )

        self._scenario_before_network_outage = (
            None
        )

    async def _synchronize_offline_queue(
        self,
        reason: str,
    ) -> SynchronizationResult | None:
        """Synchronize persistent offline queue when MQTT is available."""

        if (
            self.synchronization_manager
            is None
            or self.mqtt_client
            is None
            or not self.mqtt_client.is_connected
        ):
            return (
                None
            )

        before = (
            self.offline_queue.size()
        )

        if before == 0:
            return (
                SynchronizationResult(
                    attempted=0,
                    sent=0,
                    failed=0,
                    remaining=0,
                )
            )

        logger.info(
            "Starting offline synchronization | "
            "reason=%s | queued=%s",
            reason,
            before,
        )

        result = (
            await asyncio.to_thread(
                self.synchronization_manager
                .synchronize,
                1000,
            )
        )

        logger.info(
            "Offline synchronization completed | "
            "attempted=%s | sent=%s | "
            "failed=%s | remaining=%s",
            result.attempted,
            result.sent,
            result.failed,
            result.remaining,
        )

        if (
            result.remaining
            < (
                self.offline_queue.maximum_items
                * 0.5
            )
        ):
            self._offline_queue_near_limit_alerted = (
                False
            )

        await self._publish_mqtt(
            topic=(
                self.mqtt_topics.events
            ),
            payload={
                "deviceId": (
                    self.device_id
                ),
                "eventType": (
                    "OFFLINE_SYNC_COMPLETED"
                ),
                "reason": (
                    reason
                ),
                "attempted": (
                    result.attempted
                ),
                "sent": (
                    result.sent
                ),
                "failed": (
                    result.failed
                ),
                "remaining": (
                    result.remaining
                ),
                "timestamp": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            },
            qos=1,
            message_type=(
                OfflineMessageType.EVENT
            ),
        )

        return (
            result
        )

    async def _enqueue_offline_message(
        self,
        message_type: OfflineMessageType,
        topic: str,
        payload: dict[str, Any],
        qos: int,
    ) -> None:
        """Persist unsent MQTT message."""

        result = (
            await asyncio.to_thread(
                self.offline_queue.enqueue,
                message_type,
                topic,
                payload,
                qos,
            )
        )

        if result.inserted:
            logger.info(
                "MQTT message stored offline | "
                "type=%s | "
                "messageId=%s | "
                "queueSize=%s",
                message_type.value,
                result.message_id,
                result.queue_size,
            )

            if (
                result.dropped_message_id
                is not None
            ):
                logger.warning(
                    "OfflineQueue evicted older "
                    "lower-priority message | "
                    "messageId=%s",
                    result.dropped_message_id,
                )

        else:
            logger.warning(
                "MQTT message was not added "
                "to OfflineQueue | "
                "messageId=%s | reason=%s",
                result.message_id,
                result.reason,
            )

        if (
            message_type
            != OfflineMessageType.ALERT
            and not self._offline_queue_near_limit_alerted
            and self.offline_queue.is_near_limit()
        ):
            self._offline_queue_near_limit_alerted = (
                True
            )

            await (
                self._queue_near_limit_alert()
            )

    async def _queue_near_limit_alert(
        self,
    ) -> None:
        """Persist one anti-spam alert when queue approaches its limit."""

        queue_size = (
            self.offline_queue.size()
        )

        alert = Alert(
            alert_id=(
                f"alert-{uuid4()}"
            ),
            device_id=(
                self.device_id
            ),
            type=(
                AlertType.OFFLINE_QUEUE_NEAR_LIMIT
            ),
            severity=(
                AlertSeverity.WARNING
            ),
            timestamp=(
                datetime.now(
                    timezone.utc
                )
            ),
            scenario=(
                self.current_scenario.value
            ),
            activity_level=(
                self.latest_snapshot.activity_level
                if (
                    self.latest_snapshot
                    is not None
                )
                else "UNKNOWN"
            ),
            measured_value=(
                queue_size
            ),
            configured_threshold=(
                self.offline_queue.maximum_items
            ),
            message=(
                "OfflineQueue is approaching "
                "its configured capacity."
            ),
        )

        self.event_bus.publish(
            self.ALERT_EVENT,
            alert.to_dict(),
        )

        await asyncio.to_thread(
            self.offline_queue.enqueue,
            OfflineMessageType.ALERT,
            self.mqtt_topics.alerts,
            alert.to_dict(),
            1,
        )

        logger.warning(
            "OFFLINE_QUEUE_NEAR_LIMIT alert queued | "
            "size=%s | maximum=%s",
            queue_size,
            self.offline_queue.maximum_items,
        )

    async def _process_shadow_deltas(
        self,
    ) -> None:
        if (
            self.shadow_client
            is None
            or (
                self.mqtt_client
                is not None
                and not self.mqtt_client.is_connected
            )
        ):
            return

        deltas = (
            self.shadow_client
            .drain_deltas()
        )

        for delta in deltas:
            await (
                self._apply_configuration_delta(
                    delta=(
                        delta.state
                    ),
                    source=(
                        f"SHADOW_DELTA_V{delta.version}"
                    ),
                )
            )

    async def _apply_configuration_delta(
        self,
        delta: dict[str, Any],
        source: str,
    ) -> ConfigurationApplyResult:
        result = (
            self.configuration_manager
            .apply_delta(
                delta
            )
        )

        if not result.applied:
            signature = (
                json.dumps(
                    delta,
                    sort_keys=True,
                    default=str,
                )
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

                await (
                    self._publish_configuration_event(
                        status="REJECTED",
                        source=source,
                        errors=list(
                            result.errors
                        ),
                    )
                )

                await (
                    self._report_configuration_rejected(
                        errors=list(
                            result.errors
                        )
                    )
                )

            return (
                result
            )

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

        await (
            self._publish_configuration_event(
                status="APPLIED",
                source=source,
                errors=[],
            )
        )

        await (
            self._report_configuration_applied(
                message=(
                    "Desired configuration "
                    "validated and applied."
                )
            )
        )

        return (
            result
        )

    def _apply_runtime_configuration(
        self,
        config: DeviceConfig,
    ) -> None:
        """Apply configuration to live modules."""

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

        self.alert_manager.spo2_minimum_threshold = (
            config.spo2_minimum_threshold
            if config.spo2_minimum_threshold
            is not None
            else 92.0
        )

        if config.spo2_measurement_enabled is not None:
            self.sensor_manager.set_spo2_enabled(
                config.spo2_measurement_enabled
            )

        self.device_health_monitor.low_battery_threshold = (
            config.low_battery_percentage
        )

        self.analytics_manager = (
            AnalyticsManager(
                device_id=(
                    self.device_id
                ),
                software_version=(
                    self.software_version
                ),
                window_sec=(
                    config.analytics_window_sec
                ),
                spo2_minimum_threshold=(
                    config.spo2_minimum_threshold
                    if config.spo2_minimum_threshold
                    is not None
                    else 92.0
                ),
                spo2_enabled=(
                    config.spo2_measurement_enabled
                ),
            )
        )

        self.offline_queue.update_maximum_items(
            config.offline_queue_maximum_items
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
            "status": (
                status
            ),
            "source": (
                source
            ),
            "errors": (
                errors
            ),
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
            topic=(
                self.mqtt_topics.events
            ),
            payload=(
                payload
            ),
            qos=1,
            message_type=(
                OfflineMessageType.EVENT
            ),
        )

    async def _report_configuration_applied(
        self,
        message: str,
    ) -> None:
        if (
            self.shadow_client is None
            or (
                self.mqtt_client
                is not None
                and not self.mqtt_client.is_connected
            )
        ):
            return

        reported = (
            self.current_config
            .to_shadow_dict()
        )

        reported[
            "softwareVersion"
        ] = (
            self.software_version
        )

        reported[
            "capabilities"
        ] = list(
            self.device_health_monitor
            .capabilities
        )

        reported[
            "configurationStatus"
        ] = {
            "status": (
                "APPLIED"
            ),
            "message": (
                message
            ),
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
        if (
            self.shadow_client is None
            or (
                self.mqtt_client
                is not None
                and not self.mqtt_client.is_connected
            )
        ):
            return

        reported = {
            "configurationStatus": {
                "status": (
                    "REJECTED"
                ),
                "errors": (
                    errors
                ),
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
            self.state_machine
            .transition_to(
                new_state=(
                    new_state
                ),
                reason=(
                    reason
                ),
            )
        )

        logger.info(
            "Device state changed: "
            "%s -> %s | reason=%s",
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
            topic=(
                self.mqtt_topics.events
            ),
            payload=(
                payload
            ),
            qos=1,
            message_type=(
                OfflineMessageType.EVENT
            ),
        )

        return (
            transition
        )

    async def _publish_presence(
        self,
        status: str,
    ) -> None:
        """
        Presence is intentionally not stored in OfflineQueue.

        Old heartbeat/presence messages are not useful after reconnect.
        """

        await self._publish_mqtt(
            topic=(
                self.mqtt_topics.presence
            ),
            payload={
                "deviceId": (
                    self.device_id
                ),
                "status": (
                    status
                ),
                "deviceState": (
                    self.current_state.value
                ),
                "softwareVersion": (
                    self.software_version
                ),
            },
            qos=1,
            message_type=(
                OfflineMessageType.OTHER
            ),
            queue_if_offline=False,
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
        message_type: OfflineMessageType,
        queue_if_offline: bool = True,
    ) -> bool:
        """
        Publish immediately or persist locally if connection is absent.

        messageId and timestamp are generated before the first attempt,
        therefore synchronized retries preserve the original identity.
        """

        prepared = (
            prepare_message(
                payload
            )
        )

        if self.mqtt_client is None:
            return (
                False
            )

        if (
            self.mqtt_client
            .is_connected
        ):
            try:
                await asyncio.to_thread(
                    self.mqtt_client.publish,
                    topic,
                    prepared,
                    qos,
                )

                return (
                    True
                )

            except Exception as exc:
                self._mqtt_send_failures += 1

                logger.warning(
                    "MQTT publish failed | "
                    "topic=%s | error=%s",
                    topic,
                    exc,
                )

                self.device_health_monitor.record_fault(
                    "MQTT_PUBLISH_FAILED: "
                    f"{topic}: {exc}"
                )

                if queue_if_offline:
                    await (
                        self._enqueue_offline_message(
                            message_type=(
                                message_type
                            ),
                            topic=(
                                topic
                            ),
                            payload=(
                                prepared
                            ),
                            qos=(
                                qos
                            ),
                        )
                    )

                return (
                    False
                )

        if queue_if_offline:
            await self._enqueue_offline_message(
                message_type=(
                    message_type
                ),
                topic=(
                    topic
                ),
                payload=(
                    prepared
                ),
                qos=(
                    qos
                ),
            )

        return (
            False
        )

    async def _log_core_status(
        self,
    ) -> None:
        mqtt_connected: (
            bool | None
        ) = None

        if (
            self.mqtt_client
            is not None
        ):
            mqtt_connected = (
                self.mqtt_client
                .is_connected
            )

        logger.info(
            "Core status | "
            "device=%s | "
            "version=%s | "
            "state=%s | "
            "scenario=%s | "
            "mqtt=%s | "
            "offlineQueue=%s | "
            "measurementInterval=%s | "
            "telemetryInterval=%s | "
            "temperatureUnit=%s",
            self.device_id,
            self.software_version,
            self.current_state.value,
            self.current_scenario.value,
            mqtt_connected,
            (
                self.offline_queue.size()
                if (
                    self.mqtt_client
                    is not None
                )
                else 0
            ),
            (
                self.current_config
                .measurement_interval_sec
            ),
            (
                self.current_config
                .telemetry_interval_sec
            ),
            (
                self.current_config
                .temperature_unit.value
            ),
        )