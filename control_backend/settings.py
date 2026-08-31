"""Configuration for the HealthBand FastAPI backend."""

from pathlib import Path

from pydantic import (
    AliasChoices,
    Field,
)
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

    ota_s3_bucket: str = Field(
        default="",
        alias="OTA_S3_BUCKET",
    )

    ota_s3_prefix: str = Field(
        default="releases",
        alias="OTA_S3_PREFIX",
    )

    ota_jobs_role_arn: str = Field(
        default="",
        validation_alias=AliasChoices(
            "OTA_IOT_JOBS_ROLE_ARN",
            "OTA_JOBS_ROLE_ARN",
        ),
    )

    ota_artifacts_root: str = Field(
        default="ota_artifacts",
        alias="OTA_ARTIFACTS_ROOT",
    )

    ota_resource_state_path: str = Field(
        default=(
            "runtime/"
            "ota_aws_resources.json"
        ),
        alias="OTA_RESOURCE_STATE_PATH",
    )

    ota_presigned_url_expiry_sec: int = Field(
        default=900,
        ge=60,
        le=3600,
        validation_alias=AliasChoices(
            "OTA_PRESIGNED_URL_EXPIRES_SEC",
            "OTA_PRESIGNED_URL_EXPIRY_SEC",
        ),
    )

    ota_update_timeout_sec: int = Field(
        default=300,
        ge=60,
        le=3600,
        alias="OTA_UPDATE_TIMEOUT_SEC",
    )

    cors_origins: str = Field(
        default=(
            "http://127.0.0.1:8000,"
            "http://localhost:8000"
        ),
        alias="BACKEND_CORS_ORIGINS",
    )

    @property
    def profile_name(
        self,
    ) -> str | None:
        """Return normalized optional boto3 profile."""

        if (
            self.aws_profile
            is None
        ):
            return None

        value = (
            self.aws_profile
            .strip()
        )

        return (
            value
            or None
        )

    @property
    def normalized_ota_s3_prefix(
        self,
    ) -> str:
        """Return OTA S3 prefix without leading or trailing slashes."""

        return (
            self.ota_s3_prefix
            .strip()
            .strip("/")
        )

    @property
    def cors_origin_list(
        self,
    ) -> list[str]:
        """Parse comma-separated CORS origins."""

        return [
            origin.strip()
            for origin
            in self.cors_origins
            .split(
                ","
            )
            if origin.strip()
        ]

    def resolve_path(
        self,
        value: str,
    ) -> Path:
        """Resolve project-relative path."""

        path = (
            Path(
                value
            ).expanduser()
        )

        if not path.is_absolute():
            path = (
                Path.cwd()
                / path
            )

        return (
            path.resolve()
        )