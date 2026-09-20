"""Drift guard for docs/findings.md (review C-6/M-09/M-39).

Regenerates the findings numbers from the live gold layer and asserts:
* no unresolved ``[X]`` / ``€[`` placeholders,
* the committed Markdown exactly matches the deterministic live render,
* every artifact read by the report is declared in its input hashes,
* the rule count matches the code,
* headline numbers are internally consistent with the gold parquet.

Skips when the gold layer is absent (e.g. a fresh checkout without data).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis import paths
from thesis.anomaly.rules import RULES
from thesis.domain.procedures import STANDARD_OPEN, classify_procedure_series

pytestmark = pytest.mark.skipif(
    not paths.GOLD_TENDERS.exists(),
    reason="gold layer not built",
)


def test_findings_render_has_no_placeholder():
    from thesis.reporting import generate

    md = generate(write=False)
    assert "[X]" not in md
    assert "€[" not in md
    assert "[ ]" not in md


def test_committed_findings_exactly_matches_live_render():
    """Fail when the checked-in report drifts from any declared input."""
    from thesis.reporting import generate

    committed = (paths.DOCS / "findings.md").read_text()

    def normalized(markdown: str) -> str:
        return markdown.replace("\r\n", "\n").rstrip("\n")

    assert normalized(committed) == normalized(generate(write=False)), (
        "docs/findings.md is stale; run `thesis report findings`"
    )


def test_findings_rule_count_matches_code():
    from thesis.reporting import compute_findings

    d = compute_findings()
    assert d["n_rules"] == len(RULES)
    # every rule with a gold column is counted
    assert len(d["rule_counts"]) == len(RULES)


def test_findings_declares_every_artifact_it_reads():
    from thesis.reporting import FINDINGS_INPUTS, compute_findings

    d = compute_findings()
    assert set(d["input_sha256"]) == {str(path) for path in FINDINGS_INPUTS if path.exists()}


def test_findings_numbers_match_live_gold():
    import pandas as pd

    from thesis.reporting import compute_findings

    d = compute_findings()
    g = pd.read_parquet(paths.GOLD_TENDERS)

    assert d["n_tenders"] == len(g)
    assert d["n_awarded_tenders"] == int(g["was_awarded"].eq(1).sum())
    subtype = g["procedure_subtype"] if "procedure_subtype" in g else classify_procedure_series(g)
    standard = g[subtype.eq(STANDARD_OPEN)]
    observed = standard[
        standard.get("bidder_data_observed", standard["num_bidders"].notna()).fillna(False)
    ]
    expected = round(100 * observed["is_single_bidder"].mean(), 2)
    reported = d["single_bidding_by_procedure"][STANDARD_OPEN]
    assert reported["n_bidder_observed_all"] == len(observed)
    assert reported["single_bidder_pct_all"] == expected


def test_findings_separates_price_quotation_and_withdraws_invalid_validation():
    from thesis.reporting import compute_findings, generate

    d = compute_findings()
    assert "standard_open" in d["single_bidding_by_procedure"]
    assert "price_quotation" in d["single_bidding_by_procedure"]
    rendered = generate(write=False)
    assert "No EU equivalence is claimed" in rendered
    assert "External outcome validation — withdrawn" in rendered
    assert "NOT CORROBORATED" not in rendered
