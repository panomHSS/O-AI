import asyncio
import unittest

from app.services.automation_run_service import AutomationRunService
from app.services.automation_scheduler import (
    AUTOMATION_SCHEDULER_POLL_SECONDS,
    AutomationScheduler,
)


class FakeRunService(AutomationRunService):
    def __init__(self):
        self.calls = 0

    def tick(self):
        self.calls += 1


class AutomationSchedulerTests(unittest.TestCase):
    def test_poll_interval_is_frozen_at_60_seconds(self):
        self.assertEqual(AUTOMATION_SCHEDULER_POLL_SECONDS, 60)

    def test_scheduler_starts_one_tick_and_stops_cleanly(self):
        async def scenario():
            run_service = FakeRunService()
            scheduler = AutomationScheduler(run_service)
            task = asyncio.create_task(scheduler.run())
            for _ in range(100):
                if run_service.calls:
                    break
                await asyncio.sleep(0)
            self.assertEqual(run_service.calls, 1)
            await scheduler.stop()
            await task
            self.assertEqual(run_service.calls, 1)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
