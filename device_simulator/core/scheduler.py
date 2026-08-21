"""Asynchronous periodic task scheduler for HealthBand."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


logger = logging.getLogger(__name__)

AsyncJob = Callable[[], Awaitable[None]]


@dataclass(slots=True)
class ScheduledJob:
    """Definition of one periodic asynchronous job."""

    name: str
    interval_sec: float
    callback: AsyncJob


class Scheduler:
    """Runs registered HealthBand jobs periodically."""

    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._running = False

    def add_periodic_job(
        self,
        name: str,
        interval_sec: float,
        callback: AsyncJob,
    ) -> None:
        """Register a periodic asynchronous job."""

        if not name.strip():
            raise ValueError("Job name cannot be empty.")

        if interval_sec <= 0:
            raise ValueError("Job interval must be greater than zero.")

        if name in self._jobs:
            raise ValueError(f"Job '{name}' is already registered.")

        self._jobs[name] = ScheduledJob(
            name=name,
            interval_sec=interval_sec,
            callback=callback,
        )

    async def start(self) -> None:
        """Start all registered jobs."""

        if self._running:
            return

        self._running = True

        for job in self._jobs.values():
            self._tasks[job.name] = asyncio.create_task(
                self._run_job(job),
                name=f"healthband-{job.name}",
            )

    async def stop(self) -> None:
        """Stop all running jobs."""

        if not self._running:
            return

        self._running = False

        tasks = tuple(self._tasks.values())

        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._tasks.clear()

    async def _run_job(self, job: ScheduledJob) -> None:
        """Internal execution loop for a scheduled job."""

        try:
            while self._running:
                await asyncio.sleep(job.interval_sec)

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