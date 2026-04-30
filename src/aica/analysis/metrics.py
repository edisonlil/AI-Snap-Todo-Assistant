"""Persistent analysis latency metrics."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from aica.paths import analysis_metrics_file as default_analysis_metrics_file


MAX_SAMPLES_PER_KEY = 20


def format_duration_ms(value: int) -> str:
    normalized = max(0, int(value))
    if normalized < 1000:
        return f"{normalized}ms"
    return f"{normalized / 1000:.1f}s"


@dataclass(frozen=True)
class AnalysisRunStats:
    provider_id: str
    provider_name: str
    model_id: str
    model_name: str
    latency_ms: int
    llm_latency_ms: int
    preprocess_ms: int
    attempts: int
    image_count: int
    input_bytes: int
    task_name: str = "analysis"

    @property
    def display_name(self) -> str:
        return f"{self.provider_name} / {self.model_name}"

    @property
    def timing_summary(self) -> str:
        return (
            f"\u672c\u6b21\u8017\u65f6 {format_duration_ms(self.latency_ms)} "
            f"\u00b7 {max(1, self.image_count)} \u5f20\u56fe "
            f"\u00b7 {max(1, self.attempts)} \u6b21\u8bf7\u6c42"
        )

    def to_record(self, *, success: bool) -> dict[str, Any]:
        return {
            "timestamp": datetime.now().isoformat(),
            "task_name": self.task_name,
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "model_id": self.model_id,
            "model_name": self.model_name,
            "latency_ms": max(0, int(self.latency_ms)),
            "llm_latency_ms": max(0, int(self.llm_latency_ms)),
            "preprocess_ms": max(0, int(self.preprocess_ms)),
            "attempts": max(1, int(self.attempts)),
            "image_count": max(1, int(self.image_count)),
            "input_bytes": max(0, int(self.input_bytes)),
            "success": bool(success),
        }


@dataclass(frozen=True)
class ModelLatencySummary:
    sample_count: int
    success_count: int
    last_latency_ms: int
    avg_latency_ms: int
    p90_latency_ms: int

    @property
    def is_empty(self) -> bool:
        return self.sample_count <= 0

    def to_display_text(self) -> str:
        if self.is_empty:
            return "\u6682\u65e0\u8017\u65f6\u6837\u672c"
        return (
            f"\u6700\u8fd1 {format_duration_ms(self.last_latency_ms)} \u00b7 "
            f"\u5e73\u5747 {format_duration_ms(self.avg_latency_ms)} \u00b7 "
            f"P90 {format_duration_ms(self.p90_latency_ms)} \u00b7 "
            f"\u6837\u672c {self.sample_count}"
        )


class AnalysisMetricsStore:
    def __init__(self, path: str | Path | None = None, *, max_samples_per_key: int = MAX_SAMPLES_PER_KEY):
        self._path = Path(path) if path is not None else default_analysis_metrics_file()
        self._max_samples_per_key = max(1, int(max_samples_per_key))

    def record(self, stats: AnalysisRunStats, *, success: bool) -> None:
        payload = self._load_payload()
        key = self._key(stats.task_name, stats.provider_id, stats.model_id)
        samples = payload.get(key, [])
        if not isinstance(samples, list):
            samples = []
        samples.append(stats.to_record(success=success))
        payload[key] = samples[-self._max_samples_per_key :]
        self._save_payload(payload)

    def get_summary(self, task_name: str, provider_id: str, model_id: str) -> ModelLatencySummary | None:
        payload = self._load_payload()
        key = self._key(task_name, provider_id, model_id)
        samples = payload.get(key, [])
        if not isinstance(samples, list) or not samples:
            return None
        latencies = []
        success_count = 0
        for item in samples:
            if not isinstance(item, dict):
                continue
            try:
                latency = max(0, int(item.get("latency_ms", 0)))
            except (TypeError, ValueError):
                continue
            latencies.append(latency)
            if bool(item.get("success", False)):
                success_count += 1
        if not latencies:
            return None
        sorted_latencies = sorted(latencies)
        p90_index = max(0, math.ceil(len(sorted_latencies) * 0.9) - 1)
        return ModelLatencySummary(
            sample_count=len(sorted_latencies),
            success_count=success_count,
            last_latency_ms=latencies[-1],
            avg_latency_ms=round(sum(sorted_latencies) / len(sorted_latencies)),
            p90_latency_ms=sorted_latencies[p90_index],
        )

    @staticmethod
    def _key(task_name: str, provider_id: str, model_id: str) -> str:
        return f"{task_name}|{provider_id}|{model_id}"

    def _load_payload(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _save_payload(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
