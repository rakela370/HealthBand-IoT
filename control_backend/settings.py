"""Configuration for the HealthBand FastAPI backend."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class BackendSettings(BaseSettings):
    """Environment-backed configuration for the control backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = (
        "HealthBand Control Backend"
    )

    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )

    backend_host: str = Field(
        default="127.0.0.1",
        alias="BACKEND_HOST",
    )

    backend_port: int = Field(
        default=8000,
        alias="BACKEND_PORT",
    )

    backend_mqtt_enabled: bool = Field(
        default=True,
        alias="BACKEND_MQTT_ENABLED",
    )

    aws_region: str = Field(
        default="eu-central-1",
        alias="AWS_REGION",
    )

    aws_profile: str | None = Field(
        default=None,
        alias="AWS_PROFILE",
    )

    aws_iot_endpoint: str = Field(
        alias="AWS_IOT_ENDPOINT",
    )

    device_id: str = Field(
        default="healthband-device-001",
        alias="HEALTHBAND_DEVICE_ID",
    )

    backend_mqtt_client_id: str = Field(
        default="healthband-control-backend",
        alias="BACKEND_MQTT_CLIENT_ID",
    )

    backend_iot_cert_path: str = Field(
        default=(
            "certificates/"
            "healthband-control-backend/"
            "backend.pem.crt"
        ),
        alias="BACKEND_IOT_CERT_PATH",
    )

    backend_iot_private_key_path: str = Field(
        default=(
            "certificates/"
            "healthband-control-backend/"
            "backend.private.key"
        ),
        alias="BACKEND_IOT_PRIVATE_KEY_PATH",
    )

    backend_root_ca_path: str = Field(
        default=(
            "certificates/"
            "healthband-control-backend/"
            "AmazonRootCA1.pem"
        ),
        alias="BACKEND_ROOT_CA_PATH",
    )

    telemetry_table: str = Field(
        default="HealthBandTelemetry",
        alias="DYNAMODB_TELEMETRY_TABLE",
    )

    analytics_table: str = Field(
        default="HealthBandAnalytics",
        alias="DYNAMODB_ANALYTICS_TABLE",
    )

    events_table: str = Field(
        default="HealthBandEvents",
        alias="DYNAMODB_EVENTS_TABLE",
    )

    cors_origins: str = Field(
        default=(
            "http://127.0.0.1:8000,"
            "http://localhost:8000,"
            "http://127.0.0.1:5500,"
            "http://localhost:5500"
        ),
        alias="BACKEND_CORS_ORIGINS",
    )

    @property
    def profile_name(
        self,
    ) -> str | None:
        """Return normalized optional boto3 profile name."""

        if self.aws_profile is None:
            return None

        value = (
            self.aws_profile.strip()
        )

        return (
            value
            or None
        )

    @property
    def cors_origin_list(
        self,
    ) -> list[str]:
        """Parse comma-separated CORS origins."""

        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    def resolve_path(
        self,
        value: str,
    ) -> Path:
        """Resolve one project-relative filesystem path."""

        path = Path(
            value
        ).expanduser()

        if not path.is_absolute():
            path = (
                Path.cwd()
                / path
            )

        return (
            path.resolve()
        )