> **SUPERSEDED HISTORICAL OUTPUT — DO NOT CITE.** Counts below predate award
> deduplication, source-aware procedure taxonomy, identity-coverage reporting,
> and the immutable base/scored gold split. Canonical current evidence is in
> `silver_tenders.dq.md`, `silver_awards.dq.md`,
> `gold_tender_summary.dq.md`, and `docs/findings.md`.

# Silver-Layer Data-Quality Report

Findings extracted from `data/silver/tenders.parquet` and `data/silver/awards.parquet`. All results are deterministic and reproducible by running `build_silver.py` then `dq_silver.py`.

## Volumes

- Tenders: **75,710**
- Awards:  **65,721**
- Tenders with ≥1 award: **54,133** (71.5%)
- Tenders with `end_before_start` bug: **17,345** (22.9%)
- Total awarded value (EUR): **4.98 B**
- Procuring entities (by id): **205**
- Unique suppliers — by business id: **4,582**
- Unique suppliers — by name: **9,427**

## Supplier entity resolution

Of the 4,582 distinct business IDs, **1 (0.0%)** appear under ≥2 different name spellings. Silver must canonicalise supplier names by `supplier_business_id`.

Top 10 suppliers by name-variant count:

|   supplier_business_id |   distinct_names |   tenders_won |   total_awarded_eur | sample_names                                   |
|-----------------------:|-----------------:|--------------:|--------------------:|:-----------------------------------------------|
|              600613419 |                2 |            15 |     11698.8         | Kadrije Spanca B.I. | N.T.SH."KOA-SOLUTION"    |
|              810828270 |                1 |           106 |         9.22957e+07 | "MEDITECH" SH.P.K.                             |
|              810527195 |                1 |            95 |         6.70258e+07 | Petrol Company - SH.P.K.                       |
|              811560293 |                1 |           369 |         4.11287e+07 | MADEKOS SH.P.K.                                |
|              600117990 |                1 |            54 |         3.67841e+07 | ,,Santefarm" Sh.p.k.                           |
|              600026555 |                1 |            26 |         3.59231e+07 | ,,Lika Trade" Sh.p.k.                          |
|              810839251 |                1 |            51 |         3.5747e+07  | BM Group SH.P.K.                               |
|           84214771175  |                1 |             8 |         3.41171e+07 | Ericsson Nikola Tesla d.d.                     |
|              810652942 |                1 |            81 |         3.0696e+07  | K.N.P.SH.  PAPENBURG & ADRIANI COMPANY SH.P.K. |
|              811302281 |                1 |            51 |         2.43654e+07 | NPN EUROING SH.P.K.                            |

## Market concentration

- Herfindahl–Hirschman index: **14** (unconcentrated)
- Top 10 suppliers capture: **8.5%** of total awarded value
- Top 50 suppliers capture: **19.7%** of total awarded value

## Award value ratio (awarded / estimated)

| metric   |   value_ratio_stats |
|:---------|--------------------:|
| count    |           65720     |
| mean     |               0.738 |
| std      |               5.466 |
| min      |               0     |
| 1%       |               0     |
| 5%       |               0.014 |
| 25%      |               0.468 |
| 50%      |               0.864 |
| 75%      |               0.99  |
| 95%      |               1     |
| 99%      |               1.183 |
| max      |             990.302 |

- Awards within ±5 % of estimate: **36.4%**
- Awards over estimate: **2.7%**
- Awards at < 50 % of estimate: **26.3%**

## Award timing (days from tender end to award date)

|       |   days_to_award |
|:------|----------------:|
| count |        55631    |
| mean  |           42.54 |
| std   |           53.11 |
| min   |         -287.43 |
| 5%    |            1.6  |
| 25%   |           14.51 |
| 50%   |           28.48 |
| 75%   |           51.48 |
| 95%   |          131.44 |
| max   |         1875.57 |

- Awards issued BEFORE tender end: **19** (impossible unless dates are shifted in the source)

## Risk profile by procurement method

| method    |   tenders |   awarded |   single_bidder |   zero_bidder |   end_before_start |   median_value |   total_value_eur |   awarded_pct |   single_bidder_pct |   zero_bidder_pct |   end_before_start_pct |
|:----------|----------:|----------:|----------------:|--------------:|-------------------:|---------------:|------------------:|--------------:|--------------------:|------------------:|-----------------------:|
| open      |     58323 |     37214 |           13671 |          6093 |                 13 |        26400   |       9.76992e+09 |         63.81 |               23.44 |             10.45 |                   0.02 |
| minimum   |     12238 |     12200 |            9451 |             1 |              12234 |          980   |       2.25185e+07 |         99.69 |               77.23 |              0.01 |                  99.97 |
| limited   |      4611 |      4187 |            3940 |            12 |               4569 |        19979.4 |       6.49829e+08 |         90.8  |               85.45 |              0.26 |                  99.09 |
| selective |         6 |         5 |               0 |             0 |                  0 |       510000   |       2.44091e+07 |         83.33 |                0    |              0    |                   0    |

## Risk profile by procurement category

| category   |   tenders |   awarded |   single_bidder |   zero_bidder |   end_before_start |   median_value |   total_value_eur |   awarded_pct |   single_bidder_pct |   zero_bidder_pct |   end_before_start_pct |
|:-----------|----------:|----------:|----------------:|--------------:|-------------------:|---------------:|------------------:|--------------:|--------------------:|------------------:|-----------------------:|
| goods      |     37819 |     27014 |           13528 |          3069 |               9405 |           9990 |       3.32998e+09 |         71.43 |               35.77 |              8.11 |                  24.87 |
| services   |     20910 |     13718 |            9094 |          2131 |               5109 |          10500 |       2.17194e+09 |         65.6  |               43.49 |             10.19 |                  24.43 |
| works      |     16981 |     13401 |            4511 |           907 |               2831 |          60000 |       4.98904e+09 |         78.92 |               26.56 |              5.34 |                  16.67 |

## Procuring-entity normalisation collisions

Same normalised name used with different `procuring_entity_id`: **2 collision groups**.

| norm                                                             |   distinct_ids |
|:-----------------------------------------------------------------|---------------:|
| agjencia per menaxhimin e komplekseve memoriale te kosoves amkmk |              2 |
| stacioni i autobuseve                                            |              2 |

## Value outliers (Tukey log-IQR)

- High outliers (log10 value > Q3 + 1.5·IQR): **240** (0.32%)
- Low outliers  (log10 value < Q1 − 1.5·IQR): **2** (0.00%)

## Monthly coverage (sample)

| release_date              |   tenders |   value_mn |   median_value_eur |   roll12_median |   delta_vs_roll12_pct |
|:--------------------------|----------:|-----------:|-------------------:|----------------:|----------------------:|
| 2024-10-31 00:00:00+00:00 |      1001 |      132.1 |              14550 |           959.5 |                   4.3 |
| 2024-11-30 00:00:00+00:00 |       820 |      196.2 |               9000 |           930.5 |                 -11.9 |
| 2024-12-31 00:00:00+00:00 |       897 |      276.1 |               4990 |           930.5 |                  -3.6 |
| 2025-01-31 00:00:00+00:00 |       307 |       22.1 |               8000 |           930.5 |                 -67   |
| 2025-02-28 00:00:00+00:00 |       618 |       91.2 |              12450 |           930.5 |                 -33.6 |
| 2025-03-31 00:00:00+00:00 |       984 |      181.7 |              18605 |           930.5 |                   5.7 |
| 2025-04-30 00:00:00+00:00 |       873 |      188.6 |              17100 |           905.5 |                  -3.6 |
| 2025-05-31 00:00:00+00:00 |       853 |      196.4 |              20000 |           885   |                  -3.6 |
| 2025-06-30 00:00:00+00:00 |       852 |      188.6 |              20000 |           871.5 |                  -2.2 |
| 2025-07-31 00:00:00+00:00 |       937 |      118.6 |              18000 |           871.5 |                   7.5 |
| 2025-08-31 00:00:00+00:00 |       703 |      105.8 |              18501 |           863   |                 -18.5 |
| 2025-09-30 00:00:00+00:00 |       761 |      133.2 |              13500 |           852.5 |                 -10.7 |
| 2025-10-31 00:00:00+00:00 |       806 |       84.8 |               9985 |           836   |                  -3.6 |
| 2025-11-30 00:00:00+00:00 |       707 |       71.4 |               8500 |           829   |                 -14.7 |
| 2025-12-31 00:00:00+00:00 |       655 |       75.2 |               9100 |           783.5 |                 -16.4 |
| 2026-01-31 00:00:00+00:00 |       228 |       11.3 |               9400 |           783.5 |                 -70.9 |
| 2026-02-28 00:00:00+00:00 |       284 |        8.9 |               3000 |           783.5 |                 -63.8 |
| 2026-03-31 00:00:00+00:00 |        63 |        1.5 |                999 |           734   |                 -91.4 |

## Silver → gold transformation checklist

1. `end_before_start` rows: keep in silver but expose `duration_computed_days` and a `date_quality_flag`. Gold aggregates should exclude them from duration stats.
2. Supplier canonicalisation: `supplier_key = supplier_business_id` when present, else `lower(_norm(supplier_name))`. Emit `supplier_name_variants` array.
3. Procuring entity: primary key is `procuring_entity_id`; name collisions should be surfaced to the oversight body, not auto-merged.
4. Tender-level gold table: one row per ocid, with derived columns `total_awarded_eur`, `awarded_value_ratio`, `num_awards`, `days_to_first_award`, `winner_concentration` (HHI within the tender's lots).
5. Incremental loads: partition bronze/silver by `release_date.year`.
