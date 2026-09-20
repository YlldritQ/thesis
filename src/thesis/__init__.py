"""Kosovo Public Procurement — heuristic screening and anomaly ranking.

A senior-data-engineering reference pipeline:

* Bronze → Silver → Gold medallion architecture (Parquet)
* Multi-model exploratory ranking (rule layer + elected unsupervised families)
* Supervised rule-proxy surrogate used only for SHAP attribution
* Contextual comparison scores (within-entity, category, and method)
* Rule-proxy agreement, resampling stability, and score diagnostics
* Pydantic data contracts + structured logging + per-artifact lineage sidecars
* Streamlit demo with SHAP explanations of a rule-proxy surrogate

Entrypoints:
    `from thesis import pipeline`        — compose pipeline tasks programmatically
    `python -m thesis ...`               — Typer CLI
    `streamlit run streamlit_app/Home.py`— interactive dashboard

This is a research/thesis project. Anomaly flags are signals for further
investigation, **not** evidence of fraud. See ``docs/responsible_use.md``.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("kosovo-procurement-thesis")
except PackageNotFoundError:
    __version__ = "1.3.0+local"

__all__ = ["__version__"]
