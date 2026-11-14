"""Regression tests for History query limits and period routing."""

import inspect

from control_backend.api.history_routes import (
    get_alerts,
    get_analytics,
    get_telemetry,
)


def _query_default(function, parameter: str) -> int:
    value = inspect.signature(function).parameters[parameter].default
    return int(value.default)


def test_one_hour_raw_telemetry_default_covers_maximum_supported_rate() -> None:
    # telemetryIntervalSec has a minimum of 1 second, therefore a full hour
    # contains at most 3,600 raw telemetry rows.
    assert _query_default(get_telemetry, "limit") >= 3600


def test_long_period_analytics_covers_30_days_at_default_window() -> None:
    # Default analyticsWindowSec is 10 seconds: 30 days = 259,200 rows.
    assert _query_default(get_analytics, "limit") >= 259_200


def test_alert_query_limit_is_not_the_old_1000_row_cap() -> None:
    assert _query_default(get_alerts, "limit") >= 20_000
