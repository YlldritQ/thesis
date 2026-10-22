# Methodology

This document explains *why* the pipeline does what it does. The
**architecture** doc covers *how*; the **findings** doc reports
*what we learned*.

## Purpose and contributions

The project asks how far openly published Kosovo procurement records
(OCDS Publication 115) can support a **transparent, reproducible review
queue**, and what such a queue can and cannot show without independently
verified outcomes. Its contributions are:

1. **A reproducible data pipeline** (bronze → silver → gold) with typed
   contracts, data-quality suites and hash-bound releases, so every
   published number can be traced to its inputs and code.
2. **Procedure-aware competition statistics.** The coarse OCDS method `open`
   mixes 39,650 standard-open records with 18,383 price quotations; separating
   them by the official procedure code (Regulation 001/2022, Art. 12.13) and
   keeping unpublished bidder data missing (never zero) changes the
   single-bidder picture materially (§2 of the findings).
3. **A transparent rule layer** whose score can be recomputed by hand, used as
   the auditable review baseline.
4. **An exploratory unsupervised ranking with an exact score decomposition**,
   reported together with an honest assessment of what it measures (§4): on
   this snapshot it mostly ranks large, multi-lot and incompletely published
   records as unusual and is not validated against outcomes.
5. **A ready-to-use manual audit protocol and frozen sample** for the
   independent evaluation that the statistical results cannot provide.

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
`data/dq/*.dq.{json,md}` suite output.

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
**Si funksionon analiza** page and in `rule_descriptions()`.

**What the composite reduces to on this snapshot.** Only four rules carry
weight, and the score moves in steps of 0.125. All 235 records with
`rule_score >= 0.5` are single-bidder records:

| Triggered weighted rules | Records |
|---|---:|
| `SINGLE_BIDDER_OPEN` + `WINNER_TAKES_ALL_LARGE` | 134 |
| `SINGLE_BIDDER_OPEN` + `HIGH_VALUE_SINGLE` | 65 |
| `SINGLE_BIDDER` + `HIGH_VALUE_SINGLE` | 24 |
| `SINGLE_BIDDER_OPEN` + `HIGH_VALUE_SINGLE` + `WINNER_TAKES_ALL_LARGE` | 9 |
| `SINGLE_BIDDER` + `HIGH_VALUE_SINGLE` + `WINNER_TAKES_ALL_LARGE` | 3 |

In effect, the review queue is *single bidder AND (top-1% value within its
category OR a multi-lot standard-open tender of at least €100,000 whose value
goes to one supplier)*. The weights are an ordinal encoding of that
prioritisation. Single bidding is the literature-backed core (Fazekas & Kocsis,
2020); the value and lot conditions are the author's prioritisation by
financial exposure and have no specific literature reference.

**Known limitation — `WINNER_TAKES_ALL_LARGE` overlaps single bidding.** When a
tender has one bidder, one supplier necessarily receives all of the awarded
value, so this rule restates the single-bidder fact for 156 of its 426 hits.
The 134 records in the first row above reach the 0.5 threshold only through
that overlap. Restricting the rule to tenders with at least two bidders would
reduce the `rule_score >= 0.5` queue from 235 to 101 records (and `>= 0.7`
from 77 to 74). The published release keeps the original definition because
changing a rule requires a new, fully revalidated publication; the dashboard
explanation shows which rules fired, so the overlap is visible per tender.

### ML layer — exploratory, unsupervised, **unvalidated**

A benchmark evaluates **23 unsupervised configurations across 8 families**
and **12 supervised configurations across 4 families**, then elects four
champion unsupervised families fitted on the 20-feature matrix. The exact
elected bundle is recorded in `data/models/benchmark/champions.json`. Each
produces a snapshot-relative `[0, 1]` score and an exploratory ranking
of records that are statistically unusual in the current feature matrix.
The elected families are One-Class SVM (Schölkopf et al., 2001), Isolation
Forest (Liu, Ting & Zhou, 2008), HBOS (Goldstein & Dengel, 2012) and
k-nearest-neighbour distance (Ramaswamy, Rastogi & Shim, 2000); the benchmark
also compares LOF (Breunig et al., 2000), Elliptic Envelope (Rousseeuw & Van
Driessen, 1999), a Gaussian mixture and PCA reconstruction error. Averaging
rank-normalised detector scores follows common outlier-ensemble practice
(Zimek, Campello & Sander, 2013; Aggarwal & Sathe, 2017).

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

The election is reproducible but **not robust to its objective**. Ranking
detectors by `precision@K` alone elects {GMM, Isolation Forest, LOF, Elliptic
Envelope}, a family Jaccard of only 0.14 against the declared set; the
stability- and proxy-emphasis weightings each swap one family. The detectors'
precision at 500 against the 77 records with `rule_score >= 0.7` is 0.000–0.006
(`leaderboard.md`), close to the 0.001 expected by chance, even though their
ROC-AUC against the same labels is 0.69–0.92. The election is therefore
reported as a documented engineering choice, not an optimum.

**What the detectors pick up.** The mean of the four detector ranks is
essentially unrelated to the rule score (Spearman −0.10) but correlates with
the number of missing model features (Spearman 0.40). Records with at least
one missing feature are 39.1% of the snapshot but 53.5% of the records with
`ensemble_score >= 0.5`; median imputation with missing-value indicators makes
incompleteness itself unusual. On this snapshot the unsupervised layer is
therefore partly a **publication-completeness and size/lot-structure ranking**.
That is useful for data-quality triage, but it is not evidence of integrity
risk.

### Ensemble — how it relates to the rules

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

The two layers produce **nested sets of very different size**, not
opposing judgements (see the confusion table in `findings.md §5` and
`validation_report.json:rule_only_baseline_and_confusion`):

* All 235 rule-flagged records also have `ensemble_score >= 0.5` (the lowest
  is 0.59); none is demoted. This is largely built in: `rule_score` is one of
  the six equally weighted components, and rule-flagged tenders are large or
  multi-lot, which also raises their other components (mean `context_score`
  0.76 versus 0.55; median detector-rank mean 0.88 versus 0.48).
* The ensemble adds 24,455 further records (99.1% of its set). This is mainly a
  consequence of the threshold: four of the six components are uniform
  percentile ranks, so the snapshot mean of `ensemble_score` is 0.437 and
  **0.5 is its 67th percentile**. `ensemble_score >= 0.5` means "upper third of
  the ranking"; it is descriptive and has no operational meaning as a review
  cut-off.
* At equal queue size, the top 235 ensemble records share 119 records with the
  rule queue; the top 235 by the four detectors alone share none.

The generated findings heading still calls this disagreement; the wording above
is the precise reading of the same numbers. Any review based on the ensemble
should take a top-K sized to reviewer capacity rather than the 0.5 cut. We
therefore treat the **rule layer as the auditable heuristic baseline** and the
ensemble as an exploratory add-on, not a corroboration. The dashboard's review
page defaults to the rule score for the same reason.

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
`(rule_score >= 0.4)`. Because no score lies between 0.375 and 0.5, this label
selects exactly the same 235 records (0.31%) as the 0.5 review threshold.
The target is a deterministic proxy built mostly from
the same or heavily overlapping raw features in `X` (although procedure
subtype itself is not supplied to the model). This overlap explains the
near-perfect **ROC-AUC**; the result is proxy-faithfulness, not detection
performance. It says *nothing* about anomaly or fraud.

Its only legitimate use is as an **explanation recovery check**: the rule
function is known, so TreeSHAP attributions (Lundberg & Lee, 2017; Lundberg
et al., 2020) of a model that imitates it show
whether SHAP recovers the expected raw-feature drivers. (Tree models are
piecewise constant; TreeSHAP does not require differentiability.) The
supervised calibration figure uses only two populated bins and should not be
read as evidence of calibration. The waterfall chart shows
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

### Known issues in the published release

A final review on 22 October 2026 found the following issues. They are
documented here rather than silently patched, because each fix changes
release-bound code and therefore requires a new, fully revalidated
publication:

* **Rule overlap.** `WINNER_TAKES_ALL_LARGE` restates single bidding for
  single-bidder tenders; see §4. Effect: 134 of the 235 queued records.
* **Time zone of dates.** The source publishes timestamps with a fixed
  `+01:00` offset; silver and gold store them in UTC and derive `year` and
  `month` from the UTC value. Of the 75,679 dated records (excluding 31 missing
  dates), 68,275 (90.2%) fall on the previous calendar day in UTC, 2,315 (3.1%)
  on the previous month and 131 on the previous year. The dashboard converts
  dates back to the published `+01:00` offset
  before displaying or grouping them; the generated findings and
  `gold.monthly_metrics` still use UTC. For awarded standard-open records with
  published bidder counts (the yearly comparison in the findings), annual
  single-bidder rates change by at most 0.052 percentage points for 2016–2025
  and by 0.513 points in partial-year 2026, whose subgroup grows from 13 to 15
  records when grouped in the published offset.
* **Award de-duplication across identically titled lots.** Awards are
  de-duplicated on (lot title, amount, currency, supplier). Where several lots
  share one title, two genuine awards of equal value to the same supplier
  collapse into one. This affects 36 award rows (about €3.2 million, 0.07% of
  recorded award value), e.g. `ocds-uhzcmx-616-20-8405-1-1-5` has five awards
  in the source and four in silver.
* **Procedure-code article.** The generated findings cite Article 12.3 of the
  *consolidated, non-official* text of Regulation 001/2022; the official
  article is 12.13 (see §2).

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
      rebuildable with `pipeline bronze`, `pipeline run --from silver --force`
      and `report findings` (see operations.md, "Intentionally rebuild from the
      preserved source"). Do not use `make all` or a plain `pipeline run` for
      this: both check the remote source and can replace the snapshot. Any
      later human audit labels must be preserved separately and are never
      treated as rebuildable output.

## 7. Related work and positioning

Red-flag approaches to procurement risk build on composite indicators computed
from administrative tender data, with single bidding in competitive procedures
as the most widely used element (Fazekas, Tóth & King, 2016; Fazekas &
Kocsis, 2020). Machine-learning studies predict malfeasance from tender
features where labelled outcomes exist (Gallego, Rivero & Martínez, 2021;
Decarolis & Giorgiantonio, 2022). For Kosovo, civil-society projects already
publish procurement red flags, for example the
[Democracy Plus red-flags work](https://dplus.org/en/?p=9958) and
[Lëvizja FOL's portal](https://levizjafol.org/en/?p=14043). This project does
not claim a new risk index. Its contribution is the reproducible, release-bound
OCDS pipeline, the procedure-code correction of competition statistics, explicit
handling of missing bidder data, and a candid evaluation of what an unsupervised
layer adds when no outcome labels exist.

## 8. References

**Procurement integrity and red flags**

* Fazekas, M., & Kocsis, G. (2020). Uncovering high-level corruption:
  Cross-national objective corruption risk indicators using public procurement
  data. *British Journal of Political Science*, 50(1), 155–164 (first published
  online 2017).
* Fazekas, M., Tóth, I. J., & King, L. P. (2016). An objective corruption risk
  index using public procurement data. *European Journal on Criminal Policy and
  Research*, 22(3), 369–397.
* Decarolis, F., & Giorgiantonio, C. (2022). Corruption red flags in public
  procurement: New evidence from Italian calls for tenders. *EPJ Data Science*,
  11, 16.
* Gallego, J., Rivero, G., & Martínez, J. (2021). Preventing rather than
  punishing: An early warning model of malfeasance in public procurement.
  *International Journal of Forecasting*, 37(1), 360–377.
* OECD (2007). *Integrity in Public Procurement: Good Practice from A to Z*.
  OECD Publishing.
* OECD (2009). *Guidelines for Fighting Bid Rigging in Public Procurement*.
  OECD Publishing (updated 2025).
* World Bank (2016). *Procurement Guidance: Abnormally Low Bids and Proposals*.
  World Bank.

The short-form `reference` strings inside `src/thesis/anomaly/rules.py` are part
of the hash-bound release and are kept unchanged. Read them against the list
above: the cross-country single-bidding indicator cited for
`SINGLE_BIDDER_OPEN` as "Fazekas et al. (2016)" is from Fazekas & Kocsis (2020);
Fazekas, Tóth & King (2016) is the Hungarian corruption-risk index. "World Bank
(2017)" refers to the guidance dated July 2016. The references attached to the
zero-weight `RATIO_ABOVE_ESTIMATE` and `IMPLAUSIBLE_ESTIMATE` diagnostics
("OECD (2007)", "Fazekas & Kocsis (2017) — estimate manipulation") are general
motivation only; neither source defines those ratio bands.

**Legal and data sources**

* Law No. 04/L-042 on Public Procurement in the Republic of Kosovo, as amended
  by Laws No. 04/L-237, 05/L-068 and 05/L-092 (consolidated text, Article 19).
* Public Procurement Regulatory Commission (2022). Regulation No. 001/2022 on
  Public Procurement (Articles 12.13, 51.3, 51.5), as amended by Regulation
  No. 002/2024.
* Open Contracting Partnership. *Kosovo — Public Procurement Regulatory
  Commission*, Publication 115 (OCDS 1.1).
  <https://data.open-contracting.org/en/publication/115>

**Anomaly detection, ensembles and explanation**

* Aggarwal, C. C., & Sathe, S. (2017). *Outlier Ensembles: An Introduction*.
  Springer.
* Breunig, M. M., Kriegel, H.-P., Ng, R. T., & Sander, J. (2000). LOF:
  Identifying density-based local outliers. In *Proceedings of the 2000 ACM
  SIGMOD International Conference on Management of Data* (pp. 93–104).
* Goldstein, M., & Dengel, A. (2012). Histogram-based outlier score (HBOS): A
  fast unsupervised anomaly detection algorithm. In *KI-2012: Poster and Demo
  Track* (pp. 59–63).
* Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation forest. In
  *Proceedings of the 8th IEEE International Conference on Data Mining*
  (pp. 413–422).
* Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting
  model predictions. In *Advances in Neural Information Processing Systems 30*
  (pp. 4765–4774).
* Lundberg, S. M., Erion, G., Chen, H., DeGrave, A., Prutkin, J. M., Nair, B.,
  Katz, R., Himmelfarb, J., Bansal, N., & Lee, S.-I. (2020). From local
  explanations to global understanding with explainable AI for trees. *Nature
  Machine Intelligence*, 2(1), 56–67.
* Ramaswamy, S., Rastogi, R., & Shim, K. (2000). Efficient algorithms for
  mining outliers from large data sets. In *Proceedings of the 2000 ACM SIGMOD
  International Conference on Management of Data* (pp. 427–438).
* Rousseeuw, P. J., & Van Driessen, K. (1999). A fast algorithm for the
  minimum covariance determinant estimator. *Technometrics*, 41(3), 212–223.
* Schölkopf, B., Platt, J. C., Shawe-Taylor, J., Smola, A. J., & Williamson,
  R. C. (2001). Estimating the support of a high-dimensional distribution.
  *Neural Computation*, 13(7), 1443–1471.
* Zimek, A., Campello, R. J. G. B., & Sander, J. (2013). Ensembles for
  unsupervised outlier detection: Challenges and research questions. *ACM
  SIGKDD Explorations Newsletter*, 15(1), 11–22.

**Evaluation statistics**

* Cohen, J. (1960). A coefficient of agreement for nominal scales.
  *Educational and Psychological Measurement*, 20(1), 37–46.
* Wilson, E. B. (1927). Probable inference, the law of succession, and
  statistical inference. *Journal of the American Statistical Association*,
  22(158), 209–212.
