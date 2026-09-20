"""Exact-XAI regressions for the deployed hybrid anomaly score."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from thesis.anomaly.comparison import explain_context_score
from thesis.anomaly.ensemble import compose_hybrid_ensemble
from thesis.anomaly.explanations import feature_deviation_profile
from thesis.anomaly.rules import RULES, explain_rule_score
from thesis.domain.features import CONTEXT_FEATURES
from thesis.viz import ensemble_contribution_bar, shap_waterfall


def _composition_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "a_score": [0.0, 0.0, 1.0, 1.0],
            "b_score": [0.2, 0.4, 0.6, 0.8],
            "rule_score": [0.0, 0.2, 0.4, 0.6],
            "context_score": [0.1, 0.3, 0.5, 0.7],
        },
        index=[10, 11, 12, 13],
    )


def test_hybrid_ensemble_tie_ranks_and_local_contributions_are_exact() -> None:
    frame = _composition_frame()
    result = compose_hybrid_ensemble(
        frame,
        ["a", "b"],
        flag_quantile=0.75,
        minimum_models_agreeing=1,
    )

    assert result.detector_rank_columns == ("ensemble_rank_a", "ensemble_rank_b")
    assert result.detector_ranks["ensemble_rank_a"].tolist() == [0.375, 0.375, 0.875, 0.875]
    assert result.detector_ranks["ensemble_rank_b"].tolist() == [0.25, 0.5, 0.75, 1.0]
    expected = pd.concat(
        [result.detector_ranks, frame[["rule_score", "context_score"]]], axis=1
    ).mean(axis=1)
    assert np.allclose(result.ensemble_score, expected, rtol=0.0, atol=1e-12)

    explanation = result.explain_record(12, published_score=float(expected.loc[12]))
    assert len(explanation) == 4
    assert explanation["weight"].eq(0.25).all()
    assert explanation["direct_contribution"].sum() == pytest.approx(expected.loc[12])
    assert result.baseline_score + explanation["effect_vs_baseline"].sum() == pytest.approx(
        expected.loc[12]
    )


@pytest.mark.parametrize(
    ("families", "mutation", "message"),
    [
        (["a", "a"], None, "unique"),
        (["missing"], None, "missing"),
        (["a", "b"], ("a_score", np.nan), "null"),
    ],
)
def test_hybrid_ensemble_fails_closed_on_invalid_components(families, mutation, message) -> None:
    frame = _composition_frame()
    if mutation is not None:
        frame.loc[10, mutation[0]] = mutation[1]
    with pytest.raises(ValueError, match=message):
        compose_hybrid_ensemble(frame, families, minimum_models_agreeing=1)


def test_record_explanation_rejects_score_from_another_rank_population() -> None:
    frame = _composition_frame()
    full = compose_hybrid_ensemble(frame, ["a", "b"], minimum_models_agreeing=1)
    filtered = compose_hybrid_ensemble(frame.iloc[:3], ["a", "b"], minimum_models_agreeing=1)

    with pytest.raises(ValueError, match="does not match"):
        filtered.explain_record(12, published_score=float(full.ensemble_score.loc[12]))


def test_context_explanation_preserves_signed_tied_drivers_and_reconstructs() -> None:
    row = dict.fromkeys(CONTEXT_FEATURES, np.nan)
    row[CONTEXT_FEATURES[0]] = -3.0
    row[CONTEXT_FEATURES[1]] = 3.0
    expected = float(np.tanh(1.5))

    explanation = explain_context_score(row, published_score=expected)

    assert explanation.drivers == tuple(CONTEXT_FEATURES[:2])
    assert explanation.signed_z_by_driver == {
        CONTEXT_FEATURES[0]: -3.0,
        CONTEXT_FEATURES[1]: 3.0,
    }
    assert explanation.reconstructed_score == pytest.approx(expected)


def test_context_explanation_all_missing_is_zero_without_driver() -> None:
    explanation = explain_context_score(
        dict.fromkeys(CONTEXT_FEATURES, np.nan), published_score=0.0
    )
    assert explanation.drivers == ()
    assert explanation.max_absolute_z == 0.0
    assert explanation.reconstructed_score == 0.0


def test_rule_explanation_keeps_zero_weight_diagnostics_out_of_arithmetic() -> None:
    scoring = next(rule for rule in RULES if rule.score_enabled)
    diagnostic = next(rule for rule in RULES if not rule.score_enabled)
    expected = min(scoring.weight / 2.0, 1.0)
    explanation = explain_rule_score(
        {scoring.code: True, diagnostic.code: True},
        published_score=expected,
    )

    assert [item["code"] for item in explanation["triggered_score_enabled"]] == [scoring.code]
    assert explanation["triggered_zero_weight_diagnostics"] == [diagnostic.code]
    assert explanation["reconstructed_score"] == pytest.approx(expected)


def test_feature_profile_labels_percentiles_and_missingness_as_descriptive_only() -> None:
    reference = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [1.0, np.nan, 1.0, 1.0]})
    profile = feature_deviation_profile(reference, {"x": 4.0, "y": np.nan}, ["x", "y"])

    by_feature = profile.set_index("feature")
    assert by_feature.at["x", "percentile"] == pytest.approx(0.875)
    assert by_feature.at["x", "basis"] == "empirical_midrank_percentile"
    assert bool(by_feature.at["y", "missing"])
    assert by_feature.at["y", "missing_rate"] == pytest.approx(0.25)
    assert by_feature.at["y", "basis"] == "missingness_frequency"


def test_ensemble_bar_uses_exact_direct_contributions() -> None:
    explanation = pd.DataFrame(
        {
            "component_label": ["A", "Rregullat"],
            "component_type": ["detector_rank", "rule"],
            "value_in_formula": [0.8, 0.2],
            "weight": [0.5, 0.5],
            "direct_contribution": [0.4, 0.1],
        }
    )
    figure = ensemble_contribution_bar(explanation)
    assert sum(figure.data[0].x) == pytest.approx(0.5)
    assert figure.layout.xaxis.title.text == "kontributi ekzakt në ensemble_score"


def test_shap_axis_names_rule_proxy_log_odds_not_anomaly_score() -> None:
    figure = shap_waterfall(["f1"], np.array([0.2]), 0.1, 0.3)
    axis = figure.layout.xaxis.title.text.lower()
    assert "log-odds" in axis
    assert "pikën e anomalisë" not in axis
