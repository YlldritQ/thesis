"""Teste njësie për detektorët e rinj dhe motorin e benchmark-ut."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.anomaly.benchmark import (
    CHAMPIONS_SCHEMA_VERSION,
    DECLARED_COMPOSITE_WEIGHTS,
    _append_result,
    benchmark_completeness,
    benchmark_implementation_provenance,
    benchmark_protocol_fingerprint,
    benchmark_protocol_provenance,
    benchmark_result_provenance,
    benchmark_semantic_check,
    build_classifier,
    build_leaderboard,
    config_key,
    data_fingerprint,
    declared_benchmark_contract,
    derive_benchmark_election,
    evaluate_supervised,
    evaluate_unsupervised,
    supervised_grid,
    unsupervised_grid,
)
from thesis.anomaly.detectors import (
    FAMILY_REGISTRY,
    HBOSScorer,
    KNNDistanceScorer,
    build_scorer,
    family_is_stochastic,
)


@pytest.fixture
def outlier_matrix() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    inliers = rng.normal(0, 1, (280, 6))
    outliers = rng.normal(7, 2, (20, 6))
    return pd.DataFrame(np.vstack([inliers, outliers]), columns=[f"f{i}" for i in range(6)])


def _complete_checkpoint_rows(quick: bool = False) -> pd.DataFrame:
    rows: list[dict] = []
    provenance = benchmark_result_provenance()
    for spec in unsupervised_grid(quick):
        rows.append(
            {
                "kind": "unsupervised",
                "family": spec["family"],
                "params": spec["params"],
                "config_key": config_key("unsupervised", spec["family"], spec["params"]),
                "status": "ok",
                "quick": quick,
                "data_fingerprint": "fixture-fingerprint",
                **provenance,
                "composite": 0.5,
                "proxy_auc_07": 0.5,
                "precision_at_k": 0.5,
                "stability_jaccard": 0.5,
                "seed_consistency": 0.5,
                "n_fits": 1,
            }
        )
    for spec in supervised_grid(quick):
        rows.append(
            {
                "kind": "supervised",
                "family": spec["family"],
                "params": spec["params"],
                "config_key": config_key("supervised", spec["family"], spec["params"]),
                "status": "ok",
                "quick": quick,
                "data_fingerprint": "fixture-fingerprint",
                **provenance,
                "oot_rocauc": 0.5,
                "cv_rocauc_mean": 0.5,
                "cv_prauc_mean": 0.5,
                "n_fits": 1,
            }
        )
    return pd.DataFrame(rows)


# ------------------------------------------------------------ detectors


@pytest.mark.parametrize("family", sorted(FAMILY_REGISTRY))
def test_every_family_round_trips(family, outlier_matrix):
    scorer = build_scorer(family)
    scorer.fit(outlier_matrix)
    assert scorer.fitted
    s = scorer.score(outlier_matrix)
    assert s.between(0.0, 1.0).all()
    assert not s.isna().any()
    assert len(s) == len(outlier_matrix)


def test_factory_rejects_unknown_family():
    with pytest.raises(KeyError):
        build_scorer("nuk_ekziston")


def test_factory_rejects_unknown_params():
    with pytest.raises(TypeError):
        build_scorer("iso", {"parameter_i_gabuar": 1})


def test_stochastic_flags_are_sane():
    assert family_is_stochastic("iso")
    assert family_is_stochastic("pca")
    assert not family_is_stochastic("hbos")


def test_hbos_scores_values_beyond_fitted_support_as_tail_events():
    train = pd.DataFrame({"x": [0.0, 0.0, 0.1, 1.0, 1.0]})
    query = pd.DataFrame({"x": [0.05, 100.0]}, index=["inside", "outside"])
    scores = HBOSScorer(n_bins=2).fit(train).score(query)
    assert scores.loc["outside"] > scores.loc["inside"]


def test_knn_zero_distance_does_not_imply_reference_membership():
    """An unseen row may duplicate a fitted vector; it is still not self."""
    train = pd.DataFrame({"x": [0.0, 1.0, 3.0]}, index=["a", "b", "c"])
    query = pd.DataFrame({"x": [0.0, 2.0]}, index=["new", "other"])
    scorer = KNNDistanceScorer(n_neighbors=1).fit(train)

    # With k=1 the duplicate query's nearest-neighbour distance is genuinely
    # zero. The former distance-based self heuristic incorrectly skipped it.
    transformed = scorer.pipe.transform(query)
    distances, _ = scorer.nn.kneighbors(transformed)
    assert distances[0, 0] == pytest.approx(0.0)
    score = scorer.score(query)
    assert score.loc["new"] < score.loc["other"]


# ------------------------------------------------------------ benchmark plumbing


def test_config_key_is_stable_and_distinct():
    a = config_key("unsupervised", "iso", {"n_estimators": 100})
    b = config_key("unsupervised", "iso", {"n_estimators": 100})
    c = config_key("unsupervised", "iso", {"n_estimators": 300})
    assert a == b
    assert a != c


def test_data_fingerprint_changes_with_data(outlier_matrix):
    rule_score = pd.Series(np.zeros(len(outlier_matrix), dtype=float))
    years = pd.Series(np.full(len(outlier_matrix), 2023, dtype=int))
    f1 = data_fingerprint(outlier_matrix, rule_score, years)
    f2 = data_fingerprint(outlier_matrix.iloc[:100], rule_score.iloc[:100], years.iloc[:100])
    assert f1 != f2


def test_data_fingerprint_hashes_label_placement_not_only_count(outlier_matrix):
    score1 = pd.Series([0.8, 0.0, *([0.0] * (len(outlier_matrix) - 2))])
    score2 = pd.Series([0.0, 0.8, *([0.0] * (len(outlier_matrix) - 2))])
    years = pd.Series(np.full(len(outlier_matrix), 2023, dtype=int))
    assert (score1 >= 0.4).sum() == (score2 >= 0.4).sum()
    assert data_fingerprint(outlier_matrix, score1, years) != data_fingerprint(
        outlier_matrix, score2, years
    )


def test_data_fingerprint_hashes_raw_scores_below_binary_threshold(
    outlier_matrix,
):
    score1 = pd.Series(np.full(len(outlier_matrix), 0.10))
    score2 = score1.copy()
    score2.iloc[0] = 0.20
    years = pd.Series(np.full(len(outlier_matrix), 2023, dtype=int))
    assert (score1 >= 0.4).equals(score2 >= 0.4)
    assert data_fingerprint(outlier_matrix, score1, years) != data_fingerprint(
        outlier_matrix, score2, years
    )


def test_data_fingerprint_hashes_oot_years(outlier_matrix):
    score = pd.Series(np.zeros(len(outlier_matrix), dtype=float))
    years1 = pd.Series(np.full(len(outlier_matrix), 2023, dtype=int))
    years2 = years1.copy()
    years2.iloc[0] = 2024
    assert data_fingerprint(outlier_matrix, score, years1) != data_fingerprint(
        outlier_matrix, score, years2
    )


def test_data_fingerprint_hashes_election_settings(outlier_matrix, monkeypatch):
    from thesis.anomaly import benchmark

    score = pd.Series(np.zeros(len(outlier_matrix), dtype=float))
    years = pd.Series(np.full(len(outlier_matrix), 2023, dtype=int))
    baseline = data_fingerprint(outlier_matrix, score, years)
    changed = benchmark.settings().model_copy(
        update={"benchmark_cv_folds": benchmark.settings().benchmark_cv_folds + 1}
    )
    monkeypatch.setattr(benchmark, "settings", lambda: changed)
    assert data_fingerprint(outlier_matrix, score, years) != baseline


def test_data_fingerprint_hashes_declared_grids(outlier_matrix, monkeypatch):
    from thesis.anomaly import benchmark

    score = pd.Series(np.zeros(len(outlier_matrix), dtype=float))
    years = pd.Series(np.full(len(outlier_matrix), 2023, dtype=int))
    baseline = data_fingerprint(outlier_matrix, score, years)
    original = benchmark.unsupervised_grid

    def changed_grid(quick=False):
        return [
            *original(quick=quick),
            {"family": "hbos", "params": {"n_bins": 999}},
        ]

    monkeypatch.setattr(benchmark, "unsupervised_grid", changed_grid)
    assert data_fingerprint(outlier_matrix, score, years) != baseline


def test_result_rows_expose_protocol_and_seed_provenance():
    provenance = benchmark_result_provenance()
    assert provenance["protocol_fingerprint"] == benchmark_protocol_fingerprint()
    assert provenance["protocol_version"]
    assert provenance["random_seed"] == 7
    assert "bootstrap_refit_offset" in provenance["seed_schedule_json"]
    assert (
        provenance["implementation_fingerprint"]
        == benchmark_implementation_provenance()["fingerprint"]
    )
    assert len(provenance["implementation_manifest_sha256"]) == 64


def test_checkpoint_json_is_strict_and_quick_results_are_separate(tmp_path, monkeypatch):
    from thesis.anomaly import benchmark

    canonical = tmp_path / "results.jsonl"
    monkeypatch.setattr(benchmark, "BENCHMARK_RESULTS", canonical)
    canonical.write_text('{"released": "old"}\n', encoding="utf-8")
    _append_result({"quick": False, "ok": np.bool_(True), "missing": np.nan})
    _append_result({"quick": True, "ok": np.bool_(True), "missing": np.nan})

    wip = tmp_path / "results.wip.jsonl"
    full = json.loads(wip.read_text())
    quick = json.loads((tmp_path / "results.quick.jsonl").read_text())
    assert full == {"missing": None, "ok": True, "quick": False}
    assert quick == {"missing": None, "ok": True, "quick": True}
    assert json.loads(canonical.read_text()) == {"released": "old"}

    wip.write_text('{"quick": false}\n{"truncated":', encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid benchmark checkpoint JSON"):
        benchmark.load_results(quick=False)
    wip.write_text('{"quick": false, "value": NaN}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid benchmark checkpoint JSON"):
        benchmark.load_results(quick=False)


def test_resume_uses_only_latest_current_complete_row(tmp_path, monkeypatch):
    from thesis.anomaly import benchmark

    canonical = tmp_path / "results.jsonl"
    monkeypatch.setattr(benchmark, "BENCHMARK_RESULTS", canonical)
    wip = tmp_path / "results.wip.jsonl"
    row = {
        key: value
        for key, value in _complete_checkpoint_rows().iloc[0].to_dict().items()
        if not (isinstance(value, (float, np.floating)) and np.isnan(value))
    }
    key = row["config_key"]
    wip.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert benchmark._load_done_keys("fixture-fingerprint") == {key}

    failed_retry = {**row, "status": "failed"}
    wip.write_text(
        json.dumps(row) + "\n" + json.dumps(failed_retry) + "\n",
        encoding="utf-8",
    )
    assert benchmark._load_done_keys("fixture-fingerprint") == set()

    stale = {**row, "implementation_fingerprint": "stale"}
    wip.write_text(json.dumps(stale) + "\n", encoding="utf-8")
    assert benchmark._load_done_keys("fixture-fingerprint") == set()


def test_completed_wip_checkpoint_atomically_replaces_release_snapshot(tmp_path):
    from thesis.anomaly import benchmark

    source = tmp_path / "results.wip.jsonl"
    target = tmp_path / "results.jsonl"
    source.write_text('{"status": "ok"}\n', encoding="utf-8")
    target.write_text('{"status": "old"}\n', encoding="utf-8")
    benchmark._publish_checkpoint_snapshot(source, target)
    assert target.read_bytes() == source.read_bytes()
    assert not list(tmp_path.glob(".results.jsonl.*.tmp"))


def test_ml_rejects_stale_benchmark_champions(tmp_path, monkeypatch, outlier_matrix):
    from thesis.pipeline import ml

    champions_path = tmp_path / "champions.json"
    champions_path.write_text(json.dumps({"data_fingerprint": "stale-data"}))
    monkeypatch.setattr(ml, "CHAMPIONS", champions_path)
    monkeypatch.setattr(
        ml,
        "_load_released_benchmark_bundle",
        lambda: (
            pd.DataFrame(),
            pd.DataFrame(),
            json.loads(champions_path.read_text()),
            {},
        ),
    )
    rule_score = pd.Series(np.zeros(len(outlier_matrix), dtype=float))
    years = pd.Series(np.full(len(outlier_matrix), 2023, dtype=int))

    with pytest.raises(RuntimeError, match=r"stale.*thesis pipeline benchmark"):
        ml._load_champions(outlier_matrix, rule_score, years)


def test_ml_guard_rejects_champions_when_only_oot_years_changed(
    tmp_path, monkeypatch, outlier_matrix
):
    from thesis.pipeline import ml

    rule_score = pd.Series(np.zeros(len(outlier_matrix), dtype=float))
    original_years = pd.Series(np.full(len(outlier_matrix), 2023, dtype=int))
    changed_years = original_years.copy()
    changed_years.iloc[0] = 2024
    champions_path = tmp_path / "champions.json"
    champions_path.write_text(
        json.dumps(
            {"data_fingerprint": data_fingerprint(outlier_matrix, rule_score, original_years)}
        )
    )
    monkeypatch.setattr(ml, "CHAMPIONS", champions_path)
    monkeypatch.setattr(
        ml,
        "_load_released_benchmark_bundle",
        lambda: (
            pd.DataFrame(),
            pd.DataFrame(),
            json.loads(champions_path.read_text()),
            {},
        ),
    )

    with pytest.raises(RuntimeError, match="champions are stale"):
        ml._load_champions(outlier_matrix, rule_score, changed_years)


def _valid_champions_payload(
    X: pd.DataFrame,
    rule_score: pd.Series,
    years: pd.Series,
) -> dict:
    fingerprint = data_fingerprint(X, rule_score, years)
    rows = _complete_checkpoint_rows().copy()
    rows["data_fingerprint"] = fingerprint
    election = derive_benchmark_election(rows)
    protocol = benchmark_protocol_provenance()
    return {
        "schema_version": CHAMPIONS_SCHEMA_VERSION,
        "data_fingerprint": fingerprint,
        "benchmark_protocol": protocol,
        "protocol_fingerprint": benchmark_protocol_fingerprint(),
        "implementation_fingerprint": protocol["implementation"]["fingerprint"],
        "created_at": "2026-07-18T00:00:00+00:00",
        "quick": False,
        **election,
        "composite_weights": DECLARED_COMPOSITE_WEIGHTS,
        "composite_formula": ("0.45×proxy_auc_07 + 0.35×stability_jaccard + 0.20×seed_consistency"),
    }


def _mock_benchmark_bundle(payload: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    rows = _complete_checkpoint_rows().copy()
    rows["data_fingerprint"] = payload["data_fingerprint"]
    leaderboard = rows.drop(columns=["error"], errors="ignore")
    check = benchmark_semantic_check(rows, payload, leaderboard=leaderboard)
    return rows, leaderboard, payload, check


def test_ml_accepts_only_complete_full_champion_contract(tmp_path, monkeypatch, outlier_matrix):
    from thesis.pipeline import ml

    rule_score = pd.Series(np.zeros(len(outlier_matrix), dtype=float))
    years = pd.Series(np.full(len(outlier_matrix), 2023, dtype=int))
    payload = _valid_champions_payload(outlier_matrix, rule_score, years)
    champions_path = tmp_path / "champions.json"
    champions_path.write_text(json.dumps(payload))
    monkeypatch.setattr(ml, "CHAMPIONS", champions_path)
    monkeypatch.setattr(
        ml,
        "_load_released_benchmark_bundle",
        lambda: _mock_benchmark_bundle(json.loads(champions_path.read_text())),
    )

    loaded = ml._load_champions(outlier_matrix, rule_score, years)

    assert loaded["completeness"]["successful_total"] == 35


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda payload: payload.pop("completeness"), "completeness proof"),
        (
            lambda payload: payload.update({"protocol_fingerprint": "stale"}),
            "protocol_fingerprint",
        ),
        (lambda payload: payload.update({"quick": True}), "quick must be false"),
        (
            lambda payload: payload.update({"ensemble_families": ["iso"]}),
            "ensemble_families",
        ),
    ],
)
def test_ml_rejects_incomplete_champion_contract(
    tmp_path, monkeypatch, outlier_matrix, mutate, message
):
    from thesis.pipeline import ml

    rule_score = pd.Series(np.zeros(len(outlier_matrix), dtype=float))
    years = pd.Series(np.full(len(outlier_matrix), 2023, dtype=int))
    payload = _valid_champions_payload(outlier_matrix, rule_score, years)
    mutate(payload)
    champions_path = tmp_path / "champions.json"
    champions_path.write_text(json.dumps(payload))
    monkeypatch.setattr(ml, "CHAMPIONS", champions_path)
    monkeypatch.setattr(
        ml,
        "_load_released_benchmark_bundle",
        lambda: _mock_benchmark_bundle(json.loads(champions_path.read_text())),
    )

    with pytest.raises(RuntimeError, match=message):
        ml._load_champions(outlier_matrix, rule_score, years)


def test_grids_have_expected_shape():
    full_u = unsupervised_grid(quick=False)
    assert len(full_u) == 23
    assert {g["family"] for g in full_u} == set(FAMILY_REGISTRY)
    keys = [config_key("unsupervised", g["family"], g["params"]) for g in full_u]
    assert len(keys) == len(set(keys))
    quick_u = unsupervised_grid(quick=True)
    assert 0 < len(quick_u) <= 6
    full_s = supervised_grid(quick=False)
    assert {g["family"] for g in full_s} == {"hgb", "rf", "logreg", "extratrees"}


def test_benchmark_completeness_requires_every_declared_successful_config():
    complete_rows = _complete_checkpoint_rows()
    contract = declared_benchmark_contract()

    complete = benchmark_completeness(complete_rows)
    assert complete["complete"]
    assert complete["successful_total"] == contract["expected_total"] == 35

    missing = benchmark_completeness(complete_rows.iloc[:-1])
    assert not missing["complete"]
    assert len(missing["missing_config_keys"]) == 1

    failed_rows = complete_rows.copy()
    failed_rows.loc[0, "status"] = "failed"
    failed = benchmark_completeness(failed_rows)
    assert not failed["complete"]
    assert failed["failed_config_keys"] == [failed_rows.loc[0, "config_key"]]


def test_benchmark_completeness_rejects_extra_or_malformed_rows():
    rows = _complete_checkpoint_rows()
    extra = rows.iloc[0].to_dict()
    extra.update(
        {
            "family": "hbos",
            "params": {"n_bins": 999},
            "config_key": config_key("unsupervised", "hbos", {"n_bins": 999}),
        }
    )
    with_extra = benchmark_completeness(pd.concat([rows, pd.DataFrame([extra])]))
    assert not with_extra["complete"]
    assert with_extra["extra_config_keys"] == [extra["config_key"]]

    malformed = rows.copy()
    malformed.at[0, "params"] = {"n_estimators": 999}
    invalid = benchmark_completeness(malformed)
    assert not invalid["complete"]
    assert invalid["invalid_config_keys"] == [malformed.loc[0, "config_key"]]


def test_benchmark_completeness_rejects_stale_implementation_provenance():
    rows = _complete_checkpoint_rows()
    rows.loc[0, "implementation_fingerprint"] = "stale"
    result = benchmark_completeness(rows)
    assert not result["complete"]
    assert result["stale_protocol_config_keys"] == [rows.loc[0, "config_key"]]


def test_semantic_check_rejects_champion_and_leaderboard_tampering(outlier_matrix, tmp_path):
    score = pd.Series(np.zeros(len(outlier_matrix), dtype=float))
    years = pd.Series(np.full(len(outlier_matrix), 2023, dtype=int))
    champions = _valid_champions_payload(outlier_matrix, score, years)
    rows, leaderboard, _, _ = _mock_benchmark_bundle(champions)
    assert benchmark_semantic_check(rows, champions, leaderboard=leaderboard)["passed"]

    parquet_frame = leaderboard.copy()
    parquet_frame["params"] = parquet_frame["params"].map(
        lambda value: json.dumps(value, sort_keys=True)
    )
    parquet_path = tmp_path / "leaderboard.parquet"
    parquet_frame.to_parquet(parquet_path, index=False)
    persisted = pd.read_parquet(parquet_path)
    assert benchmark_semantic_check(rows, champions, leaderboard=persisted)["passed"]

    tampered_champions = json.loads(json.dumps(champions))
    tampered_champions["ensemble_families"] = list(
        reversed(tampered_champions["ensemble_families"])
    )
    assert not benchmark_semantic_check(rows, tampered_champions, leaderboard=leaderboard)["passed"]

    tampered_leaderboard = leaderboard.copy()
    tampered_leaderboard.loc[0, "proxy_auc_07"] = 0.9
    check = benchmark_semantic_check(rows, champions, leaderboard=tampered_leaderboard)
    assert not check["passed"]
    assert "leaderboard" in " ".join(check["errors"])


def test_complete_leaderboard_records_lineage_and_publishes_champions_last(monkeypatch, tmp_path):
    from thesis.anomaly import benchmark
    from thesis.io import writers

    rows = _complete_checkpoint_rows()
    events: list[tuple[str, object]] = []
    captured: dict[str, object] = {}
    test_settings = benchmark.settings().model_copy(update={"data_dir": tmp_path})
    monkeypatch.setattr(benchmark, "settings", lambda: test_settings)
    monkeypatch.setattr(benchmark, "BENCHMARK_RESULTS", tmp_path / "results.jsonl")
    monkeypatch.setattr(benchmark, "BENCHMARK_LEADERBOARD", tmp_path / "leaderboard.parquet")
    monkeypatch.setattr(benchmark, "BENCHMARK_RELEASE_DQ", tmp_path / "benchmark.dq.json")

    monkeypatch.setattr(benchmark, "load_results", lambda fingerprint, quick: rows)
    monkeypatch.setattr(
        benchmark,
        "_publish_checkpoint_snapshot",
        lambda source, target: events.append(("snapshot", (source, target))),
    )
    monkeypatch.setattr(
        benchmark,
        "_write_leaderboard_md",
        lambda *args, **kwargs: events.append(("markdown", None)),
    )

    def fake_parquet(frame, path, **kwargs):
        captured["leaderboard_frame"] = frame.copy()
        path.write_bytes(b"parquet-fixture")
        captured["inputs"] = kwargs["inputs"]
        events.append(("parquet", None))

    def fake_json(payload, path, **kwargs):
        del kwargs
        if path == benchmark.CHAMPIONS:
            captured["champions"] = payload
        if path == benchmark.BENCHMARK_RELEASE_DQ:
            captured["semantic_check"] = payload
        events.append(("json", None))

    monkeypatch.setattr(writers, "write_parquet", fake_parquet)
    monkeypatch.setattr(writers, "write_json", fake_json)
    monkeypatch.setattr(
        benchmark,
        "publish_release",
        lambda *args, **kwargs: events.append(("release", kwargs)),
    )
    monkeypatch.setattr(
        benchmark.pd,
        "read_parquet",
        lambda path: captured["leaderboard_frame"].copy(),
    )

    summary = build_leaderboard("fixture-fingerprint", expected_gold_release_sha256="a" * 64)

    assert summary["configs_ok"] == 35
    assert captured["inputs"] == [benchmark.GOLD_FEATURES, benchmark.BENCHMARK_RESULTS]
    champions = captured["champions"]
    assert champions["schema_version"] == CHAMPIONS_SCHEMA_VERSION
    assert champions["completeness"]["complete"] is True
    assert champions["protocol_fingerprint"] == benchmark_protocol_fingerprint()
    assert champions["implementation_fingerprint"]
    assert captured["semantic_check"]["passed"] is True
    assert captured["semantic_check"]["rows"] == 35
    assert captured["semantic_check"]["release_binding"]["artifact_path"] == ("leaderboard.parquet")
    assert len(captured["semantic_check"]["data_fingerprint"]) == 64
    release_kwargs = events[-1][1]
    assert benchmark.BENCHMARK_RESULTS in release_kwargs["artifacts"]
    assert release_kwargs["checks"] == [benchmark.BENCHMARK_RELEASE_DQ]
    assert release_kwargs["expected_input_manifest_sha256"] == {benchmark.GOLD_RELEASE: "a" * 64}
    assert events[0] == (
        "snapshot",
        (
            benchmark.BENCHMARK_RESULTS.with_name("results.wip.jsonl"),
            benchmark.BENCHMARK_RESULTS,
        ),
    )
    assert [event[0] for event in events[-3:]] == ["json", "json", "release"]


# ------------------------------------------------------------ evaluations


def test_evaluate_unsupervised_returns_metrics(outlier_matrix, monkeypatch):
    monkeypatch.setenv("THESIS_BENCHMARK_BOOTSTRAP_RUNS", "2")
    monkeypatch.setenv("THESIS_BENCHMARK_EXTRA_SEEDS", "1")
    from thesis.config import reset_settings_for_tests

    reset_settings_for_tests()

    rng = np.random.default_rng(0)
    rule = pd.Series(rng.uniform(0, 1, len(outlier_matrix)))
    y04 = (rule >= 0.4).astype(int)
    y07 = (rule >= 0.7).astype(int)
    m = evaluate_unsupervised("hbos", {"n_bins": 10}, outlier_matrix, y04, y07, rule)
    for key in [
        "proxy_auc_04",
        "proxy_auc_07",
        "stability_jaccard",
        "seed_consistency",
        "composite",
        "n_fits",
        "fit_seconds",
    ]:
        assert key in m, key
    assert 0.0 <= m["composite"] <= 1.0
    assert m["n_fits"] >= 3


def test_evaluate_supervised_cv_and_oot(outlier_matrix, monkeypatch):
    monkeypatch.setenv("THESIS_BENCHMARK_SUPERVISED_SEEDS", "1")
    monkeypatch.setenv("THESIS_BENCHMARK_CV_FOLDS", "3")
    monkeypatch.setenv("THESIS_BENCHMARK_OOT_TRAIN_MAX_YEAR", "2020")
    from thesis.config import reset_settings_for_tests

    reset_settings_for_tests()

    rng = np.random.default_rng(0)
    n = len(outlier_matrix)
    # label correlated with first feature so AUC is meaningfully > 0.5
    y = pd.Series((outlier_matrix["f0"] + rng.normal(0, 0.5, n) > 0.3).astype(int))
    years = pd.Series(rng.integers(2016, 2026, n))
    m = evaluate_supervised("logreg", {"C": 1.0}, outlier_matrix, y, years)
    assert m["cv_rocauc_mean"] > 0.7
    assert m["n_fits"] >= 3
    # OOT may be None on tiny samples; when present it must be a valid AUC
    if m["oot_rocauc"] is not None:
        assert 0.0 <= m["oot_rocauc"] <= 1.0


@pytest.mark.parametrize(
    ("family", "params"),
    [
        ("hgb", {"max_depth": 2, "learning_rate": 0.1, "max_iter": 10}),
        ("rf", {"n_estimators": 10, "max_depth": 3}),
        ("logreg", {"C": 1.0}),
        ("extratrees", {"n_estimators": 10}),
    ],
)
def test_evaluate_supervised_accepts_nullable_numeric_features(family, params, monkeypatch):
    """Nullable bidder counts must reach sklearn as float NaN, never pd.NA."""
    monkeypatch.setenv("THESIS_BENCHMARK_SUPERVISED_SEEDS", "1")
    monkeypatch.setenv("THESIS_BENCHMARK_CV_FOLDS", "2")
    from thesis.config import reset_settings_for_tests

    reset_settings_for_tests()
    rng = np.random.default_rng(13)
    n = 120
    signal = rng.normal(size=n)
    X = pd.DataFrame(
        {
            "continuous": signal,
            "num_bidders": pd.Series(rng.integers(0, 4, size=n), dtype="Int64"),
        }
    )
    X.loc[[3, 27, 88], "num_bidders"] = pd.NA
    y = pd.Series((signal > 0).astype(int))
    years = pd.Series([2020] * n)

    metrics = evaluate_supervised(family, params, X, y, years)

    assert np.isfinite(metrics["cv_rocauc_mean"])
    assert metrics["n_fits"] == 2


def test_build_classifier_families():
    for fam in ["hgb", "rf", "logreg", "extratrees"]:
        model = build_classifier(fam, {}, seed=1)
        assert hasattr(model, "fit")
    with pytest.raises(KeyError):
        build_classifier("i_panjohur", {}, seed=1)
