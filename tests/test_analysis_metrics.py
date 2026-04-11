from pathlib import Path

from aica.analysis_metrics import AnalysisMetricsStore, AnalysisRunStats


def _stats(latency_ms: int, *, attempts: int = 1) -> AnalysisRunStats:
    return AnalysisRunStats(
        provider_id="siliconflow",
        provider_name="SiliconFlow",
        model_id="qwen-vl",
        model_name="Qwen/Qwen3-VL-32B-Thinking",
        latency_ms=latency_ms,
        llm_latency_ms=max(0, latency_ms - 120),
        preprocess_ms=120,
        attempts=attempts,
        image_count=2,
        input_bytes=2048,
    )


def test_analysis_metrics_store_records_and_summarizes_samples():
    metrics_path = Path("tests") / "_tmp_analysis_metrics.json"
    if metrics_path.exists():
        metrics_path.unlink()
    store = AnalysisMetricsStore(metrics_path)

    try:
        store.record(_stats(8200), success=True)
        store.record(_stats(11600), success=False)
        summary = store.get_summary("analysis", "siliconflow", "qwen-vl")

        assert summary is not None
        assert summary.sample_count == 2
        assert summary.success_count == 1
        assert summary.last_latency_ms == 11600
        assert summary.avg_latency_ms == 9900
        assert summary.p90_latency_ms == 11600
    finally:
        if metrics_path.exists():
            metrics_path.unlink()


def test_analysis_run_stats_formats_timing_summary():
    summary = _stats(8400, attempts=1).timing_summary

    assert "8.4s" in summary
    assert "2 张图" in summary
