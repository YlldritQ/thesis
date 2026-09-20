# Bundled data and research artifacts

This directory contains the static publication used by the dashboard and thesis
reports. Keep its current data, models, manifests, and companion files together.
The application validates their hashes before displaying the results.

## Directory map

| Directory | Contents | Retention |
|---|---|---|
| `raw/` | Compressed OCDS source and Bronze release manifest | Keep the archive and manifest; restore the expanded JSONL after cloning |
| `silver/` | Normalized tender and award tables | Keep tables, release manifest, and adjacent lineage sidecars |
| `gold/` | Feature table, scored tender table, and entity/monthly summaries | Keep all published artifacts and sidecars |
| `models/` | Fitted models, explanation values, validation, and ML release | Keep all published artifacts |
| `models/benchmark/` | Full results, leaderboard, champions, and benchmark release | Keep canonical files; local quick/WIP checkpoints are ignored by Git |
| `dq/` | Current table checks and immutable publication-gate evidence | Keep all `*.dq.json` and `*.dq.md` files; see [the report guide](dq/README.md) |
| `review/` | Manual-audit sample and its metadata | Preserve; never discard or overwrite completed human review work |
| `external/` | OSHP source snapshot and the report withdrawing its use as external validation | Retained as methodological evidence and a test dependency; not outcome labels |
| `_lineage/` | Timestamped copies of lineage records | Nine copies from the bundled publication are retained; additional run history is local |

The canonical lineage records are the `*.parquet.lineage.json` files **beside the
Parquet artifacts**. The timestamped history under `_lineage/` is supplementary;
it is not a substitute for those sidecars.

## Restore the source after cloning

From the repository root, when the expanded JSONL is absent:

```bash
gzip -dk data/raw/kosovo_ocds.jsonl.gz
```

This keeps the gzip archive and restores the exact source bytes expected by the
Bronze manifest. The expanded file exceeds GitHub's individual-file size limit
and is intentionally ignored. It is required by the dashboard's validation chain,
even when no model training is being performed.

## Reading, rebuilding, and editing

Use the [dashboard setup](../README.md#hapja-e-panelit) to inspect the bundled
publication. Its readers allow a compatible Python environment while checking
source, configuration, file integrity, and the complete publication chain.
Strict release verification and pipeline mutation require the recorded runtime;
see the [operations guide](../docs/operations.md) before rebuilding.

Do not edit generated tables, model files, release-owned DQ evidence, or manifests
by hand. A change requires intentional republication of the affected chain.
Regenerate [findings](../docs/findings.md) after a rebuild rather than copying
numbers into that generated report manually.

The notebooks are exploratory templates. Their outputs are not a replacement for
published data, [methodology](../docs/methodology.md), or
[manual outcome review](../docs/manual_audit_protocol.md).

## Cleanup policy

`make clean` removes development caches and coverage output while preserving this
directory, `.venv`, and research notebooks. Benchmark quick/WIP files and newly
generated lineage history are local working files excluded from new Git additions.
Keep unfinished benchmark checkpoints if you intend to resume that run.

Superseded prototype DQ tables, old execution-history copies, and draft review
reports were removed from the working tree during cleanup. Their earlier versions
remain in Git history. The current figures come from the bundled publication and
[generated findings](../docs/findings.md), not those historical reports.
