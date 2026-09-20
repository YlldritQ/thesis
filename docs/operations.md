# Operations

The project ships a static, published research dataset and its dashboard.
Opening those results and rebuilding them are separate workflows. All commands
below run from the project root; the CLI also provides `--help` for each command.

## Open the bundled dashboard

CI and Docker use uv 0.11.28. Create a locked Python 3.11 environment:

```bash
uv sync --frozen --python 3.11
```

If `data/raw/kosovo_ocds.jsonl` is missing, restore the exact original source:

```bash
gzip -dk data/raw/kosovo_ocds.jsonl.gz
```

The compressed archive is preserved. The expanded file is required because
readers verify the complete raw-to-model release chain, even when opening
existing results. Do not replace it with a newer download just to run the UI.

```bash
uv run --no-sync python -m thesis ui
```

Open [localhost:8501](http://localhost:8501). Use `--port 8502` if the default port
is occupied. No pipeline run or model training is needed for normal viewing.

The package supports Python 3.9–3.12. An alternative editable development
installation is `python -m pip install -e '.[dev,notebooks]'` inside an activated
virtual environment. The quoted extras work in shells such as zsh; this command
resolves allowed versions rather than reproducing the committed lockfile.

## Understand release and runtime checks

The release chain is:

```text
bronze → silver → gold/tender_features → benchmark → ml/tender_summary → dashboard
```

Readers verify artifact hashes, input and lineage bindings, publication DQ
evidence, configuration and implementation fingerprints. Every upstream release
is checked recursively. A partial or inconsistent generation is rejected.

| Operation | Runtime policy |
| --- | --- |
| Dashboard and other read-only artifact readers | Validate the runtime recorded inside the release, but allow a different compatible host runtime. Source, configuration and artifact checks still apply. |
| `pipeline status` | Uses exact runtime matching when deciding whether a stage is fresh. A readable snapshot can therefore appear stale on another machine. |
| `pipeline validate-releases` | Requires the current Python, platform and recorded library versions to match the published runtime, in addition to all integrity checks. |
| Pipeline stages consuming upstream releases | Require upstream releases from the current runtime. Rebuild the chain from Bronze when intentionally changing runtime or implementation. |

The bundled generation records CPython 3.9.6 on macOS. `requirements-lock.txt`
captures that audited environment; it is not a portable cross-platform lock.
`uv.lock` resolves the supported environments used by CI and Docker. Installing
it on Python 3.11 does not make the host identical to the original runtime.

The implementation fingerprint covers all `src/thesis/**/*.py` files and
`pyproject.toml`, `requirements.txt`, `requirements-lock.txt` and `uv.lock`.
Even a reporting-only edit under `src/thesis/` can invalidate Bronze and every
downstream stage. Display-only changes in `streamlit_app/` and edits to docs or
tests are outside that fingerprint.

## Inspect and test without rebuilding

```bash
uv run --no-sync python -m thesis info
uv run --no-sync python -m thesis pipeline status
```

`info` lists settings and artifact presence; it does not certify their integrity.
To exercise the dashboard readers and pages, install development dependencies
and run:

```bash
uv sync --frozen --extra dev --python 3.11
uv run --no-sync pytest tests/test_streamlit_pages.py tests/test_dashboard_presentations.py -q
```

For the strict publication check, use the runtime recorded by the release:

```bash
python -m thesis pipeline validate-releases
```

Do not edit a manifest to make a runtime or hash mismatch disappear. Restore the
matching files/environment, or deliberately rebuild a new generation.

To rerun DQ checks against validated existing tables:

```bash
uv run --no-sync python -m thesis dq run
```

This refreshes general reports under `data/dq/` but does not publish new data or
replace immutable release-owned DQ evidence. Errors cause a nonzero exit status;
warnings also do so when `THESIS_FAIL_FAST_ON_DQ=true`. Changing that setting can
itself invalidate an existing configuration fingerprint.

## Intentionally rebuild from the preserved source

Keep a copy of the published dataset before replacing a research generation.
Use one environment for every stage. With the bundled gzip and JSONL both
present, these commands reuse the local source without requesting a newer copy:

```bash
uv run --no-sync python -m thesis pipeline bronze
uv run --no-sync python -m thesis pipeline run --from silver --force
uv run --no-sync python -m thesis pipeline validate-releases
uv run --no-sync python -m thesis report findings
```

The first command validates the local gzip/JSONL pair and republishes Bronze
provenance when required. The second rebuilds Silver, Gold, the full benchmark
and ML in order. The full benchmark uses checkpoints; duration depends on
hardware, data and reusable work. There is no fixed completion-time guarantee.
`report findings` regenerates `docs/findings.md` from the resulting validated
artifacts.

When upstream releases already match the current code, configuration and
runtime, narrower rebuilds are available:

```bash
# Rebuild the benchmark and then ML.
uv run --no-sync python -m thesis pipeline run --from benchmark --force

# Refit ML only, using the valid full benchmark release.
uv run --no-sync python -m thesis pipeline run --only ml --force
```

`--only` does not rebuild dependencies. ML rejects stale or edited champion
metadata and re-derives the model election from release-bound benchmark evidence.
`pipeline benchmark --quick` is a development smoke run; its output cannot
replace the full benchmark consumed by ML.

## Intentionally refresh from the remote publication

The ordinary DAG command always checks the remote Bronze publication, even when
other stages are fresh. It can replace the bundled source and derived results:

```bash
uv run --no-sync python -m thesis pipeline run
```

Add `--force` to rerun every stage. `pipeline check-updates` refreshes Bronze
only; downstream results then require rebuilding when the source changes.
`pipeline bronze --force` also forces a fresh download and extraction. These
commands are maintenance operations, not prerequisites for opening the dashboard.

## Docker and scheduling

Restore the raw JSONL before starting the Compose app:

```bash
docker compose up --build app
```

Compose mounts the local `data/` directory at `/data` and exposes port 8501.
The image uses a locked Python 3.11 environment, so the bundled results use the
compatible read-only policy described above. The image does not contain the
dataset by itself.

`GET /_stcore/health` checks whether Streamlit is alive. Docker polls it every
30 seconds; a healthy process does not prove that a page can read its data.
Use the page tests or open the dashboard to verify that separately.

`airflow_dags/` is an optional orchestration example. It is not started by the
Compose app and does not make this submitted snapshot a live monitoring service.

## Troubleshooting and maintenance

| Symptom | Action |
| --- | --- |
| `ModuleNotFoundError: thesis` | Run the environment setup from the project root and launch through `uv run --no-sync`. |
| Missing raw JSONL | Restore it with `gzip -dk data/raw/kosovo_ocds.jsonl.gz` if absent. |
| “Produced with a different runtime” | For viewing, use the dashboard's compatible read-only path. For strict validation, restore the recorded runtime; for new results, rebuild from Bronze. |
| Hash, source or configuration mismatch | Check the named file and local `THESIS_*` settings. Restore the matching release or intentionally rebuild; do not patch its hashes. |
| A DQ suite fails | Read `data/dq/<suite_name>.dq.md`. ERROR expectations block publication; WARNING expectations block it when fail-fast is enabled. |
| A dashboard page raises an exception | Run the page tests above and inspect `streamlit_app/_bootstrap.py` and the reported traceback. |
| Upstream download times out | For an intentional download, set `THESIS_OCDS_REQUEST_TIMEOUT_S`; it is part of the recorded pipeline configuration. |

Pipeline writers hold the interprocess lock `data/.pipeline.lock` for the
complete stage/run. Files are replaced atomically and the stage manifest is
published last. A concurrent reader can temporarily fail validation during a
multi-file replacement; continuous availability is not guaranteed. Do not
remove a lock file to bypass an active writer.

Structured logs include an event, timestamp, level and run identifier, plus
context-specific fields such as task and duration. Set `THESIS_LOG_FORMAT=json`
for machine-readable log events. CLI tables and summaries may still be printed
alongside those events, so redirected CLI output is not necessarily pure JSONL.

`make clean` removes development caches and coverage output, preserving research
data and model results. Preserve the compressed raw snapshot, current release
manifests, lineage sidecars, lockfiles and any human judgements in `data/review/`
when archiving the project. Derived data can be rebuilt; human review cannot.
