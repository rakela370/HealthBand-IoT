"""Utilities for resolving REST history time ranges."""

from datetime import (
    datetime,
    timedelta,
    timezone,
)


_PERIODS = {
    "15m": timedelta(
        minutes=15
    ),
    "1h": timedelta(
        hours=1
    ),
    "24h": timedelta(
        hours=24
    ),
    "7d": timedelta(
        days=7
    ),
    "30d": timedelta(
        days=30
    ),
}


def parse_iso_datetime(
    value: str,
) -> datetime:
    """Parse timezone-aware ISO 8601 datetime."""

    normalized = (
        value.strip()
        .replace(
            "Z",
            "+00:00",
        )
    )

    parsed = (
        datetime.fromisoformat(
            normalized
        )
    )

    if parsed.tzinfo is None:
        raise ValueError(
            "Datetime must contain timezone information."
        )

    return (
        parsed.astimezone(
            timezone.utc
        )
    )


def resolve_time_range(
    period: str = "1h",
    start: str | None = None,
    end: str | None = None,
    now: datetime | None = None,
) -> tuple[
    datetime,
    datetime,
]:
    """Resolve predefined or explicit history range."""

    if (
        start is not None
        or end is not None
    ):
        if (
            start is None
            or end is None
        ):
            raise ValueError(
                "Both start and end must be supplied."
            )

        start_time = (
            parse_iso_datetime(
                start
            )
        )

        end_time = (
            parse_iso_datetime(
                end
            )
        )

        if (
            start_time
            >= end_time
        ):
            raise ValueError(
                "start must be before end."
            )

        return (
            start_time,
            end_time,
        )

    if period not in _PERIODS:
        raise ValueError(
            "Unsupported period. "
            "Allowed: 15m, 1h, 24h, 7d, 30d."
        )

    if now is None:
        now = (
            datetime.now(
                timezone.utc
            )
        )

    now = (
        now.astimezone(
            timezone.utc
        )
    )

    return (
        now
        - _PERIODS[
            period
        ],
        now,
    )