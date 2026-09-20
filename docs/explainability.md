# Explaining the published scores

The dashboard explains how each tender's review-priority score was calculated.
It provides an exact decomposition of `ensemble_score`, transparent rule
arithmetic, and the contextual measurements that contribute to that score.
A separate SHAP explanation describes a classifier trained to reproduce the
rules. These explanations establish the system's arithmetic, not whether a
procurement involves wrongdoing.

## What each explanation means

| Explanation | Target | Interpretation |
|---|---|---|
| Component contributions | `ensemble_score` | Each component's weighted contribution to the published score |
| Effects relative to the baseline | `ensemble_score` | How components raise or lower the score relative to their snapshot means |
| Triggered-rule arithmetic | `rule_score` | Which scored rules fired and how their weights combine |
| Contextual drivers | `context_score` | Which contextual z-score has the greatest absolute value |
| Feature percentiles and missingness | Input features | Descriptive context; not feature attribution inside an anomaly detector |
| HGB SHAP | Rule-proxy classifier's raw log-odds | How input features contribute to the classifier output; does not explain `ensemble_score` |

The project does not claim causal explanations or feature-level attribution
inside each unsupervised detector. See [methodology](methodology.md) and
[responsible use](responsible_use.md) for the evidence limits.

## The hybrid score

The bundled release contains 75,710 records and four selected detector families:
One-Class SVM (`ocsvm`), Isolation Forest (`iso`), HBOS (`hbos`), and KNN (`knn`).
Their scores are converted to percentile ranks over the **complete released
snapshot**, using pandas `rank(method="average", pct=True)`. Tied scores receive
their average rank. The four ranks and two transparent components are averaged:

```text
ensemble_score = (
    ensemble_rank_ocsvm
  + ensemble_rank_iso
  + ensemble_rank_hbos
  + ensemble_rank_knn
  + rule_score
  + context_score
) / 6
```

Each current component therefore has weight `1/6`. Raw detector scores are not
the detector values in this formula. The rule and context scores enter directly,
without another percentile transformation.

Selected families, component order, weights, rank method, and baselines are
declared in the `ensemble_explanation` object in
[`feature_list.json`](../data/models/feature_list.json), with a matching copy in
[`validation_report.json`](../data/models/validation_report.json). Code reads that
definition rather than assuming every future release will contain six components.

Dashboard filters select records to display; they do not recompute the ranks or
scores. A full pipeline rebuild on a changed population can change a record's
score even when its own fields remain unchanged.

## Direct contributions and baseline effects

For component value `v`, weight `w`, and complete-snapshot component mean `b`:

```text
direct_contribution = w × v
effect_vs_baseline = w × (v − b)
baseline_score = sum(w × b)

ensemble_score = sum(direct_contribution)
ensemble_score = baseline_score + sum(effect_vs_baseline)
```

The baseline of the bundled release is **0.43699591144885175**. A positive effect
means that component raises the score relative to its own snapshot mean; a
negative effect lowers it. The baseline is a mathematical reference, not a
decision threshold or an estimated probability of a violation. Reconstruction
checks allow a floating-point tolerance of `1e-12`.

## Worked example from the bundled release

Record `ocds-uhzcmx-701-22-1274-1-1-1` has the highest published ensemble score
in this snapshot. This identifies its position in the model's ranking, not a
confirmed irregularity. The following values were checked against the stored
artifacts on 20 September 2026; displayed contributions are rounded to 12 places.

| Component | Value in formula | Weight | Direct contribution |
|---|---:|---:|---:|
| `ensemble_rank_ocsvm` | 0.9953374719323735 | 1/6 | 0.165889578655 |
| `ensemble_rank_iso` | 0.9911240258882579 | 1/6 | 0.165187337648 |
| `ensemble_rank_hbos` | 0.9780346057324000 | 1/6 | 0.163005767622 |
| `ensemble_rank_knn` | 0.9961167613261128 | 1/6 | 0.166019460221 |
| `rule_score` | 1.0000000000000000 | 1/6 | 0.166666666667 |
| `context_score` | 0.8842698349625934 | 1/6 | 0.147378305827 |

Using the stored precision, the contributions reconstruct
**`ensemble_score = 0.9741471166402895`**. The alternative baseline explanation is:

```text
0.43699591144885175 + 0.5371512051914378 ≈ 0.9741471166402895
baseline              combined effects    published score
```

### Rule arithmetic

Only rules marked `score_enabled=True` contribute. Their author-selected
weights are summed, divided by `2.0`, and clipped to `[0, 1]`:

```text
rule_score = clip(sum(weight × triggered) / 2.0, 0, 1)
```

This record triggers three scored rules:

| Rule | Weight |
|---|---:|
| `SINGLE_BIDDER_OPEN` | 0.75 |
| `HIGH_VALUE_SINGLE` | 0.75 |
| `WINNER_TAKES_ALL_LARGE` | 0.50 |

Thus `(0.75 + 0.75 + 0.50) / 2 = 1.0`; clipping does not alter the result.
Data-quality and operational diagnostics remain visible but contribute zero.
The weights and normalization are screening choices, not learned probabilities
or legal severity grades. Definitions and limitations are maintained in
[`rules.py`](../src/thesis/anomaly/rules.py).

### Contextual contribution

The context component uses the largest absolute available contextual z-score:

```text
context_score = tanh(max(abs(contextual_z_scores)) / 2)
```

The contextual features compare values, bidder counts, or award-value ratios
within the relevant authority, category, or source method. For this example,
the driver is `log_value_z_within_category = 2.790034351468596`, giving
`tanh(2.790034351468596 / 2) = 0.8842698349625934`. When all contextual values
are missing, the implementation returns zero and no driver; that is not evidence
that the record is typical. See [`comparison.py`](../src/thesis/anomaly/comparison.py).

## SHAP explains a different model

The HGB classifier predicts the internally generated label
`rule_score >= 0.4` in this release. Its inputs overlap with the inputs used by
the rules, so strong predictive agreement is expected and is not independent
evidence of detection accuracy.

Stored SHAP values explain the classifier's **raw log-odds**, not the hybrid
score or a real-world misconduct probability:

```text
shap_base_value + sum(feature_shap_values) = HGB raw log-odds
```

For the same example record, the stored base is `-10.710334624360387`, and the
feature contributions sum to `20.92212529639591`. They reconstruct
`10.211790672035525`, agreeing with the persisted classifier's raw output
`10.21179067203552` within `5.33e-15`. This output is on a different scale from
the ensemble score `0.9741471166402895`.

The SHAP target and output space are explicitly recorded in `shap_explanation`.
The stored table is [`shap_values.parquet`](../data/models/shap_values.parquet).

## Agreement between detectors

`model_agreement_count` counts selected detectors whose complete-snapshot
percentile rank is at least `0.95`. The historical column `high_confidence`
equals one when at least three of the four selected detectors meet that
condition. Ties can affect the exact number above a rank threshold.

The example meets the threshold in all four detectors. This agreement is
separate from the six-component average and does not establish calibrated
confidence, fewer false positives, or independent corroboration.

## Verification and implementation

[`ensemble.py`](../src/thesis/anomaly/ensemble.py) owns the composition and
per-record decomposition. Release-owned DQ evidence binds the explanation to
the published artifacts:

- [`gold_tender_summary.release.dq.json`](../data/dq/gold_tender_summary.release.dq.json)
  records the reconstruction checks for detector ranks, ensemble scores, and
  agreement fields.
- [`ml_shap_values.release.dq.json`](../data/dq/ml_shap_values.release.dq.json)
  records SHAP column/order, finite-value, and raw-output additivity checks.
- [`ml.release.json`](../data/models/ml.release.json) binds the models, tables,
  metadata, checks, and upstream publications to one release generation.

The verification used for this guide recomputed every published ensemble score
from all 75,710 records; the maximum difference was `0.0`. It also checked the
example's rules, contextual driver, and persisted HGB output without changing
any artifact. To repeat the release and explanation checks in a complete local
installation:

```bash
.venv/bin/python -m thesis pipeline validate-releases
.venv/bin/python -m pytest tests/unit/test_ensemble_explanations.py \
  tests/unit/test_comparison.py tests/unit/test_ml_artifact_integrity.py \
  tests/integration/test_xai_release.py -q
```

These commands require the original snapshot and its complete publication chain.
`validate-releases` additionally requires the recorded runtime; see the
[operations guide](operations.md) for the compatible read-only dashboard policy.
Artifact integrity and score reconstruction establish reproducibility; external
outcome evaluation still requires the [manual audit](manual_audit_protocol.md).
