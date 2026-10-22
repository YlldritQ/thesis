"""Presentation regressions: filters, denominators, missing values, and chart meaning.

These tests use small fixtures instead of altering the published dataset. The
overview interaction tests exercise real sidebar widgets so a return to global,
pre-aggregated monthly data cannot silently ignore the user's selection.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "streamlit_app"))

import _charts  # noqa: E402 - application helpers live outside the installed package
import _narrative  # noqa: E402


@pytest.fixture
def dashboard_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ocid": [f"fixture-{i}" for i in range(6)],
            "tender_id": [f"fixture-{i}-1" for i in range(6)],
            "title": [f"Tenderi {i}" for i in range(6)],
            "release_date": pd.to_datetime(
                ["2024-01-10", "2024-01-11", "2024-01-12", "2024-03-10", "2024-03-12", None],
                utc=True,
            ),
            "year": pd.Series([2024, 2024, 2024, 2024, 2024, pd.NA], dtype="Int64"),
            "category": ["goods", "goods", "services", "goods", "services", "works"],
            "method": ["open"] * 6,
            "method_details": ["otvoreni postupak"] * 6,
            "procuring_entity_name": ["Autoriteti A", "Autoriteti A", "Autoriteti B"] * 2,
            "estimated_value_eur": [
                100_000.0,
                200_000.0,
                900_000.0,
                300_000.0,
                800_000.0,
                70_000.0,
            ],
            "total_awarded_eur": [80_000.0, 0.0, 850_000.0, 0.0, 780_000.0, 0.0],
            "n_awards": [1, 0, 1, 0, 1, 0],
            "num_bidders": pd.Series([1, pd.NA, 3, 0, 1, pd.NA], dtype="Int64"),
            "bidder_data_observed": [True, False, True, True, True, False],
        }
    )


@pytest.fixture
def source_boundary_rows(dashboard_rows) -> pd.DataFrame:
    rows = dashboard_rows.copy(deep=True)
    rows["release_date"] = pd.to_datetime(
        [
            "2023-12-31 23:30:00",
            "2024-01-31 23:30:00",
            "2024-06-30 22:30:00",
            "2024-06-30 23:30:00",
            "2024-12-31 22:30:00",
            None,
        ],
        utc=True,
    )
    rows["award_date"] = rows["release_date"] + pd.Timedelta(days=1)
    rows["year"] = rows["release_date"].dt.year.astype("Int64")
    rows["month"] = rows["release_date"].dt.strftime("%Y-%m")
    rows["ensemble_score"] = [0.1, 0.5, 0.8, 0.3, 0.6, np.nan]
    return rows


def test_source_local_dates_drive_year_filter_and_monthly_buckets(source_boundary_rows):
    import _bootstrap

    original = source_boundary_rows.copy(deep=True)
    local = _bootstrap._to_source_local_time(source_boundary_rows)

    assert local["release_date"].dt.strftime("%Y-%m-%d %H:%M").iloc[:5].tolist() == [
        "2024-01-01 00:30",
        "2024-02-01 00:30",
        "2024-06-30 23:30",  # Summer dates retain the source's fixed +01 offset.
        "2024-07-01 00:30",
        "2024-12-31 23:30",
    ]
    pd.testing.assert_series_equal(
        local["year"], pd.Series([2024] * 5 + [pd.NA], name="year", dtype="Int64")
    )
    assert local["month"].iloc[:5].tolist() == [
        "2024-01",
        "2024-02",
        "2024-06",
        "2024-07",
        "2024-12",
    ]
    assert pd.isna(local.loc[5, "month"])
    for column in ("release_date", "award_date"):
        pd.testing.assert_series_equal(local[column].dt.tz_convert("UTC"), original[column])
    pd.testing.assert_series_equal(local["ensemble_score"], original["ensemble_score"])

    selected = local[_bootstrap._selected_filter_mask(local["year"], [2024])]
    assert selected["ocid"].tolist() == [f"fixture-{i}" for i in range(5)]
    monthly = _charts.monthly_summary(selected).dropna(subset=["tenders"])
    assert monthly["release_date"].dt.strftime("%Y-%m").tolist() == [
        "2024-01",
        "2024-02",
        "2024-06",
        "2024-07",
        "2024-12",
    ]
    assert monthly["tenders"].tolist() == [1] * 5
    assert monthly["value_mn"].tolist() == pytest.approx([0.1, 0.2, 0.9, 0.3, 0.8])
    undated = local[
        _bootstrap._selected_filter_mask(local["year"], [_bootstrap.UNKNOWN_FILTER_OPTION])
    ]
    assert undated["ocid"].tolist() == ["fixture-5"]
    assert _charts.monthly_summary(undated).empty
    pd.testing.assert_frame_equal(source_boundary_rows, original)


def test_source_local_time_leaves_naive_dates_and_their_buckets_unchanged(source_boundary_rows):
    import _bootstrap

    rows = source_boundary_rows.copy(deep=True)
    for column in ("release_date", "award_date"):
        rows[column] = rows[column].dt.tz_localize(None)
    original = rows.copy(deep=True)

    pd.testing.assert_frame_equal(_bootstrap._to_source_local_time(rows), original)
    pd.testing.assert_frame_equal(rows, original)


def test_monthly_summary_recomputes_values_and_denominators_from_selected_rows(dashboard_rows):
    original = dashboard_rows.copy(deep=True)
    selected = dashboard_rows[dashboard_rows["category"].eq("goods")]
    monthly = _charts.monthly_summary(selected).set_index("release_date")
    january = monthly.loc[pd.Timestamp("2024-01-01", tz="UTC")]
    march = monthly.loc[pd.Timestamp("2024-03-01", tz="UTC")]

    assert january["tenders"] == 2
    assert january["value_mn"] == pytest.approx(0.3)
    assert january["observed_bidders"] == 1
    assert january["single_bidder_pct"] == 100
    assert january["zero_bidder_pct"] == 0
    assert january["bidder_data_coverage_pct"] == 50
    assert march["tenders"] == 1
    assert march["zero_bidder_pct"] == 100
    pd.testing.assert_frame_equal(dashboard_rows, original)


def test_monthly_summary_missing_bidder_lists_never_count_as_zero_or_single():
    rows = pd.DataFrame(
        {
            "release_date": pd.to_datetime(["2024-01-01"] * 5, utc=True),
            "estimated_value_eur": [10.0] * 5,
            "num_bidders": pd.Series([1, 0, 1, pd.NA, pd.NA], dtype="Int64"),
            "bidder_data_observed": pd.Series([True, True, False, True, pd.NA], dtype="boolean"),
        }
    )

    january = _charts.monthly_summary(rows).iloc[0]

    assert january["tenders"] == 5
    assert january["observed_bidders"] == 2
    assert january["single_bidder_pct"] == 50
    assert january["zero_bidder_pct"] == 50
    assert january["bidder_data_coverage_pct"] == 40


def test_monthly_summary_preserves_absent_months_and_unknown_rates(dashboard_rows):
    monthly = _charts.monthly_summary(dashboard_rows).set_index("release_date")
    gap = monthly.loc[pd.Timestamp("2024-02-01", tz="UTC")]
    assert gap.isna().all(), "An unrepresented month must not imply zero activity or competition."

    unknown = dashboard_rows.iloc[[1]].copy()
    rates = _charts.monthly_summary(unknown).iloc[0]
    assert rates["tenders"] == 1
    assert rates["observed_bidders"] == 0
    assert rates["bidder_data_coverage_pct"] == 0
    assert pd.isna(rates["single_bidder_pct"])
    assert pd.isna(rates["zero_bidder_pct"])


def test_monthly_summary_distinguishes_missing_amounts_from_recorded_zero(dashboard_rows):
    rows = dashboard_rows.iloc[[0, 1, 3, 4]].copy()
    rows["estimated_value_eur"] = [np.nan, np.nan, 0.0, np.nan]
    monthly = _charts.monthly_summary(rows).set_index("release_date")

    assert pd.isna(monthly.loc[pd.Timestamp("2024-01-01", tz="UTC"), "value_mn"])
    assert monthly.loc[pd.Timestamp("2024-03-01", tz="UTC"), "value_mn"] == 0


def test_undated_selection_has_empty_time_series_without_dropping_other_charts(dashboard_rows):
    undated = dashboard_rows[dashboard_rows["release_date"].isna()]
    monthly = _charts.monthly_summary(undated)

    assert monthly.empty
    assert len(_charts.time_series_volume(monthly).data[0].x) == 0
    assert len(_charts.time_series_value(monthly).data[0].x) == 0
    category = _charts.category_bar(undated, "estimated_value_eur", "Kategoritë")
    assert list(category.data[0].customdata) == ["Punë"]
    assert list(category.data[0].x) == [70_000]


def test_category_totals_keep_null_and_blank_metadata_visible():
    frame = pd.DataFrame(
        {
            "category": ["goods", None, "", "services", "works"],
            "estimated_value_eur": [10.0, 20.0, 30.0, 0.0, np.nan],
        }
    )

    fig = _charts.category_bar(frame, "estimated_value_eur", "Kategoritë")
    totals = dict(zip(fig.data[0].customdata, fig.data[0].x))

    assert totals == {"Shërbime": 0.0, "Furnizime": 10.0, "E papërcaktuar": 50.0}
    assert sum(totals.values()) == frame["estimated_value_eur"].sum()
    assert "Punë" not in totals, "An entirely missing total must not be drawn as zero."


def test_procedure_chart_separates_quotation_from_coarse_open_method():
    frame = pd.DataFrame(
        {
            "method": ["open", "open", "open"],
            "method_details": ["otvoreni postupak", "otvoreni postupak", None],
            "tender_id": ["source-2024-1", "source-2024-6", None],
            "estimated_value_eur": [20_000.0, 5_000.0, 3_000.0],
        }
    )

    fig = _charts.method_bar(frame, "estimated_value_eur", "Procedurat")
    totals = dict(zip(fig.data[0].customdata, fig.data[0].x))

    assert totals == {
        "E papërcaktuar": 3_000,
        "Kuotim i çmimeve": 5_000,
        "Procedurë e hapur": 20_000,
    }


def test_long_authority_names_stay_distinct_even_when_display_prefixes_match():
    common = "Autoriteti me një emër shumë të gjatë të përbashkët "
    names = [common + "A", common + "B"]
    frame = pd.DataFrame({"authority": names, "estimated_value_eur": [2_000_000, 3_000_000]})

    fig = _charts.top_n_bar(frame, "authority", "estimated_value_eur")
    bars = fig.data[0]

    assert len(set(bars.y)) == 2
    assert set(bars.customdata) == set(names)
    assert list(bars.x) == [2, 3]
    assert len(fig.layout.yaxis.ticktext) == 2
    assert fig.layout.yaxis.ticktext[0] == fig.layout.yaxis.ticktext[1]
    assert "customdata" in bars.hovertemplate
    assert fig.layout.xaxis.title.text == "Milionë euro"


def test_value_bands_count_zero_and_boundary_amounts_without_logarithmic_units():
    values = pd.Series([0.0, 999.0, 1_000.0, 10_000.0, 100_000.0, 1e6, 1e7, np.nan])
    fig = _charts.value_histogram(values)
    assert list(fig.data[0].y) == [2, 1, 1, 1, 1, 1]
    assert sum(fig.data[0].y) == values.notna().sum()
    assert all("€" in label for label in fig.data[0].x)


def test_lorenz_curve_includes_origin_and_full_population():
    fig = _charts.lorenz_curve(pd.Series([30.0, 10.0, np.nan]), "Furnizuesit")
    curve = fig.data[0]

    np.testing.assert_allclose(curve.x, [0, 0.5, 1])
    np.testing.assert_allclose(curve.y, [0, 0.25, 1])
    assert np.isfinite(curve.y).all()
    assert fig.layout.yaxis.tickformat == ".0%"


@pytest.mark.parametrize("values", [[0.0, 0.0], [np.nan], []])
def test_lorenz_curve_without_positive_values_shows_empty_state(values):
    fig = _charts.lorenz_curve(pd.Series(values, dtype=float), "Furnizuesit")
    assert not fig.data
    assert fig.layout.annotations
    assert "Nuk ka vlera pozitive" in fig.layout.annotations[0].text


@pytest.mark.parametrize("missing", [None, np.nan, pd.NA])
def test_missing_numeric_values_use_dash_instead_of_zero(missing):
    assert _charts.fmt_number(missing) == "—"
    assert _charts.fmt_eur(missing) == "—"


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "0 €"), (1234, "1,2 mijë €"), (1_250_000, "1,25 milionë €"), (2e9, "2,00 miliardë €")],
)
def test_euro_labels_include_readable_scale_and_currency(value, expected):
    assert _charts.fmt_eur(value) == expected


def test_plain_summary_distinguishes_missing_bidders_and_absent_award_from_zero():
    missing = _narrative.plain_summary(
        {"num_bidders": pd.NA, "was_awarded": 0, "total_awarded_eur": 0}
    )
    recorded_zero = _narrative.plain_summary(
        {"num_bidders": 0, "was_awarded": 1, "total_awarded_eur": 0}
    )

    assert "Numri i ofertuesve nuk është publikuar" in missing
    assert "Nuk ka vendim dhënieje të regjistruar" in missing
    assert "**0 €**" not in missing
    assert "zero ofertues" in recorded_zero
    assert "**0 €**" in recorded_zero


def test_nullable_rule_flags_do_not_invent_signals_or_change_published_registry():
    from thesis.anomaly.rules import RULES

    assert set(_narrative.FLAG_NARRATIVE) == {rule.code for rule in RULES}
    row = dict.fromkeys(_narrative.FLAG_NARRATIVE, pd.NA)
    assert _narrative.explain_flags(row) == []
    row["SINGLE_BIDDER_OPEN"] = True
    flags = _narrative.explain_flags(row)
    assert [flag["code"] for flag in flags] == ["SINGLE_BIDDER_OPEN"]
    assert flags[0]["title"] == "Një ofertues në procedurë të hapur"


def _overview_app(monkeypatch, dashboard_rows):
    import _bootstrap
    from streamlit.testing.v1 import AppTest

    calls = []
    original_summary = _charts.monthly_summary

    def record_summary(frame):
        result = original_summary(frame)
        calls.append((frame.copy(), result.copy()))
        return result

    monkeypatch.setattr(_bootstrap, "cached_gold", lambda: dashboard_rows.copy())
    monkeypatch.setattr(_charts, "monthly_summary", record_summary)
    app = AppTest.from_file(str(ROOT / "streamlit_app" / "pages" / "1_Overview.py"))
    app.run()
    assert not app.exception
    return app, calls


def test_overview_category_widget_changes_monthly_charts_and_headline_totals(
    monkeypatch, dashboard_rows
):
    app, calls = _overview_app(monkeypatch, dashboard_rows)
    assert len(calls[-1][0]) == 6

    app.multiselect(key="filter_cats").set_value(["goods"]).run()
    assert not app.exception
    selected, monthly = calls[-1]
    assert selected["category"].tolist() == ["goods"] * 3
    assert monthly["tenders"].sum() == 3
    assert monthly["value_mn"].sum() == pytest.approx(0.6)
    assert app.metric[0].value == "3"
    assert app.metric[1].value == "600,0 mijë €"

    app.multiselect(key="filter_cats").set_value(["services"]).run()
    assert not app.exception
    assert calls[-1][1]["value_mn"].sum() == pytest.approx(1.7)
    assert app.metric[0].value == "2"


def test_overview_unknown_year_keeps_headlines_but_has_no_invented_monthly_data(
    monkeypatch, dashboard_rows
):
    import _bootstrap

    app, calls = _overview_app(monkeypatch, dashboard_rows)
    app.multiselect(key="filter_years").set_value([_bootstrap.UNKNOWN_FILTER_OPTION]).run()

    assert not app.exception
    selected, monthly = calls[-1]
    assert len(selected) == 1
    assert selected["release_date"].isna().all()
    assert monthly.empty
    assert app.metric[0].value == "1"
    assert app.metric[1].value == "70,0 mijë €"
