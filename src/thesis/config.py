"""Application configuration via Pydantic Settings.

12-factor compliant: every value can be overridden by environment variable
(prefix ``THESIS_``) or by ``.env`` in the project root. Default values are
production-safe.

Example::

    from thesis.config import settings
    raw_dir = settings.data_dir / "raw"
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT: Path = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Project-wide configuration.

    Override any field via env var, e.g. ``THESIS_LOG_LEVEL=DEBUG``.
    """

    model_config = SettingsConfigDict(
        env_prefix="THESIS_",
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----------------------------------------------------------- paths
    project_root: Path = ROOT
    data_dir: Path = ROOT / "data"
    docs_dir: Path = ROOT / "docs"

    # ----------------------------------------------------------- logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["console", "json"] = "console"
    pipeline_run_id: str | None = None  # auto-generated per run if absent

    # ---------------------------------------------------------- ingestion
    ocds_publication_url: str = (
        "https://data.open-contracting.org/en/publication/115/download?name=full.jsonl.gz"
    )
    ocds_request_timeout_s: int = 600
    ocds_chunk_bytes: int = 1 << 20  # 1 MiB

    # ---------------------------------------------------- model parameters
    random_seed: int = 7
    iso_forest_n_estimators: int = 300
    iso_forest_contamination: float = 0.05
    lof_n_neighbors: int = 30
    lof_contamination: float = 0.05
    elliptic_envelope_contamination: float = 0.05
    ocsvm_nu: float = 0.05
    ocsvm_subsample_size: int = 10_000  # OCSVM is O(n²); subsample
    hgb_n_estimators: int = 300
    hgb_max_depth: int = 4
    cv_folds: int = 5
    bootstrap_samples: int = 20
    rule_label_threshold: float = 0.4

    # ------------------------------------------------ benchmark
    benchmark_bootstrap_runs: int = 4  # stability re-fits per config
    benchmark_extra_seeds: int = 2  # extra refits for stochastic families
    benchmark_supervised_seeds: int = 2  # CV repetitions with different seeds
    benchmark_cv_folds: int = 5
    # Retrospective date-split rule-proxy diagnostic; not temporal validation.
    benchmark_oot_train_max_year: int = 2023
    benchmark_flag_quantile: float = 0.95  # top-5 % = flag set for stability
    benchmark_top_k_families: int = 4  # families in the final ensemble
    benchmark_precision_at: int = 500

    # ------------------------------------------------ anomaly thresholds
    rule_score_review_threshold: float = 0.5  # author-selected review queue
    rule_score_priority_threshold: float = 0.7  # author-selected sensitivity cut
    ensemble_score_review_threshold: float = 0.5
    minimum_models_agreeing_for_high_confidence: int = 3

    # ------------------------------------------------ ui
    streamlit_default_page_size: int = 500
    streamlit_max_search_results: int = 1000

    # ------------------------------------------------ misc
    # ERROR expectations always block; this additionally makes warnings and
    # sampled typed-contract warnings blocking.
    fail_fast_on_dq: bool = False
    write_lineage_sidecars: bool = True

    @field_validator("data_dir", "docs_dir", "project_root", mode="before")
    @classmethod
    def _expand(cls, v: object) -> Path:
        if isinstance(v, str):
            return Path(v).expanduser().resolve()
        if isinstance(v, Path):
            return v.expanduser().resolve()
        return v  # type: ignore[return-value]


# Singleton accessor
_settings: Settings | None = None


def settings() -> Settings:
    """Lazily-instantiated singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings_for_tests() -> None:
    """Reset the cached singleton so tests can re-read env vars."""
    global _settings
    _settings = None
