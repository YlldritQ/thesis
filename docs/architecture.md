# Architecture

## Scope

The submitted system is a **static retrospective snapshot** of Open
Contracting Partnership Publication 115. It contains 75,710 procurement
records and 118 populated months out of the 121-month calendar span from
2016-03 through 2026-03. It is not a live monitor or a claim to contain
every procurement procedure conducted in Kosovo.

## Pipeline diagram

```text
Open Contracting Partnership — Publication 115
                              |
                              v
python -m thesis pipeline bronze
  data/raw/kosovo_ocds.jsonl                         75,710 records
                              |
                              v
python -m thesis pipeline silver  + schema contracts / DQ checks
  data/silver/tenders.parquet                        75,710 rows
  data/silver/awards.parquet                         62,129 rows post-dedup
                              |
                              v
python -m thesis pipeline gold
  data/gold/tender_features.parquet                   tender facts + rules
  data/gold/{supplier,procuring_entity,monthly}_*.parquet
                              |
                              v
python -m thesis pipeline benchmark
  leaderboard + champions
                              |
                              v
python -m thesis pipeline ml
  data/gold/tender_summary.parquet                    ML-scored research table
  persisted detector ranks + exact ensemble XAI contract
  rule-proxy surrogate + separately labelled SHAP
                              |
                              v
                 Streamlit research dashboard (static snapshot)
```

## Medallion layers

### Bronze — preserved source snapshot

* **Source format:** OCDS JSONL (Open Contracting Data Standard 1.1).
* **Volume:** 23 MB compressed, 206 MB extracted, 75,710 records.
* **Coverage:** 2016-03 → 2026-03; 118 populated months out of 121.
* **Storage:** `data/raw/kosovo_ocds.jsonl` plus the downloaded gzip.
* **Implementation:** `src/thesis/pipeline/bronze.py`, exposed through the
  `thesis pipeline bronze` CLI command.

### Silver — typed, normalised, validated

* Produced by `src/thesis/pipeline/silver.py` through
  `thesis pipeline silver`.
* Two relational tables joined by `ocid` / `tender_id`.
* `tenders.parquet` contains 75,710 rows.
* `awards.parquet` contains **62,129 post-dedup rows**. The 65,721 figure
  is the raw pre-dedup award-object count and must not label silver output.
* Numeric columns have explicit units (`*_eur`, `*_days`) and datetimes
  are timezone-aware UTC.
* Because awards contain a lot title rather than a shared lot identifier,
  `award_lot_match_status` exposes exact-unique, exact-ambiguous, unmatched,
  and missing-title cases; no translated-title join is inferred.
* Pydantic models in `src/thesis/domain/contracts.py` and DataFrame schemas
  in `src/thesis/domain/schemas.py` form the data contract.

### Gold — analytics-ready snapshot

* Produced by `src/thesis/pipeline/gold.py` from the silver tables.
* `tender_features` is the immutable feature/rule artifact consumed by the
  benchmark and ML stages. The gold stage never writes `tender_summary`.
* After benchmark selection, `src/thesis/pipeline/ml.py` is the sole writer of
  the scored `tender_summary`, which is the central wide dashboard table.
* `supplier_summary`, `procuring_entity_summary`, and `monthly_metrics`
  are pre-aggregated for the static dashboard.
* Supplier aggregation publishes three identity sensitivities: business ID
  then normalised name; business ID then source party ID/UID then name; and
  business-ID-only. Sentinel IDs are null-normalised while their raw values
  remain in Silver. Source party IDs are publication identities, not verified
  legal IDs. Concentration statistics still require a relevant-market
  definition; a single national HHI is not a valid headline measure.
* The terminal source procedure code is retained in Silver and mapped using
  official Regulation 001/2022, Article 12.13, together with official amending
  Regulation 002/2024. A PPRC-hosted non-official consolidation renumbers the
  mapping as Article 12.3 and is used only as a reading aid. The mapping includes
  code 3 design contests and code 6 price quotations; the predecessor 2016 Rules
  annex corroborates codes 1--7 for the historical records. Missing bidder
  publication remains a nullable count plus an explicit observation flag.

### DQ — run evidence

* `src/thesis/dq/` contains the expectation framework and suites.
* DQ JSON/Markdown files describe the particular run that produced them.
  They are run evidence, not an independent outcome-validation dataset.
* A failed `ERROR` expectation always blocks canonical publication. Failed
  `WARNING` expectations are recorded and block only when
  `THESIS_FAIL_FAST_ON_DQ=true`.

### Benchmark and ML — exploratory ranking

* `src/thesis/pipeline/benchmark.py` evaluates 23 unsupervised and 12
  supervised configurations. Its atomic release binds the strict full JSONL
  checkpoint, leaderboard, champion bundle, exact relevant implementation
  hashes, and a passed semantic completeness/re-election check. Quick-mode
  checkpoints are separate and non-deployable.
* `src/thesis/pipeline/ml.py` fits the detector families, produces
  and persists snapshot-relative ranks, publishes their exact additive XAI
  contract, trains the HistGradientBoosting rule surrogate, computes separately
  labelled rule-proxy SHAP values, and publishes the scored research snapshot.
* The supervised metrics measure faithfulness to deterministic rule labels.
  They are not detection-performance or temporal-generalisation evidence.
* `high_confidence` uses the released metadata's minimum-agreement and rank
  quantile (currently 3 of 4 champion detectors in the current-batch top 5%);
  it is rank agreement, not a calibrated probability. The validation artifact reports membership
  sensitivity at q=0.90/0.95/0.99 and deployed-model feature-subset refits as
  rank-stability diagnostics only.

## Why Parquet, not Postgres / DuckDB / Spark?

For a thesis-scale dataset (about 75 k rows and tens of columns), Parquet
is a practical fit:

* Fast columnar reads with pandas/pyarrow.
* Streamlit-friendly caching in memory.
* Portable, versionable release artifacts.
* Straightforward migration to DuckDB or Polars if the data grows.

The submitted package uses source-change detection, atomic single-file writes,
and manifest-last stage publication so static readers can reject partial or
mixed releases. A future live service would still need transactional storage,
frozen/versioned peer statistics, online score calibration, access controls,
and operational monitoring. This package makes no production-monitoring claim.

Each canonical stage has an exact input/artifact/DQ-check contract. Manifests
bind relative logical paths, full file hashes/sizes, Parquet shape/schema,
release-owned DQ fingerprints, source/config/runtime provenance, and the exact
upstream manifest bytes. Coupled tables are loaded under one before/after
manifest token; Streamlit caches are keyed by that validated token. The
single-writer lock prevents two canonical publishers from interleaving. These
controls make mixed generations fail closed, but they are not a substitute for
transactional, continuously available publication in a live multi-reader
service.

## Rebuild contract

The pipeline is designed to rebuild derived artifacts from the same bronze
snapshot. For a defensible release:

1. Keep the bronze snapshot and model/data fingerprints with the release.
2. Rerun benchmark → ML → reports after any rule or feature change.
3. Treat scores and detector percentiles as relative to that complete batch,
   not as stable online scores for isolated requests.
4. Regenerate and verify documentation/UI numbers after the final build.

## Schema versioning

The Pydantic models in `src/thesis/domain/contracts.py` and schemas in
`src/thesis/domain/schemas.py` are the data contract. Whenever a silver
column changes:

1. Update the model and DataFrame schema.
2. Update `src/thesis/pipeline/silver.py`.
3. Update tests.
4. Rebuild all downstream artifacts and documentation.

Downstream code imports shared paths and typed readers from
`src/thesis/io/`; schema changes still require a complete downstream
regeneration.
