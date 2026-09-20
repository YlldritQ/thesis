# Operations Runbook

Day-2 operational procedures for the Kosovo procurement pipeline.

## Pipeline overview

```
bronze ─► silver ─► gold/tender_features ─► benchmark ─► ml/tender_summary
                                                                  ▼
                                                             streamlit
```

* **Local execution**: `python -m thesis pipeline run`
* **Scheduled-deployment example**: Airflow DAG
  `kosovo_procurement_pipeline` (configured for daily 04:00 UTC if deployed)
* **Dashboard**: Docker container exposing port 8501

## Healthchecks

| Check                      | Where                              | Frequency  |
|----------------------------|------------------------------------|------------|
| Streamlit liveness         | `GET /_stcore/health`              | every 30 s |
| Pipeline freshness         | `python -m thesis pipeline status` | on demand  |
| Release integrity          | `python -m thesis pipeline validate-releases` | every run |
| DQ suites                  | `python -m thesis dq run`          | every run  |
| Model-generation binding   | recursive ML release validation   | every read |

## Common operations

### Restore the bundled snapshot after cloning

Git includes the original compressed source, its bronze manifest, and the
published downstream data and models. The expanded raw JSONL exceeds GitHub's
per-file limit, so it is intentionally ignored. On a fresh clone, restore it:

```bash
gzip -dk data/raw/kosovo_ocds.jsonl.gz
```

Run this only when `data/raw/kosovo_ocds.jsonl` is absent. Decompression restores
the exact bytes recorded in the bronze manifest while preserving the archive.
Every dashboard reader validates this raw-to-model chain, so restoring the raw
file is required even when only viewing the existing results. A newer download
cannot replace this file without intentionally rebuilding the downstream stages.

### Force a full rebuild

```bash
python -m thesis pipeline run --force
```

### Re-train the ML layer only (e.g. after parameter tweak)

```bash
python -m thesis pipeline run --only ml --force
```

This is valid only when the Gold and full benchmark releases still validate
against the current implementation/configuration, the data fingerprint matches,
and the release-bound semantic election check can re-derive `champions.json` from
the checkpoint/leaderboard. After a rule, feature, protocol, or relevant source
change, rerun benchmark before ML; stale or manually altered champions are
rejected. A `--quick` run is never a deployable benchmark input.

### Run only DQ checks (no rebuild)

```bash
python -m thesis dq run
```

This refreshes the general DQ reports only. Each published generation also
contains immutable, release-owned copies of its publication-gate evidence.

### Verify every publication generation

```bash
python -m thesis pipeline validate-releases
```

The command verifies file sizes and hashes, lineage input/output bindings,
DQ evidence, effective configuration, implementation fingerprint, and every
upstream release recursively. It fails closed when code, configuration, an
upstream file, or a required artifact no longer matches the published chain.

### Concurrency, runtime, and invalidation policy

All supported mutating entry points (the DAG and individual CLI stages) hold
one interprocess lock at `data/.pipeline.lock` for the complete run/stage.
Parquet/JSON files are replaced atomically and the stage manifest is published
last. During the short multi-file replacement window an existing reader can
fail validation; it cannot accept a hybrid as a valid release. This static
package does not claim lock-free, continuously available live publication.

Mutating stages and `pipeline validate-releases` require an exact match to the
recorded Python/package runtime. Read-only dashboard readers still verify the
release's internally consistent runtime plus current source/configuration, but
allow a different compatible host runtime so a release can be inspected on a
different machine. No mutation is authorized under that relaxed read policy.

The implementation fingerprint deliberately hashes the complete
`src/thesis/**/*.py` tree rather than trying to infer a precise stage-level
dependency graph. This is conservative: a reporting-only source change can
invalidate Bronze and cascade a full rebuild. Treat that as over-invalidation,
not evidence that the current provenance system identifies minimal stage
dependencies.

### Inspect lineage of a single artifact

```bash
cat data/silver/tenders.parquet.lineage.json | jq .
```

The chronological history is in `data/_lineage/<table>/`.

### Bring up the Streamlit container locally

```bash
docker compose up app
# now browse http://localhost:8501
```

### Run the integration test

```bash
pytest tests/integration -v
```

## Troubleshooting

### "ModuleNotFoundError: thesis"

The package isn't installed. From the repo root:

```bash
pip install -e .[dev]
```

### Streamlit page raises an exception

Check `streamlit_app/_bootstrap.py` first — every page imports through
it. Run the page-render smoke test:

```bash
PYTHONPATH=src pytest tests/test_streamlit_pages.py -v
```

### A DQ suite fails

Look at `data/dq/<suite_name>.dq.md` for a per-expectation breakdown.
A `severity == "error"` row means the artifact violates a contract and always
blocks canonical publication in the producing stage. A `severity == "warning"`
is recorded but normally non-blocking; it also blocks when
`THESIS_FAIL_FAST_ON_DQ=true`. The standalone `thesis dq run` command writes
and displays evidence but does not itself republish an artifact.

### Bronze download times out

Tune the request timeout:

```bash
THESIS_OCDS_REQUEST_TIMEOUT_S=1800 python -m thesis pipeline bronze --force
```

### Pipeline says "task fresh, skipping" but you want it to rerun

Pass `--force`. Freshness is content- and provenance-based; changing only a
timestamp does not create a valid generation:

```bash
python -m thesis pipeline run --from silver
# or, to rebuild even when the release is valid:
python -m thesis pipeline run --from silver --force
```

### A model behaves unexpectedly after retraining

First run release validation. Then compare an intentionally retained copy of
the prior report with the new `validation_report.json`. Metrics against
rule-derived labels measure agreement with those labels, not independently
observed correctness. Investigate:

1. whether the rule-label distribution shifted (`python -m thesis info`),
2. whether feature or detector code changed (implementation fingerprint),
3. whether data or configuration changed (release input/configuration hashes),
4. whether resampling stability, detector agreement, or feature-family
   ablations changed materially.

## Capacity & SLOs

| Metric                              | Target                       |
|-------------------------------------|------------------------------|
| Bronze fetch time                   | < 5 min (single 23 MB blob)  |
| Silver build time                   | < 60 s                       |
| Gold build time                     | < 5 s                        |
| ML training + SHAP + validation     | < 90 s on 4-core CPU         |
| Full benchmark                     | checkpointed; hardware/data dependent |
| End-to-end pipeline (cold start)    | no fixed SLO; includes full benchmark |
| Streamlit page first paint          | < 2 s                        |
| Streamlit page interactive (search) | < 200 ms                     |

## Log conventions

All logs are structured (structlog). Production runs ship JSON
(`THESIS_LOG_FORMAT=json`). Each line carries:

* `event` — short snake_case identifier (e.g. `silver.parse.progress`)
* `run_id` — auto-generated per pipeline run (`run-YYYYMMDDTHHMMSS-<8hex>`)
* `stage` — `bronze` / `silver` / `gold` / `benchmark` / `ml`
* `task` — the DAG task name when invoked through the runner
* extra fields specific to the event

Useful jq one-liners:

```bash
# all errors from one run
jq -c 'select(.run_id=="run-20260506T151945-3e5ba3ed" and .level=="error")' < pipeline.log

# task durations
jq -c 'select(.event=="task.done") | {task, duration_s}' < pipeline.log
```

## Disaster recovery

* Preserve the validated bronze snapshot. It can be reacquired with
  `python -m thesis pipeline bronze --force` only while the same upstream
  publication remains available.
* Preserve `data/review/` once people add audit judgements. Derived silver,
  gold, benchmark, and model artifacts can be rebuilt; human review cannot.
* A full rebuild includes the checkpointed benchmark and has no fixed
  seven-minute recovery promise.
* Preserve `uv.lock` with an archived release. Docker installs from it with
  `uv sync --frozen`; `requirements-lock.txt` remains an exact capture of the
  audited local Python 3.9 environment and is not the cross-platform resolver.
  Platform-specific reproduction can still be blocked when a locked wheel is
  unavailable.
* Release manifests and lineage sidecars record output/input hashes and schemas.
  A changed byte hash warrants investigation; semantic equivalence must be
  checked from rows, values, schema and protocol metadata rather than assumed
  from Parquet byte identity across library versions.
* If the upstream OCDS publication changes URL, edit
  `THESIS_OCDS_PUBLICATION_URL` in the environment / secret store.
* The current Bronze manifest binds the exact gzip/JSONL hashes and records the
  configured expected source URL. Historical HTTP retrieval time, ETag, and
  Last-Modified headers were unavailable for the pre-existing snapshot and are
  intentionally not inferred. Future forced downloads record the actual HTTP
  acquisition metadata returned by the source.
