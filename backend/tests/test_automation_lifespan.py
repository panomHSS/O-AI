import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.db.verification import DatabaseVerificationResult
from app.main import app, lifespan


class FakeScheduler:
    def __init__(self):
        self.run_calls = 0
        self.stop_calls = 0
        self._event = asyncio.Event()

    async def run(self):
        self.run_calls += 1
        await self._event.wait()

    async def stop(self):
        self.stop_calls += 1
        self._event.set()


class AutomationLifespanTests(unittest.TestCase):
    @staticmethod
    def settings(enabled):
        return SimpleNamespace(
            app_name="O-AI API",
            environment="development",
            oai_database_url="sqlite:///unused.db",
            oai_automation_enabled=enabled,
        )

    def test_disabled_mode_creates_zero_scheduler_tasks(self):
        async def scenario():
            with (
                patch("app.main.settings", self.settings(False)),
                patch(
                    "app.main.verify_database",
                    return_value=DatabaseVerificationResult(
                        "0011_automation_foundation"
                    ),
                ),
                patch(
                    "app.main.create_automation_scheduler"
                ) as factory,
            ):
                async with lifespan(app):
                    factory.assert_not_called()
                factory.assert_not_called()

        asyncio.run(scenario())

    def test_enabled_mode_lifespan_owns_start_and_stop(self):
        async def scenario():
            scheduler = FakeScheduler()
            with (
                patch("app.main.settings", self.settings(True)),
                patch(
                    "app.main.verify_database",
                    return_value=DatabaseVerificationResult(
                        "0011_automation_foundation"
                    ),
                ),
                patch(
                    "app.main.create_automation_scheduler",
                    return_value=scheduler,
                ) as factory,
            ):
                async with lifespan(app):
                    factory.assert_called_once_with()
                    for _ in range(100):
                        if scheduler.run_calls:
                            break
                        await asyncio.sleep(0)
                    self.assertEqual(scheduler.run_calls, 1)
                    self.assertEqual(scheduler.stop_calls, 0)

                self.assertEqual(scheduler.stop_calls, 1)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
