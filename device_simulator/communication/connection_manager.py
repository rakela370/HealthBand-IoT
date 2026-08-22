"""AWS IoT Core MQTT/TLS connection management."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from awscrt import mqtt
from awsiot import mqtt_connection_builder
from dotenv import load_dotenv


logger = logging.getLogger(__name__)


class AwsIotConfigurationError(ValueError):
    """Raised when required AWS IoT connection settings are invalid."""


@dataclass(frozen=True, slots=True)
class AwsIotConnectionSettings:
    """Configuration required for AWS IoT Core mTLS connection."""

    region: str
    endpoint: str
    client_id: str

    certificate_path: str
    private_key_path: str
    root_ca_path: str

    port: int = 8883

    @classmethod
    def from_environment(
        cls,
    ) -> "AwsIotConnectionSettings":
        """Load and validate AWS IoT settings from the project .env."""

        load_dotenv(
            dotenv_path=(
                Path.cwd() / ".env"
            ),
            override=False,
        )

        variable_names = (
            "AWS_REGION",
            "AWS_IOT_ENDPOINT",
            "HEALTHBAND_DEVICE_ID",
            "AWS_IOT_CERT_PATH",
            "AWS_IOT_PRIVATE_KEY_PATH",
            "AWS_ROOT_CA_PATH",
        )

        values = {
            name: os.getenv(
                name,
                "",
            ).strip()
            for name in variable_names
        }

        missing = [
            name
            for name, value
            in values.items()
            if not value
        ]

        if missing:
            raise AwsIotConfigurationError(
                "Missing required environment variables: "
                + ", ".join(missing)
            )

        endpoint = values[
            "AWS_IOT_ENDPOINT"
        ]

        if endpoint.startswith(
            (
                "http://",
                "https://",
                "mqtt://",
                "mqtts://",
            )
        ):
            raise AwsIotConfigurationError(
                "AWS_IOT_ENDPOINT must contain only "
                "the AWS IoT hostname, without a URL scheme."
            )

        certificate_path = (
            cls._resolve_required_file(
                values["AWS_IOT_CERT_PATH"],
                "AWS_IOT_CERT_PATH",
            )
        )

        private_key_path = (
            cls._resolve_required_file(
                values[
                    "AWS_IOT_PRIVATE_KEY_PATH"
                ],
                "AWS_IOT_PRIVATE_KEY_PATH",
            )
        )

        root_ca_path = (
            cls._resolve_required_file(
                values["AWS_ROOT_CA_PATH"],
                "AWS_ROOT_CA_PATH",
            )
        )

        return cls(
            region=values["AWS_REGION"],
            endpoint=endpoint,
            client_id=values[
                "HEALTHBAND_DEVICE_ID"
            ],
            certificate_path=(
                certificate_path
            ),
            private_key_path=(
                private_key_path
            ),
            root_ca_path=root_ca_path,
        )

    @staticmethod
    def _resolve_required_file(
        value: str,
        variable_name: str,
    ) -> str:
        """Resolve and verify a certificate/key path."""

        path = Path(
            value
        ).expanduser()

        if not path.is_absolute():
            path = (
                Path.cwd()
                / path
            )

        path = path.resolve()

        if not path.is_file():
            raise AwsIotConfigurationError(
                f"{variable_name} points to a file "
                f"that does not exist: {path}"
            )

        return str(path)


class ConnectionManager:
    """
    Own the low-level AWS IoT Core MQTT connection.

    Full offline queue and application-level reconnect behavior
    will be implemented in the offline module.
    """

    def __init__(
        self,
        settings: AwsIotConnectionSettings,
    ) -> None:
        self.settings = settings

        self._connection: Any = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Return current MQTT connection state."""

        return self._connected

    @property
    def mqtt_connection(
        self,
    ) -> Any:
        """Return the underlying AWS CRT MQTT connection."""

        if self._connection is None:
            self._connection = (
                self._build_connection()
            )

        return self._connection

    def connect(self) -> None:
        """Connect to AWS IoT Core over MQTT/TLS."""

        if self._connected:
            return

        logger.info(
            "Connecting to AWS IoT Core | "
            "endpoint=%s | clientId=%s | port=%s",
            self.settings.endpoint,
            self.settings.client_id,
            self.settings.port,
        )

        connection_future = (
            self.mqtt_connection.connect()
        )

        connection_future.result(
            timeout=15
        )

        self._connected = True

        logger.info(
            "AWS IoT Core MQTT connection established."
        )

    def disconnect(self) -> None:
        """Gracefully disconnect from AWS IoT Core."""

        if (
            self._connection is None
            or not self._connected
        ):
            return

        logger.info(
            "Disconnecting from AWS IoT Core."
        )

        disconnect_future = (
            self._connection.disconnect()
        )

        disconnect_future.result(
            timeout=10
        )

        self._connected = False

        logger.info(
            "AWS IoT Core MQTT connection closed."
        )

    def _build_connection(
        self,
    ) -> Any:
        """Build an mTLS AWS IoT Device SDK connection."""

        return mqtt_connection_builder.mtls_from_path(
            endpoint=(
                self.settings.endpoint
            ),
            port=self.settings.port,
            cert_filepath=(
                self.settings.certificate_path
            ),
            pri_key_filepath=(
                self.settings.private_key_path
            ),
            ca_filepath=(
                self.settings.root_ca_path
            ),
            client_id=(
                self.settings.client_id
            ),
            clean_session=False,
            keep_alive_secs=30,
            reconnect_min_timeout_secs=1,
            reconnect_max_timeout_secs=32,
            on_connection_interrupted=(
                self._on_connection_interrupted
            ),
            on_connection_resumed=(
                self._on_connection_resumed
            ),
        )

    def _on_connection_interrupted(
        self,
        connection: Any,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Handle an unexpected connection loss."""

        del connection
        del kwargs

        self._connected = False

        logger.warning(
            "AWS IoT MQTT connection interrupted: %s",
            error,
        )

    def _on_connection_resumed(
        self,
        connection: Any,
        return_code: mqtt.ConnectReturnCode,
        session_present: bool,
        **kwargs: Any,
    ) -> None:
        """Handle automatic SDK reconnection."""

        del kwargs

        self._connected = (
            return_code
            == mqtt.ConnectReturnCode.ACCEPTED
        )

        logger.info(
            "AWS IoT MQTT connection resumed | "
            "accepted=%s | sessionPresent=%s",
            self._connected,
            session_present,
        )

        if (
            self._connected
            and not session_present
        ):
            future, _ = (
                connection.resubscribe_existing_topics()
            )

            future.add_done_callback(
                self._on_resubscribe_complete
            )

    @staticmethod
    def _on_resubscribe_complete(
        future: Any,
    ) -> None:
        """Log completion of automatic resubscription."""

        try:
            future.result()

            logger.info(
                "MQTT subscriptions restored "
                "after reconnect."
            )

        except Exception:
            logger.exception(
                "Failed to restore MQTT "
                "subscriptions after reconnect."
            )