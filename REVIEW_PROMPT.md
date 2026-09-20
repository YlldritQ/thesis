> **Historical prompt — superseded.** This prompt targets an earlier repository
> state and its embedded figures are not current. Use
> [THESIS_REVIEW_R3.md](THESIS_REVIEW_R3.md) and
> [THESIS_REMEDIATION_R3.md](THESIS_REMEDIATION_R3.md) as the current review
> record.

# Round-2 Multi-Agent Thesis Review Prompt

Paste everything below the line into Claude Code from the repo root
(`/Users/ylldrit/Desktop/thesis`). The phrase "use a multi-agent workflow" is
what authorizes the orchestration. To make it a from-scratch review instead of
a round-2 delta review, delete the second paragraph.

---

Use a multi-agent workflow to run an adversarial, evidence-grounded review of
the Kosovo procurement anomaly-detection thesis in this repo.

This is **round 2**. A full review already exists in `THESIS_REVIEW.md`
(2026-07-13), and its defense-blockers were fixed on 2026-07-13/14 (see
`CHANGELOG.md`). Do NOT re-report findings already listed there unless the fix
is inadequate or has regressed. Your job: verify the fixes hold, find what the
fixes broke, and surface NEW issues.

## Ground rules for every agent

- **Evidence or it doesn't count.** Every finding cites `file:line`. Every
  number is recomputed from the shipped data (`data/gold/*.parquet`), never
  quoted from docs — docs have been stale before.
- **Try to refute before you report.** Before writing a finding, actively look
  for the code, test, or caveat that already handles it.
- **No praise, no generic advice.** "Consider adding more tests" is a failed
  finding. Every finding names the defect, the failure scenario, a concrete
  fix, and an effort estimate (S/M/L).
- **Severity is defense-calibrated:** BLOCKER (an examiner can sink the thesis
  with one question), MAJOR (costs credibility, fix before submission), MINOR
  (polish).
- An empty findings list is acceptable only with a record of what you tried to
  break and why it held.

## Phase 0 — Fact sheet (one agent, runs first)

Build the ground truth all reviewers must use: headline numbers recomputed
live from `data/gold/tender_summary.parquet` (tender/award counts, total
value, single-bidder rate by procedure type), `pytest` and `ruff` status,
number of dashboard pages serving, ML feature count, and the external
validation (OSHP) result from `validation_report.json`. Append the list of
round-1 findings already fixed (from `THESIS_REVIEW.md` + `CHANGELOG.md`) so
no reviewer wastes effort rediscovering them.

## Phase 1 — Independent reviews (parallel, blind to each other, each gets the fact sheet)

1. **Skeptical thesis examiner** (methodology & statistics). Simulate the
   defense committee: the ten hardest questions, especially around the
   circularity reframing and the honest-negative OSHP external validation.
   Is the current framing defensible, or does any section still oversell?
2. **Procurement domain expert.** Audit each of the 13 rules: is the
   threshold cited and justified? Does it measure corruption risk or just
   market structure? Scrutinize per-category HHI, single-bidder-by-method
   framing, and the OSHP lift interpretation (rules 0.65×, ML 1.48×) — is
   "we measure a different dimension" a valid explanation or a
   rationalization?
3. **Senior data engineer.** Audit the medallion pipeline end-to-end:
   ingestion, joins, dedup, currency handling, DQ severity handling, and
   especially the newer `award_data_missing` indicator with 0-sentinel fills
   — did that fix introduce its own distortion? Look for leakage between
   layers and silent row loss between bronze → silver → gold.
4. **ML evaluation auditor.** Labels, feature/label overlap, the
   out-of-time protocol, and the rule-vs-ensemble confusion numbers (40.6%
   demoted, 72.5% ML-only) — recompute them. Then answer: what evaluation
   design would demonstrate *detection* rather than rule-mimicry, and how
   far is the current setup from it? Check the status of frozen
   reference-period scoring (round-1 item H-4).
5. **Naive reader.** Open the Streamlit app cold and read only `README.md`
   and `docs/findings.md`. Is every claim understandable and non-misleading
   to a non-expert? Do the caveats actually register, or do they read as
   boilerplate an examiner would say nobody reads?
6. **Regression hunter.** Diff-driven: for each fix claimed in
   `CHANGELOG.md`/`THESIS_REVIEW.md` (reporting CLI, caveat-header test,
   rule reweights, dead-band, €100K floor, DQ abort, OSHP module), verify
   the implementation matches the claim, then probe for new bugs the fix
   introduced.

## Phase 2 — Adversarial verification (parallel, per finding)

Every Phase-1 finding goes to an independent verifier with full repo and data
access whose job is to KILL it: re-read the code, reproduce the numbers.
Findings survive only as CONFIRMED (reproduced) or PLAUSIBLE (sound reasoning,
not directly reproducible); refuted findings are dropped with the refutation
recorded.

## Phase 3 — Roundtable and synthesis (one agent, all confirmed findings)

Resolve conflicts between personas, dedup, and rank by defense impact. Then
triage the still-open round-1 backlog — tender-level OSHP match via activity
numbers, lot-level ratio rebuild (H-3), contract-splitting/buyer-supplier
rules (H-5), frozen reference scores (H-4) — and for each: do before
submission, or defer with a one-line stated reason.

## Deliverables

Write `THESIS_REVIEW_R2.md` in the repo root containing:
- Verdict, and the delta vs round 1 ("was: not defensible as-is; now: …")
- Confirmed findings grouped by severity, each with `file:line`, concrete
  fix, and effort
- A fix-verification table for every round-1 fix (holds / regressed / partial)
- A prioritized top-10 action list
- A one-page defense-prep section: the hardest committee questions plus the
  honest answers the thesis can currently support

Review only — do not modify any source files.
