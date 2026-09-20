# DQ — silver_tenders

_Run at_: `2026-07-19T12:19:20.887518+00:00`  ·  _table_: `silver.tenders`

_shape_: `75710 × 28`  ·  _data fingerprint_: `e1ea81ac5f0a1254f8cfd328f6c4550944f5632e2e1ca928b6519053541f26a5`

**Result:** ✅ PASS  ·  errors=0  warnings=3  infos=0  passed=13  failed=3  duration_ms=448.5

| status | severity | name | description | observed |
|---|---|---|---|---|
| ✅ | error | `row_count_positive` | table has at least one row | `75710` |
| ✅ | error | `ocid_unique` | every ocid appears exactly once | `0` |
| ✅ | error | `ocid_non_null` | no null ocid | `0` |
| ✅ | error | `tender_id_unique` | tender_id is unique where present | `0` |
| ✅ | error | `category_in_set` | category ∈ {goods, services, works} or null | `{'goods': 37819, 'services': 20910, 'works': 16981}` |
| ✅ | error | `estimated_value_non_negative` | estimated_value_eur >= 0 | `0` |
| ✅ | warning | `currency_eur_only` | all currencies are EUR (sanity) | `{'EUR': 75710}` |
| ❌ | warning | `release_date_non_null` | release_date is populated | `31` |
| ✅ | warning | `release_date_in_window` | populated release_date values are between 2010-01-01 and now+1y | `min=2016-03-25 12:59:00+00:00 max=2026-03-05 23:42:07+00:00` |
| ✅ | warning | `method_known_or_null` | method is one of the known OCDS values | `{'open': 58323, 'minimum': 12238, 'limited': 4611, 'selective': 6}` |
| ✅ | error | `num_bidders_non_negative` | observed num_bidders >= 0; unobserved bidder data remains null | `0` |
| ✅ | error | `bidder_observation_matches_nullable_count` | bidder_data_observed is true exactly when num_bidders is populated | `0` |
| ✅ | warning | `bidder_data_coverage` | at least 90% of tenders publish bidder data | `0.9193` |
| ❌ | warning | `price_quotation_value_band_conflicts` | code-6 price quotations should be reviewed when estimate is >= EUR 10,000 | `7` |
| ❌ | warning | `buyer_name_id_collisions` | normalized buyer names should map to one source ID (diagnostic; no auto-merge) | `{'normalized_names_with_multiple_ids': 2, 'affected_source_ids': 4}` |
| ✅ | warning | `no_future_release` | no release_date is more than 30 days into the future | `0` |
