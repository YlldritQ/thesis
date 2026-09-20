"""Fail-closed semantic checks for persisted ML-stage artifacts.

Release manifests prove byte identity.  This module proves that the bytes written
by the ML stage still encode the in-memory feature/model/provenance contract before
the manifest is allowed to publish them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype

from .. import paths
from ..config import settings
from ..dq.framework import (
    Expectation,
    ExpectationSuite,
    Severity,
    SuiteResult,
    dataframe_fingerprint,
    run_suite,
)
from ..jsonutil import json_ready, loads_json
from ..lineage import file_sha256
from .ensemble import compose_hybrid_ensemble
from .models import to_model_matrix

ML_JSON_SCHEMA_VERSION = 2
MODEL_BUNDLE_SCHEMA_VERSION = 1
HGB_ARTIFACT_SCHEMA_VERSION = 1

DEPLOYMENT_PROVENANCE_KEYS = frozenset(
    {
        "data_fingerprint",
        "protocol_fingerprint",
        "benchmark_complete",
        "champions_schema_version",
        "champions_created_at",
        "benchmark_implementation_fingerprint",
        "benchmark_semantic_fingerprint",
    }
)

FEATURE_LIST_FIELDS = frozenset(
    {
        "schema_version",
        *DEPLOYMENT_PROVENANCE_KEYS,
        "ml_features",
        "ensemble_families",
        "model_selection",
        "ensemble_explanation",
        "shap_explanation",
        "shap_base_value",
    }
)

VALIDATION_REPORT_FIELDS = frozenset(
    {
        "schema_version",
        *DEPLOYMENT_PROVENANCE_KEYS,
        "n_records",
        "n_features",
        "features",
        "ensemble_models",
        "all_detector_families",
        "model_selection",
        "supervised_model",
        "rule_label_threshold",
        "IMPORTANT_metrics_are_faithfulness_to_rules_not_detection",
        "circularity_note",
        "cross_validation",
        "rule_only_baseline_and_confusion",
        "stability_by_ensemble_family",
        "limited_replication_note",
        "inter_model_agreement",
        "rank_agreement_quantile_sensitivity",
        "deployed_score_feature_ablation",
        "model_election_sensitivity",
        "supervised_calibration",
        "ensemble_explanation",
        "shap_explanation",
        "shap_base_value",
    }
)


class MLArtifactIntegrityError(ValueError):
    """A persisted ML artifact contradicts the generation being published."""


def _json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = loads_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise MLArtifactIntegrityError(f"invalid persisted {label} JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise MLArtifactIntegrityError(f"persisted {label} must contain a JSON object")
    return payload


def _require_exact_keys(payload: Mapping[str, Any], expected: frozenset[str], label: str) -> None:
    actual = set(payload)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise MLArtifactIntegrityError(
            f"persisted {label} schema mismatch (missing={missing}, extra={extra})"
        )


def _require_provenance(
    payload: Mapping[str, Any], expected_provenance: Mapping[str, Any], label: str
) -> None:
    if set(expected_provenance) != DEPLOYMENT_PROVENANCE_KEYS:
        raise MLArtifactIntegrityError("internal deployment provenance schema is incomplete")
    observed = {key: payload.get(key) for key in DEPLOYMENT_PROVENANCE_KEYS}
    if observed != dict(expected_provenance):
        raise MLArtifactIntegrityError(f"persisted {label} provenance is stale or inconsistent")


def _finite_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and np.isfinite(value)


def validate_persisted_json_artifacts(
    feature_list_path: Path,
    validation_report_path: Path,
    *,
    expected_feature_list: Mapping[str, Any],
    expected_validation_report: Mapping[str, Any],
    expected_provenance: Mapping[str, Any],
    expected_features: Sequence[str],
    expected_ensemble_families: Sequence[str],
    expected_all_families: Sequence[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reload and strictly validate both JSON artifacts written by the ML stage."""
    feature_list = _json_object(feature_list_path, "feature-list")
    report = _json_object(validation_report_path, "validation-report")

    _require_exact_keys(feature_list, FEATURE_LIST_FIELDS, "feature-list")
    _require_exact_keys(report, VALIDATION_REPORT_FIELDS, "validation-report")
    _require_provenance(feature_list, expected_provenance, "feature-list")
    _require_provenance(report, expected_provenance, "validation-report")

    if feature_list.get("schema_version") != ML_JSON_SCHEMA_VERSION:
        raise MLArtifactIntegrityError("unsupported persisted feature-list schema version")
    if report.get("schema_version") != ML_JSON_SCHEMA_VERSION:
        raise MLArtifactIntegrityError("unsupported persisted validation-report schema version")
    if feature_list.get("ml_features") != list(expected_features):
        raise MLArtifactIntegrityError("persisted feature-list feature order is inconsistent")
    if report.get("features") != list(expected_features):
        raise MLArtifactIntegrityError("persisted validation-report feature order is inconsistent")
    if report.get("n_features") != len(expected_features):
        raise MLArtifactIntegrityError("persisted validation-report feature count is inconsistent")
    if feature_list.get("ensemble_families") != list(expected_ensemble_families):
        raise MLArtifactIntegrityError("persisted feature-list ensemble families are inconsistent")
    if report.get("ensemble_models") != list(expected_ensemble_families):
        raise MLArtifactIntegrityError(
            "persisted validation-report ensemble families are inconsistent"
        )
    if report.get("all_detector_families") != list(expected_all_families):
        raise MLArtifactIntegrityError(
            "persisted validation-report detector families are inconsistent"
        )
    feature_explanation = feature_list.get("ensemble_explanation")
    report_explanation = report.get("ensemble_explanation")
    if not isinstance(feature_explanation, dict) or not isinstance(report_explanation, dict):
        raise MLArtifactIntegrityError(
            "persisted ensemble explanation contracts must be JSON objects"
        )
    if feature_explanation != report_explanation:
        raise MLArtifactIntegrityError(
            "persisted feature-list and validation ensemble explanations differ"
        )
    if feature_explanation.get("detector_families") != list(expected_ensemble_families):
        raise MLArtifactIntegrityError(
            "persisted ensemble explanation family order is inconsistent"
        )
    if (
        feature_explanation.get("target") != "ensemble_score"
        or feature_explanation.get("explanation_type") != "exact_additive_component_decomposition"
    ):
        raise MLArtifactIntegrityError("persisted ensemble explanation contract is invalid")
    shap_explanation = feature_list.get("shap_explanation")
    if not isinstance(shap_explanation, dict) or shap_explanation != report.get("shap_explanation"):
        raise MLArtifactIntegrityError("persisted SHAP explanation semantics are inconsistent")
    if shap_explanation != {
        "target": "rule_proxy_binary_label",
        "output_space": "raw_log_odds",
        "does_not_explain": "ensemble_score",
    }:
        raise MLArtifactIntegrityError("persisted SHAP explanation semantics are invalid")
    if report.get("IMPORTANT_metrics_are_faithfulness_to_rules_not_detection") is not True:
        raise MLArtifactIntegrityError("persisted validation-report lost the proxy-metric warning")
    if not isinstance(report.get("n_records"), int) or isinstance(report.get("n_records"), bool):
        raise MLArtifactIntegrityError("persisted validation-report record count is invalid")
    if not _finite_number(feature_list.get("shap_base_value")) or not _finite_number(
        report.get("shap_base_value")
    ):
        raise MLArtifactIntegrityError("persisted SHAP base value is not finite")

    dict_sections = {
        "cross_validation",
        "rule_only_baseline_and_confusion",
        "stability_by_ensemble_family",
        "inter_model_agreement",
        "rank_agreement_quantile_sensitivity",
        "deployed_score_feature_ablation",
        "model_election_sensitivity",
        "supervised_calibration",
        "ensemble_explanation",
        "shap_explanation",
    }
    invalid_sections = sorted(key for key in dict_sections if not isinstance(report.get(key), dict))
    if invalid_sections:
        raise MLArtifactIntegrityError(
            f"persisted validation-report sections are not objects: {invalid_sections}"
        )
    if set(report["stability_by_ensemble_family"]) != set(expected_ensemble_families):
        raise MLArtifactIntegrityError("persisted stability report does not cover the ensemble")

    expected_feature_ready = json_ready(dict(expected_feature_list))
    expected_report_ready = json_ready(dict(expected_validation_report))
    if feature_list != expected_feature_ready:
        raise MLArtifactIntegrityError("persisted feature-list differs from the generated payload")
    if report != expected_report_ready:
        raise MLArtifactIntegrityError(
            "persisted validation-report differs from the generated payload"
        )
    return feature_list, report


def _expected_shap_columns(features: Sequence[str]) -> list[str]:
    return ["ocid", "base_value", *features]


def _ocid_order_matches(shap: pd.DataFrame, gold: pd.DataFrame) -> tuple[bool, object]:
    if "ocid" not in shap or "ocid" not in gold:
        return False, "ocid column missing"
    observed = shap["ocid"].reset_index(drop=True)
    expected = gold["ocid"].reset_index(drop=True)
    if observed.isna().any() or expected.isna().any():
        return False, "null OCID"
    mismatches = int(
        sum(left != right for left, right in zip(observed.astype(str), expected.astype(str)))
    )
    mismatches += abs(len(observed) - len(expected))
    return mismatches == 0, {"mismatches": mismatches, "rows": len(observed)}


def shap_release_suite(
    shap: pd.DataFrame,
    gold: pd.DataFrame,
    expected_features: Sequence[str],
    expected_raw_output: np.ndarray | None = None,
) -> SuiteResult:
    """Validate persisted SHAP semantics against the persisted scored Gold table."""
    expected_columns = _expected_shap_columns(expected_features)
    value_columns = ["base_value", *expected_features]

    def columns_exact(frame: pd.DataFrame) -> tuple[bool, object]:
        observed = list(frame.columns)
        return observed == expected_columns, observed

    def rows_match(frame: pd.DataFrame) -> tuple[bool, object]:
        return len(frame) == len(gold), {"shap": len(frame), "gold": len(gold)}

    def ocids_match(frame: pd.DataFrame) -> tuple[bool, object]:
        return _ocid_order_matches(frame, gold)

    def numeric_values(frame: pd.DataFrame) -> tuple[bool, object]:
        if not set(value_columns).issubset(frame.columns):
            return False, "one or more expected value columns are missing"
        invalid = [column for column in value_columns if not is_numeric_dtype(frame[column].dtype)]
        return not invalid, invalid

    def finite_values(frame: pd.DataFrame) -> tuple[bool, object]:
        if not set(value_columns).issubset(frame.columns):
            return False, "one or more expected value columns are missing"
        try:
            values = frame[value_columns].to_numpy(dtype=np.float64, na_value=np.nan)
        except (TypeError, ValueError) as exc:
            return False, f"numeric conversion failed: {exc}"
        invalid = int((~np.isfinite(values)).sum())
        return invalid == 0, invalid

    def raw_output_additivity(frame: pd.DataFrame) -> tuple[bool, object]:
        if expected_raw_output is None:
            return False, "expected rule-proxy raw output was not supplied"
        if not set(value_columns).issubset(frame.columns):
            return False, "one or more expected SHAP value columns are missing"
        reconstructed = frame["base_value"].to_numpy(dtype=float) + frame[
            list(expected_features)
        ].sum(axis=1).to_numpy(dtype=float)
        expected = np.asarray(expected_raw_output, dtype=float)
        if expected.ndim != 1 or len(expected) != len(frame) or not np.isfinite(expected).all():
            return False, "expected rule-proxy raw output has invalid shape or values"
        max_delta = float(np.max(np.abs(reconstructed - expected)))
        return max_delta <= 1e-10, {
            "max_absolute_delta": max_delta,
            "target": "rule_proxy_binary_label",
            "output_space": "raw_log_odds",
            "does_not_explain": "ensemble_score",
        }

    expectations = [
        Expectation(
            "exact_columns",
            "SHAP columns and order exactly match ocid, base_value, and ML_FEATURES",
            columns_exact,
            Severity.ERROR,
        ),
        Expectation(
            "row_parity_with_gold",
            "SHAP contains exactly one row for every scored Gold row",
            rows_match,
            Severity.ERROR,
        ),
        Expectation(
            "exact_ocid_order",
            "SHAP OCIDs exactly match scored Gold values and row order",
            ocids_match,
            Severity.ERROR,
        ),
        Expectation(
            "numeric_shap_values",
            "base_value and every SHAP feature column use numeric dtypes",
            numeric_values,
            Severity.ERROR,
        ),
        Expectation(
            "finite_shap_values",
            "base_value and every SHAP value are finite",
            finite_values,
            Severity.ERROR,
        ),
    ]
    if expected_raw_output is not None:
        expectations.append(
            Expectation(
                "rule_proxy_raw_output_additivity",
                "SHAP base plus feature values reconstruct HGB rule-proxy raw log-odds",
                raw_output_additivity,
                Severity.ERROR,
            )
        )
    suite = ExpectationSuite(
        name="ml_shap_release",
        table="models.shap_values",
        expectations=expectations,
    )
    return run_suite(suite, shap)


def persisted_shap_release_payload(
    shap_path: Path,
    gold_path: Path,
    *,
    expected_features: Sequence[str],
    hgb_path: Path | None = None,
) -> dict[str, Any]:
    """Reload SHAP/Gold Parquets and return exact, artifact-bound DQ evidence."""
    shap = pd.read_parquet(shap_path)
    gold = pd.read_parquet(gold_path)
    expected_raw_output = None
    if hgb_path is not None:
        artifact = _load_joblib(hgb_path, "standalone HGB")
        if not isinstance(artifact, dict) or not hasattr(artifact.get("model"), "model"):
            raise MLArtifactIntegrityError("persisted standalone HGB cannot bind SHAP output")
        classifier = artifact["model"].model
        decision_function = getattr(classifier, "decision_function", None)
        if not callable(decision_function):
            raise MLArtifactIntegrityError("persisted HGB has no raw decision function")
        expected_raw_output = np.asarray(
            decision_function(to_model_matrix(gold[list(expected_features)])),
            dtype=float,
        )
    result = shap_release_suite(shap, gold, expected_features, expected_raw_output)
    payload = result.release_payload(shap_path, shap)
    payload["gold_reference_binding"] = {
        "artifact_path": gold_path.resolve().relative_to(paths.DATA.resolve()).as_posix(),
        "artifact_sha256": file_sha256(gold_path),
        "artifact_size_bytes": gold_path.stat().st_size,
        "rows": len(gold),
        "columns": gold.shape[1],
        "data_fingerprint": dataframe_fingerprint(gold),
    }
    payload["expected_columns"] = _expected_shap_columns(expected_features)
    payload["xai_semantics"] = {
        "target": "rule_proxy_binary_label",
        "output_space": "raw_log_odds",
        "does_not_explain": "ensemble_score",
    }
    return payload


def _load_joblib(path: Path, label: str) -> Any:
    try:
        return joblib.load(path)
    except Exception as exc:  # noqa: BLE001 - normalize serializer/load failures
        raise MLArtifactIntegrityError(f"persisted {label} joblib is not loadable: {path}") from exc


def _score_model(model: Any, X: pd.DataFrame, label: str) -> np.ndarray:
    score_method = getattr(model, "score", None)
    if not callable(score_method):
        raise MLArtifactIntegrityError(f"persisted {label} has no callable score method")
    fitted = getattr(model, "fitted", True)
    if fitted is not True:
        raise MLArtifactIntegrityError(f"persisted {label} is not fitted")
    try:
        scores = score_method(X)
    except Exception as exc:  # noqa: BLE001 - normalize arbitrary estimator failures
        raise MLArtifactIntegrityError(
            f"persisted {label} cannot score the current matrix"
        ) from exc
    if isinstance(scores, pd.Series) and not scores.index.equals(X.index):
        raise MLArtifactIntegrityError(f"persisted {label} changed score row order")
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 1 or len(values) != len(X):
        raise MLArtifactIntegrityError(f"persisted {label} returned an invalid score shape")
    if not np.isfinite(values).all():
        raise MLArtifactIntegrityError(f"persisted {label} returned non-finite scores")
    return values


def _assert_scores_match(
    observed: np.ndarray,
    expected: pd.Series,
    label: str,
    *,
    rtol: float,
    atol: float,
) -> None:
    expected_values = pd.to_numeric(expected, errors="raise").to_numpy(dtype=np.float64)
    if not np.isfinite(expected_values).all():
        raise MLArtifactIntegrityError(f"persisted scored table has non-finite {label} values")
    if not np.allclose(observed, expected_values, rtol=rtol, atol=atol):
        max_delta = float(np.max(np.abs(observed - expected_values)))
        raise MLArtifactIntegrityError(
            f"persisted {label} scores do not reproduce the scored table (max_delta={max_delta})"
        )


def validate_persisted_model_artifacts(
    bundle_path: Path,
    hgb_path: Path,
    scored_gold_path: Path,
    *,
    X: pd.DataFrame,
    expected_ocids: pd.Series,
    expected_provenance: Mapping[str, Any],
    expected_families: Sequence[str],
    expected_ensemble_families: Sequence[str],
    rtol: float = 1e-12,
    atol: float = 1e-12,
) -> None:
    """Reload both joblibs and reproduce every persisted detector/HGB score."""
    bundle = _load_joblib(bundle_path, "champion-model bundle")
    standalone = _load_joblib(hgb_path, "standalone HGB")
    if not isinstance(bundle, dict) or set(bundle) != {
        "schema_version",
        "provenance",
        "scorers",
        "explainer",
        "ensemble_families",
    }:
        raise MLArtifactIntegrityError("persisted champion-model bundle schema is invalid")
    if bundle.get("schema_version") != MODEL_BUNDLE_SCHEMA_VERSION:
        raise MLArtifactIntegrityError("unsupported persisted champion-model bundle schema")
    if bundle.get("provenance") != dict(expected_provenance):
        raise MLArtifactIntegrityError("persisted champion-model bundle provenance is stale")
    if not isinstance(standalone, dict) or set(standalone) != {
        "schema_version",
        "family",
        "provenance",
        "model",
    }:
        raise MLArtifactIntegrityError("persisted standalone HGB schema is invalid")
    if standalone.get("schema_version") != HGB_ARTIFACT_SCHEMA_VERSION:
        raise MLArtifactIntegrityError("unsupported persisted standalone HGB schema")
    if standalone.get("family") != "hgb":
        raise MLArtifactIntegrityError("persisted standalone HGB family is invalid")
    if standalone.get("provenance") != dict(expected_provenance):
        raise MLArtifactIntegrityError("persisted standalone HGB provenance is stale")

    scorers = bundle.get("scorers")
    expected_family_set = set(expected_families)
    if not isinstance(scorers, dict) or set(scorers) != expected_family_set:
        raise MLArtifactIntegrityError("persisted detector bundle family coverage is invalid")
    if bundle.get("ensemble_families") != list(expected_ensemble_families):
        raise MLArtifactIntegrityError("persisted detector bundle ensemble families are invalid")
    if not set(expected_ensemble_families).issubset(expected_family_set):
        raise MLArtifactIntegrityError("declared ensemble is not a subset of detector families")

    scored = pd.read_parquet(scored_gold_path)
    observed_ocids = scored.get("ocid")
    if observed_ocids is None:
        raise MLArtifactIntegrityError("persisted scored table has no OCID column")
    expected_ocids = expected_ocids.reset_index(drop=True)
    observed_ocids = observed_ocids.reset_index(drop=True)
    if (
        len(observed_ocids) != len(expected_ocids)
        or observed_ocids.isna().any()
        or expected_ocids.isna().any()
        or observed_ocids.astype(str).tolist() != expected_ocids.astype(str).tolist()
    ):
        raise MLArtifactIntegrityError("persisted scored table OCID order changed")

    for family in expected_families:
        column = f"{family}_score"
        if column not in scored:
            raise MLArtifactIntegrityError(f"persisted scored table is missing {column}")
        reproduced = _score_model(scorers[family], X, f"detector {family}")
        _assert_scores_match(reproduced, scored[column], column, rtol=rtol, atol=atol)

    if "hgb_score" not in scored:
        raise MLArtifactIntegrityError("persisted scored table is missing hgb_score")
    bundle_hgb_scores = _score_model(bundle.get("explainer"), X, "bundle HGB explainer")
    standalone_hgb_scores = _score_model(standalone.get("model"), X, "standalone HGB")
    _assert_scores_match(bundle_hgb_scores, scored["hgb_score"], "hgb_score", rtol=rtol, atol=atol)
    _assert_scores_match(
        standalone_hgb_scores,
        scored["hgb_score"],
        "standalone hgb_score",
        rtol=rtol,
        atol=atol,
    )

    cfg = settings()
    try:
        composition = compose_hybrid_ensemble(
            scored,
            expected_ensemble_families,
            flag_quantile=cfg.benchmark_flag_quantile,
            minimum_models_agreeing=cfg.minimum_models_agreeing_for_high_confidence,
        )
    except (TypeError, ValueError, RuntimeError) as exc:
        raise MLArtifactIntegrityError(
            "persisted scored table cannot reconstruct the deployed ensemble"
        ) from exc
    for column in composition.detector_rank_columns:
        if column not in scored:
            raise MLArtifactIntegrityError(
                f"persisted scored table is missing XAI rank component {column}"
            )
        _assert_scores_match(
            composition.detector_ranks[column].to_numpy(dtype=np.float64),
            scored[column],
            column,
            rtol=rtol,
            atol=atol,
        )
    _assert_scores_match(
        composition.ensemble_score.to_numpy(dtype=np.float64),
        scored["ensemble_score"],
        "ensemble_score",
        rtol=rtol,
        atol=atol,
    )
    for column, expected in {
        "model_agreement_count": composition.model_agreement_count,
        "high_confidence": composition.high_confidence,
    }.items():
        if column not in scored:
            raise MLArtifactIntegrityError(f"persisted scored table is missing {column}")
        observed = pd.to_numeric(scored[column], errors="coerce")
        if observed.isna().any() or not np.array_equal(
            observed.to_numpy(dtype=np.int64),
            expected.to_numpy(dtype=np.int64),
        ):
            raise MLArtifactIntegrityError(
                f"persisted {column} does not reproduce the ensemble definition"
            )
