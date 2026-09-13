"""Best-effort, portable host telemetry for configured Local AI inference."""

from __future__ import annotations

from dataclasses import dataclass, replace
import subprocess
from threading import Event, Lock, Thread
from typing import Literal

import psutil

from app.contracts.local_ai_runtime import LocalAIRuntimeClient


RuntimeStatus = Literal["ONLINE", "OFFLINE", "UNKNOWN"]
ModelStatus = Literal["LOADED", "IDLE", "UNKNOWN"]
ActivityStatus = Literal["ACTIVE", "IDLE"]


@dataclass(frozen=True, slots=True)
class SystemMetrics:
    cpu_percent: float | None
    ram_percent: float | None
    gpu_percent: float | None
    vram_used_mib: int | None
    vram_total_mib: int | None
    vram_percent: float | None
    activity_status: ActivityStatus
    runtime_status: RuntimeStatus
    model_status: ModelStatus


@dataclass(frozen=True, slots=True)
class InferenceTelemetrySummary:
    """Latest and peak best-effort values for the most recent inference."""

    activity_status: ActivityStatus
    sample_count: int
    latest: SystemMetrics | None
    peak_cpu_percent: float | None
    peak_ram_percent: float | None
    peak_gpu_percent: float | None
    peak_vram_used_mib: int | None
    peak_vram_percent: float | None


class InferenceTelemetrySession:
    """Daemon sampler that never blocks or raises into Local AI inference."""

    def __init__(
        self,
        provider: "SystemMetricsProvider",
        *,
        interval_seconds: float,
    ) -> None:
        self._provider = provider
        self._interval_seconds = interval_seconds
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        """Mark inference active and start non-blocking periodic sampling."""
        self._provider._mark_active()
        self._thread = Thread(target=self._sample_until_stopped, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop sampling promptly and mark inference idle without changing model state."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=0.1)
        self._provider._mark_idle()

    def _sample_until_stopped(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._provider._record_active_sample()
            except Exception:
                pass
            self._stop_event.wait(self._interval_seconds)


class SystemMetricsProvider:
    """Isolated telemetry store and best-effort Local AI inference sampler."""

    def __init__(
        self,
        *,
        runtime_client: LocalAIRuntimeClient | None = None,
        model: str | None = None,
        sample_interval_seconds: float = 1.0,
    ) -> None:
        self._runtime_client = runtime_client
        self._model = model
        self._sample_interval_seconds = sample_interval_seconds
        self._lock = Lock()
        self._summary = InferenceTelemetrySummary(
            activity_status="IDLE",
            sample_count=0,
            latest=None,
            peak_cpu_percent=None,
            peak_ram_percent=None,
            peak_gpu_percent=None,
            peak_vram_used_mib=None,
            peak_vram_percent=None,
        )

    @property
    def latest_summary(self) -> InferenceTelemetrySummary:
        """Return the retained latest/peak telemetry for future monitoring."""
        with self._lock:
            return self._summary

    def start_inference_session(self) -> InferenceTelemetrySession:
        """Create and start a best-effort sampler for one runtime generation."""
        session = InferenceTelemetrySession(
            self,
            interval_seconds=self._sample_interval_seconds,
        )
        session.start()
        return session

    def collect(self, *, activity_status: ActivityStatus = "IDLE") -> SystemMetrics:
        """Return one best-effort CPU, memory, GPU, and runtime sample."""
        cpu_percent = self._read_cpu_percent()
        ram_percent = self._read_ram_percent()
        gpu_percent, vram_used_mib, vram_total_mib = self._read_gpu_metrics()
        runtime_status, model_status = self._read_runtime_status()
        vram_percent = (
            round((vram_used_mib / vram_total_mib) * 100, 1)
            if vram_used_mib is not None and vram_total_mib
            else None
        )
        return SystemMetrics(
            cpu_percent=cpu_percent,
            ram_percent=ram_percent,
            gpu_percent=gpu_percent,
            vram_used_mib=vram_used_mib,
            vram_total_mib=vram_total_mib,
            vram_percent=vram_percent,
            activity_status=activity_status,
            runtime_status=runtime_status,
            model_status=model_status,
        )

    def _mark_active(self) -> None:
        with self._lock:
            self._summary = replace(self._summary, activity_status="ACTIVE")

    def _mark_idle(self) -> None:
        with self._lock:
            latest = self._summary.latest
            if latest is not None:
                latest = replace(latest, activity_status="IDLE")
            self._summary = replace(
                self._summary,
                activity_status="IDLE",
                latest=latest,
            )

    def _record_active_sample(self) -> None:
        sample = self.collect(activity_status="ACTIVE")
        with self._lock:
            current = self._summary
            if current.activity_status != "ACTIVE":
                return
            self._summary = InferenceTelemetrySummary(
                activity_status="ACTIVE",
                sample_count=current.sample_count + 1,
                latest=sample,
                peak_cpu_percent=self._peak(current.peak_cpu_percent, sample.cpu_percent),
                peak_ram_percent=self._peak(current.peak_ram_percent, sample.ram_percent),
                peak_gpu_percent=self._peak(current.peak_gpu_percent, sample.gpu_percent),
                peak_vram_used_mib=self._peak(
                    current.peak_vram_used_mib,
                    sample.vram_used_mib,
                ),
                peak_vram_percent=self._peak(
                    current.peak_vram_percent,
                    sample.vram_percent,
                ),
            )

    @staticmethod
    def _peak(current: float | int | None, value: float | int | None) -> float | int | None:
        if current is None:
            return value
        if value is None:
            return current
        return max(current, value)

    @staticmethod
    def _read_cpu_percent() -> float | None:
        try:
            return float(psutil.cpu_percent(interval=None))
        except Exception:
            return None

    @staticmethod
    def _read_ram_percent() -> float | None:
        try:
            return float(psutil.virtual_memory().percent)
        except Exception:
            return None

    @staticmethod
    def _read_gpu_metrics() -> tuple[float | None, int | None, int | None]:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=2,
            )
            values = [item.strip() for item in result.stdout.splitlines()[0].split(",")]
            if len(values) != 3:
                return None, None, None
            return float(values[0]), int(values[1]), int(values[2])
        except Exception:
            return None, None, None

    def _read_runtime_status(self) -> tuple[RuntimeStatus, ModelStatus]:
        if self._runtime_client is None or self._model is None:
            return "UNKNOWN", "UNKNOWN"
        try:
            if not self._runtime_client.is_runtime_available():
                return "OFFLINE", "IDLE"
            return (
                "ONLINE",
                "LOADED" if self._runtime_client.is_model_loaded(self._model) else "IDLE",
            )
        except Exception:
            return "UNKNOWN", "UNKNOWN"
