# Findings — Kosovo Public Procurement

> **Auto-generated from the live gold layer** at `2026-07-19T12:30:35.687388+00:00` by `thesis report findings`. Numbers are recomputed from the declared gold, silver and model inputs; do not hand-edit.
> Input hashes: `tender_summary.parquet:1dfdb7155539` · `awards.parquet:3498ec4d4157` · `supplier_summary.parquet:7a2811d4c682` · `validation_report.json:f22db44cfe82` · `champions.json:733b592ab098` · `gold.release.json:d893acf1204f` · `benchmark.release.json:12a9ca82afc5` · `ml.release.json:fa0b3834c5b6` · `manual_audit_sample.metadata.json:4b375b85ef45`

> ⚠️ **This is a bachelor-thesis research project, not an official government tool.** Anomaly flags are signals for review, never proof of wrongdoing. See `docs/responsible_use.md`.

## 1. Scale

- Tenders: **75,710**  ·  awarded: **54,133**
- Award rows (silver, post-dedup): **62,129**
- Total estimated: **€10.49 bn**  ·  total awarded: **€4.77 bn**
- Populated procuring-entity IDs: **205**  ·  resolved supplier keys (business ID, else normalized name, else source party): **9,940**
- Scope: records in KRPP/OCP OCDS publication 115; this is not a claim of complete national-census coverage.
- Award→lot title linkage: **61,260** exact unique · **244** exact ambiguous · **505** no exact match · **120** missing award lot title. Award values and ratio diagnostics therefore remain tender-level; title equality is not treated as a verified lot identifier.

## 2. Single-bidding — source subtype and eligible population

The coarse OCDS value `open` mixes ordinary open procedures with a distinct price-quotation procedure (consolidated Regulation 001/2022 as amended by 002/2024, Arts. 12.3 and 51.3; Art. 51.5 sets its five-day minimum), while official KRPP code 3 identifies design contests. The table keeps source subtypes separate and computes bidder rates only where bidder data was published. No EU equivalence is claimed because the external indicator's year, exclusions and denominator have not been replicated.

| Source subtype | All records | Bidder data observed | Single-bidder (observed) | Awarded records | Single-bidder (awarded + observed) | Median value |
|---|---:|---:|---:|---:|---:|---:|
| design_contest | 291 | 65 (22.3%) | 41.5% | 0 | — | €31,228 |
| framework_mini_tender | 930 | 929 (99.9%) | 9.8% | 925 | 9.8% | €15,519 |
| minimum_value | 11,840 | 11,839 (100.0%) | 79.7% | 11,802 | 79.7% | €980 |
| negotiated_with_notice | 6 | 6 (100.0%) | 0.0% | 5 | 0.0% | €510,000 |
| negotiated_without_notice | 4,572 | 4,568 (99.9%) | 86.1% | 4,163 | 86.5% | €19,669 |
| price_quotation | 18,383 | 16,129 (87.7%) | 31.0% | 12,726 | 27.6% | €5,227 |
| restricted | 38 | 31 (81.6%) | 25.8% | 24 | 12.5% | €450,000 |
| standard_open | 39,650 | 36,036 (90.9%) | 24.0% | 24,488 | 22.1% | €55,000 |
| **pooled (descriptive only)** | 75,710 | — (91.9%) | **39.0%** | — | — | — |

### Awarded standard-open records by value band

| Estimated-value band | Records | Single-bidder % |
|---|---:|---:|
| ≤€10k | 504 | 30.0% |
| €10k–€100k | 15,903 | 23.9% |
| >€100k | 8,080 | 17.9% |

### Awarded standard-open records by year

| Year | Records | Single-bidder % |
|---:|---:|---:|
| 2016 | 4 | 0.0% |
| 2017 | 1,473 | 17.4% |
| 2018 | 1,835 | 16.4% |
| 2019 | 2,318 | 16.4% |
| 2020 | 2,151 | 12.7% |
| 2021 | 2,612 | 21.1% |
| 2022 | 3,449 | 21.8% |
| 2023 | 3,892 | 24.4% |
| 2024 | 3,672 | 27.6% |
| 2025 | 3,062 | 29.9% |
| 2026 | 13 | 46.1% |

Year-level rates support time-matched comparison; none is interpreted here as detection evidence.

## 3. Supplier concentration — identity sensitivity, not market HHI

Broad procurement categories are not defensible relevant markets. The descriptive concentration below is therefore a sensitivity check only. It reports name-first, published-party-ID-first and business-ID-only sensitivities with coverage. A source party ID is publication identity, not a verified legal identifier; every fallback can split or merge firms.

| Category | HHI (ID/name/party fallback) | HHI (ID/party/name) | HHI (ID only) | Top-1 (name-first) | Name-first coverage | Party-first coverage | ID coverage | Keys |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| goods | 113 | 113 | 197 | 6.6% | 100.0% / 100.0% | 100.0% / 100.0% | 77.8% / 73.5% | 3,567 |
| services | 52 | 52 | 111 | 2.1% | 100.0% / 100.0% | 100.0% / 100.0% | 71.2% / 56.6% | 4,490 |
| works | 30 | 29 | 102 | 2.5% | 100.0% / 100.0% | 100.0% / 100.0% | 55.6% / 34.4% | 3,746 |

No national or broad-category figure is interpreted as a healthy, moderate or concentrated *market* without a defensible market definition. Unknown-one-group and unknown-distinct-row scenarios are retained in the computed report data; they are allocation sensitivities, not truth bounds.

## 4. Transparent indicator registry — counts live

There are **15** visible indicators; only **4** contribute author-selected priority points. The remaining diagnostics cannot train the weak-label target.

| Indicator | Type | In score | Weight | Records | % |
|---|---|---:|---:|---:|---:|
| `SINGLE_BIDDER` | review | yes | 0.25 | 18,484 | 24.41% |
| `SINGLE_BIDDER_OPEN` | review | yes | 0.75 | 8,649 | 11.42% |
| `RATIO_BELOW_50` | data_quality | no | 0.0 | 3,668 | 4.84% |
| `UNAWARDED_HIGH_VALUE` | operational | no | 0.0 | 1,625 | 2.15% |
| `RATIO_ABOVE_ESTIMATE` | data_quality | no | 0.0 | 1,373 | 1.81% |
| `BUYER_NAME_ID_COLLISION` | data_quality | no | 0.0 | 550 | 0.73% |
| `WINNER_TAKES_ALL_LARGE` | review | yes | 0.5 | 426 | 0.56% |
| `LOT_VALUE_MISMATCH` | data_quality | no | 0.0 | 260 | 0.34% |
| `HIGH_VALUE_SINGLE` | review | yes | 0.75 | 101 | 0.13% |
| `ULTRA_SHORT_OPEN` | operational | no | 0.0 | 41 | 0.05% |
| `IMPLAUSIBLE_ESTIMATE` | data_quality | no | 0.0 | 25 | 0.03% |
| `END_BEFORE_START_OPEN` | data_quality | no | 0.0 | 9 | 0.01% |
| `PRICE_QUOTATION_VALUE_BAND_CONFLICT` | data_quality | no | 0.0 | 7 | 0.01% |
| `NEGATIVE_DAYS_TO_AWARD` | data_quality | no | 0.0 | 6 | 0.01% |
| `ZERO_BIDDER` | operational | no | 0.0 | 0 | 0.00% |

## 5. Triage populations (each clearly labelled)

- `rule_score_ge_0.5`: **235** (0.3% of tenders)
- `rule_score_ge_0.7`: **77** (0.1% of tenders)
- `ensemble_ge_0.5`: **24,690** (32.6% of tenders)
- `ensemble_ge_0.7`: **6,505** (8.6% of tenders)
- `high_confidence`: **2,453** (3.2% of tenders)

### Rule layer × ensemble — they substantially DISAGREE

The rule layer is the auditable heuristic baseline. The layered ensemble is exploratory and **not** a corroboration of it:

- both flagged: **235**
- rule-flagged but ensemble demoted it: **0** (0.0% of rule flags)
- ensemble-only (ML, unvalidated, no rule support): **24,455** (99.1% of ensemble flags)

## 6. Award value ratio (awarded ÷ estimated)

| percentile | value |
|---|---:|
| p25 | 0.76 |
| p50 | 0.936 |
| p75 | 0.995 |
| p95 | 1.0 |
| p99 | 1.238 |

## 7. Temporal coverage

- Span: **2016-03-25 → 2026-03-05**
- Distinct months with data: **118** of 121 calendar months in the span (3 missing — a publishing-coverage gap, not continuous coverage).

## 7b. External outcome validation — withdrawn

The bundled OSHP snapshot contains operator and authority names but no request outcome, case/activity identifier, decision date or exact tender link. Supplier-name overlap expanded to historical wins is therefore **not an outcome label set and is not reported as validation**. A future evaluation requires approved decisions linked to exact tenders and eligible controls, with supplier-clustered uncertainty.

## 7c. Manual outcome audit — not yet labelled

A deterministic stratified queue over the four possible quadrants has been generated for human document review: `both_flagged` 50, `rule_only` 0, `ensemble_only` 50, `neither` 50.
Empty source strata are reported rather than synthetically filled: `rule_only`.
Completed labels recorded in its provenance: **0**. Empty review fields are unreviewed, not negative labels. See `docs/manual_audit_protocol.md`.

## 8. What the thesis CAN legitimately claim

1. A reproducible **static, retrospective medallion pipeline** (bronze→silver→gold) over publication-115 records, with lineage, typed contracts and data-quality checks.
2. A **transparent heuristic indicator registry** (15 visible indicators; 4 score-enabled) producing calculator-reproducible author-selected priority points. References motivate constructs, not exact calibrated weights.
3. **Descriptive statistics** separated by source procedure subtype, award eligibility and supplier-identity coverage; no EU-equivalence or relevant-market conclusion is asserted.
4. An **exact additive XAI contract for the published hybrid score**: the released detector percentile ranks, rule score and context score reconstruct every `ensemble_score`; snapshot-baseline effects show which components raised or lowered the ordering. This explains the system arithmetic, not causation or wrongdoing.
5. A **surrogate supervised model** that reproduces the deterministic rule proxy with near-perfect AUC expected from heavily overlapping inputs, used **solely** for raw-feature attribution of its log-odds via SHAP. It does not explain `ensemble_score`, directly identify which rule fired, or provide independent evidence.
6. An **exploratory unsupervised layer** (a 4-model ensemble — ocsvm/iso/hbos/knn) that produces a ranking whose added value over the rules is **not yet validated** against external ground truth.
7. Every peer rank, quantile and detector calibration is relative to the complete shipped snapshot; scores are not stable single-row or live monitoring outputs.

## 9. What the thesis CANNOT claim

1. **Cannot** claim any measured *detection* performance. The AUC/OOT/proxy-AUC figures are agreement with the model's own deterministic inputs, not detection of anomaly or fraud.
2. **Cannot** claim temporal generalization — the out-of-time experiment measures only faithfulness to an internally generated rule proxy whose inputs overlap heavily with the model matrix.
3. **Cannot** claim the unsupervised layer 'surfaces real anomalies the rules miss' — the majority of the ensemble inbox is ML-only with no ground-truth check (see §5).
4. **Cannot** claim 'principled model selection' beat a rule-only baseline — no external validation was run.
5. **Cannot** claim SHAP explains the hybrid ensemble or gives independent evidence — it restates the rule proxy through overlapping raw features. The exact ensemble decomposition explains score arithmetic, not the real-world cause of a procurement pattern.
6. **Cannot** claim OSHP validation, calibrated confidence/risk, production monitoring, or score comparability across rebuilds.

**Defensible positioning:** *a static, transparent heuristic review queue with an exploratory unsupervised layer, exact component-level XAI for its published hybrid score, and a separately labelled rule-proxy SHAP surrogate; its ML ordering is engineered but not yet validated against external ground truth.*
