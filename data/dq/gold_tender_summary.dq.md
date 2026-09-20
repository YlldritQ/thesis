# DQ — gold_tender_summary

_Run at_: `2026-07-19T12:32:46.388479+00:00`  ·  _table_: `gold.tender_summary`

_shape_: `75710 × 99`  ·  _data fingerprint_: `239cdb97817ef068d880e5ead520a8800d4a498641686611c1cdf24889e98089`

**Result:** ✅ PASS  ·  errors=0  warnings=0  infos=0  passed=7  failed=0  duration_ms=86.7

| status | severity | name | description | observed |
|---|---|---|---|---|
| ✅ | error | `ocid_unique` | ocid unique in gold layer | `0` |
| ✅ | error | `rule_score_in_unit_interval` | rule_score ∈ [0, 1] | `min=0.0 max=1.0` |
| ✅ | error | `expected_score_columns` | all score columns present | `[]` |
| ✅ | error | `score_values_non_null` | every detector, proxy, context and ensemble score is non-null | `{}` |
| ✅ | error | `score_values_finite` | every detector, proxy, context and ensemble score is finite | `0` |
| ✅ | error | `score_values_in_unit_interval` | every detector, proxy, context and ensemble score is in [0, 1] | `0` |
| ✅ | error | `ensemble_xai_exact_reconstruction` | persisted detector ranks, agreement fields and ensemble score exactly reconstruct | `{'families': ['ocsvm', 'iso', 'hbos', 'knn'], 'max_absolute_delta': 0.0, 'column` |
