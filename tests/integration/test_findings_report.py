"""Drift guard for docs/findings.md (review C-6/M-09/M-39).

Regenerates the findings numbers from the live gold layer and asserts:
* no unresolved ``[X]`` / ``€[`` placeholders,
* the committed Markdown matches the live render except for its input-mtime timestamp,
* every artifact read by the report is declared in its input hashes,
* the rule count matches the code,
* headline numbers are internally consistent with the gold parquet.

Skips when the gold layer is absent (e.g. a fresh checkout without data).
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
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


def _normalized_findings(markdown: str) -> str:
    """Ignore only the validated timestamp of the generated-report header."""
    # The renderer uses the latest input mtime. Git checkout assigns new mtimes,
    # even when all input bytes and hashes match the original publication.
    # Keep every hash, numeric result and other header/body character exact.
    pattern = (
        r"(?m)^(> \*\*Auto-generated from the live gold layer\*\* at `)"
        r"([^`\n]+)(` by `thesis report findings`\.)"
    )

    def replace_timestamp(match: re.Match) -> str:
        timestamp = datetime.fromisoformat(match.group(2).replace("Z", "+00:00"))
        assert timestamp.tzinfo is not None, "Findings timestamp must include a timezone"
        return f"{match.group(1)}<generated-at>{match.group(3)}"

    normalized, count = re.subn(
        pattern, replace_timestamp, markdown.replace("\r\n", "\n").rstrip("\n")
    )
    assert count == 1, "Findings must contain exactly one generated timestamp header"
    return normalized


def test_findings_normalization_preserves_content_and_input_hashes():
    published_time = "2026-07-19T12:30:35.687388+00:00"
    checkout_time = "2026-09-20T19:16:20.141963+00:00"
    published = (
        f"> **Auto-generated from the live gold layer** at `{published_time}` "
        "by `thesis report findings`. Do not hand-edit.\n"
        "> Input hashes: `tenders.parquet:abc123`\n"
        "- Tenders: **10**\n"
        f"- Source timestamp: `{published_time}`\n"
    )
    checked_out = published.replace(published_time, checkout_time, 1)
    assert _normalized_findings(published) == _normalized_findings(checked_out)
    for original, changed in (
        ("abc123", "def456"),
        ("**10**", "**11**"),
        ("Do not hand-edit.", "Changed description."),
        (f"- Source timestamp: `{published_time}`", f"- Source timestamp: `{checkout_time}`"),
    ):
        assert _normalized_findings(published) != _normalized_findings(
            published.replace(original, changed)
        )


@pytest.mark.parametrize("timestamp", ["not-a-date", "2026-07-19T12:30:35"])
def test_findings_normalization_rejects_invalid_timestamps(timestamp):
    markdown = (
        f"> **Auto-generated from the live gold layer** at `{timestamp}` "
        "by `thesis report findings`."
    )
    with pytest.raises((AssertionError, ValueError)):
        _normalized_findings(markdown)


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

    assert _normalized_findings(committed) == _normalized_findings(generate(write=False)), (
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
