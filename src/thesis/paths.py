"""Project paths derived from :mod:`thesis.config`.

A *single source of truth*: every script, notebook, and Streamlit page
imports from here. Path locations can be overridden by setting
``THESIS_DATA_DIR`` in the environment.
"""

from __future__ import annotations

from pathlib import Path

from .config import settings

_cfg = settings()

# ------------------------------------------------------------- top-level
ROOT: Path = _cfg.project_root
DATA: Path = _cfg.data_dir
DOCS: Path = _cfg.docs_dir

# ------------------------------------------------------------- layers
BRONZE: Path = DATA / "raw"
SILVER: Path = DATA / "silver"
GOLD: Path = DATA / "gold"
DQ: Path = DATA / "dq"
MODELS: Path = DATA / "models"
LINEAGE: Path = DATA / "_lineage"

# ------------------------------------------------------------- bronze artifacts
RAW_JSONL: Path = BRONZE / "kosovo_ocds.jsonl"
RAW_GZ: Path = BRONZE / "kosovo_ocds.jsonl.gz"
BRONZE_RELEASE: Path = BRONZE / "bronze.release.json"

# ------------------------------------------------------------- silver artifacts
SILVER_TENDERS: Path = SILVER / "tenders.parquet"
SILVER_AWARDS: Path = SILVER / "awards.parquet"
SILVER_RELEASE: Path = SILVER / "silver.release.json"
SILVER_TENDERS_RELEASE_DQ: Path = DQ / "silver_tenders.release.dq.json"
SILVER_AWARDS_RELEASE_DQ: Path = DQ / "silver_awards.release.dq.json"

# ------------------------------------------------------------- gold artifacts
GOLD_FEATURES: Path = GOLD / "tender_features.parquet"
GOLD_TENDERS: Path = GOLD / "tender_summary.parquet"
GOLD_SUPPLIERS: Path = GOLD / "supplier_summary.parquet"
GOLD_ENTITIES: Path = GOLD / "procuring_entity_summary.parquet"
GOLD_MONTHLY: Path = GOLD / "monthly_metrics.parquet"
GOLD_RELEASE: Path = GOLD / "gold.release.json"
GOLD_FEATURES_RELEASE_DQ: Path = DQ / "gold_tender_features.release.dq.json"
GOLD_SUPPLIERS_RELEASE_DQ: Path = DQ / "gold_supplier_summary.release.dq.json"
GOLD_ENTITIES_RELEASE_DQ: Path = DQ / "gold_entity_summary.release.dq.json"
GOLD_MONTHLY_RELEASE_DQ: Path = DQ / "gold_monthly_metrics.release.dq.json"

# ------------------------------------------------------------- model artifacts
ISO_FOREST: Path = MODELS / "isolation_forest.joblib"
LOF_MODEL: Path = MODELS / "lof.joblib"
ELLIPTIC_ENVELOPE: Path = MODELS / "elliptic_envelope.joblib"
OCSVM_MODEL: Path = MODELS / "one_class_svm.joblib"
HGB_MODEL: Path = MODELS / "hgb_classifier.joblib"
CHAMPION_MODELS: Path = MODELS / "champion_models.joblib"
SHAP_VALUES: Path = MODELS / "shap_values.parquet"
FEATURE_LIST: Path = MODELS / "feature_list.json"
MODEL_VALIDATION: Path = MODELS / "validation_report.json"
ML_RELEASE: Path = MODELS / "ml.release.json"
GOLD_TENDERS_RELEASE_DQ: Path = DQ / "gold_tender_summary.release.dq.json"
SHAP_VALUES_RELEASE_DQ: Path = DQ / "ml_shap_values.release.dq.json"

# ------------------------------------------------------------- benchmark artifacts
BENCHMARK_DIR: Path = MODELS / "benchmark"
BENCHMARK_RESULTS: Path = BENCHMARK_DIR / "results.jsonl"
BENCHMARK_LEADERBOARD: Path = BENCHMARK_DIR / "leaderboard.parquet"
BENCHMARK_LEADERBOARD_MD: Path = BENCHMARK_DIR / "leaderboard.md"
CHAMPIONS: Path = BENCHMARK_DIR / "champions.json"
BENCHMARK_RELEASE: Path = BENCHMARK_DIR / "benchmark.release.json"
BENCHMARK_RELEASE_DQ: Path = DQ / "benchmark.release.dq.json"


def ensure_dirs() -> None:
    """Create every layer directory. Safe to call repeatedly."""
    for d in (BRONZE, SILVER, GOLD, DQ, MODELS, LINEAGE, DOCS, BENCHMARK_DIR):
        d.mkdir(parents=True, exist_ok=True)
