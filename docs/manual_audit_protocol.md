# Manual tender-audit protocol

The statistical benchmark in this repository measures how faithfully models
reproduce author-defined screening rules. It does **not** measure whether a
tender contains an integrity problem. The four-quadrant audit queue is the
first outcome-oriented evaluation step; it remains incomplete until people
inspect source documents and record evidence.

Generate the frozen queue after the final ML run:

```bash
.venv/bin/python -m thesis report audit-sample
```

This samples **up to** 50 tenders from each rule×ensemble quadrant: both
flagged, rule-only, ensemble-only, and neither. A quadrant with no records at
the declared operational thresholds remains empty; examples are never
manufactured merely to balance the table. The command records the source
parquet hash, thresholds, seed, population counts, and any empty quadrants in
`data/review/manual_audit_sample.metadata.json`. It refuses to overwrite an
existing queue unless `--force` is supplied. Forced regeneration preserves
every human field by OCID and aborts if it would remove an OCID containing any
human-entered review data.

The queue pre-fills `source_document_url` from an exact OCDS document URL where
one is published. `source_document_url_status` distinguishes a missing value,
an invalid source value, and a structurally valid but **HTTP-unverified** URL;
structural checking is not evidence that the remote document is available or
is the correct evidentiary document. Metadata records raw/scored-source hashes,
the exact sample-file hash, a review-label-state hash, a sample-definition
hash, thresholds, populations, seed, URL-status counts, and completion status.
This is source navigation, not a label; newly generated `review_*` judgement
fields remain blank for human reviewers.

## Review unit and question

The unit is one tender (`ocid`). Review the original notice, award decision,
lot information, dates, and amendments where available. The primary question
is:

Treat an OCDS `award` as a recorded award decision only. Do not mark a contract
as signed, executed or paid unless a separate source document explicitly
supports that status; absence of such evidence is not a negative finding.

> Does the source documentation contain a concrete, review-relevant concern
> that is supported by recorded evidence, rather than merely being unusual?

Record one of `yes`, `no`, or `uncertain` in
`review_relevant_concern`. An empty field means **not reviewed**, never “no”.
Separately record `review_data_quality_issue` so source/field problems are not
mislabelled as conduct concerns.

Suggested `review_concern_type` values are `competition`, `timing`,
`value_or_lot_comparability`, `award_process`, `data_quality`, `other`, or
`none`. Every `yes` or `uncertain` decision needs a short evidence note and a
source-document URL. Do not infer intent, fraud, corruption, illegality, or a
supplier-level label from an indicator alone.

## Blinding and agreement

Where feasible, hide `audit_quadrant`, scores, and `active_indicators` during
the first document read. Two reviewers should independently assess at least a
20% overlap sample. Resolve disagreements only after both initial judgements
are frozen; report raw agreement and Cohen's kappa together with the adjudicated
result.

## Reporting

For each populated quadrant, report reviewed `n`, yes/no/uncertain counts, the proportion
of evidence-supported `yes` judgements, and a 95% Wilson interval. Report data
quality issues separately. Never compute precision by treating unreviewed or
uncertain rows as negative. The “neither” quadrant is required to estimate the
background rate. Report an empty stratum explicitly rather than omitting it or
substituting records selected under a different threshold.

Until these labels have been completed and independently checked, the honest
conclusion remains: **the ML ranking is exploratory and unvalidated against
tender-level outcomes**.
