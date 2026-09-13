import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import time

from app.telemetry.system_metrics import SystemMetrics, SystemMetricsProvider


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
        self.assertEqual(metrics.activity_status, "IDLE")
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

    def test_session_samples_during_activity_and_retains_latest_peaks(self) -> None:
        provider = SystemMetricsProvider(sample_interval_seconds=0.01)
        samples = iter(
            (
                SystemMetrics(10.0, 20.0, 30.0, 100, 1000, 10.0, "ACTIVE", "ONLINE", "LOADED"),
                SystemMetrics(40.0, 50.0, 60.0, 700, 1000, 70.0, "ACTIVE", "ONLINE", "LOADED"),
            )
        )
        provider.collect = Mock(side_effect=lambda **_: next(samples))  # type: ignore[method-assign]

        session = provider.start_inference_session()
        for _ in range(50):
            if provider.latest_summary.sample_count >= 2:
                break
            time.sleep(0.01)

        active_summary = provider.latest_summary
        self.assertEqual(active_summary.activity_status, "ACTIVE")
        self.assertGreaterEqual(active_summary.sample_count, 2)
        self.assertEqual(active_summary.peak_cpu_percent, 40.0)
        self.assertEqual(active_summary.peak_ram_percent, 50.0)
        self.assertEqual(active_summary.peak_gpu_percent, 60.0)
        self.assertEqual(active_summary.peak_vram_used_mib, 700)
        self.assertEqual(active_summary.peak_vram_percent, 70.0)

        session.stop()

        idle_summary = provider.latest_summary
        self.assertEqual(idle_summary.activity_status, "IDLE")
        self.assertEqual(idle_summary.latest.activity_status, "IDLE")  # type: ignore[union-attr]

    def test_consecutive_sessions_reset_metrics_and_reject_old_sampler(self) -> None:
        provider = SystemMetricsProvider(sample_interval_seconds=10)
        first = SystemMetrics(90.0, 80.0, 70.0, 900, 1000, 90.0, "ACTIVE", "ONLINE", "LOADED")
        second = SystemMetrics(10.0, 20.0, 30.0, 100, 1000, 10.0, "ACTIVE", "ONLINE", "LOADED")
        provider.collect = Mock(return_value=first)  # type: ignore[method-assign]

        first_session = provider.start_inference_session()
        for _ in range(50):
            if provider.latest_summary.sample_count:
                break
            time.sleep(0.01)
        first_session.stop()

        provider.collect.return_value = second
        second_session = provider.start_inference_session()
        for _ in range(50):
            if provider.latest_summary.sample_count:
                break
            time.sleep(0.01)

        provider._record_active_sample(first_session._session_id)  # type: ignore[arg-type]
        second_summary = provider.latest_summary
        self.assertEqual(second_summary.sample_count, 1)
        self.assertEqual(second_summary.latest.cpu_percent, 10.0)  # type: ignore[union-attr]
        self.assertEqual(second_summary.peak_cpu_percent, 10.0)
        self.assertEqual(second_summary.peak_ram_percent, 20.0)
        self.assertEqual(second_summary.peak_gpu_percent, 30.0)
        self.assertEqual(second_summary.peak_vram_used_mib, 100)
        self.assertEqual(second_summary.peak_vram_percent, 10.0)

        second_session.stop()
        self.assertEqual(provider.latest_summary.activity_status, "IDLE")


if __name__ == "__main__":
    unittest.main()
