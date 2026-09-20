# DQ — gold_entity_summary

_Run at_: `2026-07-19T12:19:44.121375+00:00`  ·  _table_: `gold.procuring_entity_summary`

_shape_: `206 × 26`  ·  _data fingerprint_: `347998d5590cb1bbf55fc224824f629fd6600785f3a8677ef0f82928e573bd31`

**Result:** ✅ PASS  ·  errors=0  warnings=0  infos=0  passed=7  failed=0  duration_ms=22.0

| status | severity | name | description | observed |
|---|---|---|---|---|
| ✅ | error | `row_count_positive` | procuring-entity summary has at least one row | `206` |
| ✅ | error | `entity_key_unique` | published procuring-entity identifiers form unique summary groups | `0` |
| ✅ | error | `counts_and_values_non_negative` | entity counts and monetary summaries are finite and non-negative | `0` |
| ✅ | error | `awarded_tenders_not_above_total` | awarded tender counts do not exceed all tenders | `0` |
| ✅ | error | `percentage_columns_in_range` | coverage and descriptive rates are in [0, 100] when observed | `0` |
| ✅ | error | `hhi_sensitivities_in_range` | all disclosed supplier-identity HHI sensitivities are in [0, 10,000] | `0` |
| ✅ | error | `source_feature_reconciliation` | entity tender, estimated-value and awarded-value totals reconcile to Gold | `{'source_projection_fingerprint': '3f094f928f47893a4b041a2411103bb8cf576e845e2b6` |
