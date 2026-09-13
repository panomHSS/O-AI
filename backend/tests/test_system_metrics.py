import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.telemetry.system_metrics import SystemMetricsProvider


class StatusRuntime:
    def __init__(self, *, online: bool = True, loaded: bool = True) -> None:
        self.online = online
        self.loaded = loaded

    def is_runtime_available(self) -> bool:
        return self.online

    def is_model_loaded(self, model: str) -> bool:
        return self.loaded


class SystemMetricsProviderTests(unittest.TestCase):
    @patch("app.telemetry.system_metrics.subprocess.run")
    @patch("app.telemetry.system_metrics.psutil.virtual_memory")
    @patch("app.telemetry.system_metrics.psutil.cpu_percent")
    def test_maps_cpu_ram_gpu_vram_and_runtime_status(
        self,
        cpu_percent,
        virtual_memory,
        subprocess_run,
    ) -> None:
        cpu_percent.return_value = 31.5
        virtual_memory.return_value = SimpleNamespace(percent=62.0)
        subprocess_run.return_value = SimpleNamespace(stdout="42, 6144, 12288\n")

        metrics = SystemMetricsProvider(
            runtime_client=StatusRuntime(),
            model="qwen",
        ).collect()

        self.assertEqual(metrics.cpu_percent, 31.5)
        self.assertEqual(metrics.ram_percent, 62.0)
        self.assertEqual(metrics.gpu_percent, 42.0)
        self.assertEqual(metrics.vram_used_mib, 6144)
        self.assertEqual(metrics.vram_total_mib, 12288)
        self.assertEqual(metrics.vram_percent, 50.0)
        self.assertEqual(metrics.activity_status, "ACTIVE")
        self.assertEqual(metrics.runtime_status, "ONLINE")
        self.assertEqual(metrics.model_status, "LOADED")

    @patch("app.telemetry.system_metrics.subprocess.run", side_effect=OSError())
    @patch("app.telemetry.system_metrics.psutil.virtual_memory", side_effect=OSError())
    @patch("app.telemetry.system_metrics.psutil.cpu_percent", side_effect=OSError())
    def test_collection_failures_are_isolated(self, *_: object) -> None:
        metrics = SystemMetricsProvider(
            runtime_client=StatusRuntime(online=False),
            model="qwen",
        ).collect()

        self.assertIsNone(metrics.cpu_percent)
        self.assertIsNone(metrics.ram_percent)
        self.assertIsNone(metrics.gpu_percent)
        self.assertIsNone(metrics.vram_percent)
        self.assertEqual(metrics.runtime_status, "OFFLINE")
        self.assertEqual(metrics.model_status, "IDLE")


if __name__ == "__main__":
    unittest.main()
