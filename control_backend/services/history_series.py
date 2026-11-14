"""Build one consistent, time-faithful history series for the web UI.

The History page needs two kinds of cloud data:

* raw telemetry for recent/live detail;
* local-analytics records for older seeded/aggregate history.

This module normalizes both sources into the same point schema so every period
(15m, 1h, 24h, 7d and 30d) can be rendered by the same chart code.  Recent raw
telemetry always takes precedence over overlapping analytics data, which keeps
short spikes (for example an OVEREXERTION 190 BPM peak) visible even when local
analytics is disabled in Device Shadow.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from statistics import fmean
from typing import Any
from zoneinfo import ZoneInfo


LOCAL_TIMEZONE = ZoneInfo("Europe/Sarajevo")

# Display density is deliberately bounded.  The browser gets enough points to
# show the shape of the signal, without trying to draw tens of thousands of
# samples on a ~1000-pixel-wide canvas.
PERIOD_BUCKET_SECONDS: dict[str, int | None] = {
    "15m": None,
    "1h": None,
    "24h": 5 * 60,
    "7d": 30 * 60,
    "30d": 2 * 60 * 60,
}

PERIOD_MAX_POINTS: dict[str, int] = {
    "15m": 2_000,
    "1h": 4_000,
    "24h": 1_500,
    "7d": 1_500,
    "30d": 1_500,
}


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _canonical_temperature(measurements: dict[str, Any]) -> float | None:
    canonical = _numeric(measurements.get("skinTemperatureCelsius"))
    if canonical is not None:
        return canonical

    displayed = _numeric(measurements.get("skinTemperature"))
    if displayed is None:
        return None

    unit = str(measurements.get("temperatureUnit", "CELSIUS")).upper()
    if unit == "FAHRENHEIT":
        return (displayed - 32.0) * 5.0 / 9.0

    return displayed


def _telemetry_point(item: dict[str, Any]) -> dict[str, Any] | None:
    timestamp = _parse_timestamp(item.get("timestamp"))
    measurements = item.get("measurements")

    if timestamp is None or not isinstance(measurements, dict):
        return None

    point: dict[str, Any] = {
        "timestamp": timestamp.isoformat(),
        "source": "TELEMETRY",
        "aggregated": False,
    }

    mappings = {
        "heartRateBpm": "heartRateBpm",
        "totalDailySteps": "totalDailySteps",
        "batteryPercentage": "batteryPercentage",
        "oxygenSaturationPercentage": "oxygenSaturationPercentage",
        "caloriesBurnedToday": "caloriesBurnedToday",
    }

    for source_key, target_key in mappings.items():
        value = _numeric(measurements.get(source_key))
        if value is not None:
            point[target_key] = value

    temperature = _canonical_temperature(measurements)
    if temperature is not None:
        point["skinTemperatureCelsius"] = temperature

    scenario = item.get("scenario")
    if isinstance(scenario, str):
        point["scenario"] = scenario

    return point


def telemetry_points(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    points = [
        point
        for item in items
        if (point := _telemetry_point(item)) is not None
    ]

    points.sort(key=lambda point: point["timestamp"])
    return points


def _analytics_points(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert analytics rows to the same chart-point schema.

    `totalDailySteps` is reconstructed from per-window step totals so seeded
    historical days can be displayed with the same daily-step semantics as raw
    telemetry.  Each local calendar day starts from zero.
    """

    ordered: list[tuple[datetime, dict[str, Any]]] = []

    for item in items:
        timestamp = _parse_timestamp(item.get("windowEnd"))
        if timestamp is not None:
            ordered.append((timestamp, item))

    ordered.sort(key=lambda pair: pair[0])

    daily_steps: dict[str, float] = defaultdict(float)
    points: list[dict[str, Any]] = []

    for timestamp, item in ordered:
        analytics = item.get("analytics")
        if not isinstance(analytics, dict):
            continue

        point: dict[str, Any] = {
            "timestamp": timestamp.isoformat(),
            "source": "ANALYTICS",
            "aggregated": True,
        }

        heart = analytics.get("heartRate")
        if isinstance(heart, dict):
            average = _numeric(heart.get("averageBpm"))
            if average is not None:
                point["heartRateBpm"] = average

        temperature = analytics.get("skinTemperature")
        if isinstance(temperature, dict):
            average = _numeric(temperature.get("averageCelsius"))
            if average is not None:
                point["skinTemperatureCelsius"] = average

        steps = analytics.get("steps")
        if isinstance(steps, dict):
            total = _numeric(steps.get("total"))
            if total is not None:
                local_day = timestamp.astimezone(LOCAL_TIMEZONE).date().isoformat()
                daily_steps[local_day] += max(0.0, total)
                point["totalDailySteps"] = daily_steps[local_day]

        battery = analytics.get("battery")
        if isinstance(battery, dict):
            value = _numeric(battery.get("endPercentage"))
            if value is None:
                value = _numeric(battery.get("averagePercentage"))
            if value is not None:
                point["batteryPercentage"] = value

        spo2 = analytics.get("spo2")
        if isinstance(spo2, dict):
            average = _numeric(spo2.get("averagePercentage"))
            if average is None:
                average = _numeric(spo2.get("average"))
            minimum = _numeric(spo2.get("minimumPercentage"))
            if average is not None:
                point["oxygenSaturationPercentage"] = average
            if minimum is not None:
                point["oxygenSaturationMinimumPercentage"] = minimum

        calories = analytics.get("calories")
        if isinstance(calories, dict):
            daily = _numeric(calories.get("dailyTotalKcal"))
            if daily is not None:
                point["caloriesBurnedToday"] = daily

        activity = analytics.get("activity")
        if isinstance(activity, dict):
            scenario = activity.get("dominantScenario")
            if isinstance(scenario, str):
                point["scenario"] = scenario

        if "scenario" not in point:
            scenario = item.get("historicalScenario")
            if isinstance(scenario, str):
                point["scenario"] = scenario

        points.append(point)

    return points


def _raw_point_timestamp(point: dict[str, Any]) -> datetime | None:
    return _parse_timestamp(point.get("timestamp"))


def _representative_bucket_points(
    bucket: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Select real telemetry samples while preserving the visible signal shape.

    Long periods can contain tens of thousands of measurements. The old UI is
    intentionally kept: one teal line and ordinary points only. We therefore
    reduce density by selecting real samples (first, last, HR minimum and HR
    maximum) from each time bucket rather than creating an averaged/peak
    overlay.
    """

    ordered = sorted(
        bucket,
        key=lambda point: point.get("timestamp", ""),
    )

    if len(ordered) <= 4:
        return ordered

    selected: list[dict[str, Any]] = [ordered[0], ordered[-1]]
    heart_points = [
        point
        for point in ordered
        if _numeric(point.get("heartRateBpm")) is not None
    ]

    if heart_points:
        selected.append(
            min(heart_points, key=lambda point: float(point["heartRateBpm"]))
        )
        selected.append(
            max(heart_points, key=lambda point: float(point["heartRateBpm"]))
        )

    unique: dict[str, dict[str, Any]] = {}
    for point in selected:
        timestamp = point.get("timestamp")
        if isinstance(timestamp, str):
            unique[timestamp] = point

    return sorted(unique.values(), key=lambda point: point["timestamp"])


def _bucket_raw_points(
    points: list[dict[str, Any]],
    start: datetime,
    bucket_seconds: int,
) -> list[dict[str, Any]]:
    """Reduce raw telemetry while keeping only real measured samples."""

    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for point in points:
        timestamp = _raw_point_timestamp(point)
        if timestamp is None:
            continue
        index = int((timestamp - start).total_seconds() // bucket_seconds)
        buckets[index].append(point)

    result: list[dict[str, Any]] = []
    for index in sorted(buckets):
        result.extend(_representative_bucket_points(buckets[index]))

    result.sort(key=lambda point: point["timestamp"])
    return result


def _thin_raw_points(
    points: list[dict[str, Any]],
    max_points: int,
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    """Bound chart density without inventing measurements."""

    if len(points) <= max_points:
        return points

    duration = max(1.0, (end - start).total_seconds())
    bucket_seconds = max(1, int(duration / max(1, max_points // 4)))
    reduced = _bucket_raw_points(points, start, bucket_seconds)

    if len(reduced) <= max_points:
        return reduced

    if max_points <= 2:
        return reduced[:max_points]

    step = (len(reduced) - 1) / (max_points - 1)
    indexes = {round(index * step) for index in range(max_points)}
    return [reduced[index] for index in sorted(indexes)]


def build_history_series(
    *,
    telemetry_items: list[dict[str, Any]],
    analytics_items: list[dict[str, Any]],
    start_iso: str,
    end_iso: str,
    period: str,
) -> list[dict[str, Any]]:
    """Return one chronological chart series for any supported period."""

    start = _parse_timestamp(start_iso)
    end = _parse_timestamp(end_iso)
    if start is None or end is None or start >= end:
        return []

    raw = telemetry_points(telemetry_items)
    bucket_seconds = PERIOD_BUCKET_SECONDS.get(period)
    max_points = PERIOD_MAX_POINTS.get(period, 900)

    if bucket_seconds is None:
        displayed_raw = _thin_raw_points(raw, max_points, start, end)
    else:
        displayed_raw = _bucket_raw_points(raw, start, bucket_seconds)
        displayed_raw = _thin_raw_points(displayed_raw, max_points, start, end)

    aggregate = _analytics_points(analytics_items)

    # Raw telemetry is the more detailed source. Suppress an analytics row only
    # when it falls in a display bucket that already contains raw telemetry.
    # Analytics in genuine raw-data gaps is retained instead of disappearing.
    if displayed_raw and bucket_seconds is not None:
        raw_bucket_indexes: set[int] = set()
        for point in displayed_raw:
            timestamp = _parse_timestamp(point.get("timestamp"))
            if timestamp is None:
                continue
            raw_bucket_indexes.add(
                int((timestamp - start).total_seconds() // bucket_seconds)
            )

        aggregate = [
            point
            for point in aggregate
            if (
                (timestamp := _parse_timestamp(point.get("timestamp"))) is None
                or int((timestamp - start).total_seconds() // bucket_seconds)
                not in raw_bucket_indexes
            )
        ]

    combined = aggregate + displayed_raw
    combined.sort(key=lambda point: point["timestamp"])
    return combined
