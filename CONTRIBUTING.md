# Contributing

Thanks for considering a contribution. This is a thesis-grade reference
project with strict standards — please read this before opening a PR.

## Quick start

```bash
git clone <repo>
cd kosovo-procurement-thesis
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev,notebooks]
pre-commit install
pytest
```

## Development workflow

1. **Branch** from `main`. Use a descriptive name: `feature/…`,
   `fix/…`, `docs/…`.
2. **Write tests first** when fixing a bug or adding a feature. We aim
   to keep the test suite < 60 s end-to-end so it stays runnable
   pre-push.
3. **Run the local checks** before pushing:
   ```bash
   ruff check . && ruff format --check .
   mypy src/thesis
   pytest -m "not slow"
   ```
   `pre-commit` runs the first two automatically on every commit.
4. **Open a PR** with:
   - a one-line summary,
   - a list of behavioural changes,
   - a screenshot if the change is visible in the Streamlit UI,
   - `closes #N` if it fixes an issue.

## Architectural rules

- **No I/O in `domain/`.** It is pure transforms over DataFrames.
- **All disk I/O goes through `io/`.** New readers register a cache
  decorator. New writers emit a lineage sidecar.
- **No bare `print`.** Use `thesis.logging.get_logger(__name__)`.
- **No hard-coded paths.** Import from `thesis.paths`.
- **No hard-coded numbers.** Add to `thesis.config.Settings`, document
  the env var in `.env.example`.
- **Every new pipeline stage** must:
  - live under `thesis.pipeline.<name>` with a `run()` entrypoint,
  - declare its inputs and outputs in `thesis.pipeline.dag.default_dag()`,
  - emit a lineage sidecar via `thesis.io.writers.write_parquet`,
  - have at least one happy-path test in `tests/unit/`.
- **Every new public function** has a Google-style docstring.

## Anomaly rules

The rule book is conservative on purpose. New rules require:
- a citation in the `reference` field,
- a weight in `[0.3, 1.0]` (the higher the weight, the stronger the
  evidence required),
- a unit test in `tests/unit/test_rules.py`,
- an entry in `docs/methodology.md`.

## Sensitive subject

This project surfaces public-procurement *signals*, not fraud verdicts.
No PR may:

- introduce a "fraud probability" column or any framing that conflates
  anomaly score with fraud,
- remove the caveat banner from Streamlit pages,
- weaken `docs/responsible_use.md`,
- silence DQ failures — they should escalate as warnings or errors.

## Releases

We follow SemVer. Tag a release with `git tag v$NEW && git push --tags`.
GitHub Actions builds and publishes the Docker image automatically.
