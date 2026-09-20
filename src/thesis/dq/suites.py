"""Expectation suites for every table in the warehouse.

Each suite is intentionally small and *important* — these are the
invariants that, if violated, signal a real problem with the pipeline or
the source data. Soft observations (distributions, drift) live in the
profilers under :mod:`thesis.dq.profile`.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from ..anomaly.ensemble import ENSEMBLE_RANK_PREFIX, compose_hybrid_ensemble
from ..anomaly.rules import RULES
from ..config import settings
from ..domain.features import (
    ML_FEATURES,
    normalise_identity_name,
    normalise_supplier_business_id,
    supplier_key,
)
from .framework import Expectation, ExpectationSuite, Severity, dataframe_fingerprint

GOLD_SCORE_COLUMNS = (
    "rule_score",
    "iso_score",
    "lof_score",
    "ee_score",
    "ocsvm_score",
    "pca_score",
    "gmm_score",
    "knn_score",
    "hbos_score",
    "hgb_score",
    "context_score",
    "ensemble_score",
)


def _missing_columns(df: pd.DataFrame, expected: set[str]) -> list[str]:
    return sorted(expected.difference(df.columns))


def _canonical_group_key(value: object) -> str:
    """Represent nullable source identifiers without inventing an identity."""
    if pd.isna(value):
        return "null:"
    text = str(value)
    return f"value:{len(text)}:{text}"


def _projection_fingerprint(df: pd.DataFrame, columns: list[str]) -> str:
    """Fingerprint the available source columns used by a dynamic suite."""
    available = [column for column in columns if column in df]
    return dataframe_fingerprint(df[available])


def _score_columns(df: pd.DataFrame) -> list[str]:
    dynamic = [column for column in df.columns if column.startswith(ENSEMBLE_RANK_PREFIX)]
    return [*GOLD_SCORE_COLUMNS, *dynamic]


def _score_values(df: pd.DataFrame) -> pd.DataFrame | None:
    """Return numeric score values, or ``None`` when columns are absent."""
    if _missing_columns(df, set(GOLD_SCORE_COLUMNS)):
        return None
    return df[_score_columns(df)].apply(pd.to_numeric, errors="coerce")


def _scores_non_null(df: pd.DataFrame) -> tuple[bool, object]:
    values = _score_values(df)
    if values is None:
        return False, {"missing_columns": _missing_columns(df, set(GOLD_SCORE_COLUMNS))}
    nulls = values.isna().sum()
    observed = {column: int(count) for column, count in nulls.items() if count}
    return not observed, observed


def _scores_finite(df: pd.DataFrame) -> tuple[bool, object]:
    values = _score_values(df)
    if values is None:
        return False, {"missing_columns": _missing_columns(df, set(GOLD_SCORE_COLUMNS))}
    finite = np.isfinite(values.to_numpy(dtype=float))
    return bool(finite.all()), int((~finite).sum())


def _scores_in_unit_interval(df: pd.DataFrame) -> tuple[bool, object]:
    values = _score_values(df)
    if values is None:
        return False, {"missing_columns": _missing_columns(df, set(GOLD_SCORE_COLUMNS))}
    invalid = ~(values.ge(0.0) & values.le(1.0))
    return bool((~invalid).all().all()), int(invalid.sum().sum())


def _ensemble_xai_reconstruction(df: pd.DataFrame) -> tuple[bool, object]:
    rank_columns = [column for column in df.columns if column.startswith(ENSEMBLE_RANK_PREFIX)]
    if not rank_columns:
        return False, "no persisted ensemble detector-rank components"
    families = [column.removeprefix(ENSEMBLE_RANK_PREFIX) for column in rank_columns]
    cfg = settings()
    try:
        composition = compose_hybrid_ensemble(
            df,
            families,
            flag_quantile=cfg.benchmark_flag_quantile,
            minimum_models_agreeing=cfg.minimum_models_agreeing_for_high_confidence,
        )
    except (TypeError, ValueError, RuntimeError) as exc:
        return False, f"composition failed: {exc}"

    deltas: dict[str, float] = {}
    for column in composition.detector_rank_columns:
        if column not in df:
            return False, f"missing persisted rank column: {column}"
        observed = pd.to_numeric(df[column], errors="coerce").to_numpy(dtype=float)
        expected = composition.detector_ranks[column].to_numpy(dtype=float)
        deltas[column] = float(np.max(np.abs(observed - expected)))
    observed_ensemble = pd.to_numeric(df["ensemble_score"], errors="coerce").to_numpy(dtype=float)
    deltas["ensemble_score"] = float(
        np.max(np.abs(observed_ensemble - composition.ensemble_score.to_numpy(dtype=float)))
    )
    integer_mismatches: dict[str, int] = {}
    for column, expected in {
        "model_agreement_count": composition.model_agreement_count,
        "high_confidence": composition.high_confidence,
    }.items():
        if column not in df:
            return False, f"missing persisted ensemble field: {column}"
        observed = pd.to_numeric(df[column], errors="coerce")
        integer_mismatches[column] = int(
            (observed.to_numpy(dtype=float) != expected.to_numpy(dtype=float)).sum()
        )
    max_delta = max(deltas.values(), default=float("inf"))
    passed = max_delta <= 1e-12 and not any(integer_mismatches.values())
    return passed, {
        "families": families,
        "max_absolute_delta": max_delta,
        "column_deltas": deltas,
        "integer_mismatches": integer_mismatches,
        "baseline_score": composition.baseline_score,
    }


def _ml_features_numeric_or_null(df: pd.DataFrame) -> tuple[bool, object]:
    missing = _missing_columns(df, set(ML_FEATURES))
    if missing:
        return False, {"missing_columns": missing}
    original = df[ML_FEATURES]
    numeric = original.apply(pd.to_numeric, errors="coerce")
    invalid = original.notna() & numeric.isna()
    return bool((~invalid).all().all()), int(invalid.sum().sum())


def _ml_features_no_infinity(df: pd.DataFrame) -> tuple[bool, object]:
    missing = _missing_columns(df, set(ML_FEATURES))
    if missing:
        return False, {"missing_columns": missing}
    numeric = df[ML_FEATURES].apply(pd.to_numeric, errors="coerce")
    infinity_count = int(np.isinf(numeric.to_numpy(dtype=float)).sum())
    return infinity_count == 0, infinity_count


def _rule_indicators_binary(df: pd.DataFrame) -> tuple[bool, object]:
    columns = [rule.code for rule in RULES]
    missing = _missing_columns(df, set(columns))
    if missing:
        return False, {"missing_columns": missing}
    invalid = df[columns].isna() | ~df[columns].isin([False, True, 0, 1])
    return bool((~invalid).all().all()), int(invalid.sum().sum())


def _valid_business_id_mask(df: pd.DataFrame) -> pd.Series:
    return df["supplier_business_id"].map(normalise_supplier_business_id).notna()


def _buyer_name_id_collisions(df: pd.DataFrame) -> tuple[bool, object]:
    names = df["procuring_entity_name"].map(normalise_identity_name)
    buyer_ids = df["procuring_entity_id"].fillna("").astype(str).str.strip()
    pairs = pd.DataFrame({"name": names, "buyer_id": buyer_ids})
    pairs = pairs[pairs["name"].ne("") & pairs["buyer_id"].ne("")].drop_duplicates()
    counts = pairs.groupby("name")["buyer_id"].nunique()
    collisions = counts[counts > 1]
    return len(collisions) == 0, {
        "normalized_names_with_multiple_ids": int(len(collisions)),
        "affected_source_ids": int(
            pairs[pairs["name"].isin(collisions.index)]["buyer_id"].nunique()
        ),
    }


def _bidder_observation_consistent(df: pd.DataFrame) -> tuple[bool, object]:
    observed = df["bidder_data_observed"].fillna(False).astype(bool)
    count_present = df["num_bidders"].notna()
    invalid = observed.ne(count_present)
    return not bool(invalid.any()), int(invalid.sum())


# =====================================================================
#  silver.tenders
# =====================================================================

silver_tenders_suite = ExpectationSuite(
    name="silver_tenders",
    table="silver.tenders",
    expectations=[
        Expectation(
            "row_count_positive",
            "table has at least one row",
            lambda df: (len(df) > 0, len(df)),
            Severity.ERROR,
        ),
        Expectation(
            "ocid_unique",
            "every ocid appears exactly once",
            lambda df: (df["ocid"].is_unique, int(df["ocid"].duplicated().sum())),
            Severity.ERROR,
        ),
        Expectation(
            "ocid_non_null",
            "no null ocid",
            lambda df: (df["ocid"].notna().all(), int(df["ocid"].isna().sum())),
            Severity.ERROR,
        ),
        Expectation(
            "tender_id_unique",
            "tender_id is unique where present",
            lambda df: (
                df["tender_id"].dropna().is_unique,
                int(df["tender_id"].dropna().duplicated().sum()),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "category_in_set",
            "category ∈ {goods, services, works} or null",
            lambda df: (
                df["category"].dropna().isin(["goods", "services", "works"]).all(),
                df["category"].dropna().value_counts().to_dict(),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "estimated_value_non_negative",
            "estimated_value_eur >= 0",
            lambda df: (
                (df["estimated_value_eur"].dropna() >= 0).all(),
                int((df["estimated_value_eur"].dropna() < 0).sum()),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "currency_eur_only",
            "all currencies are EUR (sanity)",
            lambda df: (
                set(df["currency"].dropna().unique()) <= {"EUR"},
                df["currency"].value_counts().to_dict(),
            ),
            Severity.WARNING,
        ),
        Expectation(
            "release_date_non_null",
            "release_date is populated",
            lambda df: (
                df["release_date"].notna().all(),
                int(df["release_date"].isna().sum()),
            ),
            Severity.WARNING,
        ),
        Expectation(
            "release_date_in_window",
            "populated release_date values are between 2010-01-01 and now+1y",
            lambda df: (
                (
                    df["release_date"].isna()
                    | (
                        (df["release_date"] >= pd.Timestamp("2010-01-01", tz="UTC"))
                        & (
                            df["release_date"]
                            <= pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=365)
                        )
                    )
                ).all(),
                f"min={df['release_date'].min()} max={df['release_date'].max()}",
            ),
            Severity.WARNING,
        ),
        Expectation(
            "method_known_or_null",
            "method is one of the known OCDS values",
            lambda df: (
                df["method"]
                .dropna()
                .isin(["open", "minimum", "limited", "selective", "direct"])
                .all(),
                df["method"].value_counts().to_dict(),
            ),
            Severity.WARNING,
        ),
        Expectation(
            "num_bidders_non_negative",
            "observed num_bidders >= 0; unobserved bidder data remains null",
            lambda df: (
                (df["num_bidders"].dropna() >= 0).all(),
                int((df["num_bidders"].dropna() < 0).sum()),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "bidder_observation_matches_nullable_count",
            "bidder_data_observed is true exactly when num_bidders is populated",
            _bidder_observation_consistent,
            Severity.ERROR,
        ),
        Expectation(
            "bidder_data_coverage",
            "at least 90% of tenders publish bidder data",
            lambda df: (
                df["bidder_data_observed"].fillna(False).mean() >= 0.90,
                round(float(df["bidder_data_observed"].fillna(False).mean()), 4),
            ),
            Severity.WARNING,
        ),
        Expectation(
            "price_quotation_value_band_conflicts",
            "code-6 price quotations should be reviewed when estimate is >= EUR 10,000",
            lambda df: (
                not bool(
                    (df["procedure_code"].eq("6") & df["estimated_value_eur"].ge(10_000)).any()
                ),
                int((df["procedure_code"].eq("6") & df["estimated_value_eur"].ge(10_000)).sum()),
            ),
            Severity.WARNING,
        ),
        Expectation(
            "buyer_name_id_collisions",
            "normalized buyer names should map to one source ID (diagnostic; no auto-merge)",
            _buyer_name_id_collisions,
            Severity.WARNING,
        ),
        Expectation(
            "no_future_release",
            "no release_date is more than 30 days into the future",
            lambda df: (
                df["release_date"]
                .dropna()
                .le(pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=30))
                .all(),
                int(
                    df["release_date"]
                    .dropna()
                    .gt(pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=30))
                    .sum()
                ),
            ),
            Severity.WARNING,
        ),
    ],
)


# =====================================================================
#  silver.awards
# =====================================================================

silver_awards_suite = ExpectationSuite(
    name="silver_awards",
    table="silver.awards",
    expectations=[
        Expectation(
            "row_count_positive",
            "table has at least one row",
            lambda df: (len(df) > 0, len(df)),
            Severity.ERROR,
        ),
        Expectation(
            "ocid_non_null",
            "no null ocid",
            lambda df: (df["ocid"].notna().all(), int(df["ocid"].isna().sum())),
            Severity.ERROR,
        ),
        Expectation(
            "awarded_value_non_negative",
            "awarded_value_eur >= 0",
            lambda df: (
                (df["awarded_value_eur"].dropna() >= 0).all(),
                int((df["awarded_value_eur"].dropna() < 0).sum()),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "bidder_observation_matches_nullable_count",
            "enriched bidder observation matches nullable bidder count",
            _bidder_observation_consistent,
            Severity.ERROR,
        ),
        Expectation(
            "supplier_business_id_coverage",
            "≥70 % of awards have a usable non-sentinel business id",
            lambda df: (
                _valid_business_id_mask(df).mean() >= 0.70,
                round(float(_valid_business_id_mask(df).mean()), 4),
            ),
            Severity.WARNING,
        ),
        Expectation(
            "supplier_business_id_value_coverage",
            "nonblank business ids cover ≥45 % of awarded value",
            lambda df: (
                float(
                    df.loc[
                        _valid_business_id_mask(df),
                        "awarded_value_eur",
                    ].sum()
                    / max(float(df["awarded_value_eur"].sum()), 1.0)
                )
                >= 0.45,
                round(
                    float(
                        df.loc[
                            _valid_business_id_mask(df),
                            "awarded_value_eur",
                        ].sum()
                        / max(float(df["awarded_value_eur"].sum()), 1.0)
                    ),
                    4,
                ),
            ),
            Severity.WARNING,
        ),
        Expectation(
            "supplier_robust_identity_coverage",
            "≥90 % of awards have a valid business id, supplier name or source party id",
            lambda df: (
                (
                    _valid_business_id_mask(df)
                    | df["supplier_name"].fillna("").astype(str).str.strip().ne("")
                    | df["supplier_party_id"].fillna("").astype(str).str.strip().ne("")
                ).mean()
                >= 0.90,
                round(
                    (
                        _valid_business_id_mask(df)
                        | df["supplier_name"].fillna("").astype(str).str.strip().ne("")
                        | df["supplier_party_id"].fillna("").astype(str).str.strip().ne("")
                    ).mean(),
                    4,
                ),
            ),
            Severity.WARNING,
        ),
        Expectation(
            "supplier_robust_identity_value_coverage",
            "business-id/name/source-party identities cover ≥90 % of awarded value",
            lambda df: (
                float(
                    df.loc[
                        (
                            _valid_business_id_mask(df)
                            | df["supplier_name"].fillna("").astype(str).str.strip().ne("")
                            | df["supplier_party_id"].fillna("").astype(str).str.strip().ne("")
                        ),
                        "awarded_value_eur",
                    ].sum()
                    / max(float(df["awarded_value_eur"].sum()), 1.0)
                )
                >= 0.90,
                round(
                    float(
                        df.loc[
                            (
                                _valid_business_id_mask(df)
                                | df["supplier_name"].fillna("").astype(str).str.strip().ne("")
                                | df["supplier_party_id"].fillna("").astype(str).str.strip().ne("")
                            ),
                            "awarded_value_eur",
                        ].sum()
                        / max(float(df["awarded_value_eur"].sum()), 1.0)
                    ),
                    4,
                ),
            ),
            Severity.WARNING,
        ),
        Expectation(
            "supplier_business_id_sentinels_normalized",
            "known business-ID sentinel strings are retained only in the raw field",
            lambda df: (
                _valid_business_id_mask(df).eq(df["supplier_business_id"].notna()).all(),
                int((df["supplier_business_id"].notna() & ~_valid_business_id_mask(df)).sum()),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "source_party_id_coverage",
            "published source party ID coverage is reported, not treated as legal-ID validation",
            lambda df: (
                df["supplier_party_id"].fillna("").astype(str).str.strip().ne("").mean() >= 0.90,
                round(
                    float(df["supplier_party_id"].fillna("").astype(str).str.strip().ne("").mean()),
                    4,
                ),
            ),
            Severity.WARNING,
        ),
        Expectation(
            "award_lot_title_linkage",
            "award lot titles should link uniquely to one published tender lot",
            lambda df: (
                df["award_lot_match_status"].eq("exact_unique").all(),
                df["award_lot_match_status"].value_counts(dropna=False).to_dict(),
            ),
            Severity.WARNING,
        ),
    ],
)


def silver_awards_suite_for(
    tender_ocids: pd.Series,
) -> ExpectationSuite:
    """Add exact award→tender OCID referential integrity to the base suite.

    Awards are a strict subset of tenders, so this is intentionally not a
    row-parity check. The expected population fingerprint makes the cross-table
    input visible in both ordinary and release-bound DQ evidence even though
    the suite result itself is bound to the awards artifact.
    """
    expected = pd.Index(tender_ocids.dropna().astype(str).unique())
    digest = hashlib.sha256()
    for ocid in sorted(expected.tolist()):
        encoded = ocid.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, byteorder="big"))
        digest.update(encoded)
    expected_fingerprint = digest.hexdigest()

    def _award_ocids_reference_tenders(df: pd.DataFrame) -> tuple[bool, object]:
        if "ocid" not in df:
            return False, {
                "missing_column": "ocid",
                "expected_tender_ocids": len(expected),
                "tender_ocid_population_sha256": expected_fingerprint,
            }
        award_ocids = df["ocid"].astype("string")
        null_mask = award_ocids.isna()
        orphan_mask = null_mask | ~award_ocids.isin(expected)
        orphan_values = award_ocids[orphan_mask & ~null_mask]
        orphan_unique = sorted(orphan_values.unique().tolist())
        return not bool(orphan_mask.any()), {
            "expected_tender_ocids": len(expected),
            "tender_ocid_population_sha256": expected_fingerprint,
            "award_rows": len(df),
            "orphan_rows": int(orphan_mask.sum()),
            "orphan_ocids": len(orphan_unique),
            "null_award_ocids": int(null_mask.sum()),
            "orphan_ocid_sample": orphan_unique[:10],
        }

    return ExpectationSuite(
        name=silver_awards_suite.name,
        table=silver_awards_suite.table,
        expectations=[
            *silver_awards_suite.expectations,
            Expectation(
                "award_ocids_reference_tenders",
                "every award OCID exists in the exact Silver tender OCID population",
                _award_ocids_reference_tenders,
                Severity.ERROR,
            ),
        ],
    )


# =====================================================================
#  gold.tender_features (unscored benchmark input)
# =====================================================================

gold_tender_features_suite = ExpectationSuite(
    name="gold_tender_features",
    table="gold.tender_features",
    expectations=[
        Expectation(
            "row_count_positive",
            "table has at least one row",
            lambda df: (len(df) > 0, len(df)),
            Severity.ERROR,
        ),
        Expectation(
            "ocid_unique",
            "ocid unique in base gold layer",
            lambda df: (df["ocid"].is_unique, int(df["ocid"].duplicated().sum())),
            Severity.ERROR,
        ),
        Expectation(
            "ocid_non_null",
            "no null ocid in base gold layer",
            lambda df: (df["ocid"].notna().all(), int(df["ocid"].isna().sum())),
            Severity.ERROR,
        ),
        Expectation(
            "expected_ml_feature_columns",
            "all declared ML feature columns are present",
            lambda df: (
                not _missing_columns(df, set(ML_FEATURES)),
                _missing_columns(df, set(ML_FEATURES)),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "procurement_semantic_columns",
            "bidder observation, supplier identity and buyer-collision facts are present",
            lambda df: (
                not _missing_columns(
                    df,
                    {
                        "bidder_data_observed",
                        "bidder_data_missing",
                        "n_supplier_identities",
                        "buyer_name_id_collision",
                        "procedure_subtype",
                    },
                ),
                _missing_columns(
                    df,
                    {
                        "bidder_data_observed",
                        "bidder_data_missing",
                        "n_supplier_identities",
                        "buyer_name_id_collision",
                        "procedure_subtype",
                    },
                ),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "expected_rule_columns",
            "all declared indicator columns and rule_score are present",
            lambda df: (
                not _missing_columns(df, {r.code for r in RULES} | {"rule_score"}),
                _missing_columns(df, {r.code for r in RULES} | {"rule_score"}),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "ml_features_numeric_or_null",
            "declared ML features contain only numeric values or nulls",
            _ml_features_numeric_or_null,
            Severity.ERROR,
        ),
        Expectation(
            "ml_features_no_infinity",
            "declared ML features contain no positive/negative infinity",
            _ml_features_no_infinity,
            Severity.ERROR,
        ),
        Expectation(
            "rule_indicators_binary_non_null",
            "every declared indicator is non-null and boolean",
            _rule_indicators_binary,
            Severity.ERROR,
        ),
        Expectation(
            "rule_score_finite_in_unit_interval",
            "rule_score is non-null, finite and in [0, 1]",
            lambda df: (
                bool(
                    pd.to_numeric(df["rule_score"], errors="coerce").notna().all()
                    and np.isfinite(
                        pd.to_numeric(df["rule_score"], errors="coerce").to_numpy(dtype=float)
                    ).all()
                    and pd.to_numeric(df["rule_score"], errors="coerce").between(0.0, 1.0).all()
                ),
                {
                    "null_or_non_numeric": int(
                        pd.to_numeric(df["rule_score"], errors="coerce").isna().sum()
                    ),
                    "outside_unit_interval": int(
                        (~pd.to_numeric(df["rule_score"], errors="coerce").between(0.0, 1.0)).sum()
                    ),
                },
            ),
            Severity.ERROR,
        ),
        Expectation(
            "procedure_subtype_nonblank",
            "every row has a source-aware procedure subtype",
            lambda df: (
                df["procedure_subtype"].fillna("").astype(str).str.strip().ne("").all(),
                int(df["procedure_subtype"].fillna("").astype(str).str.strip().eq("").sum()),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "bidder_observation_matches_nullable_count",
            "gold preserves missing bidder counts rather than converting them to zero",
            _bidder_observation_consistent,
            Severity.ERROR,
        ),
    ],
)


def gold_tender_features_suite_for(
    expected_ocids: pd.Series,
) -> ExpectationSuite:
    """Add exact silver→gold OCID parity to the reusable base suite."""
    expected = pd.Index(expected_ocids.dropna().astype(str).unique())

    def _source_ocid_parity(df: pd.DataFrame) -> tuple[bool, object]:
        if "ocid" not in df:
            return False, {"missing_column": "ocid"}
        actual = pd.Index(df["ocid"].dropna().astype(str).unique())
        missing = expected.difference(actual)
        unexpected = actual.difference(expected)
        return (
            len(df) == len(expected) and not len(missing) and not len(unexpected),
            {
                "expected_rows": len(expected),
                "actual_rows": len(df),
                "missing_ocids": len(missing),
                "unexpected_ocids": len(unexpected),
            },
        )

    return ExpectationSuite(
        name=gold_tender_features_suite.name,
        table=gold_tender_features_suite.table,
        expectations=[
            *gold_tender_features_suite.expectations,
            Expectation(
                "silver_to_gold_ocid_parity",
                "base gold has exactly the silver tender OCID population",
                _source_ocid_parity,
                Severity.ERROR,
            ),
        ],
    )


# =====================================================================
#  gold descriptive summaries
# =====================================================================


def _numeric_columns_non_negative(
    df: pd.DataFrame,
    columns: list[str],
) -> tuple[bool, object]:
    missing = _missing_columns(df, set(columns))
    if missing:
        return False, {"missing_columns": missing}
    values = df[columns].apply(pd.to_numeric, errors="coerce")
    invalid = (df[columns].notna() & values.isna()) | (
        values.notna() & (~np.isfinite(values) | values.lt(0))
    )
    return bool((~invalid).all().all()), int(invalid.sum().sum())


def _numeric_columns_in_range(
    df: pd.DataFrame,
    columns: list[str],
    lower: float,
    upper: float,
) -> tuple[bool, object]:
    missing = _missing_columns(df, set(columns))
    if missing:
        return False, {"missing_columns": missing}
    values = df[columns].apply(pd.to_numeric, errors="coerce")
    invalid = (df[columns].notna() & values.isna()) | (
        values.notna() & (~np.isfinite(values) | values.lt(lower) | values.gt(upper))
    )
    return bool((~invalid).all().all()), int(invalid.sum().sum())


gold_supplier_summary_suite = ExpectationSuite(
    name="gold_supplier_summary",
    table="gold.supplier_summary",
    expectations=[
        Expectation(
            "row_count_positive",
            "supplier summary has at least one identified supplier group",
            lambda df: (len(df) > 0, len(df)),
            Severity.ERROR,
        ),
        Expectation(
            "supplier_key_unique_non_null",
            "supplier fallback keys are unique and non-null",
            lambda df: (
                bool(df["supplier_key"].notna().all() and df["supplier_key"].is_unique),
                {
                    "null": int(df["supplier_key"].isna().sum()),
                    "duplicates": int(df["supplier_key"].duplicated().sum()),
                },
            ),
            Severity.ERROR,
        ),
        Expectation(
            "counts_and_values_non_negative",
            "supplier counts and monetary summaries are finite and non-negative",
            lambda df: _numeric_columns_non_negative(
                df,
                [
                    "tenders_won",
                    "award_rows",
                    "total_awarded_eur",
                    "median_awarded_eur",
                    "max_awarded_eur",
                    "distinct_procuring_entities",
                    "distinct_categories",
                    "distinct_methods",
                    "distinct_names",
                    "distinct_source_identity_keys",
                ],
            ),
            Severity.ERROR,
        ),
        Expectation(
            "percentage_columns_in_range",
            "supplier shares, coverage and observed single-bidder rates are in [0, 100]",
            lambda df: _numeric_columns_in_range(
                df,
                [
                    "share_of_total_awarded_pct",
                    "share_of_identified_value_pct",
                    "identity_value_coverage_pct",
                    "single_bidder_win_pct",
                ],
                0.0,
                100.0,
            ),
            Severity.ERROR,
        ),
        Expectation(
            "identity_source_declared",
            "every supplier group discloses the identity fallback used",
            lambda df: (
                df["identity_source"]
                .isin(
                    {
                        "business_id",
                        "name_fallback",
                        "source_party_id_fallback",
                        "unidentified",
                    }
                )
                .all(),
                df["identity_source"].value_counts(dropna=False).to_dict(),
            ),
            Severity.ERROR,
        ),
    ],
)


def gold_supplier_summary_suite_for(
    awards: pd.DataFrame,
) -> ExpectationSuite:
    """Bind the supplier summary to the identified source-award population.

    Rows without a robust supplier key remain in the recorded-value denominator
    and coverage calculation, but are not turned into a fictitious supplier.
    """
    source_columns = [
        "supplier_business_id",
        "supplier_name",
        "supplier_party_id",
        "supplier_uid",
        "awarded_value_eur",
    ]
    source_missing = _missing_columns(awards, {"awarded_value_eur"})
    source_fingerprint = _projection_fingerprint(awards, source_columns)
    if source_missing:
        expected_by_key = pd.DataFrame(columns=["award_rows", "total_awarded_eur"])
        source_rows = identified_rows = unidentified_rows = 0
        total_value = identified_value = unidentified_value = 0.0
        expected_coverage = 0.0
    else:
        keys = supplier_key(awards)
        values = pd.to_numeric(awards["awarded_value_eur"], errors="coerce").fillna(0.0)
        identified = keys.notna()
        source_rows = len(awards)
        identified_rows = int(identified.sum())
        unidentified_rows = int((~identified).sum())
        total_value = float(values.sum())
        identified_value = float(values[identified].sum())
        unidentified_value = float(values[~identified].sum())
        expected_coverage = round(100 * identified_value / max(total_value, 1.0), 2)
        expected_source = pd.DataFrame(
            {
                "_key": keys[identified].astype(str),
                "_value": values[identified],
            }
        )
        expected_by_key = expected_source.groupby("_key").agg(
            award_rows=("_key", "size"),
            total_awarded_eur=("_value", "sum"),
        )

    def _source_award_reconciliation(df: pd.DataFrame) -> tuple[bool, object]:
        required = {
            "supplier_key",
            "award_rows",
            "total_awarded_eur",
            "identity_value_coverage_pct",
        }
        summary_missing = _missing_columns(df, required)
        base_observed = {
            "source_projection_fingerprint": source_fingerprint,
            "source_missing_columns": source_missing,
            "summary_missing_columns": summary_missing,
            "source_award_rows": source_rows,
            "identified_award_rows": identified_rows,
            "unidentified_award_rows": unidentified_rows,
            "total_recorded_awarded_eur": total_value,
            "identified_awarded_eur": identified_value,
            "unidentified_awarded_eur": unidentified_value,
            "expected_identity_value_coverage_pct": expected_coverage,
        }
        if source_missing or summary_missing:
            return False, base_observed

        actual_keys = df["supplier_key"].astype("string")
        actual_rows = pd.to_numeric(df["award_rows"], errors="coerce")
        actual_values = pd.to_numeric(df["total_awarded_eur"], errors="coerce")
        actual_coverage = pd.to_numeric(df["identity_value_coverage_pct"], errors="coerce")
        invalid_numeric = int(
            actual_rows.isna().sum() + actual_values.isna().sum() + actual_coverage.isna().sum()
        )
        actual_source = pd.DataFrame(
            {
                "_key": actual_keys,
                "award_rows": actual_rows,
                "total_awarded_eur": actual_values,
            }
        ).dropna(subset=["_key"])
        actual_by_key = actual_source.groupby("_key").agg(
            award_rows=("award_rows", "sum"),
            total_awarded_eur=("total_awarded_eur", "sum"),
        )
        expected_keys = set(expected_by_key.index.astype(str))
        actual_keys_set = set(actual_by_key.index.astype(str))
        missing_keys = sorted(expected_keys - actual_keys_set)
        unexpected_keys = sorted(actual_keys_set - expected_keys)
        common_keys = sorted(expected_keys & actual_keys_set)
        row_mismatches = sum(
            not np.isclose(
                float(actual_by_key.loc[key, "award_rows"]),
                float(expected_by_key.loc[key, "award_rows"]),
            )
            for key in common_keys
        )
        value_mismatches = sum(
            not np.isclose(
                float(actual_by_key.loc[key, "total_awarded_eur"]),
                float(expected_by_key.loc[key, "total_awarded_eur"]),
                rtol=1e-9,
                atol=1e-6,
            )
            for key in common_keys
        )
        coverage_mismatches = int(
            (~np.isclose(actual_coverage, expected_coverage, rtol=0.0, atol=1e-9)).sum()
        )
        duplicate_keys = int(actual_keys.dropna().duplicated().sum())
        null_keys = int(actual_keys.isna().sum())
        actual_identified_rows = float(actual_rows.sum()) if not actual_rows.isna().any() else None
        actual_identified_value = (
            float(actual_values.sum()) if not actual_values.isna().any() else None
        )
        passed = bool(
            invalid_numeric == 0
            and duplicate_keys == 0
            and null_keys == 0
            and not missing_keys
            and not unexpected_keys
            and row_mismatches == 0
            and value_mismatches == 0
            and coverage_mismatches == 0
            and actual_identified_rows == identified_rows
            and actual_identified_value is not None
            and np.isclose(
                actual_identified_value,
                identified_value,
                rtol=1e-9,
                atol=1e-6,
            )
        )
        return passed, {
            **base_observed,
            "expected_supplier_keys": len(expected_keys),
            "actual_summary_rows": len(df),
            "missing_supplier_keys": len(missing_keys),
            "unexpected_supplier_keys": len(unexpected_keys),
            "missing_supplier_key_sample": missing_keys[:10],
            "unexpected_supplier_key_sample": unexpected_keys[:10],
            "duplicate_supplier_keys": duplicate_keys,
            "null_supplier_keys": null_keys,
            "per_key_award_row_mismatches": row_mismatches,
            "per_key_awarded_value_mismatches": value_mismatches,
            "coverage_mismatch_rows": coverage_mismatches,
            "invalid_numeric_values": invalid_numeric,
            "actual_identified_award_rows": actual_identified_rows,
            "actual_identified_awarded_eur": actual_identified_value,
        }

    return ExpectationSuite(
        name=gold_supplier_summary_suite.name,
        table=gold_supplier_summary_suite.table,
        expectations=[
            *gold_supplier_summary_suite.expectations,
            Expectation(
                "source_award_reconciliation",
                "supplier keys, rows, value and recorded identity coverage reconcile to awards",
                _source_award_reconciliation,
                Severity.ERROR,
            ),
        ],
    )


gold_entity_summary_suite = ExpectationSuite(
    name="gold_entity_summary",
    table="gold.procuring_entity_summary",
    expectations=[
        Expectation(
            "row_count_positive",
            "procuring-entity summary has at least one row",
            lambda df: (len(df) > 0, len(df)),
            Severity.ERROR,
        ),
        Expectation(
            "entity_key_unique",
            "published procuring-entity identifiers form unique summary groups",
            lambda df: (
                df["procuring_entity_id"].is_unique,
                int(df["procuring_entity_id"].duplicated().sum()),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "counts_and_values_non_negative",
            "entity counts and monetary summaries are finite and non-negative",
            lambda df: _numeric_columns_non_negative(
                df,
                [
                    "tenders",
                    "awarded_tenders",
                    "total_estimated_eur",
                    "total_awarded_eur",
                    "median_estimated_eur",
                ],
            ),
            Severity.ERROR,
        ),
        Expectation(
            "awarded_tenders_not_above_total",
            "awarded tender counts do not exceed all tenders",
            lambda df: (
                df["awarded_tenders"].le(df["tenders"]).all(),
                int(df["awarded_tenders"].gt(df["tenders"]).sum()),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "percentage_columns_in_range",
            "coverage and descriptive rates are in [0, 100] when observed",
            lambda df: _numeric_columns_in_range(
                df,
                [
                    "bidder_data_coverage_pct",
                    "single_bidder_pct",
                    "zero_bidder_pct",
                    "end_before_start_pct",
                    "supplier_identity_value_coverage_pct",
                    "supplier_source_party_identity_value_coverage_pct",
                    "supplier_business_id_value_coverage_pct",
                ],
                0.0,
                100.0,
            ),
            Severity.ERROR,
        ),
        Expectation(
            "hhi_sensitivities_in_range",
            "all disclosed supplier-identity HHI sensitivities are in [0, 10,000]",
            lambda df: _numeric_columns_in_range(
                df,
                [
                    "supplier_hhi",
                    "supplier_hhi_name_fallback",
                    "supplier_hhi_source_party_fallback",
                    "supplier_hhi_id_only",
                    "supplier_hhi_unknown_one_group_scenario",
                    "supplier_hhi_unknown_distinct_rows_scenario",
                ],
                0.0,
                10_000.000001,
            ),
            Severity.ERROR,
        ),
    ],
)


def gold_entity_summary_suite_for(
    features: pd.DataFrame,
) -> ExpectationSuite:
    """Bind entity tender/value rollups to the exact Gold feature population."""
    source_columns = [
        "ocid",
        "procuring_entity_id",
        "estimated_value_eur",
        "total_awarded_eur",
    ]
    source_missing = _missing_columns(features, set(source_columns))
    source_fingerprint = _projection_fingerprint(features, source_columns)
    if source_missing:
        expected_by_key = pd.DataFrame(
            columns=["tenders", "total_estimated_eur", "total_awarded_eur"]
        )
        expected_tenders = 0
        expected_estimated = expected_awarded = 0.0
    else:
        estimated = pd.to_numeric(features["estimated_value_eur"], errors="coerce").fillna(0.0)
        awarded = pd.to_numeric(features["total_awarded_eur"], errors="coerce").fillna(0.0)
        source = pd.DataFrame(
            {
                "_key": features["procuring_entity_id"].map(_canonical_group_key),
                "_tender": features["ocid"].notna().astype(int),
                "_estimated": estimated,
                "_awarded": awarded,
            }
        )
        expected_by_key = source.groupby("_key").agg(
            tenders=("_tender", "sum"),
            total_estimated_eur=("_estimated", "sum"),
            total_awarded_eur=("_awarded", "sum"),
        )
        expected_tenders = int(source["_tender"].sum())
        expected_estimated = float(estimated.sum())
        expected_awarded = float(awarded.sum())

    def _source_feature_reconciliation(df: pd.DataFrame) -> tuple[bool, object]:
        required = {
            "procuring_entity_id",
            "tenders",
            "total_estimated_eur",
            "total_awarded_eur",
        }
        summary_missing = _missing_columns(df, required)
        base_observed = {
            "source_projection_fingerprint": source_fingerprint,
            "source_missing_columns": source_missing,
            "summary_missing_columns": summary_missing,
            "expected_tenders": expected_tenders,
            "expected_total_estimated_eur": expected_estimated,
            "expected_total_awarded_eur": expected_awarded,
        }
        if source_missing or summary_missing:
            return False, base_observed

        actual_keys = df["procuring_entity_id"].map(_canonical_group_key)
        actual_tenders = pd.to_numeric(df["tenders"], errors="coerce")
        actual_estimated = pd.to_numeric(df["total_estimated_eur"], errors="coerce")
        actual_awarded = pd.to_numeric(df["total_awarded_eur"], errors="coerce")
        invalid_numeric = int(
            actual_tenders.isna().sum()
            + actual_estimated.isna().sum()
            + actual_awarded.isna().sum()
        )
        actual = pd.DataFrame(
            {
                "_key": actual_keys,
                "tenders": actual_tenders,
                "total_estimated_eur": actual_estimated,
                "total_awarded_eur": actual_awarded,
            }
        )
        actual_by_key = actual.groupby("_key").agg(
            tenders=("tenders", "sum"),
            total_estimated_eur=("total_estimated_eur", "sum"),
            total_awarded_eur=("total_awarded_eur", "sum"),
        )
        expected_keys = set(expected_by_key.index.astype(str))
        actual_keys_set = set(actual_by_key.index.astype(str))
        missing_keys = sorted(expected_keys - actual_keys_set)
        unexpected_keys = sorted(actual_keys_set - expected_keys)
        common_keys = sorted(expected_keys & actual_keys_set)
        tender_mismatches = sum(
            not np.isclose(
                float(actual_by_key.loc[key, "tenders"]),
                float(expected_by_key.loc[key, "tenders"]),
            )
            for key in common_keys
        )
        estimated_mismatches = sum(
            not np.isclose(
                float(actual_by_key.loc[key, "total_estimated_eur"]),
                float(expected_by_key.loc[key, "total_estimated_eur"]),
                rtol=1e-9,
                atol=1e-6,
            )
            for key in common_keys
        )
        awarded_mismatches = sum(
            not np.isclose(
                float(actual_by_key.loc[key, "total_awarded_eur"]),
                float(expected_by_key.loc[key, "total_awarded_eur"]),
                rtol=1e-9,
                atol=1e-6,
            )
            for key in common_keys
        )
        duplicate_keys = int(actual_keys.duplicated().sum())
        actual_tender_total = (
            float(actual_tenders.sum()) if not actual_tenders.isna().any() else None
        )
        actual_estimated_total = (
            float(actual_estimated.sum()) if not actual_estimated.isna().any() else None
        )
        actual_awarded_total = (
            float(actual_awarded.sum()) if not actual_awarded.isna().any() else None
        )
        passed = bool(
            invalid_numeric == 0
            and duplicate_keys == 0
            and not missing_keys
            and not unexpected_keys
            and tender_mismatches == 0
            and estimated_mismatches == 0
            and awarded_mismatches == 0
            and actual_tender_total == expected_tenders
            and actual_estimated_total is not None
            and np.isclose(
                actual_estimated_total,
                expected_estimated,
                rtol=1e-9,
                atol=1e-6,
            )
            and actual_awarded_total is not None
            and np.isclose(
                actual_awarded_total,
                expected_awarded,
                rtol=1e-9,
                atol=1e-6,
            )
        )
        return passed, {
            **base_observed,
            "expected_entity_rows": len(expected_keys),
            "actual_entity_rows": len(df),
            "missing_entity_keys": len(missing_keys),
            "unexpected_entity_keys": len(unexpected_keys),
            "missing_entity_key_sample": missing_keys[:10],
            "unexpected_entity_key_sample": unexpected_keys[:10],
            "duplicate_entity_keys": duplicate_keys,
            "per_entity_tender_mismatches": tender_mismatches,
            "per_entity_estimated_value_mismatches": estimated_mismatches,
            "per_entity_awarded_value_mismatches": awarded_mismatches,
            "invalid_numeric_values": invalid_numeric,
            "actual_tenders": actual_tender_total,
            "actual_total_estimated_eur": actual_estimated_total,
            "actual_total_awarded_eur": actual_awarded_total,
        }

    return ExpectationSuite(
        name=gold_entity_summary_suite.name,
        table=gold_entity_summary_suite.table,
        expectations=[
            *gold_entity_summary_suite.expectations,
            Expectation(
                "source_feature_reconciliation",
                "entity tender, estimated-value and awarded-value totals reconcile to Gold",
                _source_feature_reconciliation,
                Severity.ERROR,
            ),
        ],
    )


gold_monthly_metrics_suite = ExpectationSuite(
    name="gold_monthly_metrics",
    table="gold.monthly_metrics",
    expectations=[
        Expectation(
            "row_count_positive",
            "monthly summary has at least one period",
            lambda df: (len(df) > 0, len(df)),
            Severity.ERROR,
        ),
        Expectation(
            "period_label_unique_nonblank",
            "every calendar or unknown-date bucket has one nonblank label",
            lambda df: (
                bool(
                    df["period_label"].fillna("").astype(str).str.strip().ne("").all()
                    and df["period_label"].is_unique
                ),
                {
                    "blank": int(
                        df["period_label"].fillna("").astype(str).str.strip().eq("").sum()
                    ),
                    "duplicates": int(df["period_label"].duplicated().sum()),
                },
            ),
            Severity.ERROR,
        ),
        Expectation(
            "counts_and_values_non_negative",
            "monthly counts and monetary aggregates are finite and non-negative",
            lambda df: _numeric_columns_non_negative(
                df,
                [
                    "tenders",
                    "flagged_count",
                    "estimated_value_eur",
                    "total_awarded_eur",
                    "value_mn",
                    "awarded_value_mn",
                ],
            ),
            Severity.ERROR,
        ),
        Expectation(
            "flagged_not_above_tenders",
            "monthly rule-review counts do not exceed all tenders",
            lambda df: (
                df["flagged_count"].le(df["tenders"]).all(),
                int(df["flagged_count"].gt(df["tenders"]).sum()),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "percentage_columns_in_range",
            "monthly bidder coverage and observed rates are in [0, 100]",
            lambda df: _numeric_columns_in_range(
                df,
                ["bidder_data_coverage_pct", "single_bidder_pct", "zero_bidder_pct"],
                0.0,
                100.0,
            ),
            Severity.ERROR,
        ),
        Expectation(
            "date_known_boolean",
            "date_known is a non-null boolean indicator",
            lambda df: (
                bool(df["date_known"].notna().all() and df["date_known"].isin([True, False]).all()),
                {
                    "true": int(df["date_known"].astype("boolean").fillna(False).sum()),
                    "false": int(df["date_known"].astype("boolean").fillna(True).eq(False).sum()),
                    "null": int(df["date_known"].isna().sum()),
                },
            ),
            Severity.ERROR,
        ),
    ],
)


def gold_monthly_metrics_suite_for(
    features: pd.DataFrame,
) -> ExpectationSuite:
    """Bind monthly totals, including the unknown-date bucket, to Gold."""
    source_columns = ["ocid", "release_date", "estimated_value_eur", "total_awarded_eur"]
    source_missing = _missing_columns(features, set(source_columns))
    source_fingerprint = _projection_fingerprint(features, source_columns)
    if source_missing:
        expected_tenders = expected_unknown_tenders = 0
        expected_estimated = expected_awarded = 0.0
        expected_unknown_estimated = expected_unknown_awarded = 0.0
    else:
        dates = pd.to_datetime(features["release_date"], errors="coerce", utc=True)
        unknown = dates.isna()
        estimated = pd.to_numeric(features["estimated_value_eur"], errors="coerce").fillna(0.0)
        awarded = pd.to_numeric(features["total_awarded_eur"], errors="coerce").fillna(0.0)
        expected_tenders = len(features)
        expected_estimated = float(estimated.sum())
        expected_awarded = float(awarded.sum())
        expected_unknown_tenders = int(unknown.sum())
        expected_unknown_estimated = float(estimated[unknown].sum())
        expected_unknown_awarded = float(awarded[unknown].sum())

    def _source_feature_reconciliation(df: pd.DataFrame) -> tuple[bool, object]:
        required = {
            "period_label",
            "date_known",
            "tenders",
            "estimated_value_eur",
            "total_awarded_eur",
        }
        summary_missing = _missing_columns(df, required)
        base_observed = {
            "source_projection_fingerprint": source_fingerprint,
            "source_missing_columns": source_missing,
            "summary_missing_columns": summary_missing,
            "expected_tenders": expected_tenders,
            "expected_total_estimated_eur": expected_estimated,
            "expected_total_awarded_eur": expected_awarded,
            "expected_unknown_date_tenders": expected_unknown_tenders,
            "expected_unknown_date_estimated_eur": expected_unknown_estimated,
            "expected_unknown_date_awarded_eur": expected_unknown_awarded,
        }
        if source_missing or summary_missing:
            return False, base_observed

        actual_tenders = pd.to_numeric(df["tenders"], errors="coerce")
        actual_estimated = pd.to_numeric(df["estimated_value_eur"], errors="coerce")
        actual_awarded = pd.to_numeric(df["total_awarded_eur"], errors="coerce")
        invalid_numeric = int(
            actual_tenders.isna().sum()
            + actual_estimated.isna().sum()
            + actual_awarded.isna().sum()
        )
        labels = df["period_label"].fillna("").astype(str)
        date_known = df["date_known"].astype("boolean")
        unknown_by_label = labels.eq("unknown_date")
        unknown_by_flag = date_known.eq(False).fillna(False)
        marker_mismatches = int(unknown_by_label.ne(unknown_by_flag).sum())
        actual_unknown_rows = int(unknown_by_label.sum())
        expected_unknown_rows = int(expected_unknown_tenders > 0)
        actual_tender_total = (
            float(actual_tenders.sum()) if not actual_tenders.isna().any() else None
        )
        actual_estimated_total = (
            float(actual_estimated.sum()) if not actual_estimated.isna().any() else None
        )
        actual_awarded_total = (
            float(actual_awarded.sum()) if not actual_awarded.isna().any() else None
        )
        actual_unknown_tenders = (
            float(actual_tenders[unknown_by_label].sum())
            if not actual_tenders[unknown_by_label].isna().any()
            else None
        )
        actual_unknown_estimated = (
            float(actual_estimated[unknown_by_label].sum())
            if not actual_estimated[unknown_by_label].isna().any()
            else None
        )
        actual_unknown_awarded = (
            float(actual_awarded[unknown_by_label].sum())
            if not actual_awarded[unknown_by_label].isna().any()
            else None
        )
        passed = bool(
            invalid_numeric == 0
            and int(date_known.isna().sum()) == 0
            and marker_mismatches == 0
            and actual_unknown_rows == expected_unknown_rows
            and actual_tender_total == expected_tenders
            and actual_unknown_tenders == expected_unknown_tenders
            and actual_estimated_total is not None
            and np.isclose(
                actual_estimated_total,
                expected_estimated,
                rtol=1e-9,
                atol=1e-6,
            )
            and actual_awarded_total is not None
            and np.isclose(
                actual_awarded_total,
                expected_awarded,
                rtol=1e-9,
                atol=1e-6,
            )
            and actual_unknown_estimated is not None
            and np.isclose(
                actual_unknown_estimated,
                expected_unknown_estimated,
                rtol=1e-9,
                atol=1e-6,
            )
            and actual_unknown_awarded is not None
            and np.isclose(
                actual_unknown_awarded,
                expected_unknown_awarded,
                rtol=1e-9,
                atol=1e-6,
            )
        )
        return passed, {
            **base_observed,
            "expected_unknown_date_rows": expected_unknown_rows,
            "actual_unknown_date_rows": actual_unknown_rows,
            "unknown_date_marker_mismatches": marker_mismatches,
            "null_date_known_values": int(date_known.isna().sum()),
            "invalid_numeric_values": invalid_numeric,
            "actual_tenders": actual_tender_total,
            "actual_total_estimated_eur": actual_estimated_total,
            "actual_total_awarded_eur": actual_awarded_total,
            "actual_unknown_date_tenders": actual_unknown_tenders,
            "actual_unknown_date_estimated_eur": actual_unknown_estimated,
            "actual_unknown_date_awarded_eur": actual_unknown_awarded,
        }

    return ExpectationSuite(
        name=gold_monthly_metrics_suite.name,
        table=gold_monthly_metrics_suite.table,
        expectations=[
            *gold_monthly_metrics_suite.expectations,
            Expectation(
                "source_feature_reconciliation",
                "monthly tender/value totals and unknown-date bucket reconcile to Gold",
                _source_feature_reconciliation,
                Severity.ERROR,
            ),
        ],
    )


# =====================================================================
#  gold.tender_summary (scored publication)
# =====================================================================

gold_tender_summary_suite = ExpectationSuite(
    name="gold_tender_summary",
    table="gold.tender_summary",
    expectations=[
        Expectation(
            "ocid_unique",
            "ocid unique in gold layer",
            lambda df: (df["ocid"].is_unique, int(df["ocid"].duplicated().sum())),
            Severity.ERROR,
        ),
        Expectation(
            "rule_score_in_unit_interval",
            "rule_score ∈ [0, 1]",
            lambda df: (
                df["rule_score"].between(0.0, 1.0).all(),
                f"min={df['rule_score'].min()} max={df['rule_score'].max()}",
            ),
            Severity.ERROR,
        ),
        Expectation(
            "expected_score_columns",
            "all score columns present",
            lambda df: (
                not _missing_columns(df, set(GOLD_SCORE_COLUMNS)),
                _missing_columns(df, set(GOLD_SCORE_COLUMNS)),
            ),
            Severity.ERROR,
        ),
        Expectation(
            "score_values_non_null",
            "every detector, proxy, context and ensemble score is non-null",
            _scores_non_null,
            Severity.ERROR,
        ),
        Expectation(
            "score_values_finite",
            "every detector, proxy, context and ensemble score is finite",
            _scores_finite,
            Severity.ERROR,
        ),
        Expectation(
            "score_values_in_unit_interval",
            "every detector, proxy, context and ensemble score is in [0, 1]",
            _scores_in_unit_interval,
            Severity.ERROR,
        ),
        Expectation(
            "ensemble_xai_exact_reconstruction",
            "persisted detector ranks, agreement fields and ensemble score exactly reconstruct",
            _ensemble_xai_reconstruction,
            Severity.ERROR,
        ),
    ],
)


ALL_SUITES = [
    silver_tenders_suite,
    silver_awards_suite,
    gold_tender_features_suite,
    gold_supplier_summary_suite,
    gold_entity_summary_suite,
    gold_monthly_metrics_suite,
    gold_tender_summary_suite,
]
