# Contributing

This is a research project for a thesis on public procurement in Kosovo.
Changes should remain reproducible and distinguish signals for review from
proven findings. Read the [methodology](docs/methodology.md) and
[responsible-use guidance](docs/responsible_use.md) before changing the analysis.

## Set up a development environment

Run commands from the project root. CI and Docker use **uv 0.11.28**; Python
3.11 is the recommended development version. Package metadata supports Python
3.9–3.12. Pipeline locking supports macOS and Linux; use Docker on Windows.

```bash
uv sync --frozen --extra dev --python 3.11
```

This creates or updates `.venv` using the committed `uv.lock`. Use a separate
checkout if you need to preserve an existing audited environment. The locked
Python 3.11 environment can read the bundled results; it does not reproduce the
original Python 3.9.6/macOS runtime recorded in their manifests.

Restore the original raw file **only if** `data/raw/kosovo_ocds.jsonl` is absent:

```bash
gzip -dk data/raw/kosovo_ocds.jsonl.gz
```

Then open the existing dashboard without rebuilding:

```bash
uv run --no-sync python -m thesis ui
```

In a Git checkout, install the optional local hooks:

```bash
uv run --no-sync pre-commit install
uv run --no-sync pre-commit install --hook-type pre-push
```

For notebook work, include the optional notebook dependencies:

```bash
uv sync --frozen --extra dev --extra notebooks --python 3.11
```

The notebooks are exploratory templates with cleared outputs.
`scripts/build_notebook.py` regenerates only `notebooks/01_eda.ipynb`; it is not
part of dashboard startup or the canonical data pipeline.

## Choose the right layer

- **Dashboard text, layout and charts:** edit `streamlit_app/`. Shared display
  helpers are `_bootstrap.py`, `_charts.py` and `_narrative.py`.
- **Data transformations and procurement features:** use `src/thesis/domain/`
  for transformations, `src/thesis/io/` for readers and writers, and
  `src/thesis/pipeline/` for orchestration. Use paths from `thesis.paths` and
  configuration from `thesis.config`.
- **Rules and models:** edit `src/thesis/anomaly/`; document the rationale,
  thresholds, weights and limitations. Diagnostic rules may have zero weight.
- **Evidence:** `docs/findings.md` is generated from validated artifacts. Change
  its generator or input data, then regenerate it; do not hand-edit its figures.

Published releases hash **all** Python files under `src/thesis/`, plus
`pyproject.toml`, `requirements.txt`, `requirements-lock.txt` and `uv.lock`.
Changing any of these invalidates the existing release chain. Presentation,
test and documentation edits outside those paths do not change that fingerprint.
See [operations](docs/operations.md) for an intentional rebuild; do not alter
manifests to conceal a mismatch.

A new pipeline stage must declare its inputs, outputs and dependencies in
`src/thesis/pipeline/dag.py`, publish the required release/DQ evidence, and use
the existing single-writer and atomic-publication mechanisms. Add tests for the
new behavior and failure cases.

## Verify changes

Run targeted tests during development, then the checks relevant to the change:

```bash
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync mypy src/thesis
uv run --no-sync pytest tests/unit tests/contracts -q
uv run --no-sync pytest tests/integration -q
uv run --no-sync pytest tests/test_streamlit_pages.py tests/test_dashboard_presentations.py -q
```

The dashboard tests require the restored, valid bundled snapshot. After a
provenance-bound source change, use unit/fixture tests while developing and
rebuild the release chain before expecting snapshot-dependent checks to pass.
The full suite is `uv run --no-sync pytest tests -q`; CI also runs it with
`-m "not slow"`. Test duration depends on the environment and selected checks.

For UI changes, open the affected pages and check filters, empty results,
missing values and chart labels. For rule changes, relevant tests include
`tests/unit/test_features_and_rules.py`, `test_narrative.py` and
`test_ensemble_explanations.py`.

`make clean` removes development caches and coverage output. It preserves the
bundled data, model artifacts, reports and human review records.

## Submit a focused change

Explain the problem, resulting behavior and checks performed. Include a
screenshot for visible UI changes and state whether published data or model
outputs need rebuilding. Keep generated artifacts consistent with their release
manifests.

Preserve these interpretation rules:

- Anomaly scores are relative review signals, not fraud probabilities.
- A recorded award decision is not proof of a signed or paid contract.
- Missing bidder data is not zero bidders.
- Rule-derived labels measure agreement with the rules, not independently
  verified detection accuracy.
- DQ failures and the dashboard's “Anomalia ≠ mashtrim” notice remain visible.

The current GitHub Actions workflow checks code, tests the project and builds a
Docker image. It does **not** publish images or create releases automatically.
