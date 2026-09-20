"""Pipeline orchestration — every layer transformation lives here.

Each module exposes a single ``run()`` entry point that the CLI and the
DAG runner invoke. ``run()`` is idempotent: re-running on the same input
produces the same output (modulo ``random_state``, which is fixed in
:mod:`thesis.config`).
"""
