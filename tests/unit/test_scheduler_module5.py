"""Tests for runtime scheduler interval updates."""

from device_simulator.core.scheduler import (
    Scheduler,
)


def test_periodic_job_interval_can_be_updated() -> None:
    scheduler = Scheduler()

    async def job() -> None:
        return None

    scheduler.add_periodic_job(
        name="measurement",
        interval_sec=2.0,
        callback=job,
    )

    assert (
        scheduler.get_periodic_job_interval(
            "measurement"
        )
        == 2.0
    )

    changed = (
        scheduler.update_periodic_job_interval(
            "measurement",
            4.0,
        )
    )

    assert changed is True

    assert (
        scheduler.get_periodic_job_interval(
            "measurement"
        )
        == 4.0
    )