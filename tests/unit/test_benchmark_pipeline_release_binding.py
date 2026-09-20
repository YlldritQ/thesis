"""The benchmark stage must retain the upstream release generation it read."""

from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from thesis.pipeline import benchmark


def test_benchmark_passes_captured_gold_manifest_hash_to_election(monkeypatch):
    gold = pd.DataFrame(
        {
            **{feature: [0.0, 1.0] for feature in benchmark.ML_FEATURES},
            "rule_score": [0.0, 0.8],
            "year": [2023, 2024],
        }
    )
    captured = {}
    monkeypatch.setattr(benchmark, "ensure_dirs", lambda: None)
    monkeypatch.setattr(
        benchmark,
        "validate_canonical_release",
        lambda *args, **kwargs: SimpleNamespace(manifest_sha256="b" * 64),
    )
    monkeypatch.setattr(benchmark, "load_gold_features", lambda: gold)

    def fake_run_benchmark(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(benchmark, "run_benchmark", fake_run_benchmark)
    assert benchmark.run() == {"ok": True}
    assert captured["expected_gold_release_sha256"] == "b" * 64
