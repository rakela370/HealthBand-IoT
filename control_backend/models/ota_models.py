"""Pydantic models used by HealthBand OTA API endpoints."""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class OtaStartRequest(BaseModel):
    """Request for starting one HealthBand OTA update."""

    model_config = ConfigDict(
        extra="forbid",
    )

    targetVersion: str = Field(
        min_length=1,
        max_length=64,
        description=(
            "Target HealthBand software version."
        ),
    )

    force: bool = False

    @property
    def target_version(
        self,
    ) -> str:
        """Python-style alias used by backend code."""

        return self.targetVersion