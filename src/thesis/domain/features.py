"""Feature engineering for the gold layer + ML modelling.

Design principles:

* Every feature is *deterministic* given the silver inputs.
* Numeric features are designed to be roughly comparable in scale
  (logs / ratios / ranks).
* All contextual ranks and z-scores are snapshot-relative.  Rebuilding on a
  different population can change them; this project does not expose an
  online/single-row scoring contract.
"""

from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

from .procedures import classify_procedure_series

# --------------------------------------------------------------------- helpers


def safe_log10(s: pd.Series) -> pd.Series:
    """``log10`` that returns NaN for non-positive or non-numeric inputs."""
    s = pd.to_numeric(s, errors="coerce")
    return np.log10(s.where(s > 0).astype(float))


def winsorize(s: pd.Series, lo: float = 0.005, hi: float = 0.995) -> pd.Series:
    """Symmetric two-sided winsorisation on the ``[lo, hi]`` percentile range."""
    a, b = s.quantile(lo), s.quantile(hi)
    return s.clip(lower=a, upper=b)


def zscore_within(df: pd.DataFrame, column: str, by: str) -> pd.Series:
    """``(value - group_mean) / group_std`` returning a Series aligned to df."""
    g = df.groupby(by)[column]
    mean = g.transform("mean")
    std = g.transform("std")
    return (df[column] - mean) / std.replace(0, np.nan)


# ----------------------------------------------------- per-tender derived facts

BUSINESS_ID_SENTINELS = frozenset(
    {
        "",
        "-",
        "--",
        "/",
        "//",
        ".",
        "..",
        "0",
        "00000000",
        "000000000",
        "n/a",
        "na",
        "none",
        "null",
        "unknown",
    }
)


def normalise_supplier_business_id(value: object) -> str | None:
    """Return a usable published business ID, excluding source sentinels.

    This is format hygiene, not registry verification. The raw source value is
    retained separately in Silver.
    """
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    text = str(value).strip()
    return None if text.casefold() in BUSINESS_ID_SENTINELS else text


def normalise_identity_name(value: object) -> str:
    """Conservatively normalise an organisation name for collision diagnostics."""
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(char for char in text if not unicodedata.combining(char)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _business_id_series(awards: pd.DataFrame) -> pd.Series:
    values = awards.get("supplier_business_id", pd.Series(index=awards.index, dtype=object))
    return values.map(normalise_supplier_business_id)


def _supplier_name_series(awards: pd.DataFrame) -> pd.Series:
    values = awards.get("supplier_name", pd.Series(index=awards.index, dtype=object))
    return (
        values.fillna("").astype(str).str.strip().str.lower().str.replace(r"\s+", " ", regex=True)
    )


def _source_party_id_series(awards: pd.DataFrame) -> pd.Series:
    party = awards.get("supplier_party_id", pd.Series(index=awards.index, dtype=object))
    uid = awards.get("supplier_uid", pd.Series(index=awards.index, dtype=object))
    party = party.fillna("").astype(str).str.strip()
    uid = uid.fillna("").astype(str).str.strip()
    return party.where(party.ne(""), uid).replace("", pd.NA)


def supplier_key(awards: pd.DataFrame) -> pd.Series:
    """Robust per-row supplier identity.

    Uses a non-sentinel Kosovo business-registry ID when present, then a
    normalised supplier name, then the published source party ID. The last
    fallback is source identity within this publication, not a verified legal
    identifier. Name-first ordering preserves the established consortium view.
    """
    biz = _business_id_series(awards)
    name = _supplier_name_series(awards)
    party = _source_party_id_series(awards)
    fallback = ("name::" + name).where(name != "")
    key = biz.where(biz.notna(), other=fallback)
    return key.where(key.notna(), other="party::" + party.astype("string"))


def supplier_source_identity_key(awards: pd.DataFrame) -> pd.Series:
    """Business ID → source party ID → name sensitivity key.

    Source party IDs are stable in the supplied snapshot but have not been
    independently verified as legal business identifiers.
    """
    biz = _business_id_series(awards)
    party = _source_party_id_series(awards)
    name = _supplier_name_series(awards)
    party_key = ("party::" + party.astype("string")).where(party.notna())
    name_key = ("name::" + name).where(name.ne(""))
    key = biz.where(biz.notna(), other=party_key)
    return key.where(key.notna(), other=name_key)


def aggregate_awards_per_tender(awards: pd.DataFrame) -> pd.DataFrame:
    """Roll up ``awards`` rows to one summary record per tender."""
    a = awards.copy()
    a["_supplier_key"] = supplier_source_identity_key(a)
    a["_business_id"] = _business_id_series(a)
    g = a.groupby("ocid", dropna=False)
    return pd.DataFrame(
        {
            "n_awards": g.size(),
            "n_supplier_identities": g["_supplier_key"].nunique(),
            "n_supplier_business_ids": g["_business_id"].nunique(),
            "total_awarded_eur": g["awarded_value_eur"].sum(min_count=1),
            "first_award_date": g["award_date"].min(),
            "last_award_date": g["award_date"].max(),
            "min_awarded_eur": g["awarded_value_eur"].min(),
            "max_awarded_eur": g["awarded_value_eur"].max(),
            "median_awarded_eur": g["awarded_value_eur"].median(),
        }
    ).reset_index()


def per_tender_winner_concentration(awards: pd.DataFrame) -> pd.DataFrame:
    """Within each tender, the share captured by the top supplier (0..1).

    Groups by a consortium-aware :func:`supplier_key` so that several distinct
    joint ventures with empty business ids are not merged into one.
    """
    a = awards[awards["awarded_value_eur"].notna()].copy()
    if a.empty:
        return pd.DataFrame(columns=["ocid", "winner_top_share"])
    a["_supplier_key"] = supplier_source_identity_key(a)
    # Unknown suppliers stay in the tender denominator but cannot become a
    # fictitious shared winner. If every supplier is unidentified, the share
    # is undefined and no concentration value is emitted for that tender.
    totals = a.groupby("ocid")["awarded_value_eur"].sum()
    g = (
        a.dropna(subset=["_supplier_key"])
        .groupby(["ocid", "_supplier_key"])["awarded_value_eur"]
        .sum()
    )
    g = g.reset_index()
    g["share"] = g["awarded_value_eur"] / g["ocid"].map(totals)
    return g.groupby("ocid")["share"].max().rename("winner_top_share").reset_index()


# ---------------------------------------------------------- main feature build


def build_tender_features(tenders: pd.DataFrame, awards: pd.DataFrame) -> pd.DataFrame:
    """Produce the immutable, unscored ``gold.tender_features`` table.

    One row per OCID. Includes:

    * Core silver columns (passed through).
    * Derived value features (logs, ratios).
    * Aggregated award stats.
    * Winner concentration within the tender.
    * Contextual rank features (within entity / category / method).
    * Contextual z-scores (sensitivity to peer-group baseline).
    * Cleanliness flags (lot-value mismatch).
    """
    df = tenders.copy()
    df["procedure_subtype"] = classify_procedure_series(df)

    # award aggregates
    aw = aggregate_awards_per_tender(awards)
    df = df.merge(aw, on="ocid", how="left")
    win = per_tender_winner_concentration(awards)
    df = df.merge(win, on="ocid", how="left")

    # value derivations
    df["estimated_value_eur"] = pd.to_numeric(df["estimated_value_eur"], errors="coerce")
    df["total_awarded_eur"] = pd.to_numeric(df["total_awarded_eur"], errors="coerce")
    df["log_estimated_eur"] = safe_log10(df["estimated_value_eur"])
    df["log_awarded_eur"] = safe_log10(df["total_awarded_eur"])
    ratio = df["total_awarded_eur"] / df["estimated_value_eur"]
    df["awarded_value_ratio"] = ratio.where(
        np.isfinite(ratio.to_numpy(dtype=float, na_value=np.nan)),
        other=np.nan,
    )

    # timing derivations
    fad = pd.to_datetime(df["first_award_date"], errors="coerce", utc=True)
    end = pd.to_datetime(df["end_date"], errors="coerce", utc=True)
    df["first_award_date"] = fad
    df["days_to_first_award"] = (fad - end).dt.total_seconds() / 86400
    df["days_tender_open"] = df["duration_computed_days"]

    # Competition signals are only defined when bidder data was actually
    # published. Missing tenderer arrays remain a nullable count and cannot be
    # silently recoded as zero participation.
    if "bidder_data_observed" not in df:
        df["bidder_data_observed"] = df["num_bidders"].notna()
    df["bidder_data_observed"] = df["bidder_data_observed"].fillna(False).astype(bool)
    observed_bidders = df["bidder_data_observed"] & df["num_bidders"].notna()
    df["bidder_data_missing"] = (~observed_bidders).astype(int)
    df["is_single_bidder"] = (observed_bidders & df["num_bidders"].eq(1).fillna(False)).astype(int)
    df["is_zero_bidder"] = (observed_bidders & df["num_bidders"].eq(0).fillna(False)).astype(int)
    df["was_awarded"] = (df["n_awards"].fillna(0) >= 1).astype(int)

    # Award state is represented once by ``was_awarded``.  Counts and total
    # value have a real zero for an unawarded tender; continuous facts such as
    # winner share, value ratio and award timing are undefined and remain NaN.
    no_award = df["was_awarded"] == 0
    for col in [
        "n_awards",
        "n_supplier_identities",
        "n_supplier_business_ids",
        "total_awarded_eur",
    ]:
        df[col] = df[col].where(~no_award, other=0.0)
    df.loc[no_award, "winner_top_share"] = np.nan

    # A normalized buyer name linked to multiple source IDs is a reviewable
    # identity collision, not proof that the IDs denote one legal entity. Keep
    # official IDs separate and expose only a zero-weight DQ diagnostic.
    buyer_names = df["procuring_entity_name"].map(normalise_identity_name)
    buyer_ids = df["procuring_entity_id"].fillna("").astype(str).str.strip()
    buyer_pairs = pd.DataFrame({"name": buyer_names, "buyer_id": buyer_ids})
    valid_pairs = buyer_pairs[buyer_pairs["name"].ne("") & buyer_pairs["buyer_id"].ne("")]
    colliding_names = valid_pairs.groupby("name")["buyer_id"].nunique()
    colliding_names = set(colliding_names[colliding_names > 1].index)
    df["buyer_name_id_collision"] = buyer_names.isin(colliding_names).astype(int)

    # entity-level rank features
    df["entity_tender_count"] = df.groupby("procuring_entity_id")["ocid"].transform("count")
    df["entity_total_value_eur"] = df.groupby("procuring_entity_id")[
        "estimated_value_eur"
    ].transform("sum")
    df["value_rank_within_entity"] = df.groupby("procuring_entity_id")["estimated_value_eur"].rank(
        pct=True
    )
    df["value_rank_within_category"] = df.groupby("category")["estimated_value_eur"].rank(pct=True)
    df["value_rank_within_method"] = df.groupby("method")["estimated_value_eur"].rank(pct=True)

    # contextual z-scores — used by the comparison-based anomaly layer
    df["log_value_z_within_entity"] = zscore_within(df, "log_estimated_eur", "procuring_entity_id")
    df["log_value_z_within_category"] = zscore_within(df, "log_estimated_eur", "category")
    df["log_value_z_within_method"] = zscore_within(df, "log_estimated_eur", "method")
    df["bidders_z_within_entity"] = zscore_within(df, "num_bidders", "procuring_entity_id")
    df["bidders_z_within_category"] = zscore_within(df, "num_bidders", "category")
    df["awarded_ratio_z_within_category"] = zscore_within(df, "awarded_value_ratio", "category")

    # cleanliness flags
    lot_delta = (df["lots_value_sum"] - df["estimated_value_eur"]).abs()
    lot_relative_delta = lot_delta / df["estimated_value_eur"].abs().replace(0, np.nan)
    df["lot_value_mismatch"] = (
        (df["num_lots"] > 1)
        & df["lots_value_sum"].notna()
        & (lot_delta > 100.0)
        & (lot_relative_delta > 0.001)
    ).astype(int)

    # derived booleans
    df["end_before_start"] = df["end_before_start"].fillna(False).astype(int)

    return df


# Numeric features fed to unsupervised models
ML_FEATURES: list[str] = [
    "log_estimated_eur",
    "num_lots",
    "num_bidders",
    "num_parties",
    "n_awards",
    "n_supplier_identities",
    "log_awarded_eur",
    "awarded_value_ratio",
    "days_to_first_award",
    "days_tender_open",
    "winner_top_share",
    "value_rank_within_category",
    "value_rank_within_method",
    "value_rank_within_entity",
    "entity_tender_count",
    "is_single_bidder",
    "is_zero_bidder",
    "was_awarded",
    "lot_value_mismatch",
    "end_before_start",
]

# Contextual z-score features (used by ComparisonScorer)
CONTEXT_FEATURES: list[str] = [
    "log_value_z_within_entity",
    "log_value_z_within_category",
    "log_value_z_within_method",
    "bidders_z_within_entity",
    "bidders_z_within_category",
    "awarded_ratio_z_within_category",
]


def select_ml_matrix(features: pd.DataFrame) -> pd.DataFrame:
    """Slice the feature DataFrame to ``ocid`` + ML feature columns."""
    return features[["ocid", *ML_FEATURES]].copy()


def select_context_matrix(features: pd.DataFrame) -> pd.DataFrame:
    """Slice to ``ocid`` + contextual-comparison features."""
    return features[["ocid", *CONTEXT_FEATURES]].copy()
