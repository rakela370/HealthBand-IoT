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
    ) -> None:
        self._validator = (
            ConfigurationValidator()
        )

        self._default_config_path = (
            default_config_path
            or Path(
                __file__
            ).with_name(
                "default_config.json"
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

    def _load_initial_configuration(
        self,
    ) -> DeviceConfig:
        """Load runtime config if available, otherwise defaults."""

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

        try:
            return (
                self._validator.apply_delta(
                    current=DeviceConfig(),
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