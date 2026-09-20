"""Exploratory anomaly ranking — multi-layer ensemble with explicit caveats.

Public-procurement anomaly detection is a **sensitive subject**. This
package therefore takes deliberate care:

* Multiple **complementary detector families** fitted to the same snapshot,
  so no single modelling assumption determines the exploratory ranking.
* **Contextual scores** comparing each tender against its peers (same
  procuring entity, same category, same method) to flag *unusual within
  context* rather than only *globally rare*.
* **Rule-proxy agreement, resampling stability, and score diagnostics** in
  ``data/models/validation_report.json``. These do not establish accuracy
  against independent outcomes or future-period generalisation.
* **No "fraud" labels**: scores are explicitly framed as "warrants
  review", with documentation in ``docs/responsible_use.md``.

A tender record scoring high here is a *signal for human review*, not a
finding about the procurement process or any party.
"""

from .comparison import contextual_score, explain_context_score  # noqa: F401
from .ensemble import (  # noqa: F401
    EnsembleScorer,
    combine_scores,
    compose_hybrid_ensemble,
)
from .explanations import (  # noqa: F401
    feature_deviation_profile,
    shap_values_for,
    top_contributions,
)
from .models import (  # noqa: F401
    UnsupervisedScorer,
    fit_elliptic_envelope,
    fit_isolation_forest,
    fit_local_outlier_factor,
    fit_one_class_svm,
    fit_supervised_hgb,
)
from .rules import RULES, Rule, apply_rules, explain_rule_score, rule_descriptions  # noqa: F401
from .validation import (  # noqa: F401
    calibration_report,
    cross_validate_supervised,
    inter_model_agreement,
    stability_bootstrap,
)

__all__ = [
    "RULES",
    "Rule",
    "apply_rules",
    "rule_descriptions",
    "explain_rule_score",
    "UnsupervisedScorer",
    "fit_isolation_forest",
    "fit_local_outlier_factor",
    "fit_elliptic_envelope",
    "fit_one_class_svm",
    "fit_supervised_hgb",
    "contextual_score",
    "explain_context_score",
    "EnsembleScorer",
    "combine_scores",
    "compose_hybrid_ensemble",
    "cross_validate_supervised",
    "stability_bootstrap",
    "inter_model_agreement",
    "calibration_report",
    "shap_values_for",
    "top_contributions",
    "feature_deviation_profile",
]
