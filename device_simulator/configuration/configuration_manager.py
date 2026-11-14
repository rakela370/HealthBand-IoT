"""Persistent HealthBand configuration management."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from device_simulator.configuration.configuration_validator import (
    ConfigurationValidationError,
    ConfigurationValidator,
)
from device_simulator.configuration.device_config import (
    DeviceConfig,
)
from device_simulator.utils.versioning import (
    is_at_least,
)


@dataclass(frozen=True, slots=True)
class ConfigurationApplyResult:
    """Result of one attempted configuration update."""

    applied: bool
    config: DeviceConfig
    errors: tuple[str, ...]


class ConfigurationManager:
    """Load, validate, apply and persist HealthBand configuration."""

    def __init__(
        self,
        default_config_path: Path | None = None,
        runtime_config_path: Path | None = None,
        software_version: str = "1.0.0",
    ) -> None:
        self.software_version = (
            software_version
        )

        self._supports_spo2 = is_at_least(
            software_version,
            "2.0.0",
        )

        self._validator = (
            ConfigurationValidator(
                software_version=(
                    software_version
                )
            )
        )

        if default_config_path is not None:
            self._default_config_path = (
                default_config_path
            )

        else:
            default_name = (
                "default_config_v2.json"
                if self._supports_spo2
                else "default_config.json"
            )

            self._default_config_path = (
                Path(
                    __file__
                ).with_name(
                    default_name
                )
            )

        self._runtime_config_path = (
            runtime_config_path
            or (
                Path.cwd()
                / "runtime"
                / "device_config.json"
            )
        )

        self._current = (
            self._load_initial_configuration()
        )

    @property
    def current(
        self,
    ) -> DeviceConfig:
        """Return current applied configuration."""

        return self._current

    def apply_delta(
        self,
        delta: dict[str, Any],
    ) -> ConfigurationApplyResult:
        """Validate and persist a partial desired-state update."""

        try:
            new_config = (
                self._validator.apply_delta(
                    current=self._current,
                    delta=delta,
                )
            )

        except ConfigurationValidationError as exc:
            return ConfigurationApplyResult(
                applied=False,
                config=self._current,
                errors=exc.errors,
            )

        self._current = (
            new_config
        )

        self._persist()

        return ConfigurationApplyResult(
            applied=True,
            config=self._current,
            errors=(),
        )

    def _base_config(self) -> DeviceConfig:
        """Return version-appropriate defaults used while merging stored state."""

        if not self._supports_spo2:
            return DeviceConfig()

        return DeviceConfig(
            spo2_alerts_enabled=True,
            spo2_minimum_threshold=92.0,
            spo2_measurement_enabled=True,
        )

    def _load_initial_configuration(
        self,
    ) -> DeviceConfig:
        """Load runtime config if available, otherwise version defaults."""

        source = (
            self._runtime_config_path
            if self._runtime_config_path.is_file()
            else self._default_config_path
        )

        if not source.is_file():
            raise FileNotFoundError(
                f"Configuration file does not exist: {source}"
            )

        with source.open(
            "r",
            encoding="utf-8",
        ) as file:
            raw = json.load(
                file
            )

        # The runtime file is shared across installed releases. After an
        # upgrade to v2 it legitimately contains SpO2-only fields. If the
        # device later starts or rolls back to v1, those newer persisted
        # fields must not make the older release unbootable. This filtering
        # applies only while loading stored state; apply_delta() still uses
        # the strict validator and therefore rejects v2-only remote
        # configuration sent to a v1 device.
        if not self._supports_spo2:
            raw = dict(raw)
            for field in (
                "spo2AlertsEnabled",
                "spo2MinimumThreshold",
                "spo2MeasurementEnabled",
            ):
                raw.pop(field, None)

        try:
            return (
                self._validator.apply_delta(
                    current=(
                        self._base_config()
                    ),
                    delta=raw,
                )
            )

        except ConfigurationValidationError as exc:
            raise RuntimeError(
                "Stored HealthBand configuration "
                f"is invalid: {'; '.join(exc.errors)}"
            ) from exc

    def _persist(self) -> None:
        """Persist applied configuration to local runtime storage."""

        self._runtime_config_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = (
            self._runtime_config_path.with_suffix(
                ".tmp"
            )
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self._current.to_shadow_dict(),
                file,
                ensure_ascii=False,
                indent=2,
            )

        temporary_path.replace(
            self._runtime_config_path
        )