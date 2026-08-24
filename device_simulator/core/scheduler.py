"""Asynchronous periodic task scheduler for HealthBand."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


logger = logging.getLogger(__name__)

AsyncJob = Callable[
    [],
    Awaitable[None],
]


@dataclass(slots=True)
class ScheduledJob:
    """Definition of one periodic asynchronous job."""

    name: str
    interval_sec: float
    callback: AsyncJob


class Scheduler:
    """Run registered HealthBand jobs periodically."""

    def __init__(
        self,
    ) -> None:
        self._jobs: dict[
            str,
            ScheduledJob,
        ] = {}

        self._tasks: dict[
            str,
            asyncio.Task[None],
        ] = {}

        self._running = False

    def add_periodic_job(
        self,
        name: str,
        interval_sec: float,
        callback: AsyncJob,
    ) -> None:
        """Register one periodic asynchronous job."""

        if not name.strip():
            raise ValueError(
                "Job name cannot be empty."
            )

        if interval_sec <= 0:
            raise ValueError(
                "Job interval must be greater than zero."
            )

        if name in self._jobs:
            raise ValueError(
                f"Job '{name}' is already registered."
            )

        self._jobs[
            name
        ] = ScheduledJob(
            name=name,
            interval_sec=(
                interval_sec
            ),
            callback=callback,
        )

    def update_periodic_job_interval(
        self,
        name: str,
        interval_sec: float,
    ) -> bool:
        """Change interval of an existing periodic job."""

        if interval_sec <= 0:
            raise ValueError(
                "Job interval must be greater than zero."
            )

        job = (
            self._jobs.get(
                name
            )
        )

        if job is None:
            return False

        job.interval_sec = (
            interval_sec
        )

        logger.info(
            "Scheduler interval updated | "
            "job=%s | intervalSec=%s",
            name,
            interval_sec,
        )

        return True

    def get_periodic_job_interval(
        self,
        name: str,
    ) -> float | None:
        """Return configured interval for one job."""

        job = (
            self._jobs.get(
                name
            )
        )

        if job is None:
            return None

        return (
            job.interval_sec
        )

    async def start(
        self,
    ) -> None:
        """Start all registered jobs."""

        if self._running:
            return

        self._running = True

        for job in self._jobs.values():
            self._tasks[
                job.name
            ] = asyncio.create_task(
                self._run_job(
                    job
                ),
                name=(
                    f"healthband-{job.name}"
                ),
            )

    async def stop(
        self,
    ) -> None:
        """Stop all running jobs."""

        if not self._running:
            return

        self._running = False

        tasks = tuple(
            self._tasks.values()
        )

        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

        self._tasks.clear()

    async def _run_job(
        self,
        job: ScheduledJob,
    ) -> None:
        """Internal periodic execution loop."""

        try:
            while self._running:
                await asyncio.sleep(
                    job.interval_sec
                )

                if not self._running:
                    break

                try:
                    await job.callback()

                except Exception:
                    logger.exception(
                        "Scheduled job '%s' failed.",
                        job.name,
                    )

        except asyncio.CancelledError:
            logger.debug(
                "Scheduled job '%s' cancelled.",
                job.name,
            )

            raise