# ADR-0005: Cautious anomaly framing — "anomaly ≠ fraud"

* **Status:** Accepted (binding on every PR)
* **Date:** 2026-04

## Context

Public-procurement anomaly detection touches living institutions and
named individuals. A high score in this dashboard could be misread as
an accusation. Even if false, that misreading is harmful.

We need a framing rule that:

* never lets the dashboard, the API, or the documentation imply
  fraud,
* makes the difference between *signal for review* and *evidence of
  wrongdoing* explicit and unmissable.

## Decision

1. **No "fraud" labels anywhere.** Score columns use neutral names such as
   `rule_score`, `<detector>_score`, `hgb_score`, `context_score`, and
   `ensemble_score`. Never
   "fraud_probability", "corruption_score", "guilt_likelihood".
2. **Every Streamlit page renders `show_caveat()`** at the top.
3. **`docs/responsible_use.md` is required reading** and is linked from
   the README, the dashboard Methodology page, and CONTRIBUTING.
4. **Exploratory rank-agreement filter.** The historical
   `high_confidence` toggle requires at least 3 of the 4 champion
   unsupervised detectors to place the record in their **current-batch
   top 5%**. It is not a raw-score threshold of 0.7, calibrated confidence,
   or evidence of fewer false positives. External presentations must name
   it "rank agreement" and keep the rule/output-label caveat visible.
5. **No name-and-shame outputs.** No CSV export of "top 50 suppliers"
   ranked by score. The CSVs published by the pipeline are aggregated
   (DQ scorecards, supplier-summary, procuring-entity-summary) and
   never combine names with anomaly scores.
6. **CONTRIBUTING.md PR-blocks** any change that weakens the above.

## Consequences

**Positive:**

* Reduces the chance of harm from a misread of the dashboard.
* Aligns with the OECD-Procurement-Integrity guidance on
  responsible use of statistical risk indicators.

**Negative:**

* Slightly more friction for developers (must type `rule_score` not
  `fraud_score`). Acceptable.
* Historical column names such as `high_confidence` need an explicit
  explanation wherever they are displayed.

## Related

* `docs/responsible_use.md`
* `streamlit_app/_bootstrap.py:show_caveat`
* `CONTRIBUTING.md` § "Sensitive subject"
