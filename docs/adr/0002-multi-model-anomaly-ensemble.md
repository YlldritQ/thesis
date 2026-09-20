# ADR-0002: Multi-model anomaly ranking + rule layer

* **Status:** Accepted; amended 2026-07
* **Original date:** 2026-04
* **Deciders:** thesis author + supervisor

## Context

Anomaly analysis in public procurement is sensitive. A high model score
can be mistaken for evidence of misconduct, while a single black-box
detector provides little auditable context.

The design therefore needs to keep the transparent rule layer visible,
show how statistical rankings differ, and avoid presenting model agreement
as independent corroboration.

## Decision

Adopt a layered, **exploratory ranking**:

1. **Rule layer** (`thesis.anomaly.rules.RULES`) — the auditable source of
   truth. The current registry contains 15 boolean review signals with
   fixed heuristic weights. A rule hit is not proof of wrongdoing.
2. **Unsupervised ensemble** — the benchmark compares 23 configurations
   across 8 detector families and elects four families. They are fitted on
   the 20 features listed by `ML_FEATURES`; the exact elected bundle is stored
   in `champions.json` rather than fixed by this ADR.
3. **Contextual layer** — peer-relative z-scores within procuring entity,
   category, and method.
4. **Supervised rule surrogate** — HistGradientBoosting trained on
   `(rule_score >= 0.4)`, used only for raw-feature SHAP attribution. Its
   near-perfect metrics arise because the target and input features overlap
   heavily; they measure rule faithfulness, not detection performance.

`ensemble_score` averages detector rank percentiles with the rule and
context scores. The detector percentiles are recomputed within the current
batch, so scores are snapshot-relative.

The ML release persists those elected detector percentile ranks and a
versioned explanation contract. For every record, the published score is the
exact sum of equal-weight component contributions. A second centered view uses
the complete-snapshot component means as baselines, so `baseline_score +
sum(effect_vs_baseline) == ensemble_score`. This is intrinsic, additive XAI for
the score actually used by the dashboard. It explains the score arithmetic,
not causation or whether the procurement is improper. Triggered-rule arithmetic
and the maximum contextual z-score driver are displayed separately. Feature
percentiles are descriptive context, not detector attribution.

`model_agreement_count` records how many elected detectors exceed the released
rank quantile. The historical `high_confidence == 1` name uses the released
minimum-agreement setting (currently **at least 3 of 4 current-batch top-5%
ranks**). It is rank agreement, not calibrated confidence or evidence of fewer
false positives.

The full election is one release bundle: the strict JSONL snapshot,
leaderboard, champions, and semantic DQ proof are hash-bound together. Each
checkpoint row binds the relevant fitting/evaluation source hashes. The ML
stage re-derives the election from the released rows, so a complete but
manually altered champion file is rejected. A full sweep resumes in
`results.wip.jsonl` and replaces the canonical snapshot only after the election
passes completeness/semantic checks; quick mode uses another separate file.
Neither mutable checkpoint invalidates the prior released generation while the
sweep is in progress.

Alternate composite weights, a `precision@K` proxy ranking, deployed
feature-subset refits, and q=0.90/0.95/0.99 vote sets are retained as rank
sensitivity diagnostics. They do not change the declared election and are not
outcome validation.

## Consequences

**Positive:**

* Triggered rules remain directly inspectable and reproducible.
* The statistical layer offers a second, explicitly exploratory ordering.
* Rule–ensemble disagreements can be measured and shown rather than hidden.
* Every hybrid score has an exact component-level explanation tied to the ML
  generation.
* Raw-feature SHAP views remain available only for the rule-proxy surrogate;
  they are not presented as explanations of the unsupervised ensemble.

**Negative:**

* No outcome-labelled evaluation currently establishes added detection
  value over the rule queue.
* Rank-percentile scores can move when the comparison population changes.
* Four bootstrap refits and two extra stochastic seeds are limited
  repeatability checks, not uncertainty estimates.
* More CPU is required than for a rule-only queue.

## Alternatives considered

* **Rules only.** Remains the auditable baseline and a valid operating view;
  the statistical layer is retained only as an exploratory comparison.
* **Isolation Forest only.** Rejected as an unauditable single-model ranking.
* **Deep autoencoder.** Rejected as unnecessary at this scale and harder to
  explain.
* **Supervised fraud model.** Rejected because no valid tender-level outcome
  labels exist in the submitted package.

## Related

* ADR-0005 — Cautious anomaly framing.
* `docs/methodology.md`
* `docs/responsible_use.md`
