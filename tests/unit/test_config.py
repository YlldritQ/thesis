"""Unit tests for the configuration module."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from thesis import config


def test_settings_defaults():
    config.reset_settings_for_tests()
    s = config.settings()
    assert s.log_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    assert s.random_seed == 7
    assert s.iso_forest_n_estimators >= 100
    assert 0 < s.iso_forest_contamination < 0.5


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("THESIS_RANDOM_SEED", "42")
    monkeypatch.setenv("THESIS_LOG_LEVEL", "DEBUG")
    config.reset_settings_for_tests()
    s = config.settings()
    assert s.random_seed == 42
    assert s.log_level == "DEBUG"


def test_settings_singleton(monkeypatch):
    config.reset_settings_for_tests()
    s1 = config.settings()
    s2 = config.settings()
    assert s1 is s2
