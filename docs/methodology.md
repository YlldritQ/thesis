# Methodology

This document explains *why* the pipeline does what it does. The
**architecture** doc covers *how*; the **findings** doc reports
*what we learned*.

## 1. Source data

The raw data is published in **OCDS 1.1** (Open Contracting Data
Standard) by Kosovo's Public Procurement Regulatory Commission. The
**Open Contracting Partnership** mirrors and re-publishes the feed at
`data.open-contracting.org/en/publication/115`. We download the
all-time JSONL bundle once and treat it as bronze. The submitted analysis
is a **static snapshot of Publication 115**: 75,710 records, with data in
118 of the 121 calendar months from 2016-03 through 2026-03. It is the
coverage of this publication, not a claim to contain every procurement
procedure conducted in Kosovo.

Each line in the JSONL is a *compiled OCDS release*: a single object
describing one contracting process from the tender publication through
to (zero or more) award decisions. An initial raw-source audit observed
60 distinct JSON paths; canonical run evidence is the current
`data/dq/*.dq.{json,md}` suite output rather than the legacy profile CSVs.

An OCDS `award` object is treated here as a **recorded award decision**.
The extract contains no evidence that a corresponding contract was signed,
executed or paid, so `awarded_value_eur` is described as recorded award value,
not contracted expenditure or actual spending.

## 2. Bronze → silver design choices

### One row per tender, one row per award

OCDS releases are heavily nested (`parties[]`, `tender.lots[]`,
`tender.tenderers[]`, `award[].suppliers[]`). For analytical use we
flatten into two relational tables:

* `silver.tenders` — one row per OCID (= per contracting process).
* `silver.awards` — one row per *(award, supplier)* combination, joined
  back to tenders via OCID.

One-to-many is the right relationship because:

* A single tender may contain recorded award decisions for multiple suppliers
  (the current post-dedup silver table has up to 53 award-supplier rows per
  OCID).
* Some tenders have zero recorded awards (28.5 %); the extract alone does not
  distinguish cancellation, an incomplete process, or an unpublished award.

Awards expose a free-text `lotTitle`, not a shared lot identifier. Silver
therefore records whether that title has one exact tender-lot match, several
exact matches, no exact match, or is missing. It never silently joins translated
or corrected titles. Award totals, value ratios, and winner shares remain
tender-level measures; they do not establish lot-level price comparability.

### Date semantics

The OCDS spec says `tender.tenderPeriod.startDate` is when bidding
opens and `endDate` is the submission deadline. In this publication,
`end_before_start` is strongly associated with the coarse method field:
0.02 % for **`open`**, versus 99.97 % and 99.09 % for **`minimum`** and
**`limited`**. The extract does not establish why those date orderings differ,
so no contract-performance or process-delay explanation is inferred.

We don't try to "fix" the source. Instead we expose:

* `start_date`, `end_date` — exactly as published.
* `duration_reported_days` — publisher's reported number.
* `duration_computed_days` — `(end_date - start_date)` in days, signed.
* `end_before_start` — boolean flag.

The final component of the published procurement identifier is retained as
`procedure_code`. The PPRC [official secondary-legislation
register](https://e-prokurimi.rks-gov.net/HOME/ClanakItemNew.aspx?id=233) lists
[Regulation 001/2022](https://e-prokurimi.rks-gov.net/HOME/Documents/Legislation/SecondaryLegislation/eng/A01%20Regulation%20No.001_2022%20on%20Public%20Procurement.pdf)
and [amending Regulation
002/2024](https://e-prokurimi.rks-gov.net/HOME/Documents/Legislation/Rregulloret/shq/FINAL%20DRAFT%20RRPP%2006.11.2024.pdf)
as official acts. Article 12.13 of Regulation 001/2022 maps codes 1–8,
including code 3 **design contest**, code 6 **price quotation**, and code 8
**mini-competition**. A separate [PPRC-hosted consolidated
text](https://e-prokurimi.rks-gov.net/HOME/Documents/Legislation/Rregulloret/shq/versioni%20i%20konsoliduar%20i%20Rregullores%20Nr.%20001%202022%20i%20plot%C3%ABsuar%20dhe%20ndryshuar%20me%20Rregulloren%20Nr.%20002%202024.pdf)
renumbers this mapping as Article 12.3, but its cover expressly labels it a
non-official convenience text; it is used only as a reading aid, not as legal
authority. The official [predecessor 2016 Rules and
Operational Guidelines
annex](https://e-prokurimi.rks-gov.net/HOME/Documents/Legislation/Aktet%20dyt%C3%ABsore%20te%20shfuqizuara/eng/A01%20Rules%20and%20Operational%20Guidelines%20for%20Public%20Procurement.pdf)
independently maps codes 1–7 for the historical period; source detail labels
for code 8 are also consistently mini-tender/mini-competition. The code is used
as publication semantics, not as a retroactive legal determination, and takes
precedence over the coarser OCDS method/detail text.

Articles 51.3 and 51.5 of official Regulation 001/2022 respectively limit
price quotation to the stated low-value and subject-matter circumstances and
give a five-day minimum. The official [consolidated Public Procurement Law, Article
19](https://e-prokurimi.rks-gov.net/Home/Documents/Legislation/Ligjet/eng/PPL%20consolidated.pdf)
defines low value as at least EUR 1,000 and below EUR 10,000. Code-6 records at
or above EUR 10,000 are therefore surfaced as a zero-weight data-quality review
diagnostic; the generated findings report supplies the live count. This is
never an automated finding of illegality.

The short-period diagnostic applies only to source-identified standard-open
records and remains zero-weight because urgency, corrigenda, historical legal
versions, and all exceptions are not encoded. A hit is not a finding of a
breached deadline.

### Currency, encoding

100 % of tender-value and award-value rows with a published currency are in
EUR. We don't store the currency column
beyond the silver layer to save space.

Most text fields are Albanian. The `tender.procurementMethodDetails`
field, oddly, is in Serbian/Bosnian (`otvoreni postupak`,
`postupak bagatelne nabave`). We expose it as-is rather than
translating.

### Pydantic validation

Both silver tables are validated against
`src/thesis/domain/contracts.py:TenderRecord` and `AwardRecord`. Every row is
validated before publication, undeclared fields are forbidden, and a Pydantic
or Pandera contract error always blocks canonical publication. The
`fail_fast_on_dq` setting controls warning policy; it cannot downgrade a schema
or row-contract error.

## 3. Silver → gold feature engineering

`src/thesis/domain/features.py:build_tender_features` produces the immutable
`tender_features` table. The gold stage adds transparent rule flags and writes
that artifact; the benchmark reads it, and the ML stage is the sole writer of
the scored `tender_summary` table. Highlights:

| Feature                         | What it captures                                    |
|---------------------------------|-----------------------------------------------------|
| `log_estimated_eur`             | Tender size, log-scaled (values span 7 orders)      |
| `awarded_value_ratio`           | `total_awarded_eur / estimated_value_eur`           |
| `winner_top_share`              | Within-tender supplier concentration (0..1)         |
| `value_rank_within_entity`      | Percentile of value among the same entity's tenders |
| `value_rank_within_method`      | Percentile within method (controls for size)        |
| `entity_tender_count`           | How many tenders this entity issues overall         |
| `is_single_bidder`              | Descriptive low-competition indicator               |
| `bidder_data_missing`           | Tenderer list/roles were not published               |
| `is_zero_bidder`                | An explicitly observed count of zero                 |
| `lot_value_mismatch`            | Sum-of-lots ≠ total — a soft data-quality flag      |
| `end_before_start`              | Schema quirk surfaced for downstream filtering      |
| `days_to_first_award`           | Recorded date ordering; negative requires source review |

The authoritative list is `ML_FEATURES` in that module; the current
registry contains **20** numeric features. Documentation and UI counts
should be derived from that constant rather than copied by hand.

### Supplier identity used in aggregation

Known business-ID sentinels are normalised to null while the raw source value
is retained. Reports then expose three different identity assumptions:

1. business ID → normalised name → source party ID/UID (the established,
   name-first supplier-summary view);
2. business ID → source party ID/UID → normalised name (a source-identity
   sensitivity used for tender winner concentration); and
3. business-ID-only.

The source party ID/UID is stable identity inside this publication, not an
externally verified legal-business identifier. Name-first keys can merge firms;
party-first keys can split one legal firm. Entity/category HHI therefore reports
both views, the business-ID-only view, value coverage, and two transparent
unknown-allocation scenarios. Those scenarios are sensitivities, not formal
bounds on the unknown truth, and no HHI is interpreted as a national or
relevant-market measure.

`tender.tenderers[]` is counted when the array is published; tenderer party
roles are a fallback. If neither is published, `num_bidders` remains null and
`bidder_data_observed=false`. Competition rates use only observed records.
Missing publication is never silently recoded as zero bidders.

## 4. Anomaly scoring

We use a **layered ensemble** because each component has distinct strengths
and weaknesses:

### Rule layer — transparent and snapshot-reproducible

The boolean rules are encoded in `src/thesis/anomaly/rules.py:RULES`.
The current registry contains **15** entries; this count is derived from
the registry in the UI. Each rule has:

* a **code** (e.g. `SINGLE_BIDDER`)
* a **description** in plain English
* a **weight** (0 – 1.0) expressing the author's heuristic review
  priority; it is not a calibrated probability

The composite `rule_score` is `clip(sum(weights × triggered) / 2.0, 0, 1)`.

* contextual `SINGLE_BIDDER` contributes `0.25 / 2 = 0.125`
* `SINGLE_BIDDER_OPEN` is mutually exclusive with the generic variant and
  contributes `0.75 / 2 = 0.375`, below the 0.5 review threshold
* zero-weight data-quality/operational indicators remain visible but do not
  contribute to the composite or weak-label target
* the review thresholds are heuristic operating choices, not calibrated
  risk bands
* `score = 1.0` is the saturating ceiling

Rule descriptions and weights are exposed in the Streamlit
**Methodology** page and in `rule_descriptions()`.

### ML layer — exploratory, unsupervised, **unvalidated**

A benchmark evaluates **23 unsupervised configurations across 8 families**
and **12 supervised configurations across 4 families**, then elects four
champion unsupervised families fitted on the 20-feature matrix. The exact
elected bundle is recorded in `data/models/benchmark/champions.json`. Each
produces a snapshot-relative `[0, 1]` score and an exploratory ranking
of records that are statistically unusual in the current feature matrix.

Checkpoint reuse is bound to the exact data fingerprint, declared thresholds,
grids/seeds and SHA-256 manifest of the source files that can affect fitting,
evaluation, or election. Full WIP and quick checkpoints are separate. A full
sweep mutates only `results.wip.jsonl`, keeping the prior release valid; after
completeness and semantic checks it atomically snapshots `results.jsonl`. The
full benchmark release hash-binds that snapshot, the leaderboard, champions and a
semantic DQ proof; the ML reader recomputes the complete deterministic election
from those released rows before accepting a champion. This proves generation
consistency and reproducibility of the election, not correctness of its proxy
objective.

**Honest status:** this layer is *exploratory*. Its added value over a
rule-only baseline is **not validated** against external ground truth,
and the benchmark's selection objective rewards agreement with the rules
and reproducibility, not detection. Treat it as a secondary ranking, not
a detector.

The declared 0.45/0.35/0.20 election is accompanied by alternate balanced,
stability-emphasis and proxy-emphasis weights plus a `precision@K`-only rank
comparison. The deployed models are also refit on a lower-derived fact subset
and a pre-outcome-field subset; only Spearman and top-5% membership overlap are
reported. These are **sensitivity analyses**, not validation or hyperparameter
selection against external outcomes. The pre-outcome-field subset still uses a
static full-period snapshot, so it cannot establish temporal generalisation.

### Ensemble — and why it DISAGREES with the rules

`ensemble_score` is the mean of the four champion detector-rank percentiles,
`rule_score`, and `context_score` (detector scores are rank-transformed within
the current snapshot to be scale-comparable). `high_confidence` is historical
column naming: it means
that at least **3 of the 4** champion detectors place a record in their
current-batch **top 5%**. It is rank agreement, not calibrated confidence
and not evidence of fewer false positives.
The validation report also recomputes this vote at q=0.90, 0.95 and 0.99 and
reports membership Jaccard against the declared threshold. That comparison
measures operating-definition sensitivity only.

The rule layer and the ensemble **substantially disagree** on the shipped
data (see the regenerated confusion table in `findings.md §5` and
`validation_report.json:rule_only_baseline_and_confusion`). We therefore
treat the **rule layer as the auditable heuristic baseline** and the
ensemble as an exploratory add-on, not a corroboration.

### Exact XAI for the published hybrid score

The ML release persists the complete-snapshot percentile rank for every
elected detector and a versioned `ensemble_explanation` contract. For the
current four-family election, every row is reconstructed as:

```text
ensemble_score = (
    rank(OCSVM) + rank(Isolation Forest) + rank(HBOS) + rank(KNN)
    + rule_score + context_score
) / 6
```

The family list and denominator are read from the released ML metadata rather
than hard-coded by the dashboard. Ties use pandas' `average` percentile-rank
method over the **complete released snapshot**. The dashboard shows each
component's value, equal weight and direct contribution. It also records a
complete-snapshot mean baseline for every component, giving the exact identity
`baseline_score + sum(effect_vs_baseline) == ensemble_score`. Release DQ and
model-artifact validation reject any rank, family, agreement-count or score
that does not reconstruct.

This is intrinsic, component-level XAI for the score that actually produced
the ordering. It explains **which system layers raised or lowered the score**;
it does not explain causation, prove that the underlying event is improper, or
turn the score into a probability. The rule component is further explained by
the exact triggered weights and clipping arithmetic. The context component is
further explained by the signed z-score(s) attaining `max(abs(z))` in
`tanh(max(abs(z))/2)`. A separate table shows input percentiles and missingness
frequency only as descriptive feature context, not as measured detector
contributions.

### SHAP / supervised rule surrogate — separate proxy-faithfulness explanation

We train a **HistGradientBoostingClassifier** against the binary label
`(rule_score >= 0.4)`. The target is a deterministic proxy built mostly from
the same or heavily overlapping raw features in `X` (although procedure
subtype itself is not supplied to the model). This overlap explains the
near-perfect **ROC-AUC**; the result is proxy-faithfulness, not detection
performance. It says *nothing* about anomaly or fraud.

Its only legitimate use is to make the rule proxy **differentiable** so
SHAP can attribute the surrogate prediction. The waterfall chart shows
contributions to the classifier's raw **log-odds** output; it does **not**
identify which rules fired and does **not** explain `ensemble_score`. Exact
triggered-rule contributions and exact ensemble-component contributions are
displayed separately. Every rule-label metric
in this project (CV AUC, OOT AUC, proxy-AUC, precision@K-vs-rules) is a
**faithfulness-to-rules** measure and must never be presented as
detection performance.

The ≤2023/≥2024 split is therefore a **temporal rule-faithfulness
check**, not a real-use simulation or evidence of temporal generalisation:
the rule-derived target and model inputs overlap heavily, even though the
exact procedure-subtype field is not in the numeric model matrix.

### Manual-audit status

After the final ML build, `python -m thesis report audit-sample` creates a
deterministic, frozen sample from all four rule×ensemble quadrants. The output
is deliberately **unlabelled**: blank review fields mean “not reviewed,” not a
negative outcome. It provides the queue and provenance needed for a future
document review; it does not validate the ML layer. Until reviewers complete
and independently check those judgements, the ranking remains unvalidated
against tender-level outcomes. See `docs/manual_audit_protocol.md`.

## 5. What this approach can and cannot do

**Can do**

* Compute transparent heuristic review signals (single-bidder, ratio
  diagnostics, date inconsistencies, winner concentration) at the
  publication-snapshot level.
* Produce an exploratory rank of unusual feature combinations for human
  inspection, without claiming that the ranking detects misconduct.
* Reconstruct the published hybrid score exactly from its detector-rank,
  rule and context components, including effects relative to the released
  snapshot baseline.
* Show exact triggered-rule and context arithmetic, descriptive feature
  percentiles, and separately labelled raw-feature SHAP contributions to the
  rule-proxy surrogate.
* Generate a reproducible, unlabelled four-quadrant queue for subsequent
  human document review.

**Cannot do**

* Confirm fraud. Indicators can prompt source-quality, operational, or
  contextual review; only an auditor with documents in hand can assess
  misconduct.
* Estimate precision or a false-positive rate before the manual queue has
  actually been reviewed; unlabelled rows are not negative examples.
* Detect collusion. Bidder-coordination patterns require cross-tender
  analysis (network features) that we haven't yet engineered.
* Adapt without retraining. The rule weights and the contamination
  parameter are static. Peer ranks, quantiles and detector calibration are
  recomputed on the current batch, so the same record's score can change
  when the comparison population changes. A live system would need frozen,
  versioned reference statistics and evaluation against auditor labels.

## 6. Reproducibility checklist

* [x] Analytical table contents and rankings are deterministic given declared
      inputs, parameters, environment and fixed seeds; run timestamps,
      durations and run IDs are evidence metadata and can differ.
* [x] Pydantic contracts on silver inputs; tests on feature engineering
      and rule logic.
* [x] All thresholds and weights live in code, not in notebooks.
* [x] Benchmark rows bind relevant implementation hashes; a release-bound
      semantic check recomputes completeness and champion election.
* [x] Benchmark sensitivity reports are explicitly rank-only: three alternate
      weight schemes, a proxy precision rank, two deployed feature-subset
      refits, and q=0.90/0.95/0.99 vote membership.
* [x] For a frozen bronze snapshot, derived data/model/report artifacts are
      rebuildable from `make all`; any later human audit labels must be
      preserved separately and are never treated as rebuildable output.
