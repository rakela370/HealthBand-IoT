"""HealthBand local alert evaluation."""

from uuid import uuid4

from device_simulator.alerts.alert import (
    Alert,
    AlertSeverity,
    AlertType,
)
from device_simulator.alerts.threshold_evaluator import (
    ThresholdEvaluator,
)
from device_simulator.sensors.sensor_manager import (
    SensorSnapshot,
)


class AlertManager:
    """Evaluate snapshots and generate technical alerts."""

    def __init__(
        self,
        device_id: str,
        heart_rate_minimum_threshold: float = 50.0,
        heart_rate_maximum_resting_threshold: float = 110.0,
        skin_temperature_minimum_threshold: float = 30.0,
        skin_temperature_maximum_threshold: float = 37.0,
        low_battery_threshold_percentage: float = 15.0,
    ) -> None:
        self.device_id = device_id

        self.heart_rate_minimum_threshold = (
            heart_rate_minimum_threshold
        )

        self.heart_rate_maximum_resting_threshold = (
            heart_rate_maximum_resting_threshold
        )

        self.skin_temperature_minimum_threshold = (
            skin_temperature_minimum_threshold
        )

        self.skin_temperature_maximum_threshold = (
            skin_temperature_maximum_threshold
        )

        self.low_battery_threshold_percentage = (
            low_battery_threshold_percentage
        )

        self._evaluator = ThresholdEvaluator()

    def evaluate_snapshot(
        self,
        snapshot: SensorSnapshot,
    ) -> list[Alert]:
        """Evaluate all currently implemented alert rules."""

        alerts: list[Alert] = []

        now = snapshot.timestamp

        heart_rate = snapshot.measurements.get(
            "heartRateBpm"
        )

        low_heart_rate = (
            heart_rate is not None
            and float(heart_rate)
            < self.heart_rate_minimum_threshold
        )

        if self._evaluator.should_trigger(
            rule_key="heart-rate-low",
            condition=low_heart_rate,
            now=now,
        ):
            alerts.append(
                self._create_alert(
                    snapshot=snapshot,
                    alert_type=(
                        AlertType.HEART_RATE_BELOW_THRESHOLD
                    ),
                    severity=AlertSeverity.WARNING,
                    measured_value=heart_rate,
                    configured_threshold=(
                        self.heart_rate_minimum_threshold
                    ),
                    sensor_name="heart_rate",
                )
            )

        high_resting_heart_rate = (
            heart_rate is not None
            and snapshot.activity_level == "RESTING"
            and float(heart_rate)
            > self.heart_rate_maximum_resting_threshold
        )

        if self._evaluator.should_trigger(
            rule_key="heart-rate-high-resting",
            condition=high_resting_heart_rate,
            now=now,
        ):
            alerts.append(
                self._create_alert(
                    snapshot=snapshot,
                    alert_type=(
                        AlertType.HEART_RATE_ABOVE_RESTING_THRESHOLD
                    ),
                    severity=AlertSeverity.WARNING,
                    measured_value=heart_rate,
                    configured_threshold=(
                        self.heart_rate_maximum_resting_threshold
                    ),
                    sensor_name="heart_rate",
                )
            )

        temperature = snapshot.measurements.get(
            "skinTemperatureCelsius"
        )

        temperature_low = (
            temperature is not None
            and float(temperature)
            < self.skin_temperature_minimum_threshold
        )

        if self._evaluator.should_trigger(
            rule_key="temperature-low",
            condition=temperature_low,
            now=now,
        ):
            alerts.append(
                self._create_alert(
                    snapshot=snapshot,
                    alert_type=(
                        AlertType.TEMPERATURE_BELOW_THRESHOLD
                    ),
                    severity=AlertSeverity.WARNING,
                    measured_value=temperature,
                    configured_threshold=(
                        self.skin_temperature_minimum_threshold
                    ),
                    sensor_name="skin_temperature",
                )
            )

        temperature_high = (
            temperature is not None
            and float(temperature)
            > self.skin_temperature_maximum_threshold
        )

        if self._evaluator.should_trigger(
            rule_key="temperature-high",
            condition=temperature_high,
            now=now,
        ):
            alerts.append(
                self._create_alert(
                    snapshot=snapshot,
                    alert_type=(
                        AlertType.TEMPERATURE_ABOVE_THRESHOLD
                    ),
                    severity=AlertSeverity.WARNING,
                    measured_value=temperature,
                    configured_threshold=(
                        self.skin_temperature_maximum_threshold
                    ),
                    sensor_name="skin_temperature",
                )
            )

        battery = snapshot.measurements.get(
            "batteryPercentage"
        )

        battery_low = (
            battery is not None
            and float(battery)
            < self.low_battery_threshold_percentage
        )

        if self._evaluator.should_trigger(
            rule_key="battery-low",
            condition=battery_low,
            now=now,
        ):
            alerts.append(
                self._create_alert(
                    snapshot=snapshot,
                    alert_type=AlertType.LOW_BATTERY,
                    severity=AlertSeverity.WARNING,
                    measured_value=battery,
                    configured_threshold=(
                        self.low_battery_threshold_percentage
                    ),
                    sensor_name="battery",
                )
            )

        expected_measurements = {
            "heart_rate": "heartRateBpm",
            "skin_temperature": (
                "skinTemperatureCelsius"
            ),
            "step_counter": "stepsInInterval",
            "battery": "batteryPercentage",
        }

        for (
            sensor_name,
            status,
        ) in snapshot.sensor_status.items():

            is_failed = status == "FAILED"

            if self._evaluator.should_trigger(
                rule_key=f"sensor-failed:{sensor_name}",
                condition=is_failed,
                now=now,
                consecutive_required=1,
            ):
                alerts.append(
                    self._create_alert(
                        snapshot=snapshot,
                        alert_type=AlertType.SENSOR_FAILED,
                        severity=AlertSeverity.HIGH,
                        sensor_name=sensor_name,
                        message=(
                            f"Sensor '{sensor_name}' "
                            "is in FAILED state."
                        ),
                    )
                )

            expected_measurement = (
                expected_measurements.get(
                    sensor_name
                )
            )

            no_data = (
                status == "OK"
                and expected_measurement is not None
                and expected_measurement
                not in snapshot.measurements
            )

            if self._evaluator.should_trigger(
                rule_key=f"sensor-no-data:{sensor_name}",
                condition=no_data,
                now=now,
            ):
                alerts.append(
                    self._create_alert(
                        snapshot=snapshot,
                        alert_type=(
                            AlertType.SENSOR_NO_DATA
                        ),
                        severity=AlertSeverity.WARNING,
                        sensor_name=sensor_name,
                    )
                )

        return alerts

    def clear(self) -> None:
        """Clear current alert evaluation state."""

        self._evaluator.clear()

    def _create_alert(
        self,
        snapshot: SensorSnapshot,
        alert_type: AlertType,
        severity: AlertSeverity,
        measured_value: object = None,
        configured_threshold: object = None,
        sensor_name: str | None = None,
        message: str | None = None,
    ) -> Alert:
        """Create one HealthBand alert object."""

        return Alert(
            alert_id=f"alert-{uuid4()}",
            device_id=self.device_id,
            type=alert_type,
            severity=severity,
            measured_value=measured_value,
            configured_threshold=(
                configured_threshold
            ),
            sensor_name=sensor_name,
            activity_level=(
                snapshot.activity_level
            ),
            scenario=snapshot.scenario,
            message=message,
            timestamp=snapshot.timestamp,
        )