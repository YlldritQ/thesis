# DQ — gold_tender_features

_Run at_: `2026-07-19T12:19:33.221159+00:00`  ·  _table_: `gold.tender_features`

_shape_: `75710 × 82`  ·  _data fingerprint_: `2c58ae397acbdde2a57bed4b7195b997df5733fade45c39521d6593fd608d0dd`

**Result:** ✅ PASS  ·  errors=0  warnings=0  infos=0  passed=13  failed=0  duration_ms=143.6

| status | severity | name | description | observed |
|---|---|---|---|---|
| ✅ | error | `row_count_positive` | table has at least one row | `75710` |
| ✅ | error | `ocid_unique` | ocid unique in base gold layer | `0` |
| ✅ | error | `ocid_non_null` | no null ocid in base gold layer | `0` |
| ✅ | error | `expected_ml_feature_columns` | all declared ML feature columns are present | `[]` |
| ✅ | error | `procurement_semantic_columns` | bidder observation, supplier identity and buyer-collision facts are present | `[]` |
| ✅ | error | `expected_rule_columns` | all declared indicator columns and rule_score are present | `[]` |
| ✅ | error | `ml_features_numeric_or_null` | declared ML features contain only numeric values or nulls | `0` |
| ✅ | error | `ml_features_no_infinity` | declared ML features contain no positive/negative infinity | `0` |
| ✅ | error | `rule_indicators_binary_non_null` | every declared indicator is non-null and boolean | `0` |
| ✅ | error | `rule_score_finite_in_unit_interval` | rule_score is non-null, finite and in [0, 1] | `{'null_or_non_numeric': 0, 'outside_unit_interval': 0}` |
| ✅ | error | `procedure_subtype_nonblank` | every row has a source-aware procedure subtype | `0` |
| ✅ | error | `bidder_observation_matches_nullable_count` | gold preserves missing bidder counts rather than converting them to zero | `0` |
| ✅ | error | `silver_to_gold_ocid_parity` | base gold has exactly the silver tender OCID population | `{'expected_rows': 75710, 'actual_rows': 75710, 'missing_ocids': 0, 'unexpected_o` |
