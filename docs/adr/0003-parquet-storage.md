# ADR-0003: Parquet as the storage format

* **Status:** Accepted
* **Date:** 2026-04

## Context

Every layer needs a persistent storage format. Options:

* CSV — universal but lossy on dtypes; slow to load.
* Parquet — columnar, compressed, dtype-preserving.
* DuckDB / SQLite — embedded SQL.
* Postgres — full RDBMS.
* Iceberg / Delta — table formats over Parquet.

## Decision

Use **Parquet** for tabular silver/gold artifacts and tabular model outputs
such as SHAP values and the benchmark leaderboard.

DQ run evidence uses JSON plus human-readable Markdown. The only CSV is the
manual-audit worksheet, which reviewers edit by hand.

Lineage sidecars use JSON (one per Parquet file, plus chronological
copy under `data/_lineage/`).

Fitted models are persisted with `joblib`; small manifests and validation
reports use JSON.

## Consequences

**Positive:**

* `pandas.read_parquet` loads the roughly 75k-row gold tables quickly enough
  for interactive use without a database service.
* Strong column compression (≈ 5–10× vs CSV).
* Dtypes are preserved — no `release_date` becomes `object` after
  round-trip.
* Streamlit's `@st.cache_data` keeps the table hot; subsequent renders
  are instant.
* Future-proof: dropping DuckDB / Polars in front of these files would
  not require pipeline changes.

**Negative:**

* Less human-friendly to peek at — but the DQ Markdown reports and the
  lineage sidecars cover that need.
* Slightly higher memory footprint at write time (Arrow buffers).

## Alternatives considered

* **DuckDB** — would be excellent for this scale, but adds a dependency
  and a binary to manage. Easy to bolt on later.
* **Postgres** — overkill; would require a server, schema migrations,
  connection management. Reserved for production deployments at scale.
* **Iceberg/Delta** — designed for >100 GB tables and concurrent
  writers; useless at our scale.
