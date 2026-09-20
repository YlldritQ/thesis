# DQ — gold_monthly_metrics

_Run at_: `2026-07-19T12:19:44.127840+00:00`  ·  _table_: `gold.monthly_metrics`

_shape_: `122 × 15`  ·  _data fingerprint_: `fbd5147dfa5dfb4674084c2cb1fcaadeae2d3d71e21712b64f3dbe69d95ed36a`

**Result:** ✅ PASS  ·  errors=0  warnings=0  infos=0  passed=7  failed=0  duration_ms=5.2

| status | severity | name | description | observed |
|---|---|---|---|---|
| ✅ | error | `row_count_positive` | monthly summary has at least one period | `122` |
| ✅ | error | `period_label_unique_nonblank` | every calendar or unknown-date bucket has one nonblank label | `{'blank': 0, 'duplicates': 0}` |
| ✅ | error | `counts_and_values_non_negative` | monthly counts and monetary aggregates are finite and non-negative | `0` |
| ✅ | error | `flagged_not_above_tenders` | monthly rule-review counts do not exceed all tenders | `0` |
| ✅ | error | `percentage_columns_in_range` | monthly bidder coverage and observed rates are in [0, 100] | `0` |
| ✅ | error | `date_known_boolean` | date_known is a non-null boolean indicator | `{'true': 121, 'false': 1, 'null': 0}` |
| ✅ | error | `source_feature_reconciliation` | monthly tender/value totals and unknown-date bucket reconcile to Gold | `{'source_projection_fingerprint': 'bd069b44a2534d899f5383cdb711c14fbf5bdfc7c3942` |
