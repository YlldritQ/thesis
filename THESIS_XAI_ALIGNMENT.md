# XAI alignment remediation and verification

**Project:** Kosovo public-procurement heuristic screening and exploratory anomaly ranking  
**Project root:** `/Users/ylldrit/Desktop/thesis`  
**Remediation date:** 2026-07-19  
**Current canonical run:** `run-20260719T121903-10fc4e60`

## Outcome

The missing XAI link has been implemented. The project now explains the score that actually orders the review queue, rather than presenting the supervised rule-proxy SHAP output as though it explained that score.

The defensible alignment statement is:

> The project is a reproducible, static system for screening Kosovo public-procurement records with transparent rules, contextual comparison, and unsupervised anomaly rankings. For every released record, it provides an exact additive explanation of the hybrid review-priority score and separately labelled descriptive feature context and rule-proxy SHAP. Its outputs prioritize human review; they are not findings of fraud, corruption, illegality, collusion, or calibrated risk.

This is an engineering and exploratory-analysis alignment result. It is **not** evidence that the ranking detects real-world misconduct or has known precision, recall, or false-positive rates.

## What was genuinely missing

Before this remediation:

- detector percentile ranks existed only transiently while the ML stage calculated `ensemble_score`;
- the released scored table did not preserve those ranks, so a dashboard reader could not prove the per-record arithmetic from immutable artifacts;
- the Anomalies page displayed raw detector scores under language that implied the values used in the hybrid formula;
- the SHAP chart was labelled as an anomaly-score explanation even though it explains the HGB model trained to reproduce a rule-derived proxy;
- there was no versioned XAI contract binding component order, rank scope, tie method, weights, baselines, agreement threshold, and interpretation to the ML release;
- release DQ did not independently recompute the complete hybrid score and SHAP raw-output additivity.

The anomaly-ranking method itself was already arithmetically decomposable. The defect was that this decomposition was neither persisted, integrity-checked, nor faithfully shown to the user.

## Implemented explanation contract

### Actual deployed score

For the current release, the benchmark elects `ocsvm`, `iso`, `hbos`, and `knn`. For every record `i` in the complete released snapshot:

```text
ensemble_score_i = (
    rankpct_average(ocsvm_score_i)
  + rankpct_average(iso_score_i)
  + rankpct_average(hbos_score_i)
  + rankpct_average(knn_score_i)
  + rule_score_i
  + context_score_i
) / 6
```

Detector ranks use pandas percentile ranks with `method="average"` over all 75,710 released rows. They are not recomputed over a dashboard filter. Each of the six current components has weight `1/6`. Family selection and the number of components come from released metadata rather than a dashboard constant.

The primary implementation is in:

- `src/thesis/anomaly/ensemble.py`: the single composition/decomposition function, complete-snapshot rank transform, exact direct contributions, mean-reference effects, per-record fail-closed reconstruction, and versioned metadata contract;
- `src/thesis/pipeline/ml.py`: persistence of elected-family ranks and use of the shared composition for `ensemble_score`, agreement, and high-confidence fields;
- `src/thesis/dq/suites.py` and `src/thesis/anomaly/artifact_integrity.py`: independent recomposition and release-time tamper checks.

### Exact explanation levels now available

| Explanation level | Status | Meaning |
|---|---|---|
| Hybrid-score decomposition | Exact | Component values × weights sum to the released `ensemble_score`. |
| Detector-rank contribution | Exact | Shows the elected detector's complete-snapshot percentile rank and its direct contribution. |
| Rule contribution | Exact | Shows each triggered score-enabled rule, weight, normalization, clipping, and zero-weight diagnostics separately. |
| Context driver | Exact at implemented component level | Shows the signed contextual z-score driver(s) whose maximum absolute value produces `context_score`. |
| Feature percentiles/missingness | Descriptive only | Describes unusual inputs; it is not detector attribution or causality. |
| HGB SHAP | Exact for the surrogate's raw output | Reconstructs rule-proxy raw log-odds; it does not explain `ensemble_score`. |
| Feature attribution inside each unsupervised detector | Not claimed or implemented | This remains outside the current contribution. |

### Baseline identity

The release stores the complete-snapshot mean for every component. For each record:

```text
baseline_score + sum(effect_vs_baseline) == ensemble_score
```

The current baseline score is `0.43699591144885175`. This identity explains which score components raised or lowered a record relative to the shipped snapshot mean. It does not explain intent, causality, or real-world wrongdoing.

### Worked released-record example

For `ocds-uhzcmx-701-22-1274-1-1-1`, the highest-scored current record:

| Component | Value in formula | Weight | Direct contribution |
|---|---:|---:|---:|
| `ensemble_rank_ocsvm` | 0.9953374719323735 | 1/6 | 0.16588957865539558 |
| `ensemble_rank_iso` | 0.9911240258882579 | 1/6 | 0.16518733764804297 |
| `ensemble_rank_hbos` | 0.9780346057324000 | 1/6 | 0.16300576762206667 |
| `ensemble_rank_knn` | 0.9961167613261128 | 1/6 | 0.16601946022101880 |
| `rule_score` | 1.0000000000000000 | 1/6 | 0.16666666666666666 |
| `context_score` | 0.8842698349625934 | 1/6 | 0.14737830582709890 |
| **Sum / released score** |  |  | **0.9741471166402895** |

The same record's exact rule arithmetic is `0.75 + 0.75 + 0.50 = 2.00`, divided by the documented normalizer `2.0`, producing `rule_score = 1.0`. The triggered score-enabled indicators are `SINGLE_BIDDER_OPEN`, `HIGH_VALUE_SINGLE`, and `WINNER_TAKES_ALL_LARGE`. Its contextual driver is `log_value_z_within_category = 2.790034351468596`, which reconstructs `context_score = 0.8842698349625934`.

## Dashboard alignment

`streamlit_app/pages/3_Anomalies.py` now:

- loads score, SHAP, and model metadata through one generation-guarded dashboard bundle;
- composes ranks once over the complete released table and verifies them against the four persisted rank columns;
- fails closed when the published score and its explanation differ;
- displays each component value, equal weight, direct contribution, snapshot baseline, and effect against that baseline;
- displays exact triggered-rule arithmetic and the actual contextual driver;
- labels feature deviations as descriptive input context, not causal or detector-specific attribution;
- labels raw detector scores as diagnostics and identifies only the elected ranked families as ensemble inputs;
- gives SHAP its true target and output space: HGB rule-proxy raw log-odds;
- derives the agreement denominator, threshold, and elected families from release metadata.

`streamlit_app/Home.py`, the methodology/model-comparison pages, `README.md`, `docs/methodology.md`, `docs/responsible_use.md`, `docs/architecture.md`, ADR 0002, visualization labels, and generated findings language were updated to preserve the same separation.

## Files and artifacts changed

### Scoring, XAI, integrity, and readers

- `src/thesis/anomaly/ensemble.py`
- `src/thesis/anomaly/comparison.py`
- `src/thesis/anomaly/rules.py`
- `src/thesis/anomaly/explanations.py`
- `src/thesis/anomaly/artifact_integrity.py`
- `src/thesis/anomaly/__init__.py`
- `src/thesis/pipeline/ml.py`
- `src/thesis/dq/suites.py`
- `src/thesis/io/readers.py`
- `src/thesis/viz.py`
- `src/thesis/reporting.py`

### Dashboard and documentation

- `streamlit_app/_bootstrap.py`
- `streamlit_app/Home.py`
- `streamlit_app/pages/3_Anomalies.py`
- `streamlit_app/pages/5_Methodology.py`
- `streamlit_app/pages/7_Krahasimi_i_Modeleve.py`
- `README.md`
- `docs/methodology.md`
- `docs/responsible_use.md`
- `docs/architecture.md`
- `docs/adr/0002-multi-model-anomaly-ensemble.md`
- `docs/findings.md` (regenerated, not manually maintained)

### Tests

- `tests/unit/test_ensemble_explanations.py` (new)
- `tests/integration/test_xai_release.py` (new)
- strengthened DQ, reader, ML-pipeline, artifact-integrity, visualization, and Streamlit regression tests

### Current generated artifacts

- `data/gold/tender_summary.parquet`: 75,710 rows × 99 columns; now includes four `ensemble_rank_*` columns
- `data/models/feature_list.json`: versioned ensemble and SHAP explanation semantics
- `data/models/validation_report.json`: matching explanation contracts
- `data/models/shap_values.parquet`: 75,710 rows × 22 columns
- `data/dq/gold_tender_summary.release.dq.json`: exact ensemble-XAI reconstruction evidence
- `data/dq/ml_shap_values.release.dq.json`: exact rule-proxy raw-output reconstruction evidence
- `data/models/ml.release.json`: coherent manifest binding all of the above

## Quantitative before/after

| Measure | Before | After |
|---|---:|---:|
| Persisted elected detector ranks | 0 columns | 4 columns |
| Scored-table shape | 75,710 × 95 | 75,710 × 99 |
| Versioned deployed-score XAI contract | absent | present in both ML JSON artifacts |
| Full-snapshot `ensemble_score` reconstruction gate | absent | max absolute delta `0.0`; 0 mismatches |
| Persisted rank-column reconstruction | absent | max absolute delta `0.0` for all 4 columns |
| Agreement/high-confidence reconstruction | absent | 0 / 0 mismatches |
| SHAP target/scale integrity gate | absent | max raw-log-odds additivity delta `3.375077994860476e-14` |
| Per-record dashboard explanation | raw scores + ambiguously labelled proxy SHAP | exact hybrid components + exact rules/context + separately limited SHAP |

The hybrid scoring formula was not changed to manufacture a different thesis result. The remediation made its existing arithmetic explicit, persisted, testable, and user-visible.

## Current release facts

| Item | Current value |
|---|---|
| Canonical release ID | `run-20260719T121903-10fc4e60` |
| Raw OCDS JSONL SHA-256 | `666d239260114464142db43dfb1b85ed5b9cb508406461321859f7b1037122d4` |
| Data fingerprint | `03e8f6b3d597540b` |
| Protocol fingerprint | `0e377abdd3607b8d` |
| Global implementation fingerprint | `08b5b2ff559bb39a2477163aa9b97e1ea03418dc13e46c466dfee065715d513d` |
| Benchmark implementation fingerprint | `f411ec1ea85d2b9fd0089adc8dfa1222ccdeba8aa416bb9bbb878a54bebfb318` |
| Benchmark semantic fingerprint | `7516c9e49e6a4b975dfeffedff43b504b9b2a46fdb376de46e3f743e91c5a1aa` |
| Configuration fingerprint | `a7e3c914421adf51649fe580583749cb0ac522e301967ddab6a7aecff8a6ba0c` |
| ML generation fingerprint | `ed7c535b7659b1b9a74b450ef8a83782f09a3932d5fcfc0eb6e8c48c964efa3b` |
| ML manifest SHA-256 | `fa0b3834c5b6f740580be31e445836149bc3af7d373131e74122600b531390c6` |
| Benchmark manifest SHA-256 | `12a9ca82afc585044f36ffe17f6dcbbb243b6d7b2ab958e24f51fb5e7fbf51b3` |
| Scored Gold SHA-256 | `1dfdb7155539dfec815ab6ffce067db76209c806c4ef286d1854b87d42f4b510` |
| Feature metadata SHA-256 | `08b117b64a4c4e40be2a3e3499c6e1ead59322f3ffb57604aa823a64ebc7cea8` |
| Validation report SHA-256 | `f22db44cfe82ae385c2120c26b18fe8db467995ef45f6186234749818af5ff6c` |
| SHAP artifact SHA-256 | `e0772d332e59c97276a7a7de8c4a3f32bfc23777ca7ae5025fa18f2f7ac19104` |
| Generated findings SHA-256 | `4803bee2e361bb1673eea6b55ace837c73388cbbc3e3f1b716fdbf0cc88a3ffd` |

## Verification performed

| Command/check | Result |
|---|---|
| `uv run python -m thesis pipeline run` | Passed all five stages; Bronze 75,710, Silver 75,710 tenders / 62,129 awards, Gold 75,710 features, benchmark 35/35 configurations with all 279 fits rerun, ML 75,710 scored + 75,710 SHAP rows. |
| `uv run python -m thesis pipeline status` | All stages fresh; all declared outputs present. |
| `uv run python -m thesis pipeline validate-releases` | Bronze, Silver, Gold, Benchmark, and ML manifests valid. |
| `uv run python -m thesis dq run` | All base suites passed; known Silver source-quality warnings remained non-blocking. |
| `uv run python -m thesis dq run --suite gold_tender_summary` | 7/7 checks passed; 0 errors/warnings, including exact XAI reconstruction. |
| Benchmark uniqueness check | 35 rows, 35 unique family/parameter/data/protocol keys, 35 successful, 0 failed. |
| `uv run ruff check .` | Passed. |
| `uv run ruff format --check .` | 92 files already formatted. |
| `uv run mypy src` | Passed; 45 source files. |
| `uv run pytest -q` | **349 passed** in 274.87 seconds on the final source/artifact state. |
| Notebook JSON + Python AST check | Both notebooks pass; 0 stored outputs and 0 execution counts. |
| Manual-review regeneration | 150 rows, 0 completed labels, 0 rows with review data, prior label-state hash preserved; empty `rule_only` stratum remains honestly empty. |

One earlier full-suite attempt overlapped a deliberate `docs/findings.md` regeneration and therefore recorded a transient live-render comparison failure; that run was not accepted as evidence. The comparison passed in isolation after artifacts were frozen, and the subsequent clean 349-test run passed completely.

### Independent non-implementer audit

A reviewer who did not implement the remediation performed a final read-only
rebind audit. The reviewer first found a real P2 dashboard contradiction: the
agreement-filter label used released metadata while its predicate still used a
literal threshold of three. The predicate, label, quantile, denominator, and
Home-page wording now all use validated release metadata, and a regression test
forbids the literal behavior.

After the final rebuild, the reviewer returned **PASS** for
`run-20260719T121903-10fc4e60`, with no remaining P0–P2 contradiction. The
independent checks reproduced all 35 unique benchmark configurations (279 fits),
zero full-snapshot rank/score/agreement mismatches, SHAP raw-log-odds additivity
within `3.375077994860476e-14`, current manifest/artifact hashes, generation-safe
dashboard behavior, and a 10/10 Streamlit smoke/regression subset.

### Manual-review preservation

- current sample SHA-256: `02672e2040e6199eb8fc8bef3cad04338c0c07b03bf4ec15deebe055f13fa79b`
- current metadata SHA-256: `4b375b85ef4584eac9e4e1175d564d460aa6fad77734c9c8c971d5eaba74f0ee`
- label-state SHA-256 before/after: `662e9fbaef0dbc09087a4d0ceae1503c2fa6673eba642a652fc5c08009fcb403`
- completed labels: `0`; no labels were created, inferred, or overwritten
- exact structurally usable document URLs: 124/150; the other 26 remain explicitly invalid, not fabricated

## Remaining evidence limitations

These are not responsibly fixable by code alone:

1. There are no independent tender-level outcome labels. Supervised metrics measure agreement with rule-derived labels, not anomaly-detection accuracy.
2. The cached OSHP data cannot be linked to exact tenders and lacks adjudicated outcomes; it remains withdrawn as external validation.
3. The current contribution explains the actual hybrid score at component level but does not provide genuine raw-feature attribution for each unsupervised detector.
4. Exact additivity proves score arithmetic, not why a procurement process occurred or whether conduct was improper.
5. Ranks and input percentiles are relative to Publication 115's complete frozen snapshot. They are not stable probabilities and need regeneration when the population changes.
6. OCDS award objects and values are recorded award decisions/values. The data does not prove signed contracts, execution, realized expenditure, or payment.
7. Legal applicability, entity resolution, lot linkage, and document conclusions still require official source evidence and qualified human review where the source data is insufficient.

Nonblocking P3 technical debt: the exported legacy helper `combine_scores()` is
not used by the canonical pipeline or dashboard and still replaces missing
inputs with zero. The deployed `compose_hybrid_ensemble()` path fails closed on
missing/non-finite inputs. Deprecating or hardening the legacy helper is a future
cleanup, not a limitation of the released score or its XAI contract.

## Examiner-facing conclusion

At the implemented and documented level, the project now includes a genuine XAI contribution: an exact, released, per-record explanation of the prioritization formula that combines unsupervised ranks, rules, and context. Keeping rule-proxy SHAP as a separate secondary explanation is methodologically honest.

The project is therefore aligned with the thesis subject **if the thesis is framed as an exploratory anomaly-screening and human-review-prioritization system**. It is not aligned with—and does not claim—the stronger subject of validated fraud/corruption detection, causal explanation, or real-world risk prediction.

For a fresh independent decision, use `THESIS_ALIGNMENT_REVIEW_PROMPT.md`. The prompt requires a new session to inspect the live project before reading this report or the earlier reviews.
