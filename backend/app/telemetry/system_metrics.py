"""Best-effort host metrics for configured Local AI deployments."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess
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


class SystemMetricsProvider:
    """Collect local host metrics without allowing telemetry to raise outward."""

    def __init__(
        self,
        *,
        runtime_client: LocalAIRuntimeClient | None = None,
        model: str | None = None,
    ) -> None:
        self._runtime_client = runtime_client
        self._model = model

    def collect(self) -> SystemMetrics:
        """Return best-effort CPU, memory, GPU, and Local AI status values."""
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
            activity_status="ACTIVE" if model_status == "LOADED" else "IDLE",
            runtime_status=runtime_status,
            model_status=model_status,
        )

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
