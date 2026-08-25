"""Pydantic models for Device Shadow configuration updates."""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class ThresholdUpdate(BaseModel):
    """Partial threshold configuration."""

    model_config = ConfigDict(
        extra="forbid"
    )

    heartRateMinimumBpm: float | None = Field(
        default=None,
        ge=20.0,
        le=250.0,
    )

    heartRateMaximumRestingBpm: float | None = Field(
        default=None,
        ge=20.0,
        le=250.0,
    )

    skinTemperatureMinimumC: float | None = Field(
        default=None,
        ge=20.0,
        le=45.0,
    )

    skinTemperatureMaximumC: float | None = Field(
        default=None,
        ge=20.0,
        le=45.0,
    )

    lowBatteryPercentage: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )

    @model_validator(
        mode="after"
    )
    def validate_orders(
        self,
    ) -> "ThresholdUpdate":
        if (
            self.heartRateMinimumBpm is not None
            and self.heartRateMaximumRestingBpm is not None
            and self.heartRateMinimumBpm
            >= self.heartRateMaximumRestingBpm
        ):
            raise ValueError(
                "heartRateMinimumBpm must be lower "
                "than heartRateMaximumRestingBpm."
            )

        if (
            self.skinTemperatureMinimumC is not None
            and self.skinTemperatureMaximumC is not None
            and self.skinTemperatureMinimumC
            >= self.skinTemperatureMaximumC
        ):
            raise ValueError(
                "skinTemperatureMinimumC must be lower "
                "than skinTemperatureMaximumC."
            )

        return self


class AlertConfigurationUpdate(BaseModel):
    """Partial alert switch configuration."""

    model_config = ConfigDict(
        extra="forbid"
    )

    enabled: bool | None = None
    heartRate: bool | None = None
    temperature: bool | None = None
    battery: bool | None = None
    sensorFailure: bool | None = None


class ConfigurationUpdateRequest(BaseModel):
    """Partial HealthBand desired configuration."""

    model_config = ConfigDict(
        extra="forbid"
    )

    measurementIntervalSec: float | None = Field(
        default=None,
        ge=0.5,
    )

    telemetryIntervalSec: float | None = Field(
        default=None,
        ge=1.0,
    )

    analyticsWindowSec: float | None = Field(
        default=None,
        ge=1.0,
    )

    healthReportIntervalSec: float | None = Field(
        default=None,
        ge=1.0,
    )

    temperatureUnit: (
        Literal[
            "CELSIUS",
            "FAHRENHEIT",
        ]
        | None
    ) = None

    thresholds: ThresholdUpdate | None = None

    alerts: AlertConfigurationUpdate | None = None

    offlineQueueMaximumItems: int | None = Field(
        default=None,
        gt=0,
    )

    activeUserProfile: str | None = Field(
        default=None,
        min_length=1,
    )

    analyticsEnabled: bool | None = None

    @model_validator(
        mode="after"
    )
    def require_change(
        self,
    ) -> "ConfigurationUpdateRequest":
        if not self.model_dump(
            exclude_none=True
        ):
            raise ValueError(
                "At least one configuration field "
                "must be supplied."
            )

        return self