# Maintenance scripts

## Recreate the EDA notebook template

From the repository root, in an environment with the `notebooks` extra installed:

```bash
.venv/bin/python scripts/build_notebook.py
```

This rewrites `notebooks/01_eda.ipynb` with the maintained, output-cleared template.
Save any research notes or executed outputs you want to retain before running it.
The destination is resolved relative to the repository, regardless of the shell's
working directory. It does not generate `02_data_quality.ipynb` or run the pipeline.

See [the notebook guide](../notebooks/README.md) for opening and executing the
notebooks, and [CONTRIBUTING.md](../CONTRIBUTING.md) for environment setup.
