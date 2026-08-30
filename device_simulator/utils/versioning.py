"""Small semantic-version helpers used by HealthBand runtime modules."""


def parse_software_version(version: str) -> tuple[int, int, int]:
    """Parse a strict numeric MAJOR.MINOR.PATCH version."""

    parts = version.strip().split(".")

    if len(parts) != 3:
        raise ValueError(
            "Software version must use MAJOR.MINOR.PATCH format."
        )

    try:
        parsed = tuple(int(part) for part in parts)
    except ValueError as exc:
        raise ValueError(
            "Software version must contain only numeric components."
        ) from exc

    if any(part < 0 for part in parsed):
        raise ValueError(
            "Software version components cannot be negative."
        )

    return parsed  # type: ignore[return-value]


def is_at_least(
    version: str,
    minimum: str,
) -> bool:
    """Return True when version is greater than or equal to minimum."""

    return (
        parse_software_version(version)
        >= parse_software_version(minimum)
    )