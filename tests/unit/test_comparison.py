"""Unit tests for the contextual-comparison anomaly layer."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis.anomaly import contextual_score
from thesis.domain.features import CONTEXT_FEATURES


def test_contextual_score_in_unit_interval():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        rng.normal(0, 1, (200, len(CONTEXT_FEATURES))),
        columns=CONTEXT_FEATURES,
    )
    s = contextual_score(df)
    assert s.between(0.0, 1.0).all()


def test_contextual_score_high_for_extreme_z():
    df = pd.DataFrame(
        # one row with a huge z-score on one feature, others tiny
        {
            "log_value_z_within_entity": [0.0, 5.0],
            "log_value_z_within_category": [0.0, 0.1],
            "log_value_z_within_method": [0.0, 0.1],
            "bidders_z_within_entity": [0.0, 0.1],
            "bidders_z_within_category": [0.0, 0.1],
            "awarded_ratio_z_within_category": [0.0, 0.1],
        }
    )
    s = contextual_score(df)
    # the second row should be much closer to 1
    assert s.iloc[1] > 0.9
    assert s.iloc[0] < 0.1


def test_contextual_score_handles_missing_columns():
    df = pd.DataFrame({"unrelated": [1.0, 2.0, 3.0]})
    s = contextual_score(df)
    assert (s == 0.0).all()
