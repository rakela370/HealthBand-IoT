"""OTA status models shared by the HealthBand update architecture."""

from dataclasses import dataclass
from enum import StrEnum


class OtaPhase(StrEnum):
    """High-level phases of one OTA transaction."""

    IDLE = "IDLE"

    DOWNLOADING = "DOWNLOADING"

    VERIFYING = "VERIFYING"

    VALIDATING = "VALIDATING"

    BACKING_UP = "BACKING_UP"

    EXTRACTING = "EXTRACTING"

    PRE_INSTALL_CHECK = "PRE_INSTALL_CHECK"

    INSTALLING = "INSTALLING"

    ACTIVATING = "ACTIVATING"

    SELF_TEST = "SELF_TEST"

    COMPLETED = "COMPLETED"

    ROLLING_BACK = "ROLLING_BACK"

    FAILED = "FAILED"


@dataclass(
    frozen=True,
    slots=True,
)
class OtaProgress:
    """One observable OTA progress update."""

    phase: OtaPhase

    progress_percentage: int

    message: str