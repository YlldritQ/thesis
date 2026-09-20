# Thesis review — round 2

**Repository:** Kosovo public-procurement anomaly-detection thesis  
**Review date:** 2026-07-18  
**Scope:** shipped code, data, model/report artifacts, documentation, tests, and cold Streamlit behavior  
**Decision rule:** a finding appears below only if a second reviewer failed to refute it

## 1. Verdict and delta from round 1

**Round 1 was:** not defensible as-is because circular rule-faithfulness metrics were presented as evidence of anomaly detection and temporal generalization.

**Round 2 is:** **still not defensible as a validated anomaly-detection thesis.** The central circularity caveat now exists, but two new defense blockers remain:

1. The OSHP section—the claimed independent, non-circular check—does not contain a valid positive-outcome set and does not validate at tender level.
2. ULTRA_SHORT_OPEN overwhelmingly classifies a legally distinct five-day quotation procedure as an illicitly short ordinary open procedure.

Those are not cosmetic limitations. The first removes the only claimed external outcome evidence; the second corrupts a high-severity rule, its weak labels, downstream benchmark, model scores, narratives, and red traffic-light status.

The thesis can still be defended after targeted repair as:

> A static, retrospective procurement-data pipeline with a transparent but heuristic review queue and an exploratory ML ranking—not a validated fraud detector, calibrated anomaly detector, or production monitoring system.

The roundtable confirms **2 BLOCKER, 10 MAJOR, and 6 MINOR findings**. The fallback above requires removing the current OSHP validation claim, correcting the procedure taxonomy, regenerating all dependent artifacts, and narrowing the remaining claims to the shipped static snapshot.

## 2. Review protocol

The requested workflow was followed:

| Phase | Execution |
|---|---|
| 0 — fact sheet | One agent independently recomputed the shared ground truth before substantive review. |
| 1 — blind reviews | Six agents reviewed as skeptical examiner, procurement expert, senior data engineer, ML auditor, naive reader, and regression hunter. Each received the fact sheet and round-one fixed-finding inventory, but not the other reviews. |
| 2 — kill verification | Every candidate was assigned to a different reviewer with instructions to reproduce it and look first for code, tests, caveats, or data that would refute it. Refuted claims were removed or narrowed. |
| 3 — roundtable | A separate chair resolved conflicts, deduplicated survivors, calibrated severity to defense impact, and triaged the open round-one backlog. |

All quantitative results below were recomputed from the shipped Parquet files, not copied from README, findings, dashboard text, or prior reviews. The exact audited inputs were:

- data/gold/tender_summary.parquet — SHA-256 09dc547806b018e97d52a7092f8f40c39d0ce6e5622f9c3f10a12e7d36e50e73
- data/silver/awards.parquet — SHA-256 070ba2a658185c026a28edb1a58fc020e6923e75083678234ee93f79a3213f32

There is no Git metadata in the supplied directory, so the regression pass could not use commit history. It reconstructed each claimed repair from THESIS_REVIEW.md, CHANGELOG.md, current code, current artifacts, and executable behavior. CHANGELOG.md has no dated 2026-07-13/14 remediation section; its identifiable adversarial-fix block is CHANGELOG.md:34-53.

The full test run can overwrite canonical DQ evidence. The fact-sheet agent therefore backed up and restored those files byte-for-byte after the run. Generated lock/package metadata created by the test environment was removed before handoff; no thesis source file was modified during this review.

## 3. Phase-0 fact sheet

### 3.1 Shipped population

| Measure | Live recomputation |
|---|---:|
| Unique tenders | 75,710 |
| Post-dedup award rows | 62,128 |
| Tenders with at least one award | 54,133 |
| Estimated value | €10,490,954,921.11 |
| Awarded value | €4,765,536,984.67 |
| Distinct populated months | 118 of the stated 121-month span |

### 3.2 Single-bidder rate by procedure type

The denominator here is all tender-summary rows unless stated otherwise.

| Procedure value in shipped gold | Single-bidder tenders | Tenders | Rate |
|---|---:|---:|---:|
| All procedures | 27,133 | 75,710 | 35.8381% |
| open | 13,671 | 58,323 | 23.4402% |
| minimum | 9,451 | 12,238 | 77.2267% |
| limited | 3,940 | 4,611 | 85.4478% |
| null method | 71 | 532 | 13.3459% |
| selective | 0 | 6 | 0.0000% |

For comparison with awarded-contract statistics, the awarded-only open rate is 23.9695%. That still does not create an EU-comparable denominator; finding M2 separates standard open procedures from low-value quotations.

### 3.3 Executable status

| Check | Result |
|---|---|
| pytest | 111 passed, 26 warnings |
| ruff | Clean |
| Streamlit scripts | Home plus 8 pages; 9/9 AppTest runs served |
| Cold browser | App opened without console errors; headline, anomaly, methodology, validation, model-comparison, and glossary claims were read as rendered |
| ML feature count | 21 in code and artifact, not 20; src/thesis/domain/features.py:183-206 and data/models/validation_report.json:2-25 |

Passing tests do not refute M5: the full suite passes while writing the E2E fixture into the canonical data/dq directory.

### 3.4 Stored OSHP result

The model artifact data/models/validation_report.json does **not** contain the OSHP result. The external calculation is stored separately at data/external/oshp_validation.json and loaded by reporting at src/thesis/reporting.py:33-41.

| Stored OSHP statistic | Live recomputation |
|---|---:|
| Distinct listed operators | 109 |
| Name-matched operators | 73 |
| Historical tenders won by matched suppliers | 4,578 |
| Rule-flag rate in matched history | 621/4,578 = 13.5649% |
| Rule-flag population rate | 15,766/75,710 = 20.8242% |
| Stored rule lift | 0.65× |
| Single-bidder rate in matched history | 1,090/4,578 = 23.8095% |
| Single-bidder population rate | 27,133/75,710 = 35.8381% |
| Stored single-bidder lift | 0.66× |
| High-confidence rate in matched history | 213/4,578 = 4.6527% |
| High-confidence population rate | 2,378/75,710 = 3.1409% |
| Stored high-confidence lift | 1.48× |
| Stored mean-rule / mean-ensemble lift | 0.83× / 0.93× |

The arithmetic reproduces. The interpretation does not: B1 shows that the source rows are not an approved-disqualification label set and that the code expands supplier names to unrelated historical tenders.

### 3.5 Current rule-versus-ensemble confusion

At the shipped 0.5 thresholds for both scores:

| | Ensemble positive | Ensemble negative | Total |
|---|---:|---:|---:|
| Rule positive | 10,547 | 5,219 | 15,766 |
| Rule negative | 22,480 | 37,464 | 59,944 |
| Total | 33,027 | 42,683 | 75,710 |

Therefore 33.1029% of rule positives are demoted and 68.0655% of ensemble positives are ML-only. The requested audit premise of 40.6% and 72.5% is not reproducible and is recorded as refuted in §7.

### 3.6 Round-one findings withheld from rediscovery

The Phase-1 agents were explicitly told not to re-report the following unless the repair was partial, had regressed, or introduced a new defect: circular rule-label metrics; pooled single-bidder headline; stale award/value/rule counts; missing all-page caveat; arbitrary rule weights and nested flags; ratio dead-band; winner-takes-all value floor; DQ severity abort; OSHP module; structural missingness; detector rank transform; category quantiles; LOF and KNN scoring bugs; HGB parameter parity; champion-parameter validation; JSONL repair; GOLD_MONTHLY freshness anchor; invalid task selection; quick-mode outputs; temporal 118/121 correction; HHI market definition; frozen reference scores; lot-level ratio; contract splitting; and buyer-supplier concentration.

The status of every claimed repair is in §8.

### 3.7 End-to-end attacks that held

These checks record attempted breakage that did not become a finding:

| Attempt | Recomputed result and code evidence |
|---|---|
| Corrupt or partial bronze extraction | The gzip inflation and shipped JSONL are byte-identical: 206,559,018 bytes, SHA-256 666d239260114464142db43dfb1b85ed5b9cb508406461321859f7b1037122d4. All 75,710 lines parse; malformed JSON, null OCIDs, and duplicate OCIDs are all zero. The downloader/extractor uses temporary replacement and complete streaming; src/thesis/pipeline/bronze.py:24-36,95-105; src/thesis/pipeline/silver.py:148-160. |
| Silent tender loss | Raw 75,710 → silver 75,710 → gold 75,710; each layer has 75,710 unique, non-null OCIDs, and silver↔gold set differences are 0/0. One-row-per-release extraction and uniqueness contracts are at src/thesis/pipeline/silver.py:70-105,158-160; src/thesis/domain/schemas.py:18-23; src/thesis/dq/suites.py:28-48. |
| Award dedup over/under-count | 65,721 raw award objects − 3,593 republications across 449 tenders = 62,128 silver rows exactly. Source awards without suppliers, exact duplicate silver rows, and duplicates on OCID/lot/value/supplier are all zero. Signature and tests: src/thesis/pipeline/silver.py:30-54,152-159; tests/unit/test_award_dedup_and_consortium.py:38-76. This does not refute the need for a lot-level ratio rebuild. |
| Broken silver enrichment join | The left join retains all 62,128 award rows; orphan OCIDs are zero, and category, method, estimate, entity ID/name, and bidder-count mismatches are zero; src/thesis/pipeline/silver.py:176-185. |
| Broken gold award aggregation | There are 54,133 awarded OCIDs; mismatches in award count, awarded total, and first-award date are zero. All 21,577 non-awarded tenders remain. Silver and gold awarded totals match exactly at €4,765,536,984.67; src/thesis/domain/features.py:55-72,94-113. |
| Currency conversion distortion | All 75,710 tender currencies and all 62,128 award currencies are EUR; missing and non-EUR values are zero. Extraction carries source amount/currency without hidden conversion and DQ checks the EUR assumption; src/thesis/pipeline/silver.py:91-92,124-125; src/thesis/dq/suites.py:58-75. |
| Rule/ML-stage tender loss | Index-aligned feature/rule construction retains all 75,710 source OCIDs with no duplicates; src/thesis/pipeline/gold.py:131-151; tests/integration/test_pipeline_e2e.py:74-104. |
| DQ ERROR predicate/gate absent | The framework correctly records predicate exceptions and distinguishes WARNING from ERROR; silver and ML raise on ERROR. The surviving M5 defect is publication order, not absent severity logic; src/thesis/dq/framework.py:120-165; tests/unit/test_dq_framework.py:46-86; src/thesis/pipeline/silver.py:223-238; src/thesis/pipeline/ml.py:311-319. |

## 4. Confirmed findings — BLOCKER

### B1 — The OSHP “external validation” is invalid at both the label and unit of analysis

**Status:** CONFIRMED  
**Evidence:** data/external/oshp_blacklist.json:2-10; src/thesis/external/oshp.py:46-64,90-113,126-183; src/thesis/reporting.py:260-277; streamlit_app/pages/6_Validation.py:48-63.

The local snapshot stores only operator and authority. It has no request outcome, case/activity identifier, decision date, or tender identifier, yet the validator calls all rows independently adjudicated disqualifications. A live 2026-07-18 check of the [official OSHP status table](https://oshp.rks-gov.net/en/Reports/GetComplaintByEOGroupRP) returned 125 current requests: 4 approvals and 121 refusals. The snapshot cannot tell which outcome any stored row represents.

Even a valid operator list would not validate individual tenders. Matching uses supplier identity without procurement activity, decision date, or outcome, then labels every historical tender won by a matched supplier. All 4,578 matched rows are awarded; 3,819 (83.44%) predate 2025; only 67 match the stored operator-authority pair; and the top ten suppliers contribute 59.55% of rows. The comparator includes unawarded tenders that cannot enter the matched cohort. Against awarded tenders, rule lift changes from 0.65× to 0.7408×, high-confidence lift from 1.48× to 1.440×, and mean-ensemble lift from 0.93× to 1.0372×.

The “different risk dimension” explanation at src/thesis/external/oshp.py:142-152 is post-hoc; it cannot rescue an invalid positive set. Name canonicalization is also unstable: punctuation is removed before punctuated legal suffixes at src/thesis/external/oshp.py:46-57, and reversing those operations changes matched operators from 73 to 78.

**Failure scenario:** an examiner asks, “Which exact approved OSHP decision corresponds to this tender?” The repository cannot identify one.

**Concrete fix — effort L:** remove the external-validation claim for submission, or rebuild it from approved outcomes containing case/activity ID, decision date, operator, authority, outcome, and exact tender linkage. Use eligible awarded controls, predeclare the analysis, and report supplier-clustered uncertainty.

### B2 — ULTRA_SHORT_OPEN primarily flags lawful low-value quotations as high-risk ordinary open procedures

**Status:** CONFIRMED  
**Evidence:** src/thesis/anomaly/rules.py:95-99,168-173; src/thesis/pipeline/silver.py:87-89; src/thesis/narrative.py:128-134,216-218; streamlit_app/pages/8_Fjalori.py:43-59.

Of 9,474 ULTRA_SHORT_OPEN flags, 9,431 (99.546%) have method detail “postupak bagatelne nabave - javna objava poziva”; only 43 are other open records. Kosovo’s quotation procedure permits a five-day minimum under [Regulation 001/2022, Article 51.5](https://e-prokurimi.rks-gov.net/HOME/Documents/Legislation/SecondaryLegislation/eng/A01%20Regulation%20No.001_2022%20on%20Public%20Procurement.pdf). Of the flagged quotation records, 7,009 meet that five-day minimum. The code instead applies a seven-day cutoff under an EU ordinary-open 35-day rationale, and the narrative says a short window may be tailored for a predetermined winner.

Any severity-3 flag is sufficient for red at src/thesis/narrative.py:212-218, although the glossary says red means several genuine red flags at streamlit_app/pages/8_Fjalori.py:43-51. Thus a compliant quotation can receive a high-risk label from this rule alone.

**Failure scenario:** an examiner presents a compliant five-day quotation marked red and asks which Kosovo deadline it breached.

**Concrete fix — effort M:** map source procedure subtypes before rule evaluation; apply the legally correct deadline by subtype and period; exclude quotations from the ordinary-open rule; then rebuild rule flags, labels, benchmark, models, reports, narratives, and severity counts.

## 5. Confirmed findings — MAJOR

### M1 — Published supplier HHI is dominated by blank identifiers and is not a relevant-market measure

**Status:** CONFIRMED  
**Evidence:** src/thesis/reporting.py:77-88; src/thesis/pipeline/gold.py:37-80; src/thesis/domain/features.py:40-52; src/thesis/dq/suites.py:159-165; streamlit_app/pages/1_Overview.py:110-122; streamlit_app/pages/4_Entities.py:94-96.

18,274 of 62,128 award rows have blank or null supplier business IDs and carry 51.7544% of awarded value. Raw ID grouping publishes Goods/Services/Works HHIs of 586/1,444/4,067 because the blank ID becomes a fictitious mega-supplier. The repository’s existing fallback supplier key yields 151/103/57 if unidentified name:: values remain, or 127/57/32 if they are excluded. Neither sensitivity is a final market estimate; their divergence invalidates the current result. The DQ suite reports 92.67% non-null coverage, while nonblank coverage is only 43,854/62,128 = 70.59%.

**Failure scenario:** an examiner opens the “top supplier” behind a high category HHI and finds an empty string aggregating unrelated firms.

**Concrete fix — effort M:** use a documented robust supplier key; isolate unidentified awards; test and report nonblank coverage; define procurement markets more narrowly than three broad categories; regenerate every entity/category HHI output with sensitivity bounds.

### M2 — The single-bidder repair still compares incompatible populations

**Status:** CONFIRMED  
**Evidence:** src/thesis/reporting.py:66-75,168-188; docs/findings.md:14-25; streamlit_app/pages/1_Overview.py:43-50; tests/integration/test_findings_report.py:59-67.

The code’s open population mixes standard open procedures with low-value quotations. Among awarded tenders, standard open procedures are 22.0802% single-bidder and quotations are 27.6049%; combining all code-open rows gives the fact-sheet rate of 23.4402%. The [European Commission Single Market Scoreboard](https://single-market-scoreboard.ec.europa.eu/node/264_hr) defines its indicator over awarded contracts and excludes specified procedures. Its red band is above 20%, so “in line with EU norms” is unsupported even before matching year, value, and procedure exclusions. The minimum procedure is also not “single bidder by design”: operators are invited competitively, although the procedure may continue with one responsive offer.

**Failure scenario:** an examiner asks for the numerator and denominator on both sides of the Kosovo–EU comparison; the thesis cannot produce compatible populations.

**Concrete fix — effort M:** report Kosovo single-bidder rates by source subtype, award status, value band, and year; remove the EU-equivalence claim until the comparator denominator is replicated; describe the minimum procedure precisely.

### M3 — The rule score double-counts one fact and lacks threshold and weight provenance

**Status:** CONFIRMED  
**Evidence:** src/thesis/anomaly/rules.py:7-8,48-125,142-150,204-207; docs/methodology.md:104-115.

SINGLE_BIDDER_OPEN necessarily implies SINGLE_BIDDER, and both weights are added. Their combined score is 0.6. Exactly 9,659 tenders with no other condition make up 61.2647% of the 15,766-record review set. Replacing the generic flag rather than stacking it reduces that set to 6,107. The docstring’s worked statement that SINGLE_BIDDER alone is about 0.5 is false; it scores 0.25. Six of 13 rules have no reference, and the exact thresholds, weights, division by two, and review threshold have no calibrated provenance.

**Failure scenario:** an examiner asks why one observed fact is counted twice and why 0.5 is a meaningful risk cutoff; the present answer is “because of hand-selected weights.”

**Concrete fix — effort M:** make nested rules mutually exclusive or define and justify the incremental weight; publish a rule registry with source, population, legal/statistical threshold, and weight rationale; calibrate the review threshold; add pinned worked-example tests.

#### Rule-by-rule audit supporting B2 and M3

The table audits all 13 shipped rules. “Weight” is the raw weight before the division by two at src/thesis/anomaly/rules.py:204-207.

| Rule | Current threshold / weight | Citation and construct verdict | Required disposition |
|---|---|---|---|
| SINGLE_BIDDER | exactly 1 bidder; 0.5; src/thesis/anomaly/rules.py:50-54,147 | OECD citation is relevant to competition risk, but one bid measures market structure and data coverage, not corruption. | Retain as a contextual review signal; do not stack it automatically with its open subtype. |
| SINGLE_BIDDER_OPEN | single bidder and method=open; 0.7; src/thesis/anomaly/rules.py:56-62,148-150 | Fazekas citation is directionally relevant, but the source method mapping includes low-value quotations. | Repair taxonomy, stratify denominators, and make the generic contribution exclusive/incremental. |
| ZERO_BIDDER | exactly 0 bidders; 0.6; src/thesis/anomaly/rules.py:64-68,151 | EBRD citation gives a risk hypothesis; zero can also be missing participation data or a procedure artifact. | Treat missingness separately and verify source-field coverage before risk use. |
| RATIO_BELOW_50 | 0.01 ≤ awarded/estimated < 0.5; 0.7; src/thesis/anomaly/rules.py:70-74,153-160 | World Bank citation does not justify the exact 0.5/0.01 thresholds; the construct mixes savings, partial/lot awards, and bad aggregation. | Rebuild at lot/contract level or disable it as a risk label. |
| RATIO_ABOVE_ESTIMATE | 1.05 ≤ ratio ≤ 4.0; 0.7; src/thesis/anomaly/rules.py:76-80,161-164 | The OECD citation is general and does not establish either cutoff; the signal mixes cost growth and estimate quality. | Retain only after lot/contract comparability and threshold sensitivity analysis. |
| IMPLAUSIBLE_ESTIMATE | ratio > 4.0; 0.6; src/thesis/anomaly/rules.py:82-88,164 | The citation supports estimate manipulation as a possibility, not the exact 4× boundary; data error is an explicit competing explanation. | Separate DQ and integrity hypotheses and validate the boundary. |
| NEGATIVE_DAYS_TO_AWARD | days_to_first_award < 0; 0.9; src/thesis/anomaly/rules.py:90-93,166 | No reference. This is primarily temporal consistency/procedure semantics, not a corruption measure. | Move to DQ unless a legally impossible sequence is established by subtype. |
| ULTRA_SHORT_OPEN | 0–6 days and method=open; 0.8; src/thesis/anomaly/rules.py:95-99,168-173 | Citation is mismatched to the quotation subtype; B2 shows the rule is overwhelmingly wrong. | Disable until subtype- and period-specific legal deadlines are implemented. |
| HIGH_VALUE_SINGLE | category top 1% and single bidder; 1.0; src/thesis/anomaly/rules.py:101-104,175-186 | No reference for the 1%, category market, or maximum weight. It compounds value rank with market structure. | Freeze a relevant peer population and calibrate both cutoff and weight. |
| END_BEFORE_START_OPEN | open and end_before_start; 0.6; src/thesis/anomaly/rules.py:106-109,188-190 | No reference. Mostly date-field semantics/DQ. | Move to DQ unless source procedure semantics establish impossibility. |
| LOT_VALUE_MISMATCH | boolean absolute mismatch; 0.4; src/thesis/anomaly/rules.py:111-114,192 | No reference and no relative materiality; N1 quantifies rounding sensitivity. | Add hybrid tolerance and keep it in DQ rather than corruption scoring. |
| WINNER_TAKES_ALL_LARGE | multiple awards, top share ≥95%, estimate ≥€100k; 0.5; src/thesis/anomaly/rules.py:116-119,194-198 | No source for 95%, €100k, or the relevant market; it is concentration/lot structure, not proof of favoritism. | Document aggregation semantics and calibrate within comparable multi-lot procedures. |
| UNAWARDED_HIGH_VALUE | category top 5% and zero awards; 0.3; src/thesis/anomaly/rules.py:121-124,200-202 | No reference. It measures status/completeness or failed procurement, not corruption. | Remove from corruption-risk language; retain only as an operational follow-up flag. |

### M4 — Scheduled ingestion freezes after the first local file

**Status:** CONFIRMED  
**Evidence:** src/thesis/pipeline/dag.py:36-46,60-64,133-145; src/thesis/pipeline/bronze.py:47-85,95-124; airflow_dags/kosovo_procurement.py:72-75.

Bronze has no DAG inputs, so an existing output is permanently considered fresh. pipeline run --force skips the DAG freshness decision but calls bronze.run without forwarding force; download and extraction then retain the existing files. Airflow likewise runs bronze without check-updates. The manual update check compares line count only, so a corrected record at unchanged cardinality is invisible.

**Failure scenario:** the source corrects a tender without changing record count; a scheduled “successful” run republishes the old snapshot indefinitely.

**Concrete fix — effort M:** make scheduled ingestion compare ETag, source checksum, or content hash; forward force explicitly through every layer; download to staging and atomically promote only a verified snapshot.

### M5 — DQ aborts after publishing rejected artifacts, while tests overwrite production DQ evidence

**Status:** CONFIRMED  
**Evidence:** src/thesis/pipeline/silver.py:215-238; src/thesis/pipeline/ml.py:284-319; src/thesis/lineage.py:173-190; src/thesis/dq/framework.py:25,77-83; tests/integration/test_pipeline_e2e.py:55-66.

Silver writes both canonical Parquets before evaluating blocking DQ. ML writes the validation report, models, feature registry, and canonical gold before gold DQ can raise. A failed job therefore leaves the rejected artifact at the path consumed by the app. Separately, the DQ output path is captured at import. The E2E test reloads paths and pipeline modules but not the DQ framework, so a passing pytest run writes its 8-tender/11-award fixture into repository data/dq. The currently shipped DQ evidence is already that synthetic-sized output.

**Failure scenario:** CI reports a passed suite or the pipeline reports a DQ failure, yet the dashboard and committed evidence point to newly overwritten, invalid, or synthetic artifacts.

**Concrete fix — effort M:** run DQ against in-memory or staged outputs and promote atomically only on pass; resolve DQ destinations at runtime; isolate all test output under a temporary root; assert tests leave repository data/dq unchanged.

### M6 — tender_summary.parquet has two incompatible writers

**Status:** CONFIRMED  
**Evidence:** src/thesis/pipeline/gold.py:120-166; src/thesis/pipeline/ml.py:113-115,302-319; src/thesis/dq/suites.py:195-209; src/thesis/cli.py:100-105.

Gold writes a 73-column rule/feature table. ML later overwrites the same path with an 86-column scored table. Running standalone pipeline gold therefore deletes every model column, although the gold DQ contract requires them. Entity/monthly and SHAP lineage can reference the pre-ML hash after the named file has been replaced.

**Failure scenario:** an analyst rebuilds only gold, opens the documented canonical table, and silently receives a different schema with all scores removed.

**Concrete fix — effort M:** publish immutable feature and scored artifacts separately, or make one stage the sole canonical publisher; atomically promote a release manifest and make all downstream lineage reference its versioned files.

### M7 — Shipped champions were selected on a different feature/label matrix and ML does not reject them

**Status:** CONFIRMED  
**Evidence:** src/thesis/anomaly/benchmark.py:169-206; data/models/benchmark/champions.json:2-4; src/thesis/pipeline/ml.py:79-88; data/models/validation_report.json:43-48.

Recomputing the implemented fingerprint over the current 75,710×21 matrix and rule_score ≥ 0.4 label gives 5132027fe251ecc5. Shipped champions record d1bedde8140c550a. Benchmark resume checks this fingerprint, but production champion loading accepts the stale bundle without comparison.

**Failure scenario:** a rule or feature repair changes the training matrix, but the pipeline silently deploys model-family choices elected on the old matrix.

**Concrete fix — effort M:** bind exact feature, label, code, and data fingerprints into the deployed bundle; fail closed on any mismatch; rerun the benchmark only after B2, M1, M3, and M8 are fixed.

### M8 — award_data_missing duplicates award status and the zero-sentinel repair distorts ML and UI semantics

**Status:** CONFIRMED  
**Evidence:** src/thesis/domain/features.py:136-153,183-206; src/thesis/anomaly/models.py:44-49; src/thesis/narrative.py:279-293; streamlit_app/pages/2_Explore.py:142-150; streamlit_app/pages/3_Anomalies.py:99-109.

For all 75,710 rows, award_data_missing equals 1 − was_awarded; both enter ML. Removing only the duplicate changes 693 of 3,786 ensemble top-5% memberships (Jaccard 0.691), so the duplicated state is material. The stronger claim that it alone created a particular top anomaly was refuted. Some zeros are valid absence counts, but winner_top_share = 0 means “undefined/no winner,” not zero concentration. The UI nevertheless renders no-award rows as genuine “contracted €0” observations.

**Failure scenario:** an unawarded tender is separated twice by the model and described to the user as a zero-value contract with zero winner concentration.

**Concrete fix — effort M:** keep one award-state feature; preserve undefined continuous values with per-field missingness; consider separate awarded/unawarded scoring regimes; branch every award narrative and metric display on was_awarded.

### M9 — The circularity reframe is contradicted at the point of use

**Status:** CONFIRMED, narrowed from the refuted claim that circularity is wholly hidden  
**Evidence:** streamlit_app/pages/7_Krahasimi_i_Modeleve.py:143-150; streamlit_app/pages/6_Validation.py:19-23,169-190; streamlit_app/pages/3_Anomalies.py:226-230; docs/adr/0005-cautious-anomaly-framing.md:28-31; src/thesis/pipeline/ml.py:150-168; docs/methodology.md:154-156; src/thesis/anomaly/explanations.py:18-45.

The core caveat exists, but the app still says proxy-label out-of-time testing “simulates real use,” low detector correlation means the ensemble “really helps,” and detector agreement reduces false positives. None follows without outcome labels. “High confidence” is actually at least three selected detectors in the current batch’s top 5% ranks; ADR/Home text says raw detector score ≥ 0.7. Raw ≥ 0.7 agreement identifies 2 tenders, while production rank voting identifies 2,378. SHAP attributes raw-feature effects on the HGB rule-proxy probability, not “which rules drove the score.”

**Failure scenario:** an examiner accepts the nearby caveat, then asks what evidence supports “helps,” “false positives,” or “real use”; no such experiment exists.

**Concrete fix — effort S:** replace those claims with “temporal rule-faithfulness,” “rank agreement,” and “raw-feature attribution”; remove benefit and false-positive language; explain exact rule contributions directly from the triggered weights.

### M10 — Frozen reference-period scoring remains unimplemented

**Status:** CONFIRMED; round-one H-4 remains open  
**Evidence:** src/thesis/domain/features.py:155-168; src/thesis/anomaly/rules.py:175-186; src/thesis/anomaly/models.py:52-58; src/thesis/pipeline/ml.py:123-160.

Peer ranks, z-scores, category quantiles, rank votes, and detector min-max calibration are recomputed on the current population or query batch. Even a persisted scorer min-max-normalizes the query batch; a singleton request necessarily receives zero. For one fixed tender, the full snapshot produced detector scores 0.000822/0.616561/0.772650/0.007964; scoring it alone produced 0/0/0/0; scoring it in a ten-row batch produced 0.200070/0.961543/0.749749/1.0.

**Failure scenario:** the same tender receives different “anomaly” scores solely because unrelated comparison rows were added or removed.

**Concrete fix — effort L:** freeze and version peer statistics, quantiles, preprocessing, fitted models, and calibration on a declared reference period; score later records without refitting or query-batch normalization.

## 6. Confirmed findings — MINOR

### N1 — Lot-value mismatch uses an absolute €1 tolerance only

**Status:** CONFIRMED  
**Evidence:** src/thesis/domain/features.py:170-175.

The rule flags 356 records; 78 differ by no more than 0.1%. A hybrid €100 and 0.1% tolerance leaves 260. **Failure scenario:** harmless rounding on a large tender is treated as a structural lot mismatch. **Concrete fix — effort S:** require both an absolute and a relative materiality breach, then document the tolerance.

### N2 — Monthly output silently drops null-date tenders

**Status:** CONFIRMED  
**Evidence:** src/thesis/pipeline/gold.py:103-117.

The tender counts in the 121-row monthly output sum to 75,679, 31 fewer than gold, omitting €3,002,101.76 estimated value, €2,443,329.37 awarded value, 17 awards, 15 single bidders, and 8 rule flags. **Failure scenario:** a reader cannot reconcile annual/monthly totals to the headline. **Concrete fix — effort S:** add an unknown-date bucket or an explicit reconciliation row and metric.

### N3 — KNN still confuses duplicate vectors with reference membership

**Status:** CONFIRMED, impact narrowed  
**Evidence:** src/thesis/anomaly/detectors.py:146-159.

Any zero-distance first neighbour is treated as proof that the query row is itself in the reference sample. Reconstruction found 115 affected raw distances, but no current top-5 membership changed and KNN is not deployed. **Failure scenario:** future champion selection or a different threshold changes because an out-of-reference duplicate skips the wrong neighbour. **Concrete fix — effort S:** track reference row membership explicitly rather than infer it from zero distance.

### N4 — The reporting drift guard does not guard the committed report or input freshness

**Status:** CONFIRMED, current OSHP staleness not alleged  
**Evidence:** src/thesis/reporting.py:1-5,33-41,52-60,133-135,149-151; tests/integration/test_findings_report.py:28-67.

The test renders a report in memory and checks selected strings; it never compares the normalized result with committed docs/findings.md. Reporting also loads OSHP JSON without a source or gold hash. Current OSHP staleness by mtime was refuted; the defect is that later staleness cannot be detected. **Failure scenario:** live gold and an old external JSON produce a plausible, passing report. **Concrete fix — effort S:** key the report to hashes of every input and compare a normalized committed render in CI.

### N5 — Cold-reader defaults and scope labels overstate coverage

**Status:** CONFIRMED  
**Evidence:** streamlit_app/_bootstrap.py:76-129; streamlit_app/Home.py:58-60; streamlit_app/pages/8_Fjalori.py:33-35.

Default filters omit 561 null-year/method rows carrying €27.052 million estimated value, while the app says it reads all Kosovo public tenders. The shipped feed has 118 populated months in the stated 121-month span. **Failure scenario:** a non-expert treats a filtered publication extract as a complete national census. **Concrete fix — effort S:** preserve explicit unknown categories in defaults and say “records in KRPP OCDS publication 115,” with date and missing-month coverage.

### N6 — Documentation generations remain mixed

**Status:** CONFIRMED  
**Evidence:** streamlit_app/Home.py:72-75; streamlit_app/pages/5_Methodology.py:69-79; docs/methodology.md:94; docs/adr/0002-multi-model-anomaly-ensemble.md:67; data/models/validation_report.json:2-25.

Home still says 11 rules and methodology/ADR say 20 features; code and the shipped validation artifact contain 13 rules and 21 features. **Failure scenario:** an examiner asks which specification is authoritative and gets different answers from the app, document, and artifact. **Concrete fix — effort S:** generate rule and feature counts and lists from one versioned registry used by code, docs, and UI.

## 7. Phase-2 refutation ledger

The following Phase-1 claims were killed or narrowed and are intentionally absent as standalone findings:

| Candidate claim | Verification result |
|---|---|
| 40.6% of rule flags are demoted and 72.5% of ensemble flags are ML-only | **REFUTED.** Current 0.5/0.5 values are 33.1029% and 68.0655%. |
| award_data_missing alone caused the top anomaly | **REFUTED.** Exact redundancy and material membership sensitivity survive; single-cause attribution does not. |
| One corrected HHI triple can replace the current result | **REFUTED.** Treatment of unidentified name:: records changes the answer; both sensitivity sets must be reported. |
| All 356 lot mismatches are rounding noise | **REFUTED.** The hybrid materiality rule leaves 260. |
| The KNN edge bug changes the deployed top 5% | **REFUTED.** It changes 115 raw distances, zero current top-5 memberships, and KNN is not a deployed champion. |
| The thesis wholly hides circularity | **REFUTED.** Explicit caveats now exist; M9 retains only contradictory point-of-use claims. |
| Current OSHP JSON is stale by file time | **REFUTED.** No current staleness is claimed; missing provenance and invalid semantics remain. |
| An awarded-only OSHP baseline reverses every direction | **REFUTED.** Rule and high-confidence directions remain below/above one; mean-ensemble lift crosses one. |
| Streamlit pages lack the anomaly-not-fraud caveat | **REFUTED.** All 9 pages render one. The test remains weak. |
| The 1.05 dead-band or €100,000 floor regressed | **REFUTED.** Both boundaries reproduce. |
| Quick mode overwrites canonical champions | **REFUTED.** Quick leaderboard and champion outputs are separate; only the checkpoint log remains shared. |
| DQ ERROR severity no longer raises | **REFUTED.** It raises; M5 is about raising after publication. |

## 8. Round-one and changelog fix verification

**Status meanings:** HOLDS = implementation and executable behavior match the claim; PARTIAL = core repair exists but is incomplete or contradicted; REGRESSED = the repair introduced or now exposes a material defect; NOT RECORDED = the claimed dated repair has no matching changelog entry.

| Round-one repair | Status | Evidence and round-two decision |
|---|---|---|
| Generated reporting CLI | **PARTIAL** | Live core arithmetic works, but cached external JSON and committed-report drift are not guarded; src/thesis/reporting.py:33-60; tests/integration/test_findings_report.py:28-67. |
| Structural all-page caveat | **HOLDS** | page_header renders it by default and 9/9 pages serve it; streamlit_app/_bootstrap.py:148-167. |
| Caveat-header test | **PARTIAL** | The assertion accepts any incidental occurrence of “anomalia,” not the actual banner; tests/test_streamlit_pages.py:35-46. |
| Rule reweights | **HOLDS, with side effect** | Current weights are active; the benchmark was not rerun for the current fingerprint; src/thesis/anomaly/rules.py:48-125; data/models/benchmark/champions.json:2-4. |
| 1.05–4.0 ratio dead-band | **HOLDS** | Boundaries reproduce; src/thesis/anomaly/rules.py:25,161-166. |
| €100,000 WINNER_TAKES_ALL_LARGE floor | **HOLDS** | All current flags meet the floor; src/thesis/anomaly/rules.py:26-28,194-198. |
| DQ ERROR abort | **PARTIAL** | ERROR raises, but only after canonical publication; src/thesis/pipeline/silver.py:215-238; src/thesis/pipeline/ml.py:302-319. |
| OSHP validation module | **REGRESSED** | Outcome semantics and unit of analysis do not survive B1; src/thesis/external/oshp.py:90-183. |
| Circularity reframe | **PARTIAL** | The model report states it, but live “real use/helps/false-positive” claims remain; data/models/validation_report.json:43-48; streamlit_app/pages/6_Validation.py:169-190. |
| Rule-only baseline and confusion matrix | **HOLDS** | Current 10,547/5,219/22,480/37,464 cells reproduce; data/models/validation_report.json:75-85. |
| Structural missingness indicator | **REGRESSED** | It is the exact complement of was_awarded and zero sentinels reach UI; src/thesis/domain/features.py:136-153,183-206. |
| Detector rank transform | **PARTIAL** | Production ranks are implemented, but ADR/Home describe raw 0.7 agreement; src/thesis/pipeline/ml.py:150-168; docs/adr/0005-cautious-anomaly-framing.md:28-31. |
| Per-category quantiles | **PARTIAL** | Category grouping is active, but reference statistics remain population-relative; src/thesis/anomaly/rules.py:175-186. |
| LOF in-sample correction | **PARTIAL** | Full-fit scores use negative_outlier_factor_; bootstrap/reference scoring retains a separate novelty path; src/thesis/anomaly/models.py:131-145; src/thesis/anomaly/benchmark.py:281-305. |
| KNN off-by-one fix | **PARTIAL** | General self-match handling works, but the duplicate-vector case in N3 remains; src/thesis/anomaly/detectors.py:146-159. |
| HGB learning-rate and training parity | **HOLDS** | Parameters propagate through classifier and validation construction; src/thesis/anomaly/benchmark.py:137-149; src/thesis/anomaly/validation.py:39-85. |
| Validation uses champion parameters | **HOLDS** | Effective champion parameters are passed; the champion bundle itself is stale; src/thesis/anomaly/validation.py:39-85; src/thesis/pipeline/ml.py:135-143. |
| JSONL tolerant read and newline repair | **HOLDS** | Resume parsing and append repair match the changelog claim; src/thesis/anomaly/benchmark.py:183-221. |
| GOLD_MONTHLY DAG freshness anchor | **HOLDS** | The prior gold/ML freshness loop is broken; the separate bronze freeze is M4; src/thesis/pipeline/dag.py:77-94. |
| Invalid pipeline --only failure | **HOLDS** | Unknown task names raise; src/thesis/pipeline/dag.py:115-126. |
| Quick-mode artifact isolation | **PARTIAL** | Quick leaderboard/champions are separate, but quick and full runs share results.jsonl; src/thesis/anomaly/benchmark.py:418-431,536-564. |
| Single-bidder by method | **PARTIAL** | Pooled reporting was split, but procedure subtype and comparator equivalence remain wrong; src/thesis/reporting.py:66-75,168-188. |
| Per-category HHI | **REGRESSED** | Blank supplier IDs corrupt the new category result; src/thesis/reporting.py:77-88; src/thesis/domain/features.py:40-52. |
| Headline and rule-count regeneration | **PARTIAL** | docs/findings.md uses the current 13-rule layer; Home still says 11; streamlit_app/Home.py:72-75. |
| Temporal 118/121 correction | **HOLDS** | The current generated report discloses the missing months; src/thesis/reporting.py:149-151. |
| Student/anomaly disclaimer | **HOLDS** | Structural caveat is present; streamlit_app/_bootstrap.py:148-167. |
| 2026-07-13/14 remediation changelog | **NOT RECORDED** | CHANGELOG.md:7-53 contains version 1.1.0 and an earlier adversarial-fix block, but no dated round-one remediation section. |

## 9. Open round-one backlog triage

| Backlog item | Decision before submission | Reason |
|---|---|---|
| Tender-level OSHP match via activity numbers | **DO, or remove the OSHP section** | Supplier-history association cannot remain the thesis’s external validation. Exact approved outcome and tender linkage are required. |
| H-3 lot-level ratio rebuild | **DO, or disable the three ratio-dependent rules** | Numerator/denominator comparability affects weighted rules and the weak label; leaving them active is not defensible. |
| H-4 frozen reference scores | **DEFER only under an explicit static-snapshot scope** | Deferral is acceptable only after removing monitoring, live scoring, temporal comparability, and production-use claims. |
| H-5 contract splitting and buyer-supplier rules | **DEFER** | Adding more uncalibrated heuristics without independent outcomes expands scope but does not repair validation. |

## 10. Prioritized top-10 action list

1. Remove the OSHP validation claim, or rebuild exact approved tender-level outcome linkage with eligible controls.
2. Correct the procedure taxonomy and disable/rebuild ULTRA_SHORT_OPEN.
3. Recompute supplier identity, nonblank-ID DQ, category/entity HHI, and relevant-market caveats.
4. Make nested single-bidder rules exclusive and document/calibrate every threshold and weight.
5. Move DQ before atomic publication and isolate test DQ output.
6. Replace the dual gold writer with one versioned release contract.
7. Implement scheduled bronze refresh using source/content hashes and atomic promotion.
8. Enforce benchmark fingerprint compatibility, then rerun benchmark and ML after upstream repairs.
9. Remove duplicate award state, represent undefined award features explicitly, and correct no-award UI semantics.
10. Replace OOT, high-confidence, diversity, SHAP, EU-comparison, and count wording from a single generated claim registry.

## 11. One-page defense preparation

### 1. What is the contribution if this does not detect corruption?

**Honest answer:** a static post-award data pipeline, a transparent but heuristic 13-rule review queue, and exploratory unsupervised rankings. It prioritizes human review; it does not estimate fraud probability.

### 2. What do AUC ≈ 1 and OOT ≈ 1 prove?

**Honest answer:** only that a classifier reconstructs a deterministic rule label from the same underlying inputs. They do not prove anomaly detection, corruption detection, or temporal generalization.

### 3. Did OSHP validate the system?

**Honest answer:** no. The current snapshot lacks outcome and case identity, and supplier-name matching is expanded to all historical wins. The section must be withdrawn or rebuilt at exact approved tender level.

### 4. What do the OSHP lifts 0.65× and 1.48× mean?

**Honest answer:** they are descriptive supplier-history associations against an ineligible all-tender comparator. Using awarded tenders changes them to 0.7408× and 1.440×. Neither is tender-level validation, and supplier clustering is unaccounted for.

### 5. Why does a lawful five-day quotation appear as high risk?

**Honest answer:** it is a procedure-taxonomy bug. The current ULTRA_SHORT_OPEN result is not defensible and all dependent outputs must be regenerated.

### 6. Is Kosovo single-bidding “in line with the EU”?

**Honest answer:** the current data do not support that equivalence. Code-open is 23.4402%; awarded standard-open is 22.0802%; awarded quotations are 27.6049%. The EU indicator uses a different denominator and exclusions.

### 7. Can the HHI findings be cited?

**Honest answer:** not currently. Blank/null supplier IDs carry 51.7544% of awarded value and distort both category and entity HHI. The three broad categories are also weak relevant-market definitions.

### 8. What does “high confidence” mean?

**Honest answer:** at least three of four selected detectors place the tender in their current-batch top 5%. It is rank agreement, not calibrated confidence and not evidence of fewer false positives.

### 9. What does SHAP explain?

**Honest answer:** raw-feature contributions to the HGB probability of the binary rule proxy. It does not identify wrongdoing and it does not directly report which rules fired; exact rule contributions can be computed without SHAP.

### 10. What evaluation would demonstrate detection, and how far away is this thesis?

**Honest answer:** use predeclared exact tender/date/operator/authority/outcome labels from approved decisions or blinded audit; construct eligible matched controls; freeze all pre-cutoff features, models, peer statistics, and calibration; split by time and by supplier/authority; compare rule-only, detector-only, and composite baselines; report precision at a review budget, PR-AUC/lift, and supplier-clustered intervals. The current project lacks both the valid outcome labels and frozen scoring protocol, so it is not one additional metric away—it needs a new evaluation dataset and protocol.

## 12. Submission decision

Do not submit the current package under the claim “validated procurement anomaly detection.” The minimum defensible submission path is to:

1. remove current OSHP validation;
2. correct ULTRA_SHORT_OPEN and regenerate every dependent artifact;
3. repair or remove HHI and incompatible EU-comparison claims;
4. state that ML is exploratory and scores are snapshot-relative; and
5. fix the publication/DQ defects that make the shipped evidence non-reproducible.

Without those changes, one precise committee question on either OSHP outcome identity or the five-day quotation rule is sufficient to invalidate the central validation story.
