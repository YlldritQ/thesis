"""Data-quality framework.

Two complementary layers:

* :mod:`thesis.dq.framework` — a tiny "expectation" runner inspired by Great
  Expectations but with zero infrastructure cost. Every silver/gold table
  ships with a suite of expectations evaluated on every pipeline run.
* :mod:`thesis.dq.suites` — the actual expectation suites for our tables.
* :mod:`thesis.dq.profile` — the discovery profilers (schema walks).

The output is two files per run:

* ``data/dq/<table>.dq.json`` — machine-readable scorecard
* ``data/dq/<table>.dq.md``   — human-readable summary
"""
