# Data-quality reports

This directory contains two kinds of evidence:

| Files | Purpose |
|---|---|
| `*.dq.json` and `*.dq.md`, excluding `*.release.dq.json` | Seven current table-suite reports in machine-readable and readable forms; refreshed by `python -m thesis dq run` |
| `*.release.dq.json` | Nine immutable publication-gate reports; their exact bytes are bound into the release manifests |

The seven table suites cover Silver tenders and awards; Gold tender features,
scored tenders, contracting-authority summaries, supplier summaries, and monthly
metrics. The release-owned evidence additionally covers the benchmark and SHAP
artifacts.

A failed `ERROR` check blocks publication. A failed `WARNING` is reported and
blocks publication only when `THESIS_FAIL_FAST_ON_DQ=true`. Data-quality checks
establish technical consistency, not independent evidence of procurement outcomes.

Regenerating general reports does not replace the evidence belonging to an
existing release. Preserve every `*.release.dq.json` file and publish a new release
if its inputs or artifacts change.

The old prototype CSVs, `integrity_issues.json`, and `summary*.md` have been removed;
they described superseded analyses and were not consumed by the current project.
Use [the generated findings](../../docs/findings.md) for current numerical results
and [the project review](../../docs/project_review_2026_09.md) for the reviewed
source-data warnings.
