"""Generation-bound integration checks for direct ensemble XAI."""

from __future__ import annotations

import numpy as np
import pandas as pd

from thesis import paths
from thesis.anomaly.ensemble import compose_hybrid_ensemble, validate_ensemble_definition
from thesis.io import readers
from thesis.jsonutil import loads_json
from thesis.release import validate_canonical_release


def test_released_ensemble_xai_reconstructs_every_published_row() -> None:
    validate_canonical_release("ml", require_current_provenance=True)
    gold = readers.load_gold_tenders()
    metadata = readers.load_feature_metadata()
    definition = metadata["ensemble_explanation"]
    composition = compose_hybrid_ensemble(
        gold,
        definition["detector_families"],
        flag_quantile=float(definition["flag_quantile"]),
        minimum_models_agreeing=int(definition["minimum_models_agreeing"]),
    )
    validate_ensemble_definition(definition, composition)

    rank_delta = max(
        float(
            np.max(
                np.abs(
                    pd.to_numeric(gold[column], errors="raise").to_numpy(dtype=float)
                    - composition.detector_ranks[column].to_numpy(dtype=float)
                )
            )
        )
        for column in composition.detector_rank_columns
    )
    ensemble_delta = float(
        np.max(
            np.abs(
                gold["ensemble_score"].to_numpy(dtype=float)
                - composition.ensemble_score.to_numpy(dtype=float)
            )
        )
    )
    centered_delta = float(
        np.max(
            np.abs(
                gold["ensemble_score"].to_numpy(dtype=float)
                - (
                    composition.baseline_score
                    + composition.centered_contributions.sum(axis=1).to_numpy(dtype=float)
                )
            )
        )
    )

    assert rank_delta <= 1e-12
    assert ensemble_delta <= 1e-12
    assert centered_delta <= 1e-12
    assert len(composition.component_columns) == len(definition["detector_families"]) + 2


def test_released_shap_dq_names_rule_proxy_raw_output_not_ensemble() -> None:
    validate_canonical_release("ml", require_current_provenance=True)
    payload = loads_json(paths.SHAP_VALUES_RELEASE_DQ.read_text(encoding="utf-8"))

    assert payload["passed"] is True
    assert payload["xai_semantics"] == {
        "target": "rule_proxy_binary_label",
        "output_space": "raw_log_odds",
        "does_not_explain": "ensemble_score",
    }
    result = next(
        item
        for item in payload["expectations"]
        if item["name"] == "rule_proxy_raw_output_additivity"
    )
    assert result["passed"] is True
