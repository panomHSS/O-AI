"""D79 lifespan-owned scheduler for local reminder run records."""

from __future__ import annotations

import asyncio
import logging

from app.services.automation_run_service import AutomationRunService


AUTOMATION_SCHEDULER_POLL_SECONDS = 60

logger = logging.getLogger(__name__)


class AutomationScheduler:
    """Poll one bounded local reminder run service every 60 seconds."""

    def __init__(self, run_service: AutomationRunService) -> None:
        if not isinstance(run_service, AutomationRunService):
            raise TypeError("run_service must be an AutomationRunService.")
        self._run_service = run_service
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.to_thread(self._run_service.tick)
            except Exception:
                logger.exception("Automation scheduler tick failed.")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=AUTOMATION_SCHEDULER_POLL_SECONDS,
                )
            except TimeoutError:
                continue

    async def stop(self) -> None:
        self._stop_event.set()


__all__ = [
    "AUTOMATION_SCHEDULER_POLL_SECONDS",
    "AutomationScheduler",
]
