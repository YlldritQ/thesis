# Exploratory notebooks

These are output-cleared research templates. They read the bundled source and
published tables; they do not publish pipeline artifacts or establish independent
model validation. Use [the generated findings](../docs/findings.md) when citing
current numerical results in the thesis.

| Notebook | Purpose |
|---|---|
| [01_eda.ipynb](01_eda.ipynb) | Explore raw OCDS coverage, values, bidders, and preliminary screening ideas |
| [02_data_quality.ipynb](02_data_quality.ipynb) | Inspect the normalized Silver/Gold tables and current data-quality evidence |

The preliminary EDA indicators are exploratory examples. The released rule
implementation and [methodology](../docs/methodology.md) define the dashboard's
actual indicators and scoring.

## Open the notebooks

Install the development/notebook environment following
[CONTRIBUTING.md](../CONTRIBUTING.md) and restore the raw JSONL as described in
[the data guide](../data/README.md). From the repository root:

```bash
.venv/bin/python -m ipykernel install --user --name thesis --display-name 'Python (thesis)'
cd notebooks
../.venv/bin/jupyter notebook
```

Select the `Python (thesis)` kernel. The notebooks resolve data paths relative to
this `notebooks/` working directory. Execute cells in order; no previously stored
outputs are supplied as evidence.

Clear outputs before committing the templates. Save completed research notes
separately if you need to retain them. The EDA template can be recreated with
[the notebook generator](../scripts/README.md); doing so overwrites that notebook.
