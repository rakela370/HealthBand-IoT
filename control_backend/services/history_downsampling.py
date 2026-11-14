"""Helpers for producing bounded, time-faithful analytics history responses."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _weighted_average(entries: list[tuple[float, float]]) -> float | None:
    total_weight = sum(weight for _, weight in entries if weight > 0)
    if total_weight <= 0:
        return None
    return sum(value * weight for value, weight in entries if weight > 0) / total_weight


def _merge_metric(
    bucket: list[dict[str, Any]],
    metric_name: str,
    average_key: str,
    minimum_key: str,
    maximum_key: str,
    sample_key: str,
    extra_sum_keys: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    weighted: list[tuple[float, float]] = []
    minima: list[float] = []
    maxima: list[float] = []
    samples = 0.0
    extra_totals = {key: 0.0 for key in extra_sum_keys}
    saw_extra = {key: False for key in extra_sum_keys}

    for item in bucket:
        metric = item.get("analytics", {}).get(metric_name)
        if not isinstance(metric, dict):
            continue

        average = _numeric(metric.get(average_key))
        sample_count = _numeric(metric.get(sample_key)) or 1.0
        minimum = _numeric(metric.get(minimum_key))
        maximum = _numeric(metric.get(maximum_key))

        if average is not None:
            weighted.append((average, sample_count))
        if minimum is not None:
            minima.append(minimum)
        if maximum is not None:
            maxima.append(maximum)

        samples += max(0.0, sample_count)

        for key in extra_sum_keys:
            value = _numeric(metric.get(key))
            if value is not None:
                extra_totals[key] += value
                saw_extra[key] = True

    average = _weighted_average(weighted)
    if average is None and not minima and not maxima:
        return None

    result: dict[str, Any] = {}
    if average is not None:
        result[average_key] = round(average, 2)
    if minima:
        result[minimum_key] = round(min(minima), 2)
    if maxima:
        result[maximum_key] = round(max(maxima), 2)
    result[sample_key] = int(round(samples))

    for key in extra_sum_keys:
        if saw_extra[key]:
            result[key] = int(round(extra_totals[key]))

    return result


def _merge_bucket(bucket: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple analytics records into one display record.

    The merge preserves extrema (especially heart-rate peaks), sums counters,
    and keeps the real first/last timestamps so the frontend can place the
    point correctly on a time axis.
    """

    first = bucket[0]
    last = bucket[-1]
    merged = deepcopy(last)
    merged["windowStart"] = first.get("windowStart", first.get("windowEnd"))
    merged["windowEnd"] = last.get("windowEnd")

    analytics: dict[str, Any] = {}

    heart = _merge_metric(
        bucket,
        "heartRate",
        "averageBpm",
        "minimumBpm",
        "maximumBpm",
        "validSamples",
        ("rejectedSamples", "thresholdExceedances"),
    )
    if heart is not None:
        analytics["heartRate"] = heart

    temperature = _merge_metric(
        bucket,
        "skinTemperature",
        "averageCelsius",
        "minimumCelsius",
        "maximumCelsius",
        "validSamples",
    )
    if temperature is not None:
        analytics["skinTemperature"] = temperature

    spo2 = _merge_metric(
        bucket,
        "spo2",
        "averagePercentage",
        "minimumPercentage",
        "maximumPercentage",
        "validSamples",
        ("belowThresholdSamples",),
    )
    if spo2 is not None:
        analytics["spo2"] = spo2

    step_totals: list[float] = []
    step_averages: list[float] = []
    for item in bucket:
        steps = item.get("analytics", {}).get("steps")
        if not isinstance(steps, dict):
            continue
        total = _numeric(steps.get("total"))
        average = _numeric(steps.get("averagePerInterval"))
        if total is not None:
            step_totals.append(total)
        if average is not None:
            step_averages.append(average)
    if step_totals or step_averages:
        analytics["steps"] = {
            "total": int(round(sum(step_totals))),
            "averagePerInterval": round(
                sum(step_averages) / len(step_averages), 2
            ) if step_averages else 0.0,
        }

    battery_records: list[dict[str, Any]] = []
    for item in bucket:
        battery = item.get("analytics", {}).get("battery")
        if isinstance(battery, dict):
            battery_records.append(battery)
    if battery_records:
        start = _numeric(battery_records[0].get("startPercentage"))
        end = _numeric(battery_records[-1].get("endPercentage"))
        values: list[float] = []
        for battery in battery_records:
            for key in ("startPercentage", "endPercentage"):
                value = _numeric(battery.get(key))
                if value is not None:
                    values.append(value)
        battery_result: dict[str, Any] = {}
        if start is not None:
            battery_result["startPercentage"] = round(start, 2)
        if end is not None:
            battery_result["endPercentage"] = round(end, 2)
        if values:
            battery_result["averagePercentage"] = round(
                sum(values) / len(values), 2
            )
        if start is not None and end is not None:
            battery_result["consumptionPercentage"] = round(
                max(0.0, start - end), 2
            )
        analytics["battery"] = battery_result

    calorie_totals: list[float] = []
    calorie_daily: list[float] = []
    for item in bucket:
        calories = item.get("analytics", {}).get("calories")
        if not isinstance(calories, dict):
            continue
        total = _numeric(calories.get("totalKcal"))
        daily = _numeric(calories.get("dailyTotalKcal"))
        if total is not None:
            calorie_totals.append(total)
        if daily is not None:
            calorie_daily.append(daily)
    if calorie_totals or calorie_daily:
        analytics["calories"] = {
            "estimated": True,
            "totalKcal": round(sum(calorie_totals), 2),
            "dailyTotalKcal": round(max(calorie_daily), 2)
            if calorie_daily else None,
        }

    alert_values: list[float] = []
    quality_values: list[float] = []
    for item in bucket:
        item_analytics = item.get("analytics", {})
        alert_count = _numeric(item_analytics.get("alertsGenerated"))
        quality = _numeric(item_analytics.get("dataQualityPercentage"))
        if alert_count is not None:
            alert_values.append(alert_count)
        if quality is not None:
            quality_values.append(quality)

    analytics["alertsGenerated"] = int(round(sum(alert_values)))
    if quality_values:
        analytics["dataQualityPercentage"] = round(
            sum(quality_values) / len(quality_values), 2
        )

    # Preserve the most recent activity/scenario summary if present.
    last_analytics = last.get("analytics", {})
    for key in ("activity", "scenario"):
        if key in last_analytics:
            analytics[key] = deepcopy(last_analytics[key])

    merged["analytics"] = analytics
    merged["historyDisplayAggregate"] = len(bucket) > 1
    merged["historyDisplaySourceRecords"] = len(bucket)
    return merged


def downsample_analytics_history(
    items: list[dict[str, Any]],
    start_iso: str,
    end_iso: str,
    max_points: int = 1200,
) -> list[dict[str, Any]]:
    """Bound analytics data while preserving the full selected time range.

    Items are grouped into evenly-sized time buckets. Each bucket is merged
    rather than simply sampled, so maximum/minimum heart-rate values are not
    lost when a long history range is reduced for browser rendering.
    """

    if max_points <= 0:
        raise ValueError("max_points must be greater than zero")

    ordered = sorted(
        (
            item for item in items
            if _parse_timestamp(item.get("windowEnd")) is not None
        ),
        key=lambda item: _parse_timestamp(item.get("windowEnd")),
    )

    if len(ordered) <= max_points:
        return ordered

    start = _parse_timestamp(start_iso)
    end = _parse_timestamp(end_iso)
    if start is None or end is None or start >= end:
        return ordered[:max_points]

    duration = (end - start).total_seconds()
    buckets: list[list[dict[str, Any]]] = [
        [] for _ in range(max_points)
    ]

    for item in ordered:
        timestamp = _parse_timestamp(item.get("windowEnd"))
        if timestamp is None:
            continue
        ratio = (timestamp - start).total_seconds() / duration
        index = int(ratio * max_points)
        index = max(0, min(max_points - 1, index))
        buckets[index].append(item)

    return [
        _merge_bucket(bucket)
        for bucket in buckets
        if bucket
    ]
