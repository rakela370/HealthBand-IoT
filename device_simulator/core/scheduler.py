"""Asynchronous periodic task scheduler for HealthBand."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    name: str
    interval_sec: float
    callback: Callable[[], Coroutine[Any, Any, None]]


class Scheduler:
    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._running = False

    def add_job(
        self,
        name: str,
        interval_sec: float,
        callback: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        self._jobs[name] = ScheduledJob(
            name=name,
            interval_sec=interval_sec,
            callback=callback,
        )

    async def start(self) -> None:
        if self._running:
            return
        self._running = True

        for job in self._jobs.values():
            self._tasks[job.name] = asyncio.create_task(
                self._run_job(job),
                name=f"healthband-{job.name}",
            )

    async def stop(self) -> None:
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
        try:
            while self._running:
                await asyncio.sleep(job.interval_sec)
                if not self._running:
                    break
                try:
                    await job.callback()
                except Exception:
                    logger.exception("Scheduled job '%s' failed.", job.name)
        except asyncio.CancelledError:
            logger.debug("Scheduled job '%s' cancelled.", job.name)
            raise
