# Changelog

All notable changes to this project. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning
follows [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Documentation, dashboard and regression tests only; the package, data and model
releases remain 1.3.0 and still validate.

### Përgatitja për shqyrtim — 4 nëntor 2026

- Kërkimi i tenderëve hap shpjegimin e pikëve për tenderin e përzgjedhur;
  një test mbulon kalimin ndërmjet faqeve.
- U shtuan katër pamje të panelit në shqip, përshkrimet për prezantim dhe
  dy pamje në README.
- U përshtatën udhëzimet për depon publike dhe nisjen e panelit pa pyetjen
  fillestare të Streamlit për emailin.

### Final review — 22 October 2026

- Dashboard: dates are shown and grouped in the source's published `+01:00`
  offset instead of UTC (most publication dates previously appeared one day
  early); the review page now ranks by the rule score by default, since the
  ensemble's 0.5 cut is only its 67th percentile; Albanian number formatting,
  page names, labels and remaining English UI text made consistent.
- Methodology: added purpose and contributions, related work and a full
  reference list; described the rule/ensemble relationship as nested rather
  than disagreeing; documented what the unsupervised detectors pick up, the
  sensitivity of the model election, and known issues that need a new
  publication (rule overlap in `WINNER_TAKES_ALL_LARGE`, UTC date bucketing,
  same-title award de-duplication).
- Corrected citation details, stale CSV and lineage references in the ADRs,
  page and document names across the Albanian docs, and the copyright holder.
- EDA notebook: reads the bundled `.jsonl.gz` when the expanded file is
  missing, and its takeaways section is filled in with verified figures.
- Date regressions cover local month/year boundaries, the fixed summer offset,
  missing dates, filtering and aggregation without changing scores or instants.
  Corrected the methodology's date-shift counts and annual-rate comparison.

### Changed

- Reorganized documentation around setup, dashboard use, development,
  methodology, explainability, and the bundled data's retention requirements.
- Removed superseded review drafts, prototype DQ reports, and historical
  lineage copies; current publication artifacts and sidecars are preserved.
  Earlier review material remains available in Git history.
- Moved the EDA notebook generator to `scripts/build_notebook.py`.
- Made `make clean` remove development caches only and removed `clean_all`;
  routine cleanup now preserves data, models, review work, and the environment.
- Documented opening the existing dashboard without retraining or checking
  for newer source data.
- Fixed the findings-report drift check on fresh Git checkouts: only its
  validated input-file timestamp may differ; all numerical content and input
  hashes must still match the committed report exactly.

## [1.3.0] — 2026-07-18 — Review R3 semantic and generation integrity

### Changed

- Corrected official procedure-code semantics, preserved unavailable bidder
  counts as missing, retained source supplier identities, and made award
  de-duplication identity-aware.
- Added transparent supplier-identity coverage and HHI sensitivity scenarios;
  these remain descriptive concentrations, not relevant-market findings.
- Bound Bronze and Silver publications, benchmark checkpoints, DQ evidence,
  models, scored tables, and reports to hash-validated release generations.
- Added strict JSON serialization, portable lineage, implementation/configuration
  fingerprints, recursive upstream validation, and an audited environment lock.
- Reframed model metrics as agreement with rule-derived proxy labels and
  snapshot-relative stability diagnostics, never external or temporal validation.
- Made the manual-review queue label-preserving and URL-audited; no human label
  or unavailable source evidence is inferred.

### Verification

- The original R3 review and remediation reports are preserved in Git history.
  For current checks and limitations, see [the project review](docs/project_review_2026_09.md)
  and [the generated findings](docs/findings.md).

## [1.2.0] — 2026-07-18 — Review R2 defensibility and pipeline safety

### Changed

- Added a source-detail procedure taxonomy that separates standard-open,
  price-quotation, minimum-value, negotiated, framework-mini-tender, and
  unknown records. Single-bidder reporting now separates procedure subtype,
  award state, value band, and year; no EU-equivalence claim is made.
- Made generic and standard-open single-bidder indicators mutually exclusive.
  Data-quality/operational diagnostics remain visible but carry zero composite
  weight; the score is explicitly an author-selected review priority, not a
  calibrated probability.
- Withdrew the prior OSHP external-validation result. The cached source has no
  outcome, case/date, tender identifier, or exact outcome-to-procurement link,
  so supplier-name overlap is no longer expanded into tender labels.
- Reworked supplier summaries and concentration views around a documented
  business-ID-else-normalized-name fallback key, isolated unidentified value, and added
  business-ID-only sensitivity plus row/value coverage. No national or broad-
  category HHI is interpreted as a relevant market.
- Split immutable `gold/tender_features.parquet` from the scored
  `gold/tender_summary.parquet`; gold and ML now have one canonical writer each.
  Benchmark/ML fingerprints include feature values, label placement, and a
  protocol version, and stale champions fail closed.
- Preserved missingness indicators during model preprocessing; corrected KNN
  self-membership using the fitted reference index; removed duplicate benchmark
  configurations and isolated quick/full result sets.
- Added unknown-date monthly reconciliation, no-award display semantics,
  atomic artifact publication, pre-publication DQ gates, decompressed-content
  bronze update detection, and scheduled remote update checks.
- Reframed all UI/docs/model reports as a static retrospective heuristic review
  queue with an exploratory snapshot-relative ML ranking. Stored notebook
  claims are either regenerated or prominently marked historical/superseded.
- Aligned the hand-written architecture/ADR specifications with the immutable
  `tender_features` → benchmark → ML-scored `tender_summary` chain, and aligned
  package metadata with release version 1.2.0.
- Added a deterministic, provenance-bound four-quadrant manual-audit queue and
  protocol. The generated sample is explicitly unlabelled until human review.

### Verification

- Added regression coverage for taxonomy, rule exclusivity, missing award
  semantics, identity-sensitive concentration, monthly reconciliation, stale
  benchmark guards, atomic writers, bronze validation, and Streamlit caveats.

## [1.1.0] — Benchmark rigoroz shumë-modelësh + UI në shqip

### Shtuar
- **4 familje të reja detektorësh** (`anomaly/detectors.py`): gabimi i
  rindërtimit PCA, Gaussian Mixture, distanca KNN, HBOS — plus fabrika
  `build_scorer(family, params)` për të 8 familjet.
- **Motori i benchmark-ut** (`anomaly/benchmark.py`): rrjeta
  hiperparametrash për 8 familje të pambikëqyrura + 4 klasifikues të
  mbikëqyrur (~440 trajnime); AUC proxy me dy pragje, Precision@500,
  stabilitet bootstrap (Jaccard i bashkësive top-5 %), konsistencë
  seed-esh, **validim jashtë-kohor** (trajno ≤ 2023, testo ≥ 2024),
  Brier + ECE. Checkpoint/resume përmes `results.jsonl`
  (vetë-riparues, me gjurmë të dhënash me hash vlerash).
- **Zgjedhje modeli e drejtuar nga benchmark-u**: `champions.json`
  konsumohet nga `pipeline/ml.py`; ansambli përbëhet nga familjet top-K
  të zgjedhura me formulën e përbërë
  `0.45×AUC(0.7) + 0.35×stabiliteti + 0.20×konsistenca`.
- **Kolona të reja pikësh në gold**: `pca_score`, `gmm_score`,
  `knn_score`, `hbos_score`; vota e pajtimit tani me kuantile rangu
  (skalë-invariante) në vend të pragut absolut 0.7.
- **`pipeline check-updates`**: kontroll për rekorde të reja të
  tenderëve me shkarkim paralel dhe swap atomik (bronze-i ekzistues
  nuk preket kurrë nga një shkarkim i dështuar).
- **Faqe e re Streamlit "Krahasimi i Modeleve"** (shqip) me leaderboard,
  grafikun saktësi↔stabilitet, rënien CV→OOT dhe kampionët.
- **UI tërësisht në shqip** + `docs/responsible_use.md` në shqip.

### Rregulluar (nga rishikimi adversarial 3-lentësh para trajnimit)
- LOF vlerësohej in-sample me `novelty=True` (përdorim i ndaluar nga
  sklearn) — tani përdoren pikët e pa-anshme `negative_outlier_factor_`
  të ruajtura në fit.
- KNN me nën-mostër: rreshtat jashtë bashkësisë referencë merrnin
  distancën e fqinjit (k+1) në vend të k — tani zgjedhje kolone për
  rresht sipas vetë-përputhjes.
- `learning_rate` i kampionit HGB binte në heshtje (hardcoded 0.08) dhe
  procedura e trajnimit në benchmark (pa pesha) ndryshonte nga ajo e
  vendosjes (me pesha të balancuara) — të dyja të bashkërenduara.
- Raporti i validimit vlerësonte hiperparametrat default në vend të
  kampionit të vendosur.
- `results.jsonl`: lexim tolerant ndaj rreshtave të cunguar + mbrojtje
  newline në append (vetë-riparim pas ndërprerjeve).
- Freskia e DAG-ut ankorohej gabimisht (gold rishkruhet nga ml) — tani
  ankorë `GOLD_MONTHLY`, që e shkruan vetëm gold.
- `--only` me emër të gabuar detyre tani ngre gabim në vend që të
  ekzekutojë asgjë në heshtje.
- Quick-mode i benchmark-ut shkruan në `*.quick.*` dhe nuk mund të
  rrëmbejë zgjedhjen kanonike të modelit.

## [1.0.0] — Senior-DE reform

### Added
- **`pyproject.toml`** as the single source of truth for dependencies and
  tool configuration (replacing `requirements.txt`, which is now derived).
- **`src/thesis/`** restructured into subpackages: `config`, `logging`,
  `lineage`, `paths`, `domain` (contracts + features + schemas), `io`
  (readers + writers), `dq` (framework + suites), `anomaly` (rules,
  models, comparison, ensemble, validation, explanations), `pipeline`
  (bronze, silver, gold, ml, dag).
- **Pydantic Settings** (`thesis.config.Settings`) — every parameter is
  overridable via environment variables.
- **Structured logging** with `structlog` + run-id context, console and
  JSON formats.
- **Lineage sidecars** — every Parquet output gets a
  `<file>.lineage.json` recording inputs, hashes, schema fingerprint,
  git SHA, build duration, run id.
- **Multi-model anomaly ensemble**: Isolation Forest, Local Outlier
  Factor, Elliptic Envelope, One-Class SVM (subsample-fitted),
  HistGradientBoosting (supervised on weak rule labels for SHAP only).
- **Contextual comparison score** — z-scores within procuring entity,
  category, method.
- **Validation framework** — k-fold CV, stability bootstrap,
  inter-model Spearman agreement, calibration / ECE.
- **Typer CLI** — `thesis pipeline run`, `thesis pipeline status`,
  `thesis dq run`, `thesis info`, `thesis ui`.
- **Internal DAG runner** with freshness checks (skip-if-fresh, force).
- **Airflow DAG** in `airflow_dags/kosovo_procurement.py` — same CLI
  used locally, `BashOperator` wrappers for prod.
- **Pandera DataFrame schemas** alongside Pydantic row contracts.
- **DQ expectation framework** (`thesis.dq.framework`) with per-table
  suites; outputs JSON + Markdown to `data/dq/`.
- **Streamlit Validation page** showing CV, stability, agreement,
  calibration evidence.
- **Caveat banner** — every page reminds users that anomaly ≠ fraud.
- **Docker** — multi-stage `Dockerfile`, `docker-compose.yml` for
  local dev, non-root user, healthcheck.
- **CI** — `.github/workflows/ci.yml` with ruff, mypy, pytest matrix,
  Docker build, integration smoke test.
- **Pre-commit** — trailing whitespace, ruff (lint + format), mypy.
- **Five ADRs** under `docs/adr/`.
- **Operations runbook** `docs/operations.md` and **Responsible-use**
  document `docs/responsible_use.md`.

### Removed
- Top-level scripts `fetch_data.py`, `build_silver.py`, `build_gold.py`,
  `train_models.py`, `dq_profile.py`, `dq_silver.py`, `profile_data.py`,
  `build_dq_notebook.py` — all functionality lives in the CLI.

## [0.1.0] — Bachelor thesis prototype

### Added
- Bronze→silver→gold pipeline (Parquet medallion architecture).
- 11 rule-based detectors + Isolation Forest + HistGradientBoosting/SHAP.
- Streamlit demo with Home / Overview / Explore / Anomalies / Entities
  / Methodology pages.
- Two notebooks for EDA and DQ.
- 19 unit + Streamlit-page tests.
- README, architecture, methodology, findings docs.
