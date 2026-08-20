"""Executable entry point for the HealthBand simulator."""

import asyncio
from device_simulator.application import HealthBandApplication


def main() -> None:
    application = HealthBandApplication()
    try:
        asyncio.run(application.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
