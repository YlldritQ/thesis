# DQ — gold_supplier_summary

_Run at_: `2026-07-19T12:19:44.081999+00:00`  ·  _table_: `gold.supplier_summary`

_shape_: `9940 × 23`  ·  _data fingerprint_: `ec82b37eb4eb90540c20d4f65a8021a82720eb35c99e0c021d41720eb45bcff1`

**Result:** ✅ PASS  ·  errors=0  warnings=0  infos=0  passed=6  failed=0  duration_ms=427.3

| status | severity | name | description | observed |
|---|---|---|---|---|
| ✅ | error | `row_count_positive` | supplier summary has at least one identified supplier group | `9940` |
| ✅ | error | `supplier_key_unique_non_null` | supplier fallback keys are unique and non-null | `{'null': 0, 'duplicates': 0}` |
| ✅ | error | `counts_and_values_non_negative` | supplier counts and monetary summaries are finite and non-negative | `0` |
| ✅ | error | `percentage_columns_in_range` | supplier shares, coverage and observed single-bidder rates are in [0, 100] | `0` |
| ✅ | error | `identity_source_declared` | every supplier group discloses the identity fallback used | `{'name_fallback': 4851, 'business_id': 4576, 'source_party_id_fallback': 513}` |
| ✅ | error | `source_award_reconciliation` | supplier keys, rows, value and recorded identity coverage reconcile to awards | `{'source_projection_fingerprint': '91ea015002ebc689ce3f7db7d0a5521bb8346bfafb8b1` |
