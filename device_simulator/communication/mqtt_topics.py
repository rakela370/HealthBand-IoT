"""MQTT topic definitions for one HealthBand device."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MqttTopics:
    """Build all custom MQTT topics for one HealthBand device."""

    device_id: str

    def __post_init__(self) -> None:
        if not self.device_id.strip():
            raise ValueError(
                "device_id cannot be empty."
            )

    @property
    def base(self) -> str:
        """Return the base topic for this device."""

        return f"healthband/{self.device_id}"

    @property
    def telemetry(self) -> str:
        return f"{self.base}/telemetry"

    @property
    def analytics(self) -> str:
        return f"{self.base}/analytics"

    @property
    def alerts(self) -> str:
        return f"{self.base}/alerts"

    @property
    def health(self) -> str:
        return f"{self.base}/health"

    @property
    def events(self) -> str:
        return f"{self.base}/events"

    @property
    def commands_request(self) -> str:
        return f"{self.base}/commands/request"

    @property
    def commands_response(self) -> str:
        return f"{self.base}/commands/response"

    @property
    def presence(self) -> str:
        return f"{self.base}/presence"