# ADR-0001: Medallion architecture (bronze / silver / gold)

* **Status:** Accepted
* **Date:** 2026-04
* **Deciders:** thesis author + supervisor

## Context

We are ingesting an external OCDS publication, transforming it
multiple times, applying ML models, and serving an interactive
dashboard. We need a layout that:

* keeps the raw input untouched for re-runs and audits,
* separates *cleaning* from *modelling*,
* makes the consumption layer (Streamlit) fast,
* is recognisable to other data engineers who join the project later.

## Decision

Adopt the **medallion architecture** popularised by Databricks:

* **Bronze** — raw OCDS JSONL, exactly as published. No edits.
* **Silver** — typed, normalised, validated Parquet tables (`tenders`
  and `awards`). One row per business entity (a tender or an award).
* **Gold** — analytics-ready Parquet tables. The gold transformation writes
  immutable `tender_features` (one row per tender, with derived features and
  rule flags) plus `supplier_summary`, `procuring_entity_summary`, and
  `monthly_metrics`. Benchmark reads `tender_features`; ML then writes the
  scored `tender_summary` as its sole canonical producer.

DQ artifacts and lineage sidecars are siblings of the layers, under
`data/dq/` and `data/_lineage/`.

## Consequences

**Positive:**

* Rebuildability: analytical tables are deterministic functions of declared
  inputs, parameters, and fixed seeds.
* Disaster recovery: deleting silver/gold/models and rerunning the pipeline
  reproduces the analytical contents under the same environment. Run IDs,
  timestamps, durations, logs, and serialized bytes may legitimately differ.
* Familiar terminology — easy onboarding for any DE.
* The Streamlit app reads the scored `tender_summary` and descriptive
  summaries from gold, so it is fast.

**Negative:**

* Some duplication: silver columns reappear in gold. This is acceptable at
  the current scale of about 75k tenders.
* Multi-step rebuild needed when changing schema in silver — but this
  is what the Pandera/Pydantic contracts catch immediately.

## Alternatives considered

* **Single flat table** — rejected; couples cleaning and modelling.
* **Star schema in Postgres** — rejected; overkill for thesis-scale data,
  and the Streamlit app does not benefit from joins.
* **Raw + transformed only (no gold)** — rejected; pre-aggregated
  tables (supplier/entity/monthly) are essential for the dashboard
  responsiveness and natural for stakeholder queries.

## Related

* ADR-0003 — Parquet as storage format.
* ADR-0006 — Airflow as production orchestrator.
