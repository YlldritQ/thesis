"""Train the anomaly ensemble + supervised explainer + write validation report.

Model selection is **benchmark-driven**: when
``data/models/benchmark/champions.json`` exists (produced by
:mod:`thesis.pipeline.benchmark`), every detector family is instantiated
with its champion hyperparameters and the ensemble is composed of the
top-K families elected by the benchmark's composite score
(0.45×proxy-AUC + 0.35×stability + 0.20×seed-consistency). A complete,
generation-matched full benchmark release is mandatory; this stage never
silently substitutes defaults for a missing election.

This stage:

1. Loads immutable gold ``tender_features``.
2. Fits all eight unsupervised detector families with the elected champion
   hyperparameters and scores every tender with each.
3. Composes ``ensemble_score`` = mean(rule, context, top-K detector
   complete-snapshot percentile ranks) and persists an exact additive XAI
   contract for that published score.
4. Fits the HistGradientBoosting explainer (champion params when
   available) on weak rule labels and computes SHAP values.
5. Runs cross-validation, stability bootstrap, inter-model agreement,
   calibration → ``data/models/validation_report.json``.
6. Runs the gold DQ suite on the complete in-memory scored table.
7. Only after DQ passes, persists every model and the scored canonical
   ``gold.tender_summary``.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ..anomaly.artifact_integrity import (
    HGB_ARTIFACT_SCHEMA_VERSION,
    ML_JSON_SCHEMA_VERSION,
    MODEL_BUNDLE_SCHEMA_VERSION,
    persisted_shap_release_payload,
    validate_persisted_json_artifacts,
    validate_persisted_model_artifacts,
)
from ..anomaly.benchmark import (
    CHAMPIONS_SCHEMA_VERSION,
    benchmark_protocol_fingerprint,
    benchmark_protocol_provenance,
    benchmark_semantic_check,
    data_fingerprint,
    declared_benchmark_contract,
)
from ..anomaly.comparison import contextual_score
from ..anomaly.detectors import FAMILY_REGISTRY, build_scorer
from ..anomaly.ensemble import compose_hybrid_ensemble
from ..anomaly.explanations import shap_values_for
from ..anomaly.models import SupervisedScorer
from ..anomaly.validation import (
    calibration_report,
    cross_validate_supervised,
    deployed_feature_family_ablation,
    inter_model_agreement,
    rank_vote_quantile_sensitivity,
    stability_bootstrap,
)
from ..config import settings
from ..domain.features import ML_FEATURES
from ..dq.framework import run_suite
from ..dq.suites import gold_tender_summary_suite
from ..io.readers import load_gold_features
from ..io.writers import write_joblib, write_json, write_parquet
from ..jsonutil import loads_json
from ..logging import bind, get_logger, unbind
from ..paths import (
    BENCHMARK_LEADERBOARD,
    BENCHMARK_RELEASE,
    BENCHMARK_RELEASE_DQ,
    BENCHMARK_RESULTS,
    CHAMPION_MODELS,
    CHAMPIONS,
    ELLIPTIC_ENVELOPE,
    FEATURE_LIST,
    GOLD_FEATURES,
    GOLD_RELEASE,
    GOLD_TENDERS,
    GOLD_TENDERS_RELEASE_DQ,
    HGB_MODEL,
    ISO_FOREST,
    LOF_MODEL,
    ML_RELEASE,
    MODEL_VALIDATION,
    MODELS,
    OCSVM_MODEL,
    SHAP_VALUES,
    SHAP_VALUES_RELEASE_DQ,
    ensure_dirs,
)
from ..release import (
    ReleaseIntegrityError,
    publish_release,
    validate_canonical_release,
)

log = get_logger("pipeline.ml")

# Declared before seeing ablation outcomes.  ``raw_fact_only`` retains direct
# counts/durations and monotone log transforms, excluding rule flags, contextual
# ranks, ratios, and concentration summaries. ``pre_outcome_fields_snapshot``
# excludes award/supplier/winner fields, but remains a static full-period
# snapshot and therefore is not a leakage-free temporal design.
DEPLOYED_ABLATION_FEATURE_SUBSETS: dict[str, list[str]] = {
    "raw_fact_only": [
        "log_estimated_eur",
        "num_lots",
        "num_bidders",
        "num_parties",
        "n_awards",
        "n_supplier_identities",
        "log_awarded_eur",
        "days_to_first_award",
        "days_tender_open",
    ],
    "pre_outcome_fields_snapshot": [
        "log_estimated_eur",
        "num_lots",
        "num_bidders",
        "days_tender_open",
        "value_rank_within_category",
        "value_rank_within_method",
        "value_rank_within_entity",
        "entity_tender_count",
        "is_single_bidder",
        "is_zero_bidder",
        "lot_value_mismatch",
        "end_before_start",
    ],
}

# The versioned ensemble bundle is authoritative.  Remove obsolete standalone
# models so tooling cannot accidentally load a stale, unbound estimator.
_OBSOLETE_MODEL_PATHS = (
    ISO_FOREST,
    LOF_MODEL,
    ELLIPTIC_ENVELOPE,
    OCSVM_MODEL,
    MODELS / "xgb_anomaly.joblib",
)


def _load_released_benchmark_bundle() -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    """Read the full benchmark election bundle under one release generation."""
    before = validate_canonical_release(
        "benchmark",
        require_current_provenance=True,
        require_current_runtime=True,
    )
    check_paths = {
        entry.get("path") for entry in before.payload.get("checks", []) if isinstance(entry, dict)
    }
    check_relative = (
        BENCHMARK_RELEASE_DQ.resolve().relative_to(settings().data_dir.resolve()).as_posix()
    )
    if check_relative not in check_paths:
        raise ReleaseIntegrityError(
            "benchmark release does not bind the semantic election DQ check"
        )

    result_rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        BENCHMARK_RESULTS.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            value = loads_json(line)
        except ValueError as exc:
            raise ReleaseIntegrityError(
                f"invalid released benchmark checkpoint row {line_number}"
            ) from exc
        if not isinstance(value, dict):
            raise ReleaseIntegrityError(
                f"released benchmark checkpoint row {line_number} is not an object"
            )
        result_rows.append(value)
    results = pd.DataFrame(result_rows)
    leaderboard = pd.read_parquet(BENCHMARK_LEADERBOARD)
    champions = loads_json(CHAMPIONS.read_text(encoding="utf-8"))
    stored_check = loads_json(BENCHMARK_RELEASE_DQ.read_text(encoding="utf-8"))
    if not isinstance(champions, dict) or not isinstance(stored_check, dict):
        raise ReleaseIntegrityError("released benchmark champions/check must contain JSON objects")
    after = validate_canonical_release(
        "benchmark",
        require_current_provenance=True,
        require_current_runtime=True,
    )
    if before.manifest_sha256 != after.manifest_sha256:
        raise ReleaseIntegrityError("benchmark release changed while reading its bundle")
    return results, leaderboard, champions, stored_check


def _load_champions(
    X: pd.DataFrame,
    rule_score: pd.Series,
    years: pd.Series,
) -> dict[str, Any]:
    """Load benchmark champions and reject results built from other data.

    Model selection fails closed if the election bundle, its feature/label
    fingerprint, or its semantic proof is missing or stale.
    """
    if not CHAMPIONS.exists():
        raise RuntimeError(
            "Benchmark champions.json is missing. Run `thesis pipeline benchmark` "
            "to publish a complete full election before running the ML stage."
        )
    try:
        results, leaderboard, champions, stored_semantic_check = _load_released_benchmark_bundle()
    except (OSError, ValueError, ReleaseIntegrityError) as exc:
        raise RuntimeError(
            "Benchmark release integrity validation failed. Run `thesis pipeline "
            "benchmark` to regenerate champions.json and its release manifest "
            "before running the ML stage."
        ) from exc

    current_fingerprint = data_fingerprint(X, rule_score, years)
    champions_fingerprint = champions.get("data_fingerprint")
    if champions_fingerprint != current_fingerprint:
        raise RuntimeError(
            "Benchmark champions are stale for the current gold feature data "
            f"(champions={champions_fingerprint!r}, "
            f"current={current_fingerprint!r}). Run `thesis pipeline benchmark` "
            "to regenerate champions.json before running the ML stage."
        )

    expected_protocol_fingerprint = benchmark_protocol_fingerprint()
    contract = declared_benchmark_contract(quick=False)
    completeness = champions.get("completeness")
    expected_unsup_families = set(contract["expected_unsupervised_families"])
    expected_sup_families = set(contract["expected_supervised_families"])
    champion_unsup = champions.get("unsupervised")
    ensemble_families = champions.get("ensemble_families")
    supervised_champion = champions.get("supervised_champion")
    explainer = champions.get("explainer")
    expected_ensemble_size = min(settings().benchmark_top_k_families, len(expected_unsup_families))
    contract_errors: list[str] = []

    current_semantic_check = benchmark_semantic_check(
        results,
        champions,
        quick=False,
        leaderboard=leaderboard,
    )
    semantic_fields = {
        key: value for key, value in current_semantic_check.items() if key != "checked_at"
    }
    stored_semantic_fields = {key: stored_semantic_check.get(key) for key in semantic_fields}
    if not current_semantic_check["passed"]:
        contract_errors.append(
            "released rows fail semantic election: " + "; ".join(current_semantic_check["errors"])
        )
    if stored_semantic_check.get("passed") is not True:
        contract_errors.append("released semantic election DQ check is not passed")
    if stored_semantic_fields != semantic_fields:
        contract_errors.append("released semantic election DQ proof does not match recomputation")

    if champions.get("schema_version") != CHAMPIONS_SCHEMA_VERSION:
        contract_errors.append("unsupported or missing schema_version")
    if champions.get("quick") is not False:
        contract_errors.append("quick must be false")
    if champions.get("protocol_fingerprint") != expected_protocol_fingerprint:
        contract_errors.append("protocol_fingerprint is missing or stale")
    if champions.get("benchmark_protocol") != benchmark_protocol_provenance():
        contract_errors.append("benchmark_protocol is missing or stale")
    if not isinstance(completeness, dict) or completeness.get("complete") is not True:
        contract_errors.append("election completeness proof is missing or false")
    else:
        for key in [
            "expected_config_keys",
            "expected_total",
            "expected_unsupervised_total",
            "expected_supervised_total",
            "expected_unsupervised_families",
            "expected_supervised_families",
        ]:
            if completeness.get(key) != contract[key]:
                contract_errors.append(f"completeness.{key} does not match the full grid")
        if completeness.get("successful_config_keys") != contract["expected_config_keys"]:
            contract_errors.append("not every declared config completed successfully")
        if completeness.get("quick") is not False:
            contract_errors.append("completeness proof is not for a full election")
        for key in [
            "missing_config_keys",
            "extra_config_keys",
            "invalid_config_keys",
            "failed_config_keys",
            "stale_protocol_config_keys",
        ]:
            if completeness.get(key) != []:
                contract_errors.append(f"completeness.{key} is not empty")
        if set(completeness.get("unsupervised_families", [])) != expected_unsup_families:
            contract_errors.append("not all detector families completed")
        if set(completeness.get("supervised_families", [])) != expected_sup_families:
            contract_errors.append("not all supervised families completed")

    if not isinstance(champion_unsup, dict) or set(champion_unsup) != expected_unsup_families:
        contract_errors.append("unsupervised champions do not cover every detector family")
    elif any(not isinstance(info.get("params"), dict) for info in champion_unsup.values()):
        contract_errors.append("one or more detector champions have invalid params")
    if (
        not isinstance(ensemble_families, list)
        or len(ensemble_families) != expected_ensemble_size
        or len(set(ensemble_families)) != len(ensemble_families)
        or not set(ensemble_families).issubset(expected_unsup_families)
    ):
        contract_errors.append("ensemble_families is incomplete or invalid")
    if (
        not isinstance(supervised_champion, dict)
        or supervised_champion.get("family") not in expected_sup_families
        or not isinstance(supervised_champion.get("params"), dict)
    ):
        contract_errors.append("supervised champion is missing or invalid")
    if (
        not isinstance(explainer, dict)
        or explainer.get("family") != "hgb"
        or not isinstance(explainer.get("params"), dict)
    ):
        contract_errors.append("a successful HGB explainer champion is required")

    if contract_errors:
        raise RuntimeError(
            "Benchmark champions fail the deployment contract: "
            + "; ".join(contract_errors)
            + ". Run `thesis pipeline benchmark` to publish a complete full election."
        )
    champions["_verified_semantic_fingerprint"] = current_semantic_check["semantic_fingerprint"]
    log.info(
        "ml.champions.loaded",
        ensemble_families=champions.get("ensemble_families"),
        created_at=champions.get("created_at"),
        data_fingerprint=current_fingerprint,
        semantic_fingerprint=current_semantic_check["semantic_fingerprint"],
    )
    return champions


def _default_params(family: str) -> dict[str, Any]:
    cfg = settings()
    defaults: dict[str, dict[str, Any]] = {
        "iso": {
            "n_estimators": cfg.iso_forest_n_estimators,
            "contamination": cfg.iso_forest_contamination,
        },
        "lof": {"n_neighbors": cfg.lof_n_neighbors},
        "ee": {"contamination": cfg.elliptic_envelope_contamination},
        "ocsvm": {"nu": cfg.ocsvm_nu, "subsample_size": cfg.ocsvm_subsample_size},
        "pca": {"n_components": 10},
        "gmm": {"n_components": 4},
        "knn": {"n_neighbors": 10},
        "hbos": {"n_bins": 20},
    }
    return defaults[family]


def run() -> dict[str, Any]:
    bind(stage="ml")
    try:
        ensure_dirs()
        cfg = settings()
        log.info("ml.start")
        gold_release = validate_canonical_release(
            "gold",
            require_current_provenance=True,
            require_current_runtime=True,
        )
        expected_input_manifest_sha256 = {GOLD_RELEASE: gold_release.manifest_sha256}
        benchmark_release = validate_canonical_release(
            "benchmark",
            require_current_provenance=True,
            require_current_runtime=True,
        )
        expected_input_manifest_sha256[BENCHMARK_RELEASE] = benchmark_release.manifest_sha256
        # Copy the generation-validated immutable feature frame before adding columns.
        gold = load_gold_features().copy()
        X = gold[ML_FEATURES].copy()
        log.info("ml.feature_matrix", shape=list(X.shape))

        rule_labels = (gold["rule_score"] >= cfg.rule_label_threshold).astype(int)
        champions = _load_champions(X, gold["rule_score"], gold["year"])
        champ_unsup: dict[str, Any] = champions["unsupervised"]
        ensemble_families: list[str] = champions["ensemble_families"]

        # ------------------------------------------------- fit all families
        scorers: dict[str, Any] = {}
        deployed_family_params: dict[str, dict[str, Any]] = {}
        for family in FAMILY_REGISTRY:
            params = _default_params(family)
            params.update(champ_unsup[family]["params"])
            deployed_family_params[family] = params.copy()
            log.info(
                "ml.fit",
                family=family,
                params=params,
                source="benchmark_champion",
            )
            scorer = build_scorer(family, params)
            scorer.fit(X)
            scorers[family] = scorer
            gold[f"{family}_score"] = scorer.score(X).values

        # explainer (SHAP-capable HGB, champion params when available)
        explainer_params = champions["explainer"]["params"]
        log.info("ml.fit.explainer", params=explainer_params)
        hgb = SupervisedScorer(
            max_depth=explainer_params.get("max_depth", cfg.hgb_max_depth),
            n_estimators=explainer_params.get("max_iter", cfg.hgb_n_estimators),
            learning_rate=explainer_params.get("learning_rate", 0.08),
        ).fit(X, gold["rule_score"])
        gold["hgb_score"] = hgb.score(X).values
        gold["context_score"] = contextual_score(gold).values

        # ------------------------------------------------- ensemble
        # Detector scores are min-max-normalised, so their absolute scale is
        # set by each detector's single most extreme record. Both the vote
        # and the ensemble contribution therefore use rank-percentiles —
        # scale-invariant and comparable across detectors. Rule and context
        # scores keep their absolute, documented scales.
        member_cols = [f"{f}_score" for f in ensemble_families]
        vote_q = cfg.benchmark_flag_quantile
        composition = compose_hybrid_ensemble(
            gold,
            ensemble_families,
            flag_quantile=vote_q,
            minimum_models_agreeing=cfg.minimum_models_agreeing_for_high_confidence,
        )
        member_ranks = composition.detector_ranks
        for column in composition.detector_rank_columns:
            gold[column] = member_ranks[column].values
        gold["ensemble_score"] = composition.ensemble_score.values
        gold["model_agreement_count"] = composition.model_agreement_count.values
        gold["high_confidence"] = composition.high_confidence.values
        ensemble_definition = composition.definition()

        log.info(
            "ml.scores.distribution",
            ensemble_families=ensemble_families,
            ensemble_mean=float(gold["ensemble_score"].mean()),
            ensemble_p95=float(gold["ensemble_score"].quantile(0.95)),
            high_confidence_count=int(gold["high_confidence"].sum()),
        )

        # Validate the complete scored table before publishing any gold,
        # model, SHAP, feature-list, or validation-report artifact.
        gold_res = run_suite(gold_tender_summary_suite, gold)
        gold_res.write()
        if not gold_res.passed:
            raise ValueError(
                f"gold DQ ERROR — aborting before publication (errors={gold_res.error_count})"
            )
        if cfg.fail_fast_on_dq and gold_res.warning_count:
            raise ValueError(
                "gold DQ warnings — aborting before publication because THESIS_FAIL_FAST_ON_DQ=true"
            )
        # ------------------------------------------------- SHAP
        log.info("ml.shap.compute")
        sv, base_value = shap_values_for(hgb.model, X)
        shap_df = pd.DataFrame(sv, columns=ML_FEATURES)
        shap_df.insert(0, "ocid", gold["ocid"].values)
        shap_df.insert(1, "base_value", base_value)

        # ------------------------------------------------- validation
        log.info("ml.validation.start")
        # validate the *deployed* explainer configuration, not the defaults
        cv = cross_validate_supervised(X, gold["rule_score"], params=explainer_params)
        log.info(
            "ml.validation.cv",
            **{k: v for k, v in cv.items() if isinstance(v, (int, float)) or v is None},
        )

        stability_by_family: dict[str, Any] = {}
        for family in ensemble_families:
            params = _default_params(family)
            params.update((champ_unsup.get(family) or {}).get("params") or {})
            log.info("ml.validation.stability", family=family, params=params)
            result = stability_bootstrap(
                X,
                lambda family=family, params=params: build_scorer(family, params),
                n_runs=cfg.benchmark_bootstrap_runs,
                sample_frac=0.8,
                flag_quantile=cfg.benchmark_flag_quantile,
            )
            stability_by_family[family] = {
                **result,
                "params": params,
                "deployed": True,
            }
        # diversity statistic over the DETECTORS only — mixing in rule/context
        # would dilute the claim the report makes about detector diversity
        all_score_cols = [f"{f}_score" for f in FAMILY_REGISTRY]
        agree = inter_model_agreement(gold[all_score_cols])
        vote_sensitivity = rank_vote_quantile_sensitivity(
            member_ranks,
            minimum_agreement=cfg.minimum_models_agreeing_for_high_confidence,
            declared_quantile=vote_q,
        )
        feature_ablation = deployed_feature_family_ablation(
            X,
            ensemble_families=ensemble_families,
            family_params={family: deployed_family_params[family] for family in ensemble_families},
            full_family_scores=gold[member_cols],
            full_ensemble_score=gold["ensemble_score"],
            fixed_ensemble_components=gold[["rule_score", "context_score"]],
            feature_subsets=DEPLOYED_ABLATION_FEATURE_SUBSETS,
        )

        from sklearn.model_selection import train_test_split

        calib: dict[str, Any]
        class_counts = rule_labels.value_counts()
        if len(class_counts) < 2 or int(class_counts.min()) < 2:
            calib = {
                "bins": [],
                "ece": None,
                "note": "insufficient class balance for a stratified holdout",
            }
        else:
            Xt, Xv, _, yv = train_test_split(
                X,
                rule_labels,
                test_size=0.2,
                random_state=cfg.random_seed,
                stratify=rule_labels,
            )
            fit_holdout = SupervisedScorer(
                max_depth=explainer_params.get("max_depth", cfg.hgb_max_depth),
                n_estimators=explainer_params.get("max_iter", cfg.hgb_n_estimators),
                learning_rate=explainer_params.get("learning_rate", 0.08),
            ).fit(Xt, gold.loc[Xt.index, "rule_score"])
            proba = fit_holdout.score(Xv)
            calib = calibration_report(proba, yv)

        # ---- rule-only baseline + rule×ensemble confusion (review C-3, H-1) ----
        rule_flag = gold["rule_score"] >= cfg.rule_score_review_threshold
        ens_flag = gold["ensemble_score"] >= cfg.ensemble_score_review_threshold
        ens_flag_hi = gold["ensemble_score"] >= cfg.rule_score_priority_threshold
        both = int((rule_flag & ens_flag).sum())
        rule_only = int((rule_flag & ~ens_flag).sum())
        ens_only = int((~rule_flag & ens_flag).sum())
        neither = int((~rule_flag & ~ens_flag).sum())
        baseline = {
            "note": (
                "The rule layer is the auditable heuristic baseline. This table "
                "shows how much the unsupervised ensemble AGREES with it. A "
                "large ML-only or rule-demoted count means the ensemble is NOT "
                "a corroboration of the rules — its added value over the "
                "rule-only baseline is unvalidated (no external ground truth)."
            ),
            "rule_flag_threshold": cfg.rule_score_review_threshold,
            "ensemble_flag_threshold": cfg.ensemble_score_review_threshold,
            "rule_flagged_total": int(rule_flag.sum()),
            "ensemble_flagged_total": int(ens_flag.sum()),
            "confusion": {
                "both_flagged": both,
                "rule_only_demoted_by_ensemble": rule_only,
                "ensemble_only_ml_unvalidated": ens_only,
                "neither": neither,
            },
            "pct_rule_flags_demoted": round(rule_only / max(int(rule_flag.sum()), 1), 4),
            "pct_ensemble_that_is_ml_only": round(ens_only / max(int(ens_flag.sum()), 1), 4),
            "ensemble_hi_total": int(ens_flag_hi.sum()),
        }

        deployment_fingerprint = data_fingerprint(X, gold["rule_score"], gold["year"])
        deployment_provenance = {
            "data_fingerprint": deployment_fingerprint,
            "protocol_fingerprint": benchmark_protocol_fingerprint(),
            "benchmark_complete": bool(champions),
            "champions_schema_version": (champions.get("schema_version") if champions else None),
            "champions_created_at": champions.get("created_at"),
            "benchmark_implementation_fingerprint": champions.get("implementation_fingerprint"),
            "benchmark_semantic_fingerprint": champions.get("_verified_semantic_fingerprint"),
        }
        shap_explanation = {
            "target": "rule_proxy_binary_label",
            "output_space": "raw_log_odds",
            "does_not_explain": "ensemble_score",
        }
        validation_report = {
            "schema_version": ML_JSON_SCHEMA_VERSION,
            **deployment_provenance,
            "n_records": len(gold),
            "n_features": len(ML_FEATURES),
            "features": ML_FEATURES,
            "ensemble_models": ensemble_families,
            "all_detector_families": list(FAMILY_REGISTRY),
            "model_selection": ("benchmark champions" if champions else "config defaults"),
            "supervised_model": "hgb (HistGradientBoosting on rule_score >= threshold)",
            "rule_label_threshold": cfg.rule_label_threshold,
            # Explicit circularity statement: these metrics measure faithfulness
            # to the deterministic rule proxy, NOT detection. Most proxy inputs
            # are present directly or through closely overlapping raw features;
            # procedure subtype itself is not in X, so "by construction" would
            # be too strong.
            "IMPORTANT_metrics_are_faithfulness_to_rules_not_detection": True,
            "circularity_note": (
                "y = (rule_score >= threshold). The proxy is built from inputs "
                "that are mostly present directly or via closely overlapping "
                "raw features in X, so near-perfect ROC-AUC/PR-AUC/OOT measures "
                "proxy faithfulness rather than independent generalization. Use "
                "ONLY for raw-feature attribution via SHAP; these are NOT "
                "detection-performance figures."
            ),
            "cross_validation": cv,
            "rule_only_baseline_and_confusion": baseline,
            "stability_by_ensemble_family": stability_by_family,
            "limited_replication_note": (
                f"Benchmark stability uses {cfg.benchmark_bootstrap_runs} bootstrap "
                f"refits and stochastic-family consistency uses "
                f"{cfg.benchmark_extra_seeds} extra seeds. These limited repeats "
                "are snapshot repeatability diagnostics, not uncertainty estimates "
                "or external validation."
            ),
            "inter_model_agreement": agree,
            "rank_agreement_quantile_sensitivity": vote_sensitivity,
            "deployed_score_feature_ablation": feature_ablation,
            "model_election_sensitivity": champions.get(
                "model_election_sensitivity",
                {
                    "status": "not_available_without_full_benchmark",
                    "interpretation": "No benchmark election was deployed.",
                },
            ),
            "supervised_calibration": calib,
            "ensemble_explanation": ensemble_definition,
            "shap_explanation": shap_explanation,
            "shap_base_value": base_value,
        }

        # ------------------------------------------------- persist
        model_inputs = [GOLD_RELEASE, GOLD_FEATURES]
        if champions:
            model_inputs.extend(
                [
                    BENCHMARK_RELEASE,
                    BENCHMARK_RESULTS,
                    BENCHMARK_LEADERBOARD,
                    CHAMPIONS,
                ]
            )

        model_selection = "benchmark champions" if champions else "config defaults"
        model_bundle_payload = {
            "schema_version": MODEL_BUNDLE_SCHEMA_VERSION,
            "provenance": deployment_provenance,
            "scorers": scorers,
            "explainer": hgb,
            "ensemble_families": ensemble_families,
        }
        hgb_artifact_payload = {
            "schema_version": HGB_ARTIFACT_SCHEMA_VERSION,
            "family": "hgb",
            "provenance": deployment_provenance,
            "model": hgb,
        }
        feature_list_payload = {
            "schema_version": ML_JSON_SCHEMA_VERSION,
            **deployment_provenance,
            "ml_features": ML_FEATURES,
            "ensemble_families": ensemble_families,
            "model_selection": model_selection,
            "ensemble_explanation": ensemble_definition,
            "shap_explanation": shap_explanation,
            "shap_base_value": base_value,
        }
        write_joblib(model_bundle_payload, CHAMPION_MODELS)
        write_joblib(hgb_artifact_payload, HGB_MODEL)
        write_json(feature_list_payload, FEATURE_LIST)
        write_json(validation_report, MODEL_VALIDATION)
        log.info("ml.validation.report.written", path=str(MODEL_VALIDATION))

        write_parquet(
            shap_df,
            SHAP_VALUES,
            table="models.shap_values",
            layer="model",
            inputs=model_inputs,
        )

        write_parquet(
            gold,
            GOLD_TENDERS,
            table="gold.tender_summary",
            layer="gold",
            inputs=model_inputs,
            parameters={
                "random_seed": cfg.random_seed,
                "rule_label_threshold": cfg.rule_label_threshold,
                "ensemble_families": ensemble_families,
            },
        )
        write_json(
            gold_res.release_payload(GOLD_TENDERS, gold),
            GOLD_TENDERS_RELEASE_DQ,
        )
        shap_release_dq = persisted_shap_release_payload(
            SHAP_VALUES,
            GOLD_TENDERS,
            expected_features=ML_FEATURES,
            hgb_path=HGB_MODEL,
        )
        write_json(shap_release_dq, SHAP_VALUES_RELEASE_DQ)
        if shap_release_dq.get("passed") is not True:
            raise ValueError(
                "SHAP release DQ ERROR — aborting before ML manifest publication "
                f"(errors={shap_release_dq.get('error_count')})"
            )

        # Reload every serialized artifact before the manifest can authorize it.
        # Strict JSON equality catches schema/type drift; joblib rescoring catches
        # corrupt, stale, or structurally plausible-but-wrong estimator bundles.
        validate_persisted_json_artifacts(
            FEATURE_LIST,
            MODEL_VALIDATION,
            expected_feature_list=feature_list_payload,
            expected_validation_report=validation_report,
            expected_provenance=deployment_provenance,
            expected_features=ML_FEATURES,
            expected_ensemble_families=ensemble_families,
            expected_all_families=list(FAMILY_REGISTRY),
        )
        validate_persisted_model_artifacts(
            CHAMPION_MODELS,
            HGB_MODEL,
            GOLD_TENDERS,
            X=X,
            expected_ocids=gold["ocid"],
            expected_provenance=deployment_provenance,
            expected_families=list(FAMILY_REGISTRY),
            expected_ensemble_families=ensemble_families,
        )

        for obsolete_path in _OBSOLETE_MODEL_PATHS:
            obsolete_path.unlink(missing_ok=True)

        publish_release(
            ML_RELEASE,
            stage="ml",
            inputs=model_inputs,
            artifacts=[
                CHAMPION_MODELS,
                HGB_MODEL,
                FEATURE_LIST,
                MODEL_VALIDATION,
                SHAP_VALUES,
                GOLD_TENDERS,
            ],
            checks=[GOLD_TENDERS_RELEASE_DQ, SHAP_VALUES_RELEASE_DQ],
            metadata={
                **deployment_provenance,
                "model_selection": model_selection,
                "ensemble_families": ensemble_families,
            },
            expected_input_manifest_sha256=expected_input_manifest_sha256,
        )

        return {
            "gold_rows": len(gold),
            "shap_rows": len(shap_df),
            "model_selection": model_selection,
            "ensemble_families": ensemble_families,
            "cv_rocauc_mean": cv.get("rocauc_mean"),
            "ensemble_p95": float(gold["ensemble_score"].quantile(0.95)),
            "high_confidence_count": int(gold["high_confidence"].sum()),
        }
    finally:
        unbind("stage")
