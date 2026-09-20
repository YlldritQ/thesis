# THESIS REMEDIATION R3

> **Historical R3 remediation baseline (superseded for current release facts).**
> This document describes the remediation state before the XAI alignment
> extension. Its root-cause and finding history remain useful, but its release
> ID, implementation fingerprint, scored-table shape, hashes, and XAI status are
> not the current generation. See
> [`THESIS_XAI_ALIGNMENT.md`](THESIS_XAI_ALIGNMENT.md) and the live manifests
> for the current source-matched release.

**Project root:** `/Users/ylldrit/Desktop/thesis`  
**Remediation period:** 2026-07-18 to 2026-07-19  
**Final status:** source-matched canonical releases, audit metadata, OSHP withdrawal status and generated findings are complete and independently hash-checked. Full pytest, Ruff, formatting, mypy, dependency, release/DQ, strict-JSON, notebook, active-surface stale-claim and patched Docker portability/health gates pass. The final non-implementer contradiction audit passes.

> **Technical remediation is complete for the narrowed scope.** The final coherent release is `run-20260719T103232-2fe4b69e`; every declared release hash, DQ, quality and Docker reader/health check has been verified and the non-implementer audit passes. Irreducible evidence limitations remain explicitly deferred.

## Remediation outcome

The remediation corrected the actionable P0–P2 defects found by the independent R3 audit without inventing human labels, external outcomes, legal conclusions, missing URLs or entity matches. The major repairs are:

- code-first procurement procedure semantics with an explicit design-contest subtype;
- identity-aware award deduplication and multiple supplier-identity/coverage/HHI sensitivities;
- honest nullable bidder publication, rather than converting missing tenderers to zero;
- exact award-stage wording, explicit tender/lot grain and zero-weight legal/data-quality diagnostics;
- manual-review URL status, provenance hashes and label-preserving forced regeneration;
- manifest-last Bronze, Silver, Gold, Benchmark and ML release contracts with portable paths, source/config/runtime fingerprints and generation-guarded readers;
- persisted semantic DQ for Silver referential integrity, Gold source-total summaries, benchmark election and ML model/SHAP/JSON/scored artifacts;
- strict JSON and persisted-Parquet schema lineage;
- implementation-bound benchmark checkpoints, isolated WIP/quick/canonical evidence, semantic champion re-election and model-selection sensitivity;
- float-NaN conversion at every sklearn/SHAP boundary for nullable pandas numerics;
- frozen uv 0.11.28 dependency installation in CI/Docker and an actual Docker HEALTHCHECK wait;
- cautious generated-report, notebook and dashboard language that distinguishes descriptive statistics, heuristic rules, anomaly ranking, human review and external validation.

The final data corrections are 62,128→62,129 canonical awards, +EUR7,200 recorded award value, 9,427→9,940 supplier-summary rows, 291 explicit design contests, 39,940→39,650 standard-open tenders, 39→38 restricted tenders, and 6,107 “zero bidders”→6,107 missing bidder publication with zero observed-zero arrays. These values are now bound by the source-matched canonical manifests; their interpretation limitations remain unchanged.

An initial complete core rebuild reached ML before audit regeneration exposed R3-PR-15. The subsequent `audit.py` repair changed the source-tree implementation fingerprint (`0e20c072…` recorded by that run versus `174e632e…` after the fix), so current-provenance validation correctly made the first rebuild inadmissible. The complete source-matched rerun `run-20260719T103232-2fe4b69e` is the generation reported below.

The final independent audit then changed only documentation, test isolation and Docker packaging: `docs/methodology.md`, `docs/architecture.md`, `tests/unit/test_writers.py` and `Dockerfile`. None of the 49 source/dependency members in the canonical global implementation manifest changed, so the data/model release remained current; the container was rebuilt and the test suite was rerun instead of needlessly republishing identical canonical data.

## Files changed or materially remediated

This repository export has no `.git` metadata, so a commit-diff inventory cannot be reconstructed. The following file set is derived from the R3 handoffs, current source content and filesystem modification evidence. Historical Git identity was not backfilled.

### Root, build, dependency and CI configuration

| File | Remediation purpose |
|---|---|
| `.github/workflows/ci.yml` | Pinned uv 0.11.28; `uv lock --check`; `uv sync --frozen --extra dev` for lint/type/test/integration; Docker start/HEALTHCHECK polling with failure diagnostics and cleanup. |
| `Dockerfile` | Locked uv build; Python standard-library health probe; copies every global-provenance dependency, including `requirements.txt`, into builder/runtime. |
| `pyproject.toml` | Current package/tool contracts and typing/lint/test configuration. |
| `uv.lock`, `requirements-lock.txt`, `requirements.txt` | Reproducible resolved environment and explicit dependency handoff. |
| `Makefile` | Updated quality/pipeline commands. |
| `README.md`, `CHANGELOG.md` | Current pipeline contract, terminology, counts/scope and limitation history. |
| `THESIS_REVIEW.md`, `REVIEW_PROMPT.md` | Superseded/historical banners link to R3 and prevent old numerical claims/instructions being mistaken for current evidence. |
| `build_notebook.py` | Output-cleared notebook generation/current-evidence banners and terminology. |

### Core data, lineage and release implementation

| File | Remediation purpose |
|---|---|
| `src/thesis/paths.py` | Bronze/Silver/Gold/Benchmark/ML manifests and release-owned DQ paths, including SHAP DQ. |
| `src/thesis/config.py` | Declared artifact-affecting configuration and benchmark repeat settings. |
| `src/thesis/provenance.py` | Deterministic source-tree, effective-configuration and runtime fingerprints when Git is unavailable. |
| `src/thesis/locking.py` | Cross-stage publication/run locking. |
| `src/thesis/jsonutil.py` | Strict typed JSON conversion, `allow_nan=False`, duplicate-key and invalid-number rejection. |
| `src/thesis/lineage.py` | Portable relative paths, success-only sidecars, source/config provenance and persisted Parquet schema fingerprint. |
| `src/thesis/release.py` | Exact five-stage canonical contracts, manifest-last publication, upstream generation binding, required checks, portability and current-provenance validation. |
| `src/thesis/io/writers.py` | Atomic writers, strict JSON and persisted Arrow-schema lineage. |
| `src/thesis/io/readers.py` | Release-validated Silver/Gold/Benchmark/ML reads and before/after cross-stage dashboard bundles. |
| `src/thesis/dq/framework.py` | Persisted artifact-bound release payloads and runtime-isolated DQ output paths. |
| `src/thesis/dq/suites.py` | Nullable bidder semantics, Silver award→tender integrity, Gold source-total summary reconciliation and scored-output contracts. |
| `src/thesis/domain/contracts.py`, `src/thesis/domain/schemas.py` | Full Silver row/schema coverage, nullable bidder contract and unconditional ERROR publication gates. |
| `src/thesis/pipeline/bronze.py` | Staged validation, manifest-last raw publication and prospective acquisition provenance. |
| `src/thesis/pipeline/silver.py` | Identity-aware dedup, nullable bidder extraction, full-row contracts, referential DQ, persisted DQ and manifest-last publication. |
| `src/thesis/pipeline/gold.py` | Multi-view supplier/entity summaries, source-total reconciliation and four-output persisted release DQ. |
| `src/thesis/pipeline/benchmark.py` | Captured Gold release generation passed to benchmark publication. |
| `src/thesis/pipeline/ml.py` | One-generation benchmark consumption, semantic re-election, nullable-safe models, persisted scored/SHAP/model integrity and ML release binding. |
| `src/thesis/pipeline/dag.py` | Five-stage manifest-aware outputs/freshness and required DQ artifacts. |
| `src/thesis/cli.py` | Updated pipeline/DQ/review operational commands. |

### Procurement semantics, rules, audit and reporting

| File | Remediation purpose |
|---|---|
| `src/thesis/domain/procedures.py` | Code-first eight-subtype taxonomy and explicit design contest. |
| `src/thesis/domain/features.py` | Supplier key hierarchy/sentinels, honest award/bidder missingness, procedure/identity/lot/context features. |
| `src/thesis/anomaly/rules.py` | 15-indicator registry, four score-enabled rules, correct applicability, code/value and buyer-ID diagnostics, threshold/reference caveats. |
| `src/thesis/audit.py` | Structural exact-URL status, stable sample/label hashes and label-preserving/refusing force regeneration. |
| `src/thesis/external/oshp.py` | Complete withdrawal of invalid tender-level OSHP metrics. |
| `src/thesis/narrative.py` | Award-decision, missing-bidder and review-priority language. |
| `src/thesis/reporting.py` | Generated claim input registry and cautious current findings. |

### ML, benchmark and artifact integrity

| File | Remediation purpose |
|---|---|
| `src/thesis/anomaly/models.py` | Numeric nullable-to-float-NaN boundary, missingness indicators and rule-proxy framing. |
| `src/thesis/anomaly/detectors.py` | PCA stochastic classification and HBOS out-of-support tail treatment. |
| `src/thesis/anomaly/benchmark.py` | Protocol r6, source implementation manifest, strict checkpoint JSON, quick/WIP/canonical isolation, semantic election/DQ and schema-2 champions. |
| `src/thesis/anomaly/validation.py` | q=.90/.95/.99 rank-vote and declared feature-subset rank sensitivity. |
| `src/thesis/anomaly/explanations.py` | Nullable-safe SHAP input boundary. |
| `src/thesis/anomaly/artifact_integrity.py` | Persisted SHAP/model/JSON provenance, schema/order/finite checks and exact detector/HGB rescoring. |

### Documentation, ADRs, notebooks and dashboard

| File group | Remediation purpose |
|---|---|
| `docs/methodology.md`, `docs/findings.md`, `docs/manual_audit_protocol.md`, `docs/responsible_use.md`, `docs/architecture.md`, `docs/operations.md` | Current award/procedure/rule/ML/release semantics, generated evidence boundaries, legal and manual-review limitations. |
| `docs/adr/0001-medallion-architecture.md` through `0006-airflow-as-prod-orchestrator.md` | Current architecture, storage, dashboard, anomaly-framing and orchestration decisions. |
| `notebooks/01_eda.ipynb`, `notebooks/02_data_quality.ipynb` | Output-cleared, JSON/AST-valid templates with current-evidence status and corrected terminology. |
| `streamlit_app/_bootstrap.py`, `Home.py`, pages `1_Overview.py`–`8_Fjalori.py` | Cross-generation guarded bundle, current source-derived counts and cautious screening/ranking/award wording. |
| `airflow_dags/kosovo_procurement.py` | Current CLI/DAG refresh orchestration. |

## Root cause, change and verification mapping

| Finding IDs | Root cause | Implemented change | Verification / remaining gate |
|---|---|---|---|
| R3-PR-01 | Translated procedure text was treated as authoritative and code 3 was not represented. | Added code-first subtype mapping and design contest. | Final Gold has 291 design contests, 39,650 standard-open and 38 restricted tenders; release DQ passes. |
| R3-PR-02, R3-PR-10 | Supplier key used business ID/name only and accepted sentinel IDs; published party identity was discarded. | Raw/sanitized IDs, multiple key views, explicit unknown allocation and coverage sensitivities. | Final supplier summary is 9,940×23 (`7a2811d4…f1a4`); all six release-owned supplier checks pass. |
| R3-PR-03 | Award dedup signature ignored supplier party identity when names were blank. | Business-ID→party-ID/UID→name identity hierarchy in signature. | Distinct-blank-name/republication regressions; final release retains +1 award/+EUR7,200. |
| R3-PR-04, PIPE-R3-15 | Missing tenderer arrays were collapsed to zero; pandas nullable numeric then crossed sklearn as literal `pd.NA`. | `bidder_data_observed`, nullable `Int64`, observed-only rules/denominators and universal float64/NaN model boundary. | Final Silver/Gold preserve 69,603 observed and 6,107 missing; benchmark completed 279 fits and ML scored/SHAP-processed all 75,710 rows. |
| R3-PR-05, R3-PR-06, R3-PR-13, R3-PR-15 | Audit logic equated nonblank with usable URL, force replaced rows and metadata did not bind sample/labels; its first stable-content hash also filled nullable `Int64` with an invalid empty string. | URL structural status/reason, stable-OCID label merge/refusal, string-normalized sample/definition/label-state hashing and explicit completion. | Final queue regeneration succeeded: 150 rows, 124 structural-valid-unverified, 26 invalid, zero labels, empty `rule_only`; all sample/state hashes independently match. The first failed attempt published nothing. |
| R3-PR-16 | PPRC-hosted non-official consolidated convenience text was mislabeled as an official regulation PDF. | Anchor claims to official original Regulation 001/2022, official amendment 002/2024 and PPL; label the consolidation non-official. | PPRC official register and primary documents rechecked; source list corrected; no procedure count changed. |
| R3-PR-17 | Manual-audit metadata retains absolute operational source paths even though portable hashes carry integrity. | Defer a future relative-logical-path field to avoid invalidating current evidence for a non-integrity P3. | Non-blocking; hashes and definitions remain portable and verified. |
| R3-PR-07 | Award-stage OCDS objects were semantically promoted to contracts/performance. | Reworded all user-facing surfaces and added absent-contract/implementation limitation. | Regenerated findings, active stale scan, narrative assertions and all Streamlit AppTest renders pass. |
| R3-PR-08, R3-PR-09, R3-PR-11, R3-PR-14 | Procedure/value, entity collision, lot linkage and rule applicability assumptions were implicit. | Zero-weight diagnostics, exact title status, source IDs preserved, no auto/fuzzy merge, explicit multi-lot predicate. | Boundary tests and final persisted DQ/counts pass; legal/entity/lot truth remains deferred. |
| R3-PR-12, ML-R3-01 | Aggregate OSHP names were expanded into tender labels without case/outcome linkage. | Withdrew every metric and made source eligibility requirements explicit. | Withdrawal tests/report assertions pass; external validation remains unavailable. |
| ML-R3-02, ML-R3-05, ML-R3-06, ML-R3-07, R3-RISK-01 | Retrospective overlapping features and author-selected election/rule/vote settings lacked sensitivity and were over-interpretable. | Rank-only ablations, alternate election weights/proxy rank, q-vote and threshold sensitivity; explicit limited-repeat/non-validation notes. | Final q, election and two feature-ablation sensitivities are populated; limitations remain explicit and are not presented as validation. |
| ML-R3-03, ML-R3-04 | Benchmark reuse/election trusted manually versioned protocol and structurally valid champion payload. | Exact relevant-source hashes, schema-2 election proof, semantic recomputation and tamper rejection. | Final 35/35 unique successful schema-2 release passed semantic election; independent verifier confirmed exact fingerprint alignment. |
| ML-R3-08, ML-R3-09 | Detector registry/edge behaviour misstated stochastic and out-of-range semantics. | PCA stochastic; HBOS epsilon tail mass. | Boundary tests pass and benchmark/ML were regenerated under the corrected implementations. |
| ML-R3-10, ML-R3-11 | Mutable checkpoint was also canonical evidence; JSON was permissive/fail-open. | Quick/WIP/released separation, fsync+atomic replace and strict fail-closed JSONL. | Canonical checkpoint has 35 successful unique rows; strict scan of 156 JSON and seven JSONL/75,881 rows passed. |
| ML-R3-12, PIPE-R3-04 | Upstream generation could swap during long stages and auxiliary artifacts lacked semantic persisted gates. | Captured manifest SHAs, before/after reads, semantic benchmark DQ, source-reconciled Gold DQ, SHAP/model/JSON reload/rescore validation. | All final release hashes/DQ pass; independent verifier reproduced all eight detector and both HGB score paths with maximum absolute delta 0.0. |
| PIPE-R3-01 | Atomic individual files were mistaken for an atomic stage generation. | Manifest-last Bronze/Silver and exact canonical contracts/readers. | Final Bronze/Silver manifests and every declared hash validate. |
| PIPE-R3-02, PIPE-R3-07 | Freshness omitted code/config/runtime; Git unavailable; dependencies floated. | Source/config/runtime fingerprints, lockfiles, frozen uv CI/Docker and current-provenance validation. | Pipeline status is fresh 3/3, 5/5, 9/9, 6/6, 9/9; uv lock, quality suite and locked Docker build pass. |
| PIPE-R3-03 | Absolute paths were integrity keys. | Data-root-relative logical paths and escape rejection. | Relocation tests and Docker-mounted generation-guarded reads pass; strict producer-runtime freshness remains environment-specific by design. |
| PIPE-R3-05 | Lineage context wrote success metadata in `finally`. | Success sidecar only in `else`; failure preserves prior evidence. | Failure-path regressions pass. |
| PIPE-R3-06 | `default=str` and permissive JSON numeric handling. | Shared strict typed JSON converter/parser. | Independent strict scan passed 156 JSON documents and seven JSONL documents/75,881 rows with no invalid constants, duplicate keys or blank lines. |
| PIPE-R3-08 | Artifact loaders/caches were independent. | Cross-stage Silver+Gold+ML before/after bundle and manifest-SHA cache keys. | Reader swap/cache tests and AppTest execution of Home plus every page pass; Docker main HTTP is 200. |
| PIPE-R3-09 | Type errors were tolerated while docs claimed a working gate. | Correct annotations/narrowing and locked mypy CI. | Full mypy passes 45 source files with zero issues. |
| PIPE-R3-10 | Runtime health command was absent and CI never started the default image command. | Python health probe and bounded health-state polling with logs/inspect/cleanup. | Patched locked image built, ran as `thesis`, became healthy, returned health OK/main HTTP 200, passed guarded reads and was removed. |
| PIPE-R3-11 | Raw acquisition metadata was ephemeral and never committed. | Prospective Bronze release manifest with available acquisition fields/hashes/counts. | Final Bronze records retrieval time, ETag, Last-Modified, byte count and raw hashes; older acquisition transaction remains unrecoverable. |
| PIPE-R3-12 | Row validation sampled first 200 and schema coverage was incomplete. | Full-row Pydantic, expanded Pandera/record models and unconditional ERROR gate. | Final persisted 75,710/62,129 rows pass full validation and both Silver release-owned DQ suites. |
| PIPE-R3-16 | Lineage fingerprinted pre-serialization pandas dtypes. | Inspect staged Parquet Arrow footer and fingerprint persisted schema in both writer APIs. | All-null object-column regressions pass. |
| PIPE-R3-17 | Runtime image omitted `requirements.txt`, although the global implementation manifest requires it; HTTP health alone did not exercise artifact portability. | Copy `requirements.txt` into builder and runtime images and add a provenance-manifest regression. | Patched image health/HTTP and guarded readers passed with all expected shapes. Cross-runtime full freshness validation correctly rejects host macOS/Python 3.9 versus Linux/Python 3.11 runtime fingerprint. |
| PIPE-R3-18 | Unit writer test used a temporary artifact path but left chronological lineage under global `data/_lineage/test.schema/`. | Test now monkeypatches `thesis.paths.DATA` to a temporary root and asserts both isolated-history creation and zero canonical mutation. | Focused regression 1 passed in 0.78 s; final full suite 330 passed in 256.75 s; no canonical trace recreated. |
| R3-DOC-01 | Notebooks were output-cleared but evidence banners/terminology differed. | Standardized current-evidence banner and award/tender wording; retained no outputs. | Independent final JSON/AST scan passed: 47 cells/23 code total, zero errors, outputs or execution counts. |
| R3-DOC-02 | Historical review/prompt files could be mistaken for current evidence or instructions. | Added superseded/historical banners linking R3 and warning that their old numbers are not current. | Both banners present; active-surface stale scan passes. |

## Tests added or strengthened

| Test file / area | Coverage added or strengthened | Recorded focused outcome |
|---|---|---|
| `tests/unit/test_features_and_rules.py` | Code-3 design contest, procedure boundaries, rule applicability/weights and multi-lot winner rule. | Included in procurement focused passes. |
| `tests/unit/test_award_dedup_and_consortium.py` | Distinct blank-name supplier IDs, duplicate releases, nullable tenderer publication and ratio guard boundaries. | Included in procurement focused passes. |
| `tests/unit/test_gold_summaries.py` | Supplier identity/unknown coverage, entity sensitivity and exact monthly/source-total reconciliation. | Included in 45 focused Gold/DQ tests reported by implementing reviewer. |
| `tests/unit/test_dq_framework.py` | Nullable bidder consistency, award→tender orphans, supplier/entity/monthly source-total tampering and persisted release payload binding. | Focused DQ suite passed. |
| `tests/unit/test_audit.py` | URL structural classification, label preservation, dropped-reviewed-OCID refusal, sample/label hashing, nullable-`Int64` hash projection and row-order stability. | Passed in clean 330-test suite. |
| `tests/contracts/test_pydantic_models.py` | Expanded tender/award contracts and nullable bidder semantics. | Included in procurement focused passes. |
| `tests/unit/test_pipeline_safety.py` | DQ-before-publication, live/persisted summary suite sources and captured release generation. | Passed in focused pipeline selections. |
| `tests/unit/test_release.py` | Exact release contracts, current provenance, portability, partial/manifest swap, lineage and upstream hash enforcement. | Passed in clean 330-test suite. |
| `tests/unit/test_bronze.py`, `test_locking.py`, `test_provenance.py`, `test_readers.py` | Acquisition/update checks, mutual exclusion, implementation/config/runtime fingerprints, Docker provenance-manifest inclusion, release swap and cache invalidation. | Passed in clean 330-test suite and patched Docker guarded-read verification. |
| `tests/unit/test_writers.py`, `test_lineage.py` | Strict/atomic writes, failure semantics and persisted Arrow schema including all-null object columns. | Passed. |
| `tests/unit/test_detectors_and_benchmark.py` | PCA/HBOS, strict JSON, implementation provenance, quick/WIP/canonical isolation, exact grid/election/tamper/release semantics and nullable supervised families. | Included in 45 focused benchmark/ML passes. |
| `tests/unit/test_validation_sensitivity.py` | q=.90/.95/.99 vote membership and rank-only deployed-feature refits, including nullable values. | Passed. |
| `tests/unit/test_benchmark_pipeline_release_binding.py` | Captured Gold manifest SHA reaches benchmark publication. | Passed. |
| `tests/unit/test_models.py` | Nullable HGB and SHAP boundaries convert to float NaN. | Passed. |
| `tests/unit/test_ml_pipeline_safety.py` | One-generation benchmark consumption, score/SHAP gates, validation fields and upstream manifest hashes. | Included in focused passes. |
| `tests/unit/test_ml_artifact_integrity.py` | Persisted SHAP schema/order/finite/Gold binding; strict JSON/model provenance; all-detector and HGB exact rescoring; canonical contract membership. | **20 passed**; broader relevant selection **101 passed**. |
| `tests/unit/test_narrative.py`, `tests/test_streamlit_pages.py` | Missing bidder/award terminology, award-not-contract language, cautious proxy/rank claims and release-keyed loaders. | Passed within clean 330-test suite; every page AppTest rendered without exception. |
| `tests/integration/test_pipeline_e2e.py`, `test_findings_report.py` | Isolated five-stage publication/input lineage and exact generated-report drift. | Passed in clean 330-test suite; canonical five-stage run independently validates. |

## Artifacts affected and required regeneration

Every artifact below is downstream of at least one semantic, lineage or benchmark change. A pre-R3 file at the same path is not accepted merely because it exists.

| Stage | Canonical artifacts/checks requiring coherent R3 publication | Final status |
|---|---|---|
| Bronze | `data/raw/kosovo_ocds.jsonl.gz`, `data/raw/kosovo_ocds.jsonl`, `data/raw/bronze.release.json` | **Published and verified** — manifest `b33a97e1…3ca4`, 75,710 records |
| Silver | `data/silver/tenders.parquet`, `awards.parquet`, both lineage sidecars, `data/dq/silver_tenders.release.dq.json`, `silver_awards.release.dq.json`, `data/silver/silver.release.json` | **Published and verified** — manifest `f1e15077…eb32`, 75,710/62,129 rows |
| Gold | `data/gold/tender_features.parquet`, `supplier_summary.parquet`, `procuring_entity_summary.parquet`, `monthly_metrics.parquet`, all four lineage sidecars, all four `*.release.dq.json`, `data/gold/gold.release.json` | **Published and verified** — manifest `a2602b70…eff`, 75,710/9,940/206/122 rows |
| Benchmark | `data/models/benchmark/results.jsonl`, `leaderboard.parquet`, `leaderboard.md`, `champions.json`, `data/dq/benchmark.release.dq.json`, `benchmark.release.json` | **Published and verified** — manifest `676cff17…b48a`, 35/35 unique successful full configurations |
| ML | `data/models/champion_models.joblib`, `hgb_classifier.joblib`, `shap_values.parquet`, `validation_report.json`, `feature_list.json`, `data/gold/tender_summary.parquet`, lineage sidecars, `data/dq/gold_tender_summary.release.dq.json`, `ml_shap_values.release.dq.json`, `data/models/ml.release.json` | **Published and verified** — manifest `77ccbcbb…db0a`, 75,710 scored and SHAP rows |
| External/manual evidence | withdrawn OSHP status artifact; `data/review/manual_audit_sample.csv`; metadata/state hashes | **Regenerated and verified** — OSHP remains withdrawn; audit 150 rows/zero labels, hashes below |
| Generated reporting | `docs/findings.md` and dashboard-derived tables/captions | `docs/findings.md` **regenerated and hash-verified** (`66f0534f…3c76`); every page AppTest and active-surface stale scan pass |
| Notebooks | Output-cleared notebook JSON only; no generated numerical output is accepted as evidence | **Verified** — JSON/AST valid, zero outputs/execution counts |
| Test-lineage cleanup | `data/_lineage/test.schema/*.json` | Five generated orphan traces were removed after confirming every referenced pytest temp artifact had expired and none belonged to a canonical release. They were not human labels or source data. The deletions are not directly recoverable except from filesystem backup, but the files were reproducible test by-products and the repaired test no longer writes them canonically. |

## Before/after quantitative remediation

| Measure | Pre-R3 canonical | Deterministic no-write after | Final published R3 |
|---|---:|---:|---:|
| Tenders | 75,710 | 75,710 | 75,710 |
| Awards | 62,128 | 62,129 | 62,129 |
| Recorded award value | EUR4,765,536,984.67 | EUR4,765,544,184.67 | EUR4,765,544,184.67 |
| Supplier summary rows | 9,427 | 9,940 | 9,940 |
| Entity summary rows | 206 | 206 | 206 |
| Monthly rows | 122 | 122 | 122 |
| Standard-open | 39,940 | 39,650 | 39,650 |
| Restricted | 39 | 38 | 38 |
| Design contest | 0 | 291 | 291 |
| Bidder publication observed | not explicit | 69,603 | 69,603 |
| Missing bidder publication | encoded as zero | 6,107 | 6,107 |
| Observed zero bidders | asserted 6,107 | 0 | 0 |
| Visible/scoring rules | 13/4 | 15/4 | 15/4 |
| Rule score ≥0.5 | 221 | 235 | 235 |
| Rule score ≥0.7 | 77 | 77 | 77 |

The complete before/after indicator table is in `THESIS_REVIEW_R3.md`. All rule counts are screening/diagnostic counts, not wrongdoing or prevalence.

| ML/ranking measure | Pre-R3 canonical | Final published R3 | Change |
|---|---:|---:|---:|
| Ensemble ≥0.5 | 25,252 | 24,690 | −562 |
| Ensemble ≥0.7 | 6,594 | 6,505 | −89 |
| `high_confidence` rank agreement | 2,536 | 2,453 | −83 |
| Ensemble mean | 0.438235 | 0.436996 | −0.001239 |
| Ensemble median | 0.421650 | 0.419316 | −0.002334 |
| Ensemble p95 | 0.744807 | 0.744340 | −0.000467 |

The ML changes are snapshot-relative ranking changes, not evidence of better or worse detection.

## Commands executed and outcomes

### Independent baseline and no-write checks

| Command/check | Outcome | Interpretation |
|---|---|---|
| `shasum -a 256 data/raw/kosovo_ocds.jsonl data/raw/kosovo_ocds.jsonl.gz`; `gzip -t`; decompression hash; `wc -l` | JSONL `666d2392…7122d4`; gzip `b782bdb3…1341b`; 75,710 records; decompressed bytes equal JSONL | Internal raw consistency only |
| Full raw JSON/object/OCID scan | 75,710 valid objects; zero invalid/blank/missing OCID; 75,710 unique OCIDs | Snapshot integrity only |
| Pre-R3 `.venv/bin/python -m pytest tests -q -p no:cacheprovider` | 194 passed, 19 warnings | Historical baseline, not final |
| Pre-R3 Ruff check/format | Passed | Historical baseline |
| Pre-R3 mypy `src/thesis` | Failed: 13 errors in six files | Confirmed PIPE-R3-09; superseded by final full mypy pass on 45 files |
| Strict pre-R3 JSON scan | Zero current JSON parse failures | Did not remove the shared-writer defect |
| No-write Silver/Gold rebuild | Pydantic 75,710/62,129; both Pandera schemas; zero DQ ERROR; documented warnings only | Strong transformation evidence, not persisted release acceptance |
| No-write deterministic frame fingerprints | Six fingerprints recorded below | In-memory reproducibility only |

### Focused remediation checks already recorded

| Check | Outcome | Scope caveat |
|---|---|---|
| Procurement/data regression selection | 131 passed in 3.60 s | Focused only |
| Narrative/UI procurement selection | 114 passed in 3.16 s | Focused only |
| Benchmark/ML/sensitivity selection | 45 passed | Focused only |
| Persisted ML artifact-integrity selection | 20 passed | Focused only |
| Broader relevant release/benchmark/model selection | 101 passed | Focused only |
| Focused Ruff/format/compile/AST | Passed | Changed files/modules only |
| Focused mypy on changed ML modules | Passed, no issues | Superseded by final full mypy pass |
| Legacy/public Parquet lineage all-null schema regression | Passed | Writer/lineage scope |
| CI YAML parse and embedded Docker health shell `bash -n` | Passed | Does not execute GitHub Actions/Docker |
| CI invariant scan | All lint/type/test/integration jobs use `astral-sh/setup-uv@v6`, uv `0.11.28`, `uv lock --check`, frozen sync; no `pip install` remains | Static workflow evidence |
| Local `uv 0.11.28`; `uv lock --check`; frozen dev sync dry run | Passed; lock resolved | Did not mutate canonical artifacts |
| First post-rebuild `thesis report audit-sample --force` | Failed before any output write: nullable `Int64` rejected empty-string fill during sample hash; old CSV/metadata mtimes and labels remained unchanged | Revealed R3-PR-15; source fix invalidated the first rebuild's current-provenance fingerprint and required a full rerun |

Historical partial-suite values (212 passed, 196-before-stop, and 151 passed/9 expected stale-release failures) are deliberately not reported as final success.

### Commands required after authoritative publication

| Command / check | Final outcome |
|---|---|
| `uv lock --check` and frozen-environment dependency checks | Passed; 261 packages locked; `uv pip check` checked 184 packages and reported all compatible |
| `uv run --frozen pytest -q` | First run: 328 passed/1 stale denominator expectation; intermediate clean run 330 passed in 290.55 s; after the final test-isolation patch, authoritative run **330 passed in 256.75 s (4:16), exit 0**. |
| `uv run --frozen ruff check .` | Passed |
| `uv run --frozen ruff format --check .` | Passed; 90 files already formatted |
| `uv run --frozen mypy src/thesis` | Passed; 45 source files, zero issues |
| Final release-owned DQ validation | All seven invoked suites and nine required persisted reports pass; Silver warnings documented; all Gold/benchmark/ML checks pass |
| `uv run --frozen thesis pipeline validate-releases` | Passed for all five releases; every declared input/artifact/check/implementation-manifest hash matches disk |
| `uv run --frozen thesis pipeline status` | Fresh: Bronze 3/3, Silver 5/5, Gold 9/9, Benchmark 6/6, ML 9/9 |
| Full benchmark semantic completeness/uniqueness/election check | Passed: 35 expected/35 successful/35 unique; 23 unsupervised +12 supervised; zero failed/extra/duplicate/stale |
| ML persisted rescore/SHAP/JSON/model gate | Passed; all eight detectors plus bundled/standalone HGB max absolute rescore delta 0.0; SHAP 5/5 checks pass |
| Manual audit label/hash/URL preservation check | Passed: 150 rows, zero labels, 124 structural-valid-unverified/26 invalid, empty `rule_only`, all state hashes match |
| Strict JSON scan | Passed: 156 JSON documents and seven JSONL documents/75,881 rows; zero duplicate keys, non-standard constants or blank lines |
| Notebook JSON/nbformat/Python-AST/no-output scan | Passed: 01 has 23/12 total/code cells; 02 has 24/11; zero errors, outputs or execution counts |
| R2/R2.1 and canonical-finding arithmetic | Passed: 18/18 R2 rows, 28/28 R2.1 rows; 50 findings = 14 P1 +29 P2 +7 P3 |
| Read-only procurement/data verification | Passed with no P0–P2 contradiction; final counts, hashes, DQ, manual evidence and active wording matched |
| Read-only ML artifact verification | Passed: fingerprints/election aligned, SHAP 5/5, all eight detector and both HGB rescore paths max delta 0.0; implementer-side, not the final independent audit |
| PIPE-R3-18 focused isolation regression | 1 passed in 0.78 s; isolated chronological trace created under tmp; canonical `data/_lineage/test.schema` remained absent; Ruff check/format passed |
| Repository stale claim/path/number scan | Passed for active README/docs/dashboard/source claims. Old OSHP/EU/numeric statements remain only in historical `THESIS_REVIEW.md`, `REVIEW_PROMPT.md`, prior-review files or explicit before/after contexts and are not cited as R3 evidence. |
| Docker image start/HEALTHCHECK/artifact-read/cleanup path | Passed after patch: image manifest-list SHA `02d9b403ebe60aafff8bf518acc66fe809a57af6673cf9afb51afcedc037bb1b`; user `thesis`; healthy; health OK; `/` HTTP 200; guarded readers loaded 75,710×95 scored, 62,129×28 awards, 9,940×23 suppliers, 206×26 entities, 35×41 leaderboard, champion schema 2 and validation schema 1; container removed. |
| Independent contradiction/integrity audit | Passed after surfacing/rechecking R3-PR-16, R3-PR-17, PIPE-R3-18 and R3-DOC-02; no unresolved P0–P2 contradiction; exact finding count 50 =14 P1 +29 P2 +7 P3 |

## Final row counts and artifact hashes

### Prepublication no-write fingerprints — not final file hashes

| Frame | Shape | DataFrame fingerprint |
|---|---:|---|
| Silver tenders | 75,710×28 | `e1ea81ac5f0a1254f8cfd328f6c4550944f5632e2e1ca928b6519053541f26a5` |
| Silver awards | 62,129×28 | `2f39dbd63b93976c8f6097069911edab682b2ec1632ab7585d5698992995b943` |
| Gold features + rules | 75,710×82 | `2c58ae397acbdde2a57bed4b7195b997df5733fade45c39521d6593fd608d0dd` |
| Supplier summary | 9,940×23 | `ec82b37eb4eb90540c20d4f65a8021a82720eb35c99e0c021d41720eb45bcff1` |
| Entity summary | 206×26 | `347998d5590cb1bbf55fc224824f629fd6600785f3a8677ef0f82928e573bd31` |
| Monthly metrics | 122×15 | `fbd5147dfa5dfb4674084c2cb1fcaadeae2d3d71e21712b64f3dbe69d95ed36a` |

### Final persisted artifacts

| Artifact | Final rows×columns | SHA-256 | Lineage schema fingerprint | Release generation |
|---|---:|---|---|---|
| `data/raw/kosovo_ocds.jsonl` | 75,710 records | `666d239260114464142db43dfb1b85ed5b9cb508406461321859f7b1037122d4` | n/a | `a44b7f9a31d9fb38736bcdd7e83584add487de4fb3e4119b9fcbc8718c2400da` |
| `data/raw/kosovo_ocds.jsonl.gz` | 75,710 records after decompression | `b782bdb3c323b3a6b9bba72c906756744700752bd9287efe55dbab4fe1f1341b` | n/a | `a44b7f9a31d9fb38736bcdd7e83584add487de4fb3e4119b9fcbc8718c2400da` |
| `data/silver/tenders.parquet` | 75,710×28 | `c4139e1313e612494b4e445c9dce561cdaeb07dffb2ab6e3197033e81968323f` | `4eeefa732389dbad` | `4f2f86eeff666dcfd4b1faa11c1b1b4a4857f901d22533e8411f5eba450fa98e` |
| `data/silver/awards.parquet` | 62,129×28 | `3498ec4d4157b81db443e41d63d45d88e4d254d47d369196fd63860c6179ffb9` | `6da9854596aa0c73` | `4f2f86eeff666dcfd4b1faa11c1b1b4a4857f901d22533e8411f5eba450fa98e` |
| `data/gold/tender_features.parquet` | 75,710×82 | `6f776a40a2bd6b71d38e3b683992152fb53f751a11803b107ab77ebf5d95a10e` | `6508fdc72c5d3d0d` | `3ef3848e17522bd5c81d32dbbf91816766e1a6c9643430c826ef4624d261f539` |
| `data/gold/supplier_summary.parquet` | 9,940×23 | `7a2811d4c682299f3a9daa76875c65d710c06cf384be619acdec240d6f3ef1a4` | `686a2dd200ca4b0b` | `3ef3848e17522bd5c81d32dbbf91816766e1a6c9643430c826ef4624d261f539` |
| `data/gold/procuring_entity_summary.parquet` | 206×26 | `b1437314eadfae6c11f3936992b48a30450acded34247d6c54298c1cedc1275a` | `5fdc8011a35ba366` | `3ef3848e17522bd5c81d32dbbf91816766e1a6c9643430c826ef4624d261f539` |
| `data/gold/monthly_metrics.parquet` | 122×15 | `f26da9a7cdd01fda8378132ff9a60138b3e3843d53d5061e5dde6e6a44accacb` | `b5cc2360621a798a` | `3ef3848e17522bd5c81d32dbbf91816766e1a6c9643430c826ef4624d261f539` |
| `data/models/benchmark/results.jsonl` | 35×41 | `ae47e890a8086f1a2d10b5cb70ff546f381789fed3a15eaf0fc866bb24c65b24` | n/a | `b1007484a576bc32ee5660a5bee4e7dd94f8487758075d162527ed1d73057044` |
| `data/models/benchmark/leaderboard.parquet` | 35×41 | `f176f705b46abcd981547dc69a392ed79e04d3c2bfb74d32878650281d450858` | `55804d456a6cfcc8` | `b1007484a576bc32ee5660a5bee4e7dd94f8487758075d162527ed1d73057044` |
| `data/models/benchmark/leaderboard.md` | n/a | `a3d8cda2f082ccdd0b057e754545294d19a07afc327ebbafa50422114157509f` | n/a | `b1007484a576bc32ee5660a5bee4e7dd94f8487758075d162527ed1d73057044` |
| `data/models/benchmark/champions.json` | n/a | `3a3f4d3c509a03218d87202d6b7523b81075a83a93179769cf57c576f331d186` | n/a | `b1007484a576bc32ee5660a5bee4e7dd94f8487758075d162527ed1d73057044` |
| `data/models/champion_models.joblib` | n/a | `179b74f1f1469f3dd1f38274171ea62e2aa7d3797bccce47fb76c6945d532320` | n/a | `74b1cbc8026ef9df47779949bf463d3818c2896b7aa5bec5a088fc63f46f398a` |
| `data/models/hgb_classifier.joblib` | n/a | `609ccdaf93d78b273c81e86301234a1b2f053bac2b17f4b6aff40466e8a2376b` | n/a | `74b1cbc8026ef9df47779949bf463d3818c2896b7aa5bec5a088fc63f46f398a` |
| `data/models/shap_values.parquet` | 75,710×22 | `e0772d332e59c97276a7a7de8c4a3f32bfc23777ca7ae5025fa18f2f7ac19104` | `4df92857cf451ddb` | `74b1cbc8026ef9df47779949bf463d3818c2896b7aa5bec5a088fc63f46f398a` |
| `data/models/validation_report.json` | n/a | `0c80b54ffacb379e059409ae335a30e94f624b75cbb9503a78ce485efa396b68` | n/a | `74b1cbc8026ef9df47779949bf463d3818c2896b7aa5bec5a088fc63f46f398a` |
| `data/models/feature_list.json` | n/a | `b0d047bcf530b5ab6a272cdc6b6834a95593e8a083368895f50038237af3e6e6` | n/a | `74b1cbc8026ef9df47779949bf463d3818c2896b7aa5bec5a088fc63f46f398a` |
| `data/gold/tender_summary.parquet` | 75,710×95 | `511700311b2a8805be304560b87c29fcd029d4e23be069ea9868c952711f530e` | `b018b61a1e6f300a` | `74b1cbc8026ef9df47779949bf463d3818c2896b7aa5bec5a088fc63f46f398a` |
| `docs/findings.md` | n/a | `66f0534f3731f7bd6783a365698e980a8aadc5402a1d46f929fb1d37031f3c76` | n/a | inputs bound to final releases |
| `data/review/manual_audit_sample.csv` | 150×28 | `5f3559385ec11a8c123fafa877022b0867ddd8fc22c4bc90d8c63c60db919120` | n/a | ML generation `74b1cbc8026ef9df47779949bf463d3818c2896b7aa5bec5a088fc63f46f398a` |
| `data/review/manual_audit_sample.metadata.json` | n/a | `694beadffe2c052e44aba3cbddc534325bb77f680faf3715a4cf880e4f81557f` | n/a | bound to sample/scored/raw hashes |
| `data/external/oshp_validation.json` | withdrawn status | `728eb1898659fa72b7712a32681c0a09ca31aaf819ebcdd203ac3e6575494354` | n/a | no metrics emitted |

No pre-R3 Parquet hash is copied into this final table. A differing final hash is not itself a defect if the semantic changes explain it; it must be recomputed and bound by the final manifest.

## Final releases, fingerprints and pipeline status

| Stage | Release ID | Manifest SHA-256 | Generation fingerprint | Implementation fingerprint | Configuration/runtime status | Validation |
|---|---|---|---|---|---|---|
| Bronze | `run-20260719T103232-2fe4b69e` | `b33a97e1fd15facbf8aab58629f531bcac687fe2c4e3380de77a721341613ca4` | `a44b7f9a31d9fb38736bcdd7e83584add487de4fb3e4119b9fcbc8718c2400da` | `174e632ef603039bb5877af0d3746c14d54d1415beba290b989ae0444e00b6f5` | config `a7e3c914…ba0c`; runtime `81f5e882…f2bc` | Passed; fresh 3/3 |
| Silver | `run-20260719T103232-2fe4b69e` | `f1e150772c8572f00dada17df43de6ea817dee041c287582e859059acef2eb32` | `4f2f86eeff666dcfd4b1faa11c1b1b4a4857f901d22533e8411f5eba450fa98e` | `174e632ef603039bb5877af0d3746c14d54d1415beba290b989ae0444e00b6f5` | same | Passed; fresh 5/5 |
| Gold | `run-20260719T103232-2fe4b69e` | `a2602b7039bf7300bb7746bc5e9821420ffdbcf1efa5fb3b2e5d49067b78aeff` | `3ef3848e17522bd5c81d32dbbf91816766e1a6c9643430c826ef4624d261f539` | `174e632ef603039bb5877af0d3746c14d54d1415beba290b989ae0444e00b6f5` | same | Passed; fresh 9/9 |
| Benchmark | `run-20260719T103232-2fe4b69e` | `676cff17b242609f4d04f465c2881f403aab9c2a4b4073005422c1f8a919b48a` | `b1007484a576bc32ee5660a5bee4e7dd94f8487758075d162527ed1d73057044` | global `174e632e…b6f5`; benchmark-specific `1ebaf580…7ac9` | same | Passed; fresh 6/6 |
| ML | `run-20260719T103232-2fe4b69e` | `77ccbcbb999710156cfb62d280ff17348434c6b4ece74a1e8bba1aa59e40db0a` | `74b1cbc8026ef9df47779949bf463d3818c2896b7aa5bec5a088fc63f46f398a` | global `174e632e…b6f5`; benchmark-specific `1ebaf580…7ac9` | same | Passed; fresh 9/9 |

| Benchmark/ML consistency item | Final value / result |
|---|---|
| Data fingerprint | `e4e6cef88490834a` |
| Protocol fingerprint | `7d5b8a909f00e6d8` |
| Benchmark-specific implementation fingerprint | `1ebaf58000d16685dbb51609b3ce1489b4aaf5d51d3dadb66dd83b5418647ac9` |
| Model-election/semantic fingerprint | `e034c3f0668d8f9b85f196371b7562653a3aed8f23350eaa7c38e4bf7d8cfd81` |
| Results/leaderboard semantic bundle fingerprint | `d4149c4f59068be799cfaee9e2e7a372190ba0293e04e912d36746f4277a8a17` |
| Full expected/successful/unique configs | 35/35/35; 23 unsupervised +12 supervised; 279 recorded fits |
| Quick/WIP/failed/extra/duplicate/stale rows | Zero in released results |
| Schema-2 family/supervised champions | Full schema-2 bundle; HGB max depth 4, learning rate 0.05, max iterations 300 |
| Released ensemble families | `ocsvm`, `iso`, `hbos`, `knn` |
| Scored/SHAP/Gold OCID order and row parity | Passed; 75,710 rows in each relevant table; SHAP 5/5 checks |
| Detector/HGB persisted rescore maximum differences | 0.0 for all eight detector families and bundled/standalone HGB |
| q=.90/.95/.99 sensitivity populated | q=.90: 5,008/Jaccard .4898; q=.95: 2,453/1.0; q=.99: 425/.1733 |
| Both deployed feature-ablation subsets populated | raw-only Spearman .9050/Jaccard .7166; pre-outcome-field snapshot .8136/.5211 |

| Pipeline/DQ status item | Final result |
|---|---|
| `pipeline status` Bronze | Fresh 3/3 |
| `pipeline status` Silver | Fresh 5/5 |
| `pipeline status` Gold | Fresh 9/9 |
| `pipeline status` Benchmark | Fresh 6/6 |
| `pipeline status` ML | Fresh 9/9 |
| Silver tender DQ | Passed: 13 OK, three warnings — 31 missing dates, seven quotation/value conflicts, two buyer-name collision groups/four IDs |
| Silver award/referential DQ | Passed: 11 OK, one linkage warning — 61,260 exact unique, 244 ambiguous, 505 unmatched, 120 missing titles |
| Gold feature/supplier/entity/monthly DQ | Passed: features 13, suppliers 6, entities 7, monthly 7; zero warnings/errors; EUR10,490,954,921.11 estimated and EUR4,765,544,184.67 recorded awards reconcile |
| Benchmark semantic DQ | Passed; exact 35-row/election/fingerprint contract |
| ML scored/SHAP/model/JSON/rescore DQ | Passed; scored 6/6 and SHAP 5/5 with zero warnings/errors; all rescore deltas 0.0 |

Final persisted-table DQ fingerprints:

| DQ report | Data fingerprint |
|---|---|
| Silver tenders | `e1ea81ac5f0a1254f8cfd328f6c4550944f5632e2e1ca928b6519053541f26a5` |
| Silver awards | `2f39dbd63b93976c8f6097069911edab682b2ec1632ab7585d5698992995b943` |
| Gold features | `2c58ae397acbdde2a57bed4b7195b997df5733fade45c39521d6593fd608d0dd` |
| Gold suppliers | `ec82b37eb4eb90540c20d4f65a8021a82720eb35c99e0c021d41720eb45bcff1` |
| Gold entities | `347998d5590cb1bbf55fc224824f629fd6600785f3a8677ef0f82928e573bd31` |
| Gold monthly | `8c6fb12024ca1aa8e8f184f3b0cef4612e2901a76bef71256fcb17f9ffe4ce20` |
| Benchmark leaderboard | `7919019769c9ae87fb9b562044366e1c3a36b2d4765e2c0c6f33e34404ba4456` |
| Scored Gold | `2e112a6d884a976646ecb6480d9d2e6f415fd78605bd1a7e776f64021ae9e1f7` |
| SHAP | `7c2bd268ce3592eb695b3fa6056e511842c35ab2acc1dc1a298d35b703477b70` |

## Manual-audit integrity record

| Field | Final value |
|---|---|
| Sample rows | 150 |
| Sample CSV SHA-256 | `5f3559385ec11a8c123fafa877022b0867ddd8fc22c4bc90d8c63c60db919120` |
| Metadata SHA-256 | `694beadffe2c052e44aba3cbddc534325bb77f680faf3715a4cf880e4f81557f` |
| Sample-definition hash | `b7daa09ccea00809fbe6f01c0b34638f1886301c63157df4e45d6582589baa1f` |
| Label-state hash | `662e9fbaef0dbc09087a4d0ceae1503c2fa6673eba642a652fc5c08009fcb403` |
| Prior sample / label-state hashes | `43a7883046746dcb70b142924fc21b2f8f73a75324dfb13a25725e0c15ca4a42` / `4e12ef9f18f47a9626be22834ffdd15cce7ece9f2349450eb10dcef7b349ce37` |
| Source raw hash | `666d239260114464142db43dfb1b85ed5b9cb508406461321859f7b1037122d4` |
| ML/release fingerprint | ML generation `74b1cbc8026ef9df47779949bf463d3818c2896b7aa5bec5a088fc63f46f398a` / release `run-20260719T103232-2fe4b69e` |
| Seed and rule/ensemble thresholds | seed 7; 0.5 / 0.5 |
| Four population/sample strata | both 235/50; rule-only 0/0; ensemble-only 24,455/50; neither 51,020/50 |
| Structurally valid-unverified URLs | 124 |
| Invalid/missing exact URLs and reasons | 26 invalid source URLs; 150 nonblank source strings retained as evidence |
| HTTP availability tested? | No; only structural validity was tested |
| Completed labels | 0; 150 remaining; blanks mean unreviewed |
| Preserved existing reviewed rows/fields | 0 existing reviewed rows/fields because the prior queue also had zero; none altered or inferred |
| Completion status/definition | `awaiting_human_review`; complete only when required review fields satisfy the declared completion definition |

## Explicitly deferred work and responsible reason

| Deferred item | Why it cannot responsibly be completed now | Required future evidence/action |
|---|---|---|
| Outcome validation/calibration | No independent tender-level ground truth and zero completed human labels. | Qualified blinded review or official exact-tender adjudicated outcomes with eligible controls. |
| Precision, recall, FPR, prevalence and calibrated risk | Rule-derived labels cannot estimate outcome performance. | Sufficient independently labelled population and prespecified evaluation. |
| OSHP evaluation | Cached rows lack case/outcome/tender/business-ID links. | Primary official dataset with explicit case, decision, date, tender ID and reviewed operator identity. |
| Legal conclusions for seven quotation/value conflicts | Static fields cannot resolve amendments, lots, exceptions or applicable historical rules. | Original notice/documents, amendments and contemporaneous law reviewed by qualified expert. |
| Deadline-breach determination | Snapshot lacks all legally relevant event/urgency/prior-notice/corrigendum context. | Period-specific law and complete procedure documents/events. |
| Supplier legal-entity resolution/relevant-market HHI | Source IDs/names are not externally verified and market definitions are absent. | Authoritative business registry/entity-history linkage and defensible relevant-market definition. |
| Buyer ID merge | Same normalized name may reflect migration or distinct entities. | Authoritative entity-history evidence/human adjudication. |
| Award-to-lot allocation | No stable shared lot ID; exact title can be ambiguous/missing. | Better source linkage or manual document review; no fuzzy synthetic allocation. |
| Contract execution/payment claims | Award objects do not establish signed, performed or paid contracts. | Contract/implementation/payment artifacts linked to the tender. |
| Frozen online/pre-award scoring | Current features include award-stage and snapshot-relative transforms. | Prespecified cutoff, frozen reference transforms/models/thresholds and genuine forward external evaluation. |
| Model-selection uncertainty | Four bootstraps/two seeds are intentionally limited. | More repetitions and prespecified uncertainty analysis; still not external validation by itself. |
| Historical Git/remote acquisition provenance | Repository export has no Git metadata; historic ETag/time cannot be reconstructed. | Preserve future source archive/commit and acquisition response metadata; record current unknown honestly. |
| Missing exact audit URLs | Raw source contains empty-ID placeholders and no alternate exact URL for some records. | Publisher/source recovery or manual official search; never invent a link. |
| Empty manual-review strata | A stratum may have zero population. | Report zero; do not synthesize members. |
| Relative audit metadata paths (P3) | Current absolute paths are operational annotations, not integrity keys; changing source now would invalidate an otherwise coherent release for minor portability polish. | Add data-root-relative logical paths on the next planned generation while retaining hashes and optional operational paths. |

## Final remediation acceptance

Implementation, documentation and canonical-publication remediation is complete for every actionable P0–P2 finding identified, and the non-implementer audit passes. The project is technically accepted only for descriptive procurement data engineering, transparent heuristic screening and exploratory retrospective anomaly ranking. Passing technical gates does not close the explicitly deferred evidence limitations or justify fraud/corruption/detection/legal-breach claims.
