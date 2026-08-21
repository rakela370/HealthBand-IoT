"""Reusable rolling statistics helpers for HealthBand analytics."""

from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True, slots=True)
class StatisticsResult:
    """Basic statistics calculated over numeric values."""

    average: float
    minimum: float
    maximum: float
    count: int


def calculate_statistics(
    values: list[float],
) -> StatisticsResult | None:
    """Calculate average, minimum and maximum values."""

    if not values:
        return None

    return StatisticsResult(
        average=fmean(values),
        minimum=min(values),
        maximum=max(values),
        count=len(values),
    )