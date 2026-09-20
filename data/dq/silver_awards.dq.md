# DQ — silver_awards

_Run at_: `2026-07-19T12:19:21.554529+00:00`  ·  _table_: `silver.awards`

_shape_: `62129 × 28`  ·  _data fingerprint_: `2f39dbd63b93976c8f6097069911edab682b2ec1632ab7585d5698992995b943`

**Result:** ✅ PASS  ·  errors=0  warnings=1  infos=0  passed=11  failed=1  duration_ms=388.6

| status | severity | name | description | observed |
|---|---|---|---|---|
| ✅ | error | `row_count_positive` | table has at least one row | `62129` |
| ✅ | error | `ocid_non_null` | no null ocid | `0` |
| ✅ | error | `awarded_value_non_negative` | awarded_value_eur >= 0 | `0` |
| ✅ | error | `bidder_observation_matches_nullable_count` | enriched bidder observation matches nullable bidder count | `0` |
| ✅ | warning | `supplier_business_id_coverage` | ≥70 % of awards have a usable non-sentinel business id | `0.7055` |
| ✅ | warning | `supplier_business_id_value_coverage` | nonblank business ids cover ≥45 % of awarded value | `0.4808` |
| ✅ | warning | `supplier_robust_identity_coverage` | ≥90 % of awards have a valid business id, supplier name or source party id | `1.0` |
| ✅ | warning | `supplier_robust_identity_value_coverage` | business-id/name/source-party identities cover ≥90 % of awarded value | `1.0` |
| ✅ | error | `supplier_business_id_sentinels_normalized` | known business-ID sentinel strings are retained only in the raw field | `0` |
| ✅ | warning | `source_party_id_coverage` | published source party ID coverage is reported, not treated as legal-ID validation | `1.0` |
| ❌ | warning | `award_lot_title_linkage` | award lot titles should link uniquely to one published tender lot | `{'exact_unique': 61260, 'no_exact_match': 505, 'exact_ambiguous': 244, 'missing_` |
| ✅ | error | `award_ocids_reference_tenders` | every award OCID exists in the exact Silver tender OCID population | `{'expected_tender_ocids': 75710, 'tender_ocid_population_sha256': 'dcc3eea156988` |
