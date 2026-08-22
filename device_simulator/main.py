"""Executable entry point for the HealthBand simulator."""

import asyncio
import logging

from device_simulator.application import (
    HealthBandApplication,
)


logger = logging.getLogger(__name__)


def main() -> None:
    """Start the HealthBand simulator."""

    try:
        application = (
            HealthBandApplication()
        )

        asyncio.run(
            application.run()
        )

    except KeyboardInterrupt:
        pass

    except Exception:
        logger.exception(
            "HealthBand terminated because "
            "of an unrecoverable startup/runtime error."
        )

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()