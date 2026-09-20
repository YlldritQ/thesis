"""Generation-validated, type-stable readers for every artifact.

Library-level no-argument caching is deliberately avoided: it can return a
prior generation after an atomic manifest swap. Streamlit applies its own
cache keyed by a validated release-manifest SHA.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pandas as pd

from .. import paths
from ..jsonutil import loads_json
from ..release import (
    ReleaseIntegrityError,
    read_released_json,
    read_released_parquet,
    validate_canonical_release,
)


# =====================================================================
#  silver
# =====================================================================
def load_silver_tenders() -> pd.DataFrame:
    return read_released_parquet(
        paths.SILVER_RELEASE,
        paths.SILVER_TENDERS,
        expected_stage="silver",
    )


def load_silver_awards() -> pd.DataFrame:
    return read_released_parquet(
        paths.SILVER_RELEASE,
        paths.SILVER_AWARDS,
        expected_stage="silver",
    )


def load_silver_bundle() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load both Silver tables under one before/after generation token."""
    before = validate_canonical_release(
        "silver",
        require_current_provenance=True,
    )
    tenders = pd.read_parquet(paths.SILVER_TENDERS)
    awards = pd.read_parquet(paths.SILVER_AWARDS)
    after = validate_canonical_release(
        "silver",
        require_current_provenance=True,
    )
    if before.manifest_sha256 != after.manifest_sha256:
        raise ReleaseIntegrityError("silver release changed while reading its bundle")
    return tenders, awards


# =====================================================================
#  gold
# =====================================================================
def load_gold_features() -> pd.DataFrame:
    """Load the immutable rule/feature table produced by the gold stage."""
    return read_released_parquet(
        paths.GOLD_RELEASE,
        paths.GOLD_FEATURES,
        expected_stage="gold",
    )


def load_gold_tenders() -> pd.DataFrame:
    """Load the scored canonical tender table produced by the ML stage."""
    return read_released_parquet(
        paths.ML_RELEASE,
        paths.GOLD_TENDERS,
        expected_stage="ml",
    )


def load_gold_suppliers() -> pd.DataFrame:
    return read_released_parquet(
        paths.GOLD_RELEASE,
        paths.GOLD_SUPPLIERS,
        expected_stage="gold",
    )


def load_gold_entities() -> pd.DataFrame:
    return read_released_parquet(
        paths.GOLD_RELEASE,
        paths.GOLD_ENTITIES,
        expected_stage="gold",
    )


def load_monthly() -> pd.DataFrame:
    return read_released_parquet(
        paths.GOLD_RELEASE,
        paths.GOLD_MONTHLY,
        expected_stage="gold",
    )


def load_shap_values() -> pd.DataFrame:
    return read_released_parquet(
        paths.ML_RELEASE,
        paths.SHAP_VALUES,
        expected_stage="ml",
    )


def load_dashboard_bundle(
    *,
    include_shap: bool = False,
    include_model_metadata: bool = False,
) -> dict[str, Any]:
    """Load cross-stage dashboard tables under one generation guard.

    Pages combine the ML-scored tender table with Silver award rows and Gold
    summaries. Independent reads can each be valid yet belong to different
    generations if publication occurs between calls. Capture every involved
    release token before reading and require the same tokens afterwards.
    """
    stages = ("silver", "gold", "ml")
    before = {
        stage: validate_canonical_release(stage, require_current_provenance=True)
        for stage in stages
    }
    bundle = {
        "gold": pd.read_parquet(paths.GOLD_TENDERS),
        "awards": pd.read_parquet(paths.SILVER_AWARDS),
        "suppliers": pd.read_parquet(paths.GOLD_SUPPLIERS),
        "entities": pd.read_parquet(paths.GOLD_ENTITIES),
    }
    if include_shap:
        bundle["shap"] = pd.read_parquet(paths.SHAP_VALUES)
    if include_model_metadata:
        feature_metadata = loads_json(paths.FEATURE_LIST.read_text(encoding="utf-8"))
        if not isinstance(feature_metadata, dict):
            raise ReleaseIntegrityError("released feature metadata must contain an object")
        bundle["feature_metadata"] = feature_metadata
    after = {
        stage: validate_canonical_release(stage, require_current_provenance=True)
        for stage in stages
    }
    changed = [
        stage for stage in stages if before[stage].manifest_sha256 != after[stage].manifest_sha256
    ]
    if changed:
        raise ReleaseIntegrityError(
            "release chain changed while reading dashboard bundle: " + ", ".join(changed)
        )
    return bundle


def load_benchmark_bundle() -> tuple[pd.DataFrame, dict]:
    """Load leaderboard and champions from the exact same release generation."""
    before = validate_canonical_release(
        "benchmark",
        require_current_provenance=True,
    )
    leaderboard = pd.read_parquet(paths.BENCHMARK_LEADERBOARD)
    champions = loads_json(paths.CHAMPIONS.read_text())
    if not isinstance(champions, dict):
        raise ReleaseIntegrityError("released champions JSON must contain an object")
    after = validate_canonical_release(
        "benchmark",
        require_current_provenance=True,
    )
    if before.manifest_sha256 != after.manifest_sha256:
        raise ReleaseIntegrityError("benchmark release changed while reading its bundle")
    return leaderboard, champions


def load_benchmark_leaderboard() -> pd.DataFrame:
    """Load the leaderboard from one validated full benchmark release."""
    return load_benchmark_bundle()[0]


def load_champions() -> dict:
    """Load model-selection champions from a validated benchmark release."""
    return load_benchmark_bundle()[1]


# =====================================================================
#  bronze (rare; mostly for spot-checks)
# =====================================================================
def iter_raw_records() -> Iterator[dict]:
    """Stream the raw OCDS JSONL one record at a time."""
    before = validate_canonical_release(
        "bronze",
        require_current_provenance=True,
    )
    try:
        with open(paths.RAW_JSONL) as f:
            for line in f:
                value = loads_json(line)
                if not isinstance(value, dict):
                    raise ValueError("raw JSONL record must contain an object")
                yield value
    finally:
        after = validate_canonical_release(
            "bronze",
            require_current_provenance=True,
        )
        if before.manifest_sha256 != after.manifest_sha256:
            raise ReleaseIntegrityError("bronze release changed while streaming raw records")


def get_raw_record(ocid: str) -> dict | None:
    """Return one record by OCID. Linear scan — slow for repeats."""
    for rec in iter_raw_records():
        if rec.get("ocid") == ocid:
            return rec
    return None


# =====================================================================
#  dq
# =====================================================================
def load_dq_csv(name: str) -> pd.DataFrame:
    """Load any CSV from ``data/dq/``."""
    return pd.read_csv(paths.DQ / name)


def load_validation_report() -> dict:
    """Load the JSON report produced by :mod:`thesis.pipeline.ml`."""
    if not paths.MODEL_VALIDATION.exists() and not paths.ML_RELEASE.exists():
        return {}
    return read_released_json(
        paths.ML_RELEASE,
        paths.MODEL_VALIDATION,
        expected_stage="ml",
    )


def load_feature_metadata() -> dict:
    """Load the ML-bound feature and exact ensemble-explanation contract."""
    return read_released_json(
        paths.ML_RELEASE,
        paths.FEATURE_LIST,
        expected_stage="ml",
    )
