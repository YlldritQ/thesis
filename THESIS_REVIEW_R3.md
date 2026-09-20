# THESIS REVIEW R3 — Independent adversarial review

> **Historical R3 baseline (superseded for current release facts).** This review
> records the independent audit and remediation completed before the XAI
> alignment extension. Its finding dispositions remain historical evidence, but
> its release ID, implementation fingerprint, scored-table shape, hashes, and
> description of the available ensemble explanation are no longer current. The
> source-matched XAI release is documented in
> [`THESIS_XAI_ALIGNMENT.md`](THESIS_XAI_ALIGNMENT.md); use that document and
> the live manifests for current technical facts.

**Project:** Kosovo public-procurement heuristic screening and exploratory anomaly ranking  
**Repository root:** `/Users/ylldrit/Desktop/thesis`  
**Review date:** 2026-07-18 to 2026-07-19  
**Review posture:** independent thesis examination, procurement/data semantics, statistical methodology, reproducibility, software quality, documentation, notebooks and dashboard  
**Final technical status:** source-matched Bronze → Silver → Gold → Benchmark → ML releases, manual-audit metadata, OSHP withdrawal status and `docs/findings.md` have been regenerated and independently hash-checked. Full pytest, Ruff, formatting, mypy, dependency, release/DQ, strict-JSON, notebook, active-surface stale-claim and patched Docker portability/health gates pass. A non-implementer final contradiction audit also passes.

> **Technical acceptance gates are closed.** The source-matched canonical release chain and all declared hashes, artifacts, DQ, quality, Docker reader/health and independent contradiction checks validate. Technical acceptance does not supply the missing human labels, external outcomes or legal/entity/lot adjudication described below.

## Executive verdict

The pre-remediation project did **not** support all claims being made. The independent pass found no fabricated human labels and no current P0 corruption, but it identified material P1 defects in procurement semantics, data meaning, release integrity and model execution. In particular:

- 291 official design contests were classified as ordinary open/restricted procedures;
- a distinct EUR 7,200 award was removed by a supplier-identity-blind deduplication key;
- published source-party supplier identities were discarded, materially changing supplier coverage and HHI sensitivity;
- 6,107 absent tenderer arrays were represented as observed zero bidders;
- award decisions and recorded award values were described as signed contracts or contracted expenditure;
- manual-audit URL coverage was overstated and force regeneration could erase future human review;
- Bronze/Silver publication, freshness, portability and DQ evidence did not provide a complete generation-level commit contract;
- benchmark evidence was not bound to exact implementation code or semantically re-elected before deployment;
- the new nullable bidder representation initially reached sklearn as literal `pd.NA`, an execution-blocking boundary defect discovered during remediation.

The actionable source and test defects have been remediated. The repaired design now preserves nullable source semantics, uses code-first procedure classification, retains source identities, publishes manifest-last release bundles with strict JSON and source/protocol fingerprints, semantically verifies benchmark elections, validates persisted model/SHAP/scored artifacts, generation-keys dashboard reads, and protects human-review fields. The final source-matched core release is `run-20260719T103232-2fe4b69e`; all five stages share global source-tree implementation fingerprint `174e632ef603039bb5877af0d3746c14d54d1415beba290b989ae0444e00b6f5`, while the benchmark's narrower relevant-source implementation fingerprint is `1ebaf58000d16685dbb51609b3ce1489b4aaf5d51d3dadb66dd83b5418647ac9`. The old canonical generation remains inadmissible and must not be cited as the R3 result.

The successful final rebuild does not broaden the defensible thesis claim:

> The project provides reproducible descriptive statistics, transparent heuristic review signals, and retrospective snapshot-relative anomaly rankings for the frozen Publication 115 snapshot. It does not detect fraud or corruption, establish illegality or causation, estimate calibrated risk or prevalence, or demonstrate precision, recall, false-positive rate, external validity, pre-award utility, temporal generalisation, or score comparability across changing populations.

There are no independent tender-level outcome labels. The supervised target is derived from the same rule score whose inputs and proxies appear in the feature matrix. Supervised AUC/PR-AUC, temporal-split metrics and proxy `precision@K` therefore measure **agreement with a rule-derived proxy**, not detection performance. SHAP attributes that rule-proxy surrogate; it does not explain fraud, legal breach or causal importance. The unsupervised ensemble is an exploratory review ordering, not a probability or validated risk scale.

The raw audit produced overlapping track records. After explicit de-duplication, remediation-time execution defects and the independent final-audit additions, this review records **50 canonical R3 findings: 14 P1, 29 P2 and 7 P3; no P0**. The cross-track duplicates C-01/C-02/C-03/C-04/C-05/C-06/C-07/C-10 are represented once under their procurement or pipeline IDs. C-08 and C-09 remain separate as R3-RISK-01 and R3-DOC-01. No prior R2 or R2.1 finding was a historical false positive and none was found to have regressed.

## Review method and independence

### Phase 1 — clean-room audit

The R3 tracks inspected source, raw and staged data, DQ evidence, release metadata, models, reports, notebooks and Streamlit surfaces before reading `THESIS_REVIEW_R2.md` or `THESIS_REVIEW_R2.1.md`. The work was split into four independent tracks:

1. procurement semantics, legal applicability, identifiers, joins, missingness, lot/tender grain and manual/external evidence;
2. model features, circularity, leakage, benchmarking, election, anomaly-score direction, stability and artifact coherence;
3. Bronze → Silver → Gold → Benchmark → ML/reporting publication, lineage, DQ, freshness, reproducibility and CI/container behaviour;
4. thesis claims, generated findings, notebooks, dashboard labels, stale outputs and cross-artifact contradictions.

The clean-room notes are `.audit_r3_procurement.md`, `.audit_r3_ml.md`, `.audit_r3_pipeline.md` and `.audit_r3_claims.md`. They preserve pre-remediation evidence. Later source dispositions are recorded in `.r3_proc_sections.md`, `.r3_ml_sections.md`, `.remediation_r3_ml.md`, `.reconcile_r2.md` and `.reconcile_r21.md`.

### Phase 2 — prior-review reconciliation

Only after the independent findings were frozen were all 18 enumerated R2 findings (B1–B2, M1–M10, N1–N6) and all 28 enumerated R2.1 findings read and checked against current source and artifacts. Contextual repair inventories and claim ledgers in the earlier documents were not double-counted as separate findings.

### Phase 3 — remediation rules

- Root causes were fixed rather than preserving previous thesis numbers.
- No human labels, external outcomes, legal conclusions or missing URLs were created or inferred.
- Existing review fields are preserved by keyed merge or the rebuild aborts.
- Empty audit strata remain empty.
- Award objects are called recorded award decisions/values, not signed or executed contracts.
- All model metrics are framed as rule-proxy agreement or rank sensitivity, never validation.
- Canonical artifacts are accepted only when their final manifest, DQ and semantic contracts validate as one generation.

## Evidence anchor and final core publication

The frozen raw JSONL contained 75,710 valid JSON objects and 75,710 unique OCIDs. Its SHA-256 was `666d239260114464142db43dfb1b85ed5b9cb508406461321859f7b1037122d4`; the gzip SHA-256 was `b782bdb3c323b3a6b9bba72c906756744700752bd9287efe55dbab4fe1f1341b`, and decompression reproduced the JSONL hash. These facts establish internal byte consistency, not historical acquisition provenance or national-census completeness.

The deterministic no-write rebuild after the procurement fixes produced the following **prepublication** frames. These are DataFrame fingerprints, not final Parquet hashes:

| Frame | Shape | Deterministic DataFrame fingerprint |
|---|---:|---|
| Silver tenders | 75,710 × 28 | `e1ea81ac5f0a1254f8cfd328f6c4550944f5632e2e1ca928b6519053541f26a5` |
| Silver awards | 62,129 × 28 | `2f39dbd63b93976c8f6097069911edab682b2ec1632ab7585d5698992995b943` |
| Gold features + rules | 75,710 × 82 | `2c58ae397acbdde2a57bed4b7195b997df5733fade45c39521d6593fd608d0dd` |
| Supplier summary | 9,940 × 23 | `ec82b37eb4eb90540c20d4f65a8021a82720eb35c99e0c021d41720eb45bcff1` |
| Entity summary | 206 × 26 | `347998d5590cb1bbf55fc224824f629fd6600785f3a8677ef0f82928e573bd31` |
| Monthly metrics | 122 × 15 | `fbd5147dfa5dfb4674084c2cb1fcaadeae2d3d71e21712b64f3dbe69d95ed36a` |

That in-memory rebuild passed full Pydantic validation for 75,710 tenders and 62,129 awards, both Pandera schemas and all then-current DQ ERROR gates. The later source-matched persisted generation reproduced the expected shapes and passed every declared release-owned DQ check.

| Stage | Manifest SHA-256 | Generation fingerprint | Core released evidence |
|---|---|---|---|
| Bronze | `b33a97e1fd15facbf8aab58629f531bcac687fe2c4e3380de77a721341613ca4` | `a44b7f9a31d9fb38736bcdd7e83584add487de4fb3e4119b9fcbc8718c2400da` | 75,710 records; raw JSONL `666d2392…7122d4`; gzip `b782bdb3…1341b` |
| Silver | `f1e150772c8572f00dada17df43de6ea817dee041c287582e859059acef2eb32` | `4f2f86eeff666dcfd4b1faa11c1b1b4a4857f901d22533e8411f5eba450fa98e` | tenders 75,710×28; awards 62,129×28 |
| Gold | `a2602b7039bf7300bb7746bc5e9821420ffdbcf1efa5fb3b2e5d49067b78aeff` | `3ef3848e17522bd5c81d32dbbf91816766e1a6c9643430c826ef4624d261f539` | features 75,710×82; suppliers 9,940×23; entities 206×26; monthly 122×15 |
| Benchmark | `676cff17b242609f4d04f465c2881f403aab9c2a4b4073005422c1f8a919b48a` | `b1007484a576bc32ee5660a5bee4e7dd94f8487758075d162527ed1d73057044` | 35×41; 35/35 unique successful full configurations; schema-2 champions; semantic DQ passed |
| ML | `77ccbcbb999710156cfb62d280ff17348434c6b4ece74a1e8bba1aa59e40db0a` | `74b1cbc8026ef9df47779949bf463d3818c2896b7aa5bec5a088fc63f46f398a` | scored Gold 75,710×95; SHAP 75,710×22; model/JSON/rescore DQ passed |

Every declared input, artifact and check hash in those manifests was independently recalculated and matched disk; every source/dependency file in the implementation manifest also matched current bytes. All five releases share configuration fingerprint `a7e3c914421adf51649fe580583749cb0ac522e301967ddab6a7aecff8a6ba0c` and runtime fingerprint `81f5e8828e90d85a27aca5a3bfa08b0c9c90071a85f88ca78261113da850f2bc`.

## Canonical independent findings

Statuses distinguish three different outcomes:

- **remediated and release-verified** — source, focused regression and the source-matched canonical generation prove the repair;
- **limitation/deferred** — no responsible code change can manufacture the missing legal, identity, temporal or outcome evidence;
- **accepted P3/cleanup** — does not block the thesis if clearly excluded from current evidence.

### Procurement, data semantics and evidence

| ID | Severity | Area | Finding | Exact evidence | Impact | Remediation | Verification | Status |
|---|---:|---|---|---|---|---|---|---|
| R3-PR-01 | P1 | Procedure semantics | Official code 3 design contests were folded into ordinary open/restricted procurement. | Raw tender-ID code cross-tab: 291 code-3 records; old counts 39,940 standard-open/39 restricted. Current code-first mapping: `src/thesis/domain/procedures.py:22,41,83`; official original Regulation 001/2022 Art. 12.13, official 002/2024 amendment and PPL Art. 73. | Wrong denominators and two false ordinary-open short-deadline diagnostics. | Added `DESIGN_CONTEST`, code-first mapping and checked text fallback. | Final Gold: 291 design contests, 39,650 standard open, 38 restricted; `ULTRA_SHORT_OPEN` 43→41; persisted Gold DQ passed. | **Remediated and release-verified.** |
| R3-PR-02 | P1 | Supplier identity / HHI | Published source-party identities were discarded when business ID and name were blank. | Corrected 62,129 awards all have source party ID; 4,551 old rows/EUR278,502,012/513 party IDs lacked business ID and name. Identity views: `src/thesis/domain/features.py:48-138`; summaries: `src/thesis/pipeline/gold.py:45-159`. | False zero supplier counts, incomplete value denominators and materially different HHI; party-ID fallback changes entity HHI by median 31.5, p95 228.6, max 1,177.8 points. | Added name/source-party and business-ID-only views, explicit unknown allocation and coverage; retained raw IDs and caveats. | Final supplier summary is 9,940×23 (`7a2811d4…f1a4`); all six persisted supplier checks passed and source/name identity covers 100% of recorded award value in this snapshot. | **Remediated and release-verified; legal-entity truth remains unavailable.** |
| R3-PR-03 | P1 | Award deduplication | Dedup used supplier name but ignored retained party identity, collapsing two distinct awards. | OCID `ocds-uhzcmx-211-23-4613-2-2-1`: two same-date EUR7,200 blank-name awards with party IDs `179852` and `179849`; fixed signature `src/thesis/pipeline/silver.py:46-85`. | One award and EUR7,200 were omitted from every downstream aggregate. | Dedup now prefers usable business ID, then party ID/UID, then name. | Final Silver has 62,129 awards (`3498ec4d…ffb9`) and recorded award value EUR4,765,544,184.67; Silver referential DQ passed. | **Remediated and release-verified.** |
| R3-PR-04 | P1 | Bidder missingness | Absent tenderer arrays were silently represented as observed zero bidders. | Raw scan: 69,603 observed tenderer arrays, 6,107 absent, no explicit observed-zero array. Nullable extraction `src/thesis/pipeline/silver.py:120-168`; feature propagation `src/thesis/domain/features.py:229-235`; DQ `src/thesis/dq/suites.py:240-249`. | False 6,107-row zero-bid narrative, wrong denominators, rules and ML boundary semantics. | Added `bidder_data_observed`; kept `num_bidders` nullable; rules require observed data. | Final Silver/Gold preserve 69,603 observed, 6,107 missing and zero observed-zero cases; `ZERO_BIDDER` is 0 and persisted DQ passes. | **Remediated and release-verified.** |
| R3-PR-05 | P1 | Manual audit URLs | Nonblank publisher placeholders were counted as usable exact document URLs. | Existing 150-row queue contained 31 `DokumentPodaciFrm.aspx?id=` empty-ID endpoints and no alternate raw URL; URL classifier `src/thesis/audit.py:65-108,322-339`. | 100% traceability claim was false; 20.67% of that queue had no usable supplied link. | Added structural URL status/reason; preserve an invalid published URL in `source_document_url` as source evidence but exclude it from the usable exact-link count. | Final 150-row queue: 124 `structurally_valid_unverified`, 26 invalid; all 150 source strings are retained. This is structural classification, not HTTP verification. | **Remediated and release-verified.** |
| R3-PR-06 | P1 | Manual audit preservation | Force regeneration could replace completed human fields with blanks. | Preservation/refusal logic `src/thesis/audit.py:269-349`; tests `tests/unit/test_audit.py:134-167`. Current queue had zero labels. | Potential irreversible destruction of human evidence. | Stable-OCID merge preserves every review field; unsafe schema, duplicate IDs or dropped reviewed OCIDs abort. | Final force regeneration preserved all zero pre-existing reviewed rows/fields and still contains zero labels; refusal/preservation regressions pass. | **Remediated and release-verified; no human review has yet occurred.** |
| R3-PR-07 | P1 | Evidence terminology | Award-stage records/values were described as signed contracts or contracted expenditure. | Raw scan found 65,721 `award` objects but zero top-level OCDS `contracts`; scoped wording now in `docs/methodology.md:21-25,41-44`, `docs/manual_audit_protocol.md:37-45`, Explore/Anomalies helpers. | Overstated legal/evidentiary status of roughly EUR4.766bn and more than 62,000 records. | Replaced user-facing wording with recorded award decision/value/supplier and disclosed absent implementation evidence. | Regenerated findings SHA `66f0534f…3c76`, active-surface stale scan and every Streamlit AppTest render/terminology assertion passed. | **Remediated and cross-surface verified.** |
| R3-PR-08 | P2 | Procedure/value applicability | Seven code-6 price quotations have estimates at or above EUR10,000; the snapshot cannot determine legality. | Seven OCIDs enumerated in `.r3_proc_sections.md`; PPL Art. 19; official Regulation 001/2022 Arts. 51.3/51.5; zero-weight rule `src/thesis/anomaly/rules.py:158-176,276-278`. | Previously invisible source/legal-semantic conflict; a legality claim would exceed evidence. | Added zero-weight `PRICE_QUOTATION_VALUE_BAND_CONFLICT` and DQ warning with period/document caveats. | Final release has seven firings; all 11,840 minimum-value procedures remain below EUR1,000; Silver DQ reports the warning. | **Safeguard complete; legal judgment deferred to original documents/historical law.** |
| R3-PR-09 | P2 | Buyer identity | Two normalised buyer names map to four source IDs across 550 tenders. | AMKMK IDs `111560/176875`; Stacioni autobusëve `115429/180109`; `BUYER_NAME_ID_COLLISION` in `src/thesis/anomaly/rules.py:177-187,279-280`; one tender lacks buyer identity. | Source may split one entity or names may collide; automatic merge could corrupt data. | Preserve source IDs; expose a zero-weight collision diagnostic; prohibit automatic merge. | Final release and Silver DQ report two collision groups/four IDs/550 rows. | **Safeguard complete; entity-history judgment deferred.** |
| R3-PR-10 | P2 | Identifier hygiene | Sentinel business IDs (`N/A`, `/`, `000000000`) were treated as real identifiers. | Old counts: 14, 1 and 1 award rows respectively; normalization `src/thesis/domain/features.py:48-78`. | Coverage was overstated and unrelated suppliers could merge. | Normalize known sentinels to null for identity keys while retaining raw source values. | Final supplier/entity summaries and persisted source-reconciliation DQ pass. | **Remediated and release-verified.** |
| R3-PR-11 | P2 | Award/lot grain | Awards expose free-text `lotTitle`, not a stable shared lot ID; exact matching is incomplete/ambiguous. | Exact status `src/thesis/pipeline/silver.py:41-42,101-117`; final release 61,260 unique, 244 ambiguous, 505 unmatched, 120 missing; 6,130 multi-lot tenders, 164 duplicate titles, 260 material mismatches. | Lot-level allocation and one-award-per-lot claims cannot be verified. | Preserve exact status; no fuzzy join; keep winner share and award/estimate ratios explicitly tender-level. | Final award DQ records the linkage warning; current raw awards each have one supplier. | **Diagnostic complete; stable lot linkage unavailable.** |
| R3-PR-12 | P2 | External validation | Cached OSHP data cannot be linked to individual tenders/outcomes; aggregate name overlap is not validation. | `src/thesis/external/oshp.py:1-14,86-121`; 126 cached rows contain authority/operator names but no sufficient tender ID or adjudicated outcome. | No external precision, recall, FPR, lift or validated-risk claim is supported. | Withdrew every metric and requires primary acquisition provenance plus exact case/tender/outcome linkage for future work. | Current status artifact is withdrawn and computes no metrics. | **Correctly withdrawn; external evidence unavailable.** |
| R3-PR-13 | P2 | Audit provenance | Audit metadata did not bind the emitted sample/label state and completion status could become stale. | State/sample hashing `src/thesis/audit.py:111-152,340-349`. | Human-review evidence could change without an auditable state transition. | Added sample, definition and label-state hashes; completion definition/status; thresholds, population, seed and preservation counts. | Final hashes: sample `5f355938…9120`, definition `b7daa09c…baa1f`, label state `662e9fba…403`; status `awaiting_human_review`, 0/150 complete. | **Remediated and release-verified.** |
| R3-PR-14 | P2 | Rule applicability | `WINNER_TAKES_ALL_LARGE` described multi-lot applicability without requiring `num_lots>1`. | Predicate `src/thesis/anomaly/rules.py:299-305`; boundary regressions `tests/unit/test_features_and_rules.py:445-468`. | Future single-lot tenders could be mislabeled relative to the documented rationale. | Added explicit multi-lot predicate. | Final Gold count is 426 and persisted feature DQ passes. | **Remediated and release-verified.** |
| R3-PR-15 | P2 | Audit nullable hashing | The first post-run audit regeneration failed before publication because stable sample hashing attempted `fillna("")` on nullable `Int64` bidder counts. | `thesis report audit-sample --force` left both audit files at their prior mtimes; pandas raised an invalid empty-string value for `Int64`. Fix: `src/thesis/audit.py:111-121`; regression `tests/unit/test_audit.py:58-70`. | Required manual-audit metadata could not be regenerated from the corrected nullable-bidder generation. Atomic writers preserved the old files, so no labels or evidence were lost. | Convert the selected hash projection to pandas `string` before filling nulls, then sort and hash stable CSV bytes. | Complete source-matched rerun `run-20260719T103232-2fe4b69e` and audit regeneration succeeded; implementation fingerprint `174e632e…6f5`; final sample/metadata hashes independently matched disk. | **Remediated and release-verified.** |
| R3-PR-16 | P2 | Legal-source provenance | The draft called the PPRC-hosted consolidated Albanian Regulation 001/2022+002/2024 an “official PDF,” although its cover says the consolidation is not official and was prepared for internal convenience. | Consolidation cover disclaimer; PPRC official secondary-legislation page separately lists original Regulation 001/2022 and amending Regulation 002/2024 as official acts. | Misstated authority status weakened an otherwise correct procedure/legal evidence chain. It does not change the procedure counts. | Relabel the consolidation as non-official convenience text and anchor code/value claims to the official original Regulation 001/2022, official 002/2024 amendment listing/document and PPL. | Official PPRC page and primary documents rechecked; source list below corrected. | **Documentation defect remediated and verified; substantive result unchanged.** |
| R3-PR-17 | P3 | Audit metadata portability | Manual-audit metadata stores absolute host paths in `source_artifact` and `document_source_artifact`. | `src/thesis/audit.py:250-253`; final metadata also carries portable content/state hashes. | Cosmetic/operational path drift after relocation; integrity remains verifiable by hashes and this path is not a release integrity key. | Future metadata should store data-root-relative logical paths plus optional operational path, without changing existing evidence. | Documented as non-blocking future cleanup; changing audit source now would unnecessarily invalidate the current source fingerprint. | **Accepted P3 portability cleanup; non-blocking.** |

### ML, statistics and benchmark integrity

| ID | Severity | Area | Finding | Exact evidence | Impact | Remediation | Verification | Status |
|---|---:|---|---|---|---|---|---|---|
| ML-R3-01 | P1 | External validity | No independent tender-level ground truth exists; all supervised and proxy benchmark metrics use rule-derived labels. | Target construction `src/thesis/anomaly/models.py:322-323`; benchmark proxy `src/thesis/anomaly/benchmark.py:805-806`; circularity warning/note `src/thesis/pipeline/ml.py:585-607`. | Fraud/corruption detection, calibrated risk, precision, recall, FPR and outcome AUC claims are unsupported. | No labels were fabricated; docs/UI/artifacts explicitly call metrics rule-proxy faithfulness and rankings exploratory. | Static claim/dashboard tests pass; outcome validity cannot be tested without real labels. | **Evidence limitation; framing fixed, validation unavailable.** |
| ML-R3-02 | P1 | Leakage / temporal validity | The 20-feature matrix contains award-stage facts, deterministic derivatives and full-snapshot peer transforms. | Registry `src/thesis/domain/features.py:300-322`; declared ablations `src/thesis/pipeline/ml.py:92-123`; old generation had 33,116 rows with at least one missing ML feature. | It cannot support pre-award monitoring or genuine forward/temporal generalisation; a date split still uses retrospective features and the same circular proxy. | Added raw-fact and pre-outcome-field snapshot refit ablations using only Spearman/top-5% overlap; retained explicit static-snapshot caveat. | Final raw-only sensitivity: Spearman 0.9050, top-5% Jaccard 0.7166; pre-outcome-field snapshot: 0.8136 and 0.5211. These are rank dependence, not validation. | **Sensitivity release-verified; real temporal validation unavailable.** |
| ML-R3-03 | P2 | Reproducibility | Benchmark rows/checkpoints were not bound to exact benchmark/detector/model/feature source. | Implementation manifest/provenance `src/thesis/anomaly/benchmark.py:162-212,423-440`; protocol `2026-07-r6-implementation-bound-semantic-election`. | Source changes could reuse numerically stale rows if a protocol constant was not manually changed. | Hash relevant files into protocol/data fingerprints and every row. | Final 35-row release binds data `e4e6cef88490834a`, protocol `7d5b8a909f00e6d8` and benchmark implementation `1ebaf580…7ac9`; all manifest files match current bytes. | **Remediated and release-verified.** |
| ML-R3-04 | P2 | Champion integrity | ML accepted structurally valid champions without independently proving they were the deterministic winners/top-K from released rows. | Re-election `src/thesis/anomaly/benchmark.py:1112-1175,1208-1316`; ML comparison `src/thesis/pipeline/ml.py:187-321`. | A tampered winner bundle could deploy arbitrary configurations. | Release results+leaderboard+champions+semantic DQ atomically; ML re-elects and rejects any mismatch. | Schema-2 semantic fingerprint `e034c3f0…cfd81`; released and independently re-elected ensemble both `ocsvm, iso, hbos, knn`; benchmark and ML DQ pass. | **Remediated and release-verified.** |
| ML-R3-05 | P2 | Statistical robustness | Election stability uses four bootstrap refits and two extra stochastic seeds, too few for uncertainty or superiority claims. | Defaults `src/thesis/config.py:71-78`; limited-replication note `src/thesis/pipeline/ml.py:602-607`; dashboard disclosure page 7. | Champion order may depend on a coarse repeatability estimate. | Kept declared repeats, added limited-replication warning and election/rank sensitivities; did not invent confidence intervals. | Final balanced election preserves the selected top four (Jaccard 1.0); stability/proxy emphasis replaces KNN with GMM (0.6); proxy-precision-only ranking has Jaccard 0.1429 and three rank conflicts. | **Diagnostic release-verified; stronger inference unsupported.** |
| ML-R3-06 | P2 | Feature geometry | Competition, award state, value and missingness appear through overlapping raw facts, flags, ratios, ranks and indicators without outcome-based weighting. | Registry `src/thesis/domain/features.py:300-322`; imputation indicators; ablation implementation `src/thesis/anomaly/validation.py:295-370`. | Related constructs may receive disproportionate geometric influence; the surrogate is circular. | Added declared deployed-family refit ablations, rank/top-set comparisons only. | `tests/unit/test_validation_sensitivity.py:38-78`. | **Partially remediated sensitivity limitation; no externally justified representation exists.** |
| ML-R3-07 | P2 | Election objective | The composite omitted its own proxy `precision@K` and exposed no alternate-weight sensitivity. | Declared/alternate weights `src/thesis/anomaly/benchmark.py:178-202`; sensitivity `:1052-1109`. | “Champion” could sound objective despite author-selected weights and top-K conflicts. | Added balanced, stability- and proxy-emphasis scenarios plus proxy-`precision@K` family ranking, labelled rank sensitivity. | Final sensitivity is populated: balanced Jaccard 1.0; stability/proxy emphasis 0.6; proxy-precision-only 0.1429 with three rank conflicts. | **Diagnostic remediation release-verified.** |
| ML-R3-08 | P3 | PCA reproducibility | PCA was marked deterministic although `svd_solver="auto"` can select randomized SVD. | Registry now marks PCA stochastic `src/thesis/anomaly/detectors.py:233-236`; old practical effect was tiny and PCA was not deployed. | It received a perfect seed-consistency value without a seed perturbation. | Classify PCA stochastic for election diagnostics. | Final 35-row benchmark regenerated under the corrected registry and semantic DQ passed. | **Remediated and release-verified.** |
| ML-R3-09 | P3 | HBOS boundary | HBOS clipped out-of-support values into edge bins. | Tail handling `src/thesis/anomaly/detectors.py:189-214`; clean-room toy case showed x=1 and x=100 scored identically after fit on [0,1]. | Extreme unseen values could appear ordinary at the edge. | Assign explicit epsilon tail mass outside fitted support. | Boundary regression passes and final benchmark/ML artifacts were regenerated; HBOS remains one of the semantically elected four families. | **Remediated and release-verified.** |
| ML-R3-10 | P2 | Atomic benchmark publication | Long full sweeps used canonical evidence as mutable resume state. | Separate quick/WIP/canonical paths and fsync/replace `src/thesis/anomaly/benchmark.py:444-471`; semantic precheck before publication `:1385-1395`. | A partial sweep could invalidate the still-current release before a complete replacement existed. | `results.quick.jsonl`, `results.wip.jsonl`, and atomic canonical `results.jsonl` have separate roles. | Canonical `results.jsonl` contains exactly 35/35 successful unique full configurations, zero failed/extra/duplicate/stale rows, and is release-bound at SHA `ae47e890…5b24`. | **Remediated and release-verified.** |
| ML-R3-11 | P2 | JSON evidence | Checkpoint JSON could stringify unsupported values, emit non-standard numbers or skip corrupt rows. | Strict converter/parser `src/thesis/jsonutil.py:17-114`; fail-closed checkpoint read `src/thesis/anomaly/benchmark.py:474-493`; bundle read `src/thesis/pipeline/ml.py:154-176`. | Evidence types/rows could silently change while a run appeared complete. | Explicit NumPy/pandas/date/null conversion, `allow_nan=False`, duplicate-key and corrupt-line rejection. | Strict JSON tests pass; canonical benchmark and ML JSON artifacts reload and all release-owned semantic/JSON checks pass. | **Remediated and release-verified.** |
| ML-R3-12 | P2 | Release/DQ binding | Benchmark/ML did not prove upstream manifest stability through publication, and auxiliary ML artifacts lacked persisted semantic gates. | Gold SHA forwarding `src/thesis/pipeline/benchmark.py:28-46`; benchmark DQ/release `src/thesis/anomaly/benchmark.py:1407-1456`; ML captures/enforces both manifests `src/thesis/pipeline/ml.py:350-367,677-744`; persisted SHAP/model/JSON validation `src/thesis/anomaly/artifact_integrity.py`. | Concurrent swaps or tampered model/SHAP/JSON artifacts could produce a mixed yet superficially valid generation. | One-generation reads, before/after manifest checks, persisted scored and SHAP DQ, strict JSON/joblib reload and all-detector/HGB rescoring. | Final Benchmark and ML manifests, all declared hashes, semantic re-election, model reload/rescore and 75,710-row SHAP/scored parity validate. | **Remediated and release-verified.** |

### Pipeline, lineage, reproducibility and software quality

| ID | Severity | Area | Finding | Exact evidence | Impact | Remediation | Verification | Status |
|---|---:|---|---|---|---|---|---|---|
| PIPE-R3-01 | P1 | Bronze/Silver publication | Bronze and Silver previously lacked bundle-level commit manifests and readers consumed bare files. | Current canonical contracts `src/thesis/release.py:72-145`; Bronze/Silver paths `src/thesis/paths.py:28-39`; publishers `src/thesis/pipeline/bronze.py:130-138` and `silver.py:369-380`; DAG outputs `src/thesis/pipeline/dag.py:108-124`. | Sequential file swaps could expose a mixed pair after crash/concurrency. | Added manifest-last Bronze/Silver releases, bound sidecars/DQ and release-validated readers. | Final Bronze manifest `b33a97e1…3ca4` and Silver manifest `f1e15077…eb32` validate every declared artifact/check/input hash and shared release ID. | **Remediated and release-verified.** |
| PIPE-R3-02 | P1 | Freshness/invalidation | DAG freshness previously used mtimes and did not bind current source/config/runtime. | Current implementation/config/runtime provenance `src/thesis/provenance.py`; enforcement `src/thesis/release.py:607-827`; DAG validation `src/thesis/pipeline/dag.py:44-81`. | Code/config/library changes could be silently skipped while status remained green. | Release metadata hashes actual source/declarations/effective config/runtime; current-provenance validation makes affected stages stale and descendant releases invalid. | Final status reports Bronze 3/3, Silver 5/5, Gold 9/9, Benchmark 6/6 and ML 9/9 fresh under current implementation/config/runtime fingerprints. | **Remediated and release-verified.** |
| PIPE-R3-03 | P1 | Release portability | Absolute lineage paths made byte-identical releases fail after relocation or Docker `/data` mounting. | Relative binding `_relative_path` `src/thesis/release.py:148-180`; portable lineage paths `src/thesis/lineage.py`; relocation tests `tests/unit/test_release.py`. | Release could not be reproduced/loaded on another machine/path. | Bind data-root-relative logical paths and reject escapes; preserve optional operational path only outside integrity key. | Final sidecars validate, relocation tests pass and Docker-mounted generation-guarded readers loaded every expected table/bundle. Strict producer-runtime freshness remains intentionally environment-specific. | **Remediated and portability-verified.** |
| PIPE-R3-04 | P1 | DQ lineage/coverage | Silver producer DQ was not release-bound; award referential integrity, Gold summaries and ML auxiliaries lacked complete persisted semantic gates. | Award→tender suite `src/thesis/dq/suites.py:468-508`; Gold source-reconciliation suites `:802-1458`; persisted gates `src/thesis/pipeline/gold.py:362-457`; ML artifact validator `src/thesis/anomaly/artifact_integrity.py`; exact release contracts `src/thesis/release.py:72-145`. | Orphans, broken aggregate totals or tampered SHAP/model/JSON could publish without relevant evidence. | Added persisted release DQ for both Silver tables, four Gold outputs, benchmark semantics, scored Gold and SHAP/model bundle; checks are required contract members. | All seven invoked suites and nine required persisted DQ reports pass: Silver tenders 13 OK/3 warnings, awards 11 OK/1 warning; Gold features/suppliers/entities/monthly/scored have 39 OK and zero warnings; benchmark/ML semantic artifact checks pass. | **Remediated and release-verified.** |
| PIPE-R3-05 | P2 | Lineage failure semantics | `track()` wrote success-looking lineage even when the writer body failed. | Correct `try/except/else` in `src/thesis/lineage.py:194-219`. | A failed publication could attach new provenance to old bytes. | Write success sidecar only in the context manager `else`; failed body logs/re-raises and preserves prior sidecar. | Failure-path regressions in `tests/unit/test_release.py`/`test_writers.py`. | **Remediated.** |
| PIPE-R3-06 | P2 | JSON serialization | Shared JSON writers used `default=str` and permitted `NaN`/`Infinity`. | Strict `src/thesis/jsonutil.py:17-114`; writers/lineage/release/benchmark use it. | NumPy booleans/numbers/dates could become strings and strict JSON could be invalid. | Explicit nested conversion, null handling, `allow_nan=False`, duplicate-key and unsupported-type rejection. | Independent strict scan passed 156 JSON documents plus seven JSONL documents/75,881 rows: zero duplicate keys, non-standard constants or blank lines. | **Remediated and verified.** |
| PIPE-R3-07 | P2 | Provenance and dependency locking | Git metadata is absent; source identity and environments were previously incomplete/range-resolved. | Source-tree fingerprint `src/thesis/provenance.py`; `uv.lock`, `requirements-lock.txt`; Docker pins uv 0.11.28; CI uses pinned uv with `uv lock --check` and `uv sync --frozen` in `.github/workflows/ci.yml:23-98`. | Exact code/environment could not be reconstructed; stale checkpoint reuse was possible. | Hash actual source/config/runtime and lock dependencies; use frozen lock in CI/Docker. | `uv lock --check`, `pip check`, full tests/quality gates and locked Docker build pass. Historical commit identity remains `unknown` and must not be invented. | **Technical remediation verified; historical Git provenance unavailable.** |
| PIPE-R3-08 | P2 | Dashboard generation coherence | Independent Streamlit caches could combine valid files from different release generations. | Cross-stage guarded read `src/thesis/io/readers.py:113-145`; cache keys all three release SHA tokens `streamlit_app/_bootstrap.py:120-137`; page callers use the bundle. | A release swap mid-render could mix old Silver/Gold/ML data. | Load coupled tables under before/after Silver+Gold+ML tokens and generation-key the cache. | Reader swap/cache tests and in-process AppTest execution of Home plus every page pass; Docker main HTTP also returns 200. | **Remediated and render-verified.** |
| PIPE-R3-09 | P2 | Static typing | Baseline mypy failed with 13 errors in six files. | Clean-room command recorded the failures; current annotations/narrowing changed in affected modules and CI runs `uv run --frozen mypy src/thesis`. | Documented quality gate was false and type defects were masked. | Corrected typing rather than disabling checks; locked CI environment. | Full mypy passes: 45 source files, zero issues. | **Remediated and verified.** |
| PIPE-R3-10 | P2 | Docker health | Runtime health check called builder-only `curl`; CI only executed a version command. | Python stdlib probe `Dockerfile`; CI starts image and waits for Docker HEALTHCHECK with failure logs and cleanup `.github/workflows/ci.yml`. | Healthy app image could be marked unhealthy; CI would not detect it. | Use `urllib.request`; poll container health, fail on exit/unhealthy/timeout, log/inspect and always remove. | Patched image rebuilt at manifest-list SHA `02d9b403…b1b`; container ran as `thesis`, became healthy, returned OK at `/_stcore/health` and HTTP 200 at `/`, then was removed. | **Remediated and container-verified.** |
| PIPE-R3-11 | P2 | Bronze acquisition provenance | Historical raw bytes lacked a committed acquisition manifest (URL/time/HTTP validators/checks). | Bronze manifest/publisher `src/thesis/pipeline/bronze.py:130-138,332-369`; raw hashes above. | Current bytes can be verified internally but the original pre-R3 acquisition transaction cannot be reconstructed. | Added manifest-last provenance for present/future acquisition and honest carry-forward of available fields. | Final Bronze records retrieval `2026-07-19T10:32:35Z`, ETag `\"16692a3-64c86b5474c6b\"`, Last-Modified `Sun, 08 Mar 2026 17:35:10 GMT`, 23,499,427 bytes and both raw hashes. | **Prospective provenance remediated and verified; older historical acquisition remains unavailable.** |
| PIPE-R3-12 | P2 | Validation coverage | Pydantic checked only the first 200 rows; awards Pandera schema covered a subset and contract failures depended on warning policy. | Full-row `validate_dataframe(..., sample=None)` and unconditional abort `src/thesis/pipeline/silver.py:298-318`; complete `AwardRecord` `src/thesis/domain/contracts.py:68-102`; expanded schemas `src/thesis/domain/schemas.py`. | Late-row/type/semantic defects could pass nominal DQ. | Full Pydantic gate, expanded strict field contracts and independent ERROR blocking. | Final persisted run validates all 75,710 tenders and 62,129 awards; both Silver release-owned DQ suites pass. | **Remediated and release-verified.** |
| PIPE-R3-13 | P3 | Historical artifacts | Archived benchmark/checkpoint and lineage traces increase audit surface. | Historical files inventoried in `.audit_r3_pipeline.md`; current releases explicitly name canonical files. | Risk of human citation confusion, not current generation mixing. | Treat as archive only; do not cite as current; future retention index recommended. | No current mixing was found. | **Accepted P3 cleanup; non-blocking.** |
| PIPE-R3-14 | P3 | Repository hygiene | Ignore/tooling policy was incomplete and quality-tool versions could drift. | `.gitignore` remains sparse; lockfiles and frozen CI now pin resolved tools. | Cache/noise can complicate reviews, but does not alter authoritative release. | Lock/CI portion fixed; broader ignore/archive cleanup left non-blocking. | Lock workflow sanity passed. | **Partially remediated P3; non-blocking.** |
| PIPE-R3-15 | P1 | Nullable ML boundary | After honest bidder missingness was introduced, mixed nullable numeric frames could reach sklearn as object arrays containing literal `pd.NA`. | Converter `src/thesis/anomaly/models.py:48-66`; use in supervised benchmark/model/SHAP/validation; regressions `tests/unit/test_models.py:75-105`, `tests/unit/test_detectors_and_benchmark.py:676-699`. | Full benchmark/ML could fail or inconsistently coerce exactly the newly repaired 6,107 missing bidder values. | Convert every model boundary to dense `float64` with `na_value=np.nan`; reject nonnumeric frames. | Final benchmark completed 279 recorded fits across all 35 configurations; ML scored and explained all 75,710 rows and artifact-integrity DQ passed. | **Remediated and release-verified.** |
| PIPE-R3-16 | P2 | Persisted schema lineage | Parquet lineage fingerprinted the in-memory pandas schema although Arrow can canonicalize it, notably for all-null object columns. | Persisted footer schema extraction `src/thesis/io/writers.py:55-73` and public `src/thesis/lineage.py:238-254`; tests `tests/unit/test_writers.py:90-105`, `tests/unit/test_lineage.py:72-88`. | Valid persisted files could fail release validation or record false schema provenance. | Fingerprint the staged Parquet Arrow schema before atomic replacement in both writer APIs. | All-null schema regressions pass. | **Remediated.** |
| PIPE-R3-17 | P2 | Container provenance | The first real Docker verification built a healthy image and served the main HTTP page, but generation-guarded artifact access exposed that the runtime image omitted `requirements.txt`, a file named in the global implementation manifest. | `Dockerfile` now copies `requirements.txt` into builder and runtime; provenance regression added. | A nominally healthy image could not consume the authoritative mounted release, contradicting the portability claim. | Include every provenance-manifest dependency in the image and test generation-guarded readers inside the runtime image. | Patched container readers loaded scored Gold 75,710×95, awards 62,129×28, suppliers 9,940×23, entities 206×26, leaderboard 35×41, champion schema 2 and validation schema 1. Full `pipeline validate-releases` correctly reports runtime staleness across host macOS/Python 3.9 versus container Linux/Python 3.11; that freshness rejection is distinct from read-only portability. | **Remediated and container-verified.** |
| PIPE-R3-18 | P2 | Test/lineage isolation | The full suite wrote chronological unit-test lineage into canonical `data/_lineage/test.schema/`. | `tests/unit/test_writers.py:90-115` used a temporary Parquet path but table `test.schema`; `src/thesis/lineage.py:146-153` writes chronological copies through global `paths.DATA`. Five traces pointed to expired `/private/var/.../pytest...` paths, including three final-run traces. | Tests polluted the repository's audit lineage on every run, increasing orphan/stale evidence and contradicting test isolation. Canonical release manifests were not changed. | Monkeypatch `thesis.paths.DATA` to an isolated temp root; assert one isolated chronological record and no canonical mutation. Remove only the five verified expired test traces. | Focused regression 1 passed in 0.78 s; post-fix full suite 330 passed in 256.75 s; canonical `data/_lineage/test.schema` remained absent. | **Remediated and verified.** |

### Cross-surface risk/document findings not double-counted above

| ID | Severity | Area | Finding | Exact evidence | Impact | Remediation | Verification | Status |
|---|---:|---|---|---|---|---|---|---|
| R3-RISK-01 | P2 | Rule scoring sensitivity | The author-selected rule threshold is highly discontinuous and `HIGH_VALUE_SINGLE` necessarily stacks with one mutually exclusive single-bid rule. | Pre-remediation exact distribution and alternate counts in `.audit_r3_claims.md`; current rules expose weights/applicability/threshold rationale; generated sensitivity is required. | A single flagged count can imply stability/calibration that does not exist. | Publish reasonable threshold/top-rank-quantile sensitivity explicitly as sensitivity, not validation; retain heuristic language. | Final counts are 235 at ≥0.4, 235 at ≥0.5 and 77 at ≥0.7; generated findings label operating points as heuristic triage. | **Sensitivity published; operating-point choice remains uncalibrated.** |
| R3-DOC-01 | P3 | Notebooks | Notebooks had no stale outputs, but EDA opening/cross-surface terminology was inconsistent. | Both notebooks parse as nbformat 4, all code cells pass Python AST, zero outputs/execution counts; clean-room note `.audit_r3_claims.md`. | Low risk of readers mistaking placeholders/“contracts” wording for current evidence. | Added current-evidence banner and award/tender terminology; notebooks remain output-cleared. | Independent final scan: notebook 01 has 23 cells/12 code; notebook 02 has 24/11; zero JSON/AST errors, outputs or execution counts. | **Remediated and verified as output-cleared templates.** |
| R3-DOC-02 | P3 | Historical review clarity | `THESIS_REVIEW.md` had a generic current-looking title and said its then-current stale values were “all confirmed exactly”; `REVIEW_PROMPT.md` was historical but could still be mistaken for current instructions. | Final active-surface scan found old EU/OSHP/numeric claims only in those historical artifacts and prior reviews, not in current README/docs/dashboard/source. | Human citation ambiguity only; no canonical artifact or current claim was wrong. | Add top-of-file superseded/historical banners pointing to R3 and warning that old numbers are not current. | Both banners present; active R3 surfaces remain clean. | **Remediated P3 clarity.** |

## New R3 findings and interaction effects

The R3 findings above are not a relabelling of R2/R2.1. The most consequential new evidence was:

- **Procedure code outranks ambiguous translated text.** Code 3 exposed 291 design contests that the previous taxonomy could not distinguish.
- **Honest missingness creates downstream type obligations.** Repairing the 6,107 absent tenderer arrays revealed the nullable `pd.NA` sklearn boundary defect (PIPE-R3-15). The repair is complete only when both semantic preservation and model execution pass.
- **Published identity is not verified legal identity, but must not be discarded.** Source party ID restores identifiable award value and supplies an HHI sensitivity; it cannot be promoted to registry-verified entity resolution.
- **Per-file atomicity is not generation atomicity.** Bronze/Silver bundle manifests, current source/config fingerprints, relative paths and before/after reader guards were required even though the old snapshot happened to reconcile.
- **A structurally valid champion file is not an election proof.** The benchmark release must bind canonical result rows, persisted leaderboard and a semantic re-election, and ML must independently verify it.
- **Persisted artifact semantics matter beyond the scored table.** Model/joblib reload, JSON provenance, SHAP row/order/finite checks and exact rescoring are now publication gates.
- **Manual evidence integrity includes preservation and retrievability.** A nonblank placeholder is not a usable exact document URL; a force flag is not authority to destroy reviewed labels.
- **Award-stage evidence is not contract-performance evidence.** Numeric totals remain reproducible after relabelling, but their legal/economic interpretation changes materially.
- **A healthy container was not yet a provenance-complete container.** Real Docker execution exposed an omitted `requirements.txt`; after PIPE-R3-17 the patched rebuild passed health, HTTP and mounted generation-guarded reads.

Four remediation-time findings, PIPE-R3-15, PIPE-R3-16, PIPE-R3-17 and R3-PR-15, were discovered after the clean-room notes were frozen. The non-implementer audit added R3-PR-16, R3-PR-17, PIPE-R3-18 and R3-DOC-02. They are recorded as new findings rather than hidden as implementation details. The first core rebuild completed before the R3-PR-15 source fix and therefore had a stale implementation fingerprint; it is not accepted as the final R3 generation.

## Reconciliation of `THESIS_REVIEW_R2.md`

All 18 enumerated R2 findings were real when issued. The final tally is **16 fixed/strengthened, one partial (M3), one intentionally deferred by scope (M10), zero false positives and zero regressions**. The source-matched release closes the artifact-dependent parts of those fixes; M3 and M10 remain evidence/scope limitations.

| R2 ID and finding | Final disposition | Current R3 evidence and explanation |
|---|---|---|
| B1 — invalid OSHP treatment/outcome validation | **Already fixed and verified at source level** | Supplier-history expansion/lift is withdrawn; `src/thesis/external/oshp.py` emits no outcome metric. Lack of linkable outcomes remains an external-evidence limitation, not successful validation. |
| B2 — quotation procedures misclassified by `ULTRA_SHORT_OPEN` | **Already fixed and strengthened** | Price quotation is excluded and the diagnostic is zero-weight/non-statutory; R3 also removed code-3 design contests from ordinary open/restricted populations. |
| M1 — supplier HHI dominated by blank identity/not a relevant market | **Already fixed and strengthened** | Blank mega-supplier removed; source-party/name/business-ID views, coverage and unknown-allocation sensitivity are explicit. Legal-entity/relevant-market truth remains unavailable. |
| M2 — incompatible single-bidder populations | **Already fixed and strengthened** | Procedure, award state, year/value and bidder-observation denominators are explicit; design contests and missing bidder publication are no longer pooled as ordinary observed cases; no EU equivalence is claimed. |
| M3 — rule double-counting and threshold/weight provenance | **Partially fixed** | Structural overlap, applicability metadata and weak-rule score effects are fixed. Remaining weights/operating thresholds are author-selected and cannot be outcome-calibrated without independent evidence. |
| M4 — scheduled ingestion freezes after first local file | **Already fixed and verified** | Content-based update check, force forwarding and manifest-last Bronze publication exist; the final release chain is fresh and hash-valid. |
| M5 — DQ aborts after publication/tests clobber evidence | **Already fixed and verified** | DQ gates precede publication, runtime DQ paths are isolated, and persisted release-owned DQ now binds canonical artifacts. |
| M6 — two incompatible writers for `tender_summary.parquet` | **Already fixed and verified** | Gold solely owns immutable feature/summary outputs; ML solely owns scored tender summary. |
| M7 — stale champions accepted | **Already fixed, then strengthened and release-verified** | Schema-2 champions bind current data/protocol/implementation/semantic fingerprints; semantic re-election and ML deployment agree. The old schema-1 generation remains inadmissible. |
| M8 — award missingness/zero sentinels distort ML/UI | **Already fixed and verified** | Structural zero, missing continuous fact and award status remain distinct; imputation indicators remain; bidder missingness received an additional R3 repair. |
| M9 — circularity reframe contradicted at point of use | **Already fixed and verified** | Reports/UI call metrics rule-proxy faithfulness and rank diagnostics, not detection or temporal validation. |
| M10 — frozen reference-period scoring | **Intentionally deferred by claimed scope** | No online/single-row/cross-rebuild scoring contract is claimed. A future serving system needs frozen reference transforms and external forward evaluation. |
| N1 — lot mismatch uses EUR1 absolute tolerance | **Already fixed and verified** | Hybrid >EUR100 and >0.1% multi-lot DQ test; 260 final-release hits; no legal/economic inference. |
| N2 — monthly output drops null dates | **Already fixed and verified** | Explicit unknown-date bucket; 122 rows reconcile to all tenders. |
| N3 — KNN duplicate vectors confused with reference membership | **Already fixed and verified** | Reference row-index membership, not zero distance; regression retained. |
| N4 — reporting drift guard misses report/input freshness | **Already fixed and verified** | `docs/findings.md` was regenerated from the final release, its declared input hashes match and its SHA is `66f0534f…3c76`. |
| N5 — cold-reader defaults/scope overstate coverage | **Already fixed and verified** | Publication 115/static snapshot and unknown date/dimension scope are explicit and retained by default. |
| N6 — mixed documentation generations | **Already fixed and verified** | Registry-derived 15 visible/four score-enabled indicator counts and current feature/grid definitions are in the regenerated findings; the final full UI/static stale scan passed. |

## Reconciliation of `THESIS_REVIEW_R2.1.md`

All 28 enumerated findings were checked individually. Final taxonomy is **21 fixed/strengthened, three partial (R2-5, R2-9, R2-21), four superseded by the more fundamental absence of tender-level OSHP evidence (R2-4, R2-6, R2-7, R2-22), zero false positives and zero regressions**.

| R2.1 ID and finding | Final disposition | Current R3 evidence and explanation |
|---|---|---|
| R2-1 — blank supplier IDs corrupt concentration statistics | **Fixed and strengthened** | Multiple identity views, source-party fallback, unknown allocation and value/row coverage replace the blank key; not legal entity/relevant-market HHI. |
| R2-2 — temporal-generalisation language survives | **Fixed** | All surfaces restrict metrics to proxy faithfulness/static ranking; genuine temporal validity remains unsupported. |
| R2-3 — champions/leaderboard fail data fingerprint | **Fixed and release-verified** | R3 binds exact data, protocol, implementation and semantic election; the 35-row schema-2 release and deployed ML bundle agree. Old artifacts remain inadmissible. |
| R2-4 — OSHP baseline mis-specified | **Superseded by fundamental evidence failure** | No eligible tender-level outcome/treatment link exists; entire statistic withdrawn rather than recomputed. |
| R2-5 — no evaluation distinguishes detection from mimicry | **Partially fixed** | Deterministic blinded four-quadrant queue/protocol exists; no completed human labels and no valid external outcomes exist. Empty strata are not synthesized. |
| R2-6 — OSHP lift lacks uncertainty | **Superseded by fundamental evidence failure** | A confidence interval cannot validate an invalid tender label; lift withdrawn. |
| R2-7 — selective OSHP lift reporting | **Superseded by fundamental evidence failure** | All invalid lifts removed rather than selectively expanded. |
| R2-8 — weight stacking crosses threshold | **Fixed** | Single-bid rules are mutually exclusive; only four rules score and exact heuristic arithmetic is disclosed. |
| R2-9 — threshold provenance/inversion | **Partially fixed** | Scope/rationale/limitations and zero weighting are explicit; remaining author-selected thresholds lack outcome calibration. |
| R2-10 — `ZERO_BIDDER` rationale empirically void | **Fixed and further corrected** | The direct-award story was removed; R3 shows all 6,107 were missing publication and there are zero observed-zero cases in this snapshot. |
| R2-11 — invented EU single-bid norm | **Fixed** | Comparator deleted; subtype/observation/status denominators retained. |
| R2-12 — missingness erased by detector imputation | **Fixed** | `add_indicator=True` preserves missingness and nullable bidder counts now cross every model boundary as float NaN, not `pd.NA`. |
| R2-13 — DQ abort after persistence/mtime resurrection | **Fixed and strengthened** | Prepublication DQ, manifest-last release, source/config freshness and content validation now fail closed. |
| R2-14 — fixture tests overwrite canonical DQ | **Fixed and verified** | Runtime path resolution and release-owned DQ prevent clobber; all seven invoked suites and nine final persisted reports pass. |
| R2-15 — stale methodology/UI numbers | **Fixed and verified** | Counts are live/registry/generated, `docs/findings.md` was regenerated from the R3 release, and the final repository-wide UI/static scan passed. |
| R2-16 — stale notebook outputs/claims | **Fixed and verified** | Independent final scan found valid JSON/AST and zero stored outputs/execution counts in both notebooks; attacked claims were removed. |
| R2-17 — red/high-risk traffic-light narrative | **Fixed** | Explanation-first review priority replaces a third uncalibrated risk system. |
| R2-18 — national HHI headline | **Fixed and strengthened** | No national/relevant-market KPI; identity/coverage sensitivity only. |
| R2-19 — pooled single-bidder headline | **Fixed** | Pooled rate is demoted and observed/subtype denominators are required. |
| R2-20 — stale landing/architecture constants and paths | **Fixed and verified** | Live registry/path definitions govern, final findings show 15 indicators and the corrected award generation, and all Streamlit AppTest renders pass. |
| R2-21 — frozen reference scoring absent | **Partially fixed** | Snapshot-relative limitation is honest; frozen cross-rebuild/online reference remains future work. |
| R2-22 — OSHP caveat/cache defects | **Superseded by fundamental evidence failure** | Cache is source material only and cannot validate tenders. |
| R2-23 — rule/ensemble disagreement absent from UI | **Fixed and release-verified** | Final four-quadrant values are both 235, rule-only 0, ensemble-only 24,455 and neither 51,020; ML-only is labelled unvalidated. |
| R2-24 — ADR describes another system/“corroboration” | **Fixed** | ADR uses current release/proxy/rank language and rejects independent corroboration. |
| R2-25 — phantom/misstated lineage | **Fixed, strengthened and release-verified** | Sole writers, actual input bindings, manifest-last generations and before/after hashes validate across the five-stage final chain. |
| R2-26 — silent sub-1% ratio guard band | **Fixed** | Floor is explicit, zero-weight and described as DQ; 3,668 final-release 1%–<50% hits. |
| R2-27 — duplicate benchmark configs/row-order ties | **Fixed and release-verified** | Content-derived unique keys, exact completeness and deterministic tie-break; final sweep is 35 expected/35 successful/35 unique with zero extra or failed rows. |
| R2-28 — quick/full benchmark contamination | **Fixed and superseded by stronger isolation** | Quick, mutable WIP and canonical results have separate paths; only complete semantic full evidence is released. |

## Claim ledger

The ledger treats a numerical or methodological claim as supported only when its live computation and final released artifact agree. The final source-matched release replaced the no-write values; unsupported inferential claims remain withdrawn regardless of technical reproducibility.

### Data and procurement claims

| Location | Material claim | Source artifact / live code | Independent recomputation | Verdict |
|---|---|---|---|---|
| README, architecture, overview | Snapshot contains 75,710 unique tenders | Final `data/silver/tenders.parquet` + Silver release | Raw unique OCIDs and released Silver both 75,710; Parquet SHA `c4139e13…323f` | **Supported for the frozen snapshot.** |
| README/dashboard | Dataset spans 118 populated months | `data/gold/monthly_metrics.parquet` | 122 rows: 121 calendar buckets plus unknown-date; 118 populated; sums to 75,710 | **Supported with explicit unknown-date scope.** |
| Architecture/findings/dashboard | 62,129 canonical award records | Corrected `data/silver/awards.parquet` + Silver release | 65,721 raw objects→62,129 identity-aware dedup; Parquet SHA `3498ec4d…ffb9` | **Supported.** All 62,128 current-generation claims are stale. |
| Findings/dashboard | Recorded award value EUR4,765,544,184.67 | Corrected Silver awards/Gold summaries | Released sum after restored EUR7,200 award; Gold DQ reconciles source totals | **Supported as recorded award value only.** Not spend or contract value. |
| Source description | 65,721 raw award objects | Frozen JSONL | Full raw-object scan | **Supported as pre-dedup object count.** |
| Methodology procedure taxonomy | Code 3 is design contest; code 1 standard open | `domain/procedures.py`; official original Regulation 001/2022 Art. 12.13, official amendment and PPL Art. 73 | Tender-ID code cross-tab | **Supported; old open/restricted classification withdrawn.** |
| Procedure counts | Standard open 39,650; restricted 38; design contest 291; negotiated with notice 6; without notice 4,572; quotation 18,383; minimum value 11,840; mini-competition 930 | Final Gold features/rule report | Released code-first recomputation | **Supported for the frozen snapshot.** |
| Single-bidder result | 8,649 of 36,036 standard-open tenders with observed bidder data (24.0%) | Final Gold features/findings | Observation-aware denominator; 39,650 is the subtype population, not the rate denominator | **Supported descriptive statistic only; no EU/risk comparison.** |
| Bidder availability | 69,603 observed, 6,107 missing, zero observed-zero | Final Silver tenders | Raw tenderer-array scan | **Supported; former 6,107 zero-bidder claim withdrawn.** |
| Price quotation/value | Seven code-6 records estimated ≥EUR10,000 | Gold rule/DQ | Exact seven-OCID recomputation | **Supported as DQ conflict, not illegality.** |
| Minimum value | All 11,840 code-7 estimates below EUR1,000 | Silver/Gold | Maximum EUR999.99 | **Supported for this snapshot, not a legality finding.** |
| Supplier identity | Source/name identity covers all corrected award rows/value in this snapshot | Supplier/Gold summary | 62,129/62,129 source-party IDs; 10,708 distinct | **Supported as publication identity, not verified legal identity.** |
| Supplier business IDs | 43,835 corrected award rows have usable business ID; 4,576 distinct | Corrected Silver awards | Sentinel-normalized recomputation | **Supported as source field usability, not registry verification.** |
| Concentration/HHI | HHI sensitivities can be reported by identity choice/unknown allocation | Gold entity/supplier summaries | Source/name/business-ID views and coverage | **Supported only as identity sensitivity.** National/relevant-market/competition-law HHI unsupported. |
| Buyer identity | Two normalized names/four IDs/550 rows | Zero-weight rule + DQ | Exact name/ID cross-tab | **Supported as DQ; merge truth unresolved.** |
| Lot linkage | 61,260 exact unique, 244 ambiguous, 505 unmatched, 120 missing | Corrected Silver awards | Exact-title-only status | **Supported QA evidence; no lot-level allocation claim.** |
| Winner-takes-all | 426 tenders meet current tender-level heuristic | Final Gold rules | Released Gold recomputation | **Supported as author-selected review signal only.** |
| Manual audit URLs | Final queue has 124 structurally valid-unverified and 26 invalid source URLs | `manual_audit_sample.csv` + final metadata | Corrected structural classifier; CSV SHA `5f355938…9120` | **Supported as structural classification only; HTTP availability was not tested.** |
| Manual audit labels | Blank review fields are unreviewed | Audit CSV/label-state hash | Direct inspection | **Supported.** No precision/recall/FPR may be calculated. |
| OSHP validation | OSHP overlap validates tender risk | Withdrawn status artifact | Cache lacks exact tender/case/outcome linkage | **Unsupported and withdrawn.** |
| Award evidence | Award objects prove signed/executed/paid contracts | Raw object schema | Zero top-level standard OCDS contract objects in frozen feed | **Unsupported and withdrawn.** |

### Rule, ML and statistical claims

| Location | Material claim | Source artifact / live code | Independent recomputation | Verdict |
|---|---|---|---|---|
| Methodology/UI | 15 visible indicators, four score-enabled | `src/thesis/anomaly/rules.py` registry + final Gold | Registry enumeration and released firing counts | **Supported as code inventory and frozen-snapshot counts.** |
| Rule score | `rule_score` is calibrated risk or wrongdoing probability | Weighted heuristic registry | No external outcomes/calibration | **Unsupported.** It is a transparent review score. |
| Rule threshold | 0.5 is a defensible empirical decision boundary | Author-selected config | Strong alternate-threshold discontinuity | **Unsupported as calibrated boundary; supported only as disclosed operating choice.** |
| ML inventory | Eight unsupervised detector families are implemented | `FAMILY_REGISTRY` | Registry/tests | **Supported as implementation inventory, not eight validated detectors.** |
| Benchmark grid | Full benchmark contract is 23 unsupervised +12 supervised =35 unique configs | Declared grids/semantic DQ | Final 35 expected/35 successful/35 unique; zero failures/extras/duplicates/stale rows | **Supported as execution completeness, not detection validity.** |
| Champion selection | Deployed ensemble uses released benchmark champions | Schema-2 election and ML re-election | Semantic fingerprint `e034c3f0…cfd81`; both select `ocsvm, iso, hbos, knn` | **Supported under the declared internal proxy/repeatability election only.** |
| Findings/dashboard | Ensemble review-threshold populations are 24,690 at ≥0.5 and 6,505 at ≥0.7; rank agreement is 2,453 | Final scored Gold + validation report | Direct count from 75,710 released rows | **Supported as snapshot-relative queue sizes only.** |
| Findings/dashboard | Rule/ensemble quadrants are 235 both, 0 rule-only, 24,455 ensemble-only, 51,020 neither | Final scored Gold + audit metadata | Direct Boolean cross-tab; sums to 75,710 | **Supported descriptively; disagreement is not validation.** |
| Validation report | q=.90/.95/.99 rank-vote sensitivity yields 5,008/2,453/425 rows and Jaccard .4898/1/.1733 relative to q=.95 | `validation_report.json` | Independent artifact read/hash verification | **Supported as threshold sensitivity only.** |
| Validation report | Raw-only and pre-outcome-field snapshot ablations yield Spearman/Jaccard .9050/.7166 and .8136/.5211 | `validation_report.json` | Independent artifact read/hash verification | **Supported as ranking dependence only, not a validated pre-outcome model.** |
| Benchmark report | Balanced election preserves the top four; stability/proxy emphasis has Jaccard .6; proxy-precision-only .1429 with three rank conflicts | Schema-2 champions/leaderboard | Semantic re-election | **Supported as objective sensitivity; no family-superiority inference.** |
| Artifact integrity | Persisted models reproduce released scores | Model bundle/HGB/scored Gold | Independent reload/rescore: max absolute delta 0.0 for all eight detectors and bundled/standalone HGB | **Supported as reproducibility, not validity.** |
| Supervised CV/AUC/PR-AUC | High metrics demonstrate detection | Target `(rule_score>=threshold)` | Target/features share rule facts/proxies | **Unsupported as detection.** May be reported only as rule-proxy agreement with class counts. |
| Temporal split | <=2023/>=2024 establishes temporal generalisation | Retrospective feature table | Full-snapshot/award-stage feature audit | **Unsupported.** Temporal proxy-faithfulness check only. |
| Ensemble score | `ensemble_score` is anomaly probability/risk | Mean of detector percentile ranks + rule/context scores | Formula/source audit | **Unsupported as probability/risk; supported as snapshot-relative review ranking.** |
| `high_confidence` | Records are high-confidence anomalies | At least configured votes among current-batch top rank | q=.90/.95/.99 sensitivity | **Historical name only; means rank agreement, not confidence/calibration.** |
| SHAP | SHAP explains fraud/risk causes | HGB trained on rule proxy | Feature/target audit | **Unsupported.** SHAP explains surrogate attribution only, non-causally. |
| Champion | Selected family is “best detector” | Author-selected internal composite | Alternate-weight/`precision@K` ranking | **Too strong.** Say “selected under declared proxy/repeatability composite.” |
| Repeatability | Four bootstraps/two seeds establish statistical stability | Config + validation report | Repeat-count audit | **Supported only as limited repeatability diagnostic, not uncertainty.** |
| Feature ablation | Ablation validates a pre-outcome system | Static refit subsets | Rank/top-set comparison only | **Unsupported.** It quantifies ranking dependence, not validity. |
| Model agreement | Detectors independently corroborate rules | Rule score is an ensemble component; inputs overlap | Correlation/confusion audit | **Unsupported as corroboration.** Agreement/disagreement is descriptive. |
| Precision/recall/FPR/prevalence | These outcome quantities are known | No outcome labels | Audit/external evidence inspection | **Unsupported.** Proxy `precision@K` must be labelled proxy agreement. |
| Live/pre-award use | System supports live scoring or comparable cross-rebuild scores | Award-stage features/current-snapshot transforms | Feature/pipeline audit | **Unsupported; future work only.** |

### Reproducibility, reports, notebooks and dashboard claims

| Location | Material claim | Source artifact / live code | Independent recomputation | Verdict |
|---|---|---|---|---|
| Raw layer | Raw gzip/JSONL are internally identical and complete | Bronze release/raw files | gzip CRC/decompression/hash/75,710 JSON parse | **Supported for current bytes; historical acquisition provenance incomplete.** |
| Architecture | Every canonical stage is generation-bound and portable | Five canonical release contracts | All declared hashes/current source/config/runtime match on host; Docker-mounted guarded readers pass across runtime | **Supported for release `run-20260719T103232-2fe4b69e`.** Strict producer-runtime freshness is intentionally not cross-runtime. |
| Pipeline status | All stages are fresh for current source/config/runtime | `thesis pipeline status` | Bronze 3/3, Silver 5/5, Gold 9/9, Benchmark 6/6, ML 9/9 fresh | **Supported for the final source-matched run.** |
| DQ | Every canonical output passed required release-owned DQ | Release check files | All seven invoked suites and nine required persisted reports pass; documented Silver warnings only; benchmark/ML semantic artifact checks pass | **Supported.** |
| Benchmark/model generation | Results, leaderboard, champions, model bundle, SHAP, validation and scored table are one R3 generation | Benchmark/ML manifests and fingerprints | Semantic re-election, reload/rescore and 75,710-row parity pass | **Supported as artifact coherence, not external validity.** |
| Reports | `docs/findings.md` is regenerated from final authoritative artifacts | Reporting input registry/test | Input hashes match final releases; SHA `66f0534f…3c76` | **Supported.** |
| Dashboard | Pages cannot mix release generations and use current terms/numbers | Cross-stage guarded bundle + manifest-keyed cache | Reader swap/cache tests plus AppTest execution of Home and all pages | **Supported; Docker main page also served HTTP 200.** |
| Notebooks | Notebooks contain current executed evidence | Two output-cleared notebooks | Independent JSON/AST/no-output audit | **They contain no executed evidence.** Both are valid, output-cleared templates with zero execution counts and must not be cited as executed results. |

## Before/after quantitative changes

The “before” column is the last pre-R3 canonical generation. “After” is the final source-matched R3 release; the earlier deterministic no-write build independently predicted these values but is not the provenance source.

| Measure | Before | Final published R3 | Change / interpretation |
|---|---:|---:|---|
| Silver award rows | 62,128 | 62,129 | +1 distinct-party award retained |
| Recorded award value | EUR4,765,536,984.67 | EUR4,765,544,184.67 | +EUR7,200; award value, not contract spend |
| Supplier-summary rows | 9,427 | 9,940 | +513 source-party-only identities surfaced |
| Explicit design contests | 0 | 291 | Code-3 records separated |
| Standard-open tenders | 39,940 | 39,650 | −290 design contests |
| Restricted tenders | 39 | 38 | −1 design contest |
| Bidder-data observed | not represented | 69,603 | New honest observation denominator |
| Missing bidder publication | silently zero | 6,107 | Preserved as null |
| Observed zero bidders | 6,107 asserted | 0 | Old claim withdrawn |
| Observed single bidders | mixed denominator | 27,133 | Rates use observed rows only |
| Rule registry | 13 visible /4 scoring | 15 visible /4 scoring | Two zero-weight DQ indicators added |
| Rule score ≥0.5 | 221 | 235 | +14; heuristic threshold, not validation |
| Rule score ≥0.7 | 77 | 77 | no change |

### Rule-count changes

| Indicator | Before | Final published R3 | Delta |
|---|---:|---:|---:|
| `SINGLE_BIDDER` | 18,457 | 18,484 | +27 |
| `SINGLE_BIDDER_OPEN` | 8,676 | 8,649 | −27 |
| `ZERO_BIDDER` | 6,107 | 0 | −6,107 |
| `RATIO_BELOW_50` | 3,669 | 3,668 | −1 |
| `RATIO_ABOVE_ESTIMATE` | 1,373 | 1,373 | 0 |
| `IMPLAUSIBLE_ESTIMATE` | 25 | 25 | 0 |
| `NEGATIVE_DAYS_TO_AWARD` | 6 | 6 | 0 |
| `ULTRA_SHORT_OPEN` | 43 | 41 | −2 design contests |
| `PRICE_QUOTATION_VALUE_BAND_CONFLICT` | absent | 7 | new zero-weight DQ signal |
| `BUYER_NAME_ID_COLLISION` | absent | 550 | new zero-weight DQ signal; two name groups/four IDs |
| `HIGH_VALUE_SINGLE` | 101 | 101 | 0 |
| `END_BEFORE_START_OPEN` | 9 | 9 | 0 |
| `LOT_VALUE_MISMATCH` | 260 | 260 | 0 |
| `WINNER_TAKES_ALL_LARGE` | 397 | 426 | +29 after upstream identity/award changes |
| `UNAWARDED_HIGH_VALUE` | 1,625 | 1,625 | 0 |

### Ensemble/ranking changes

These changes arise from the corrected data/features and regenerated benchmark champions. They describe the new snapshot-relative ordering and are not outcome-validation improvements or regressions.

| Measure | Before | Final published R3 | Delta |
|---|---:|---:|---:|
| `ensemble_score ≥ 0.5` | 25,252 | 24,690 | −562 |
| `ensemble_score ≥ 0.7` | 6,594 | 6,505 | −89 |
| `high_confidence` rank-agreement rows | 2,536 | 2,453 | −83 |
| Ensemble mean | 0.438235 | 0.436996 | −0.001239 |
| Ensemble median | 0.421650 | 0.419316 | −0.002334 |
| Ensemble p95 | 0.744807 | 0.744340 | −0.000467 |
| Rule and ensemble both ≥0.5 | — | 235 | final descriptive quadrant |
| Rule-only ≥0.5 | — | 0 | empty final population, not synthesized |
| Ensemble-only ≥0.5 | — | 24,455 | unvalidated review-ranking disagreement |
| Neither ≥0.5 | — | 51,020 | descriptive only |

### ML/release contract changes

| Dimension | Before | R3 contract | Final quantitative result |
|---|---|---|---|
| Champion schema | schema 1; no implementation fingerprint | schema 2; exact config keys, implementation/election fingerprints and sensitivity | Final schema 2; semantic fingerprint `e034c3f0…cfd81`; elected/deployed `ocsvm, iso, hbos, knn` |
| Benchmark checkpoint | data/settings-bound mutable evidence | implementation-bound quick/WIP/canonical isolation; strict JSON | Canonical SHA `ae47e890…5b24`; exactly 35 successful unique full rows, zero failed/extra/duplicate/stale |
| Benchmark release | omitted canonical results/semantic check | binds results, leaderboard, Markdown, champions and exact semantic DQ | Manifest `676cff17…b48a`; 35×41; semantic DQ passed |
| ML release checks | scored-table DQ only | scored-table + SHAP/model/JSON/rescore integrity | Manifest `77ccbcbb…db0a`; scored 75,710×95 and SHAP 75,710×22; every check passed |
| Election sensitivity | one 0.45/0.35/0.20 composite | declared + three alternate weights + proxy-`precision@K` rank | Balanced top-four Jaccard 1.0; stability/proxy 0.6; proxy-precision-only 0.1429 with three conflicts |
| Vote sensitivity | q=.95 only | q=.90/.95/.99 count/share/Jaccard | q=.90: 5,008/J=.4898; q=.95: 2,453/J=1; q=.99: 425/J=.1733 |
| Feature sensitivity | none | two declared refit subsets; Spearman/top-5% overlap only | Raw-only 0.9050/.7166; pre-outcome-field snapshot 0.8136/.5211 |
| Docker/CI dependencies | range `pip install`; version-only image smoke | uv 0.11.28 frozen lock + actual HEALTHCHECK wait | Locked build passed; image SHA `02d9b403…b1b`; healthy/HTTP/guarded-reader checks passed |

## Primary legal/procedure sources and limits

The taxonomy and diagnostic applicability use the following PPRC-hosted primary sources, with the non-official consolidation identified separately:

1. [PPRC official secondary-legislation register](https://e-prokurimi.rks-gov.net/HOME/ClanakItemNew.aspx?id=233), which lists original Regulation No. 001/2022 (effective 1 November 2022) and amending Regulation No. 002/2024 (effective 11 November 2024) as the official acts.
2. [Official original English Regulation No. 001/2022](https://e-prokurimi.rks-gov.net/HOME/Documents/Legislation/SecondaryLegislation/eng/A01%20Regulation%20No.001_2022%20on%20Public%20Procurement.pdf), Art. 12.13 for procedure codes 1–8 and Arts. 51.3/51.5 for price-quotation applicability/minimum period.
3. [Official Albanian amending Regulation No. 002/2024](https://e-prokurimi.rks-gov.net/HOME/Documents/Legislation/Rregulloret/shq/FINAL%20DRAFT%20RRPP%2006.11.2024.pdf), read with the official register above.
4. [Kosovo Public Procurement Law, consolidated official English text](https://e-prokurimi.rks-gov.net/Home/Documents/Legislation/Ligjet/eng/PPL%20consolidated.pdf), Art. 19 for value bands, Art. 73 for design contests and Arts. 44–46 for context-dependent time limits.
5. [PPRC-hosted Albanian consolidation of Regulations 001/2022 and 002/2024](https://e-prokurimi.rks-gov.net/HOME/Documents/Legislation/Rregulloret/shq/versioni%20i%20konsoliduar%20i%20Rregullores%20Nr.%20001%202022%20i%20plot%C3%ABsuar%20dhe%20ndryshuar%20me%20Rregulloren%20Nr.%20002%202024.pdf), used only as a **non-official convenience text**; its cover expressly disclaims official status. Its renumbered Art. 12.3 is not cited as the legal authority in place of the official acts.
6. [PPRC 2016 Rules and Operational Guidelines (official English predecessor)](https://e-prokurimi.rks-gov.net/HOME/Documents/Legislation/Aktet%20dyt%C3%ABsore%20te%20shfuqizuara/eng/A01%20Rules%20and%20Operational%20Guidelines%20for%20Public%20Procurement.pdf), used only for historical context and never retroactively as current law.

The official original regulation, amendment and PPL support the subtype mapping and justify surfacing seven quotation/value conflicts for review. They do **not** prove those procedures unlawful. Deadline legality requires the period-specific rule, invitation/publication event, urgency, prior-information notice, corrigenda, amendments and original tender documents.

## Remaining evidence and human-judgment limitations

1. **No completed human labels.** Blank fields mean unreviewed, not negative. Precision, recall, FPR, inter-rater agreement and outcome calibration cannot be reported.
2. **No linkable external outcomes.** The OSHP cache lacks an adequate exact tender/case/outcome relation. Aggregate authority or supplier overlap is not validation.
3. **Manual URLs are sometimes unavailable.** The final queue has 26 invalid source URLs and 124 structurally valid-unverified URLs. No alternate exact URL may be invented, and structural validity is not HTTP availability.
4. **Empty strata are real.** The final `rule_only` population is zero and its sample stratum is empty; no synthetic members were added.
5. **Supplier identity is unresolved.** Source party IDs are publication identifiers; names may merge homonyms and IDs may split one legal entity. HHI remains identity sensitivity, not market concentration.
6. **Buyer merge truth is unresolved.** The two name/ID collision groups require authoritative entity history; automatic merging is unsafe.
7. **Lot allocation is unresolved.** No shared stable award-to-lot ID exists; exact title status is QA only.
8. **Legal conclusions are unavailable.** The seven quotation/value conflicts and all deadline screens require original documents and applicable historical law.
9. **Award-stage records do not prove performance.** No signed/executed/paid contract conclusion follows from an award object.
10. **Static-snapshot validity is limited.** Award-stage facts, full-snapshot ranks and no external outcomes preclude pre-award, causal, temporal-generalisation and production-monitoring claims.
11. **Model-selection uncertainty is limited.** Four bootstraps/two extra seeds are repeatability diagnostics only; election weights, feature geometry and vote thresholds remain author choices.
12. **Historical provenance is incomplete.** The export has no Git metadata and the original pre-R3 acquisition transaction cannot be reconstructed. The final Bronze retrieval recorded URL-response metadata, while source-tree/config/runtime hashes secure the R3 build prospectively.

## Final verification record

Known focused evidence is retained here without promoting it to full acceptance:

| Check | Recorded outcome | Acceptance meaning |
|---|---|---|
| Clean-room baseline pytest | 194 passed before R3 remediation | Baseline only; not final |
| Procurement focused regression | 131 passed; later narrative/UI subset 114 passed | Source/no-write evidence only |
| ML benchmark-focused selection | 45 passed | Source contract evidence only |
| Persisted ML artifact-integrity selection | 20 passed | New artifact gate unit evidence |
| Broader release/benchmark/model selection | 101 passed | Source contract evidence only |
| Focused Ruff/mypy/compile/AST | passed in tracks | Not the final full-repository gate |
| No-write procurement DQ | zero ERROR; documented warnings | Not persisted release evidence |
| First final full suite | 328 passed, 1 failed in 283.18 s | Failure was a stale test expectation using all 39,650 standard-open rows instead of the correct 36,036 observed-bidder denominator; expectation repaired |
| Clean full suite before final-audit test-isolation patch | 330 passed in 290.55 s | Superseded by post-fix rerun |
| Final post-fix full suite | 330 passed in 256.75 s (4:16), exit 0; no canonical `test.schema` trace | Required gate passed |
| Ruff lint/format | Check passed; format check passed for 90 files | Required gate passed |
| Full mypy | 45 source files, zero issues | Required gate passed |
| Dependency gates | `uv lock --check` passed for 261 packages; `uv pip check` checked 184 packages and reported all compatible | Required local environment gates passed |
| Five-stage DQ/release validation | Releases valid; status 3/3, 5/5, 9/9, 6/6, 9/9 fresh; all seven invoked suites/nine persisted DQ reports pass | Required artifact gate passed |
| Review reconciliation arithmetic | 18/18 R2 and 28/28 R2.1 table rows; 50 canonical findings = 14 P1 +29 P2 +7 P3 | Completeness/count check passed |
| Procurement/data read-only verification | Final rows, value, bidder missingness, supplier/entity/monthly reconciliation, rules, audit URLs and active legal/procurement wording matched; no P0–P2 contradiction | Domain verification passed; irreducible identity/lot/legal/outcome limits remain |
| ML read-only verification | 35/35 benchmark, aligned fingerprints/election, SHAP 5/5 and exact rescore max delta 0.0 | Artifact integrity passed; this was implementer-side verification, not the final independent contradiction audit |
| Docker portability/health execution | Patched image SHA `02d9b403…b1b`; healthy; health endpoint OK; main HTTP 200; guarded readers loaded all expected host artifacts; container removed | Required gate passed; cross-runtime freshness rejection is expected |

## Final acceptance checklist

- [x] **Authoritative release chain:** Bronze, Silver, Gold, Benchmark and ML/reporting published in order with manifest-last contracts and no source/config changes during the source-matched run.
- [x] **Release validation:** all five canonical release contracts validate exact inputs, artifacts, checks, sidecars, hashes, schemas, provenance and upstream manifest SHA-256 values.
- [x] **DQ:** all required persisted suites pass; warnings are reported honestly; Silver award OCIDs are a subset of tenders; Gold summary totals reconcile to sources; SHAP/model/JSON/rescore checks pass.
- [x] **Benchmark:** exactly 35 expected, successful, unique full configurations; no quick, WIP, failed, duplicate, extra, stale-protocol or stale-implementation rows.
- [x] **Champion/fingerprint consistency:** schema-2 champions and semantic election agree with released rows/leaderboard; data, protocol, implementation, semantic, Gold-manifest and benchmark-manifest fingerprints agree through every ML artifact.
- [x] **Models/SHAP:** all eight deployed scorer families and HGB reload and reproduce persisted scores within declared tolerance; SHAP OCID order/row count/feature order and finite numeric values match scored Gold.
- [x] **Rows and hashes:** final row×column values, SHA-256 values, release ID, manifest SHA-256 and generation fingerprints are recorded below and independently matched disk.
- [x] **Manual audit:** regenerated after ML with label preservation; sample/definition/label-state hashes, seed, thresholds/populations, URL statuses, empty stratum and completion status are recorded; no label was altered or inferred.
- [x] **Reports/dashboard:** `docs/findings.md` and generated tables were rebuilt from final artifacts; all Streamlit pages pass AppTest from a guarded current-generation bundle and use cautious award/screening/ranking language; Docker main page returns HTTP 200.
- [x] **Notebooks:** both notebooks parse as JSON/nbformat, every code cell parses as Python AST, no stale outputs/execution counts are presented as current evidence, and banners identify their evidence status.
- [x] **Stale scan:** no stale `62,128`, `9,427`, observed-zero `6,107`, 13-rule, 43-ultra-short, 397-winner, schema-1 champion or old fingerprint claim remains where it purports to describe R3; no unsupported fraud/corruption/detection/legal-breach/contracted-value/OSHP-lift/EU-comparator claim survives. Historical prior-review/prompt and before/after mentions are retained as explicitly non-current evidence.
- [x] **Quality gates:** full pytest, Ruff check, Ruff format check, mypy, strict JSON scan, dependency/lock check and pipeline status all pass in the locked environment.
- [x] **Container:** built image starts and becomes Docker `healthy`; health/main HTTP and generation-guarded mounted-artifact reads pass; temporary container is removed. Cross-runtime full freshness validation rejects the host-built runtime fingerprint by design.
- [x] **Independent contradiction audit:** a reviewer who did not implement the fixes confirmed source, manifests, artifacts, reports, notebooks and dashboard describe one generation after independently surfacing and rechecking the late legal-source, lineage-isolation and historical-banner repairs.

### Final authoritative values

| Item | Final result |
|---|---|
| Full test suite | First run: 328 passed/1 stale-expectation failure; intermediate clean run 330 passed; final post-PIPE-R3-18 run **330 passed in 256.75 s**, exit 0 |
| Ruff / formatting / mypy | Ruff check passed; format check passed for 90 files; mypy passed 45 files with zero issues |
| Pipeline status | Bronze 3/3, Silver 5/5, Gold 9/9, Benchmark 6/6, ML 9/9 fresh |
| Release IDs / manifest SHAs / generation fingerprints | Shared release `run-20260719T103232-2fe4b69e`; Bronze `b33a97e1…3ca4`/`a44b7f9a…0da`; Silver `f1e15077…eb32`/`4f2f86ee…98e`; Gold `a2602b70…eff`/`3ef3848e…539`; Benchmark `676cff17…b48a`/`b1007484…044`; ML `77ccbcbb…db0a`/`74b1cbc8…398a` |
| Final artifact row counts and SHA-256 values | Recorded in `THESIS_REMEDIATION_R3.md`; every declared manifest hash independently matched disk |
| Benchmark data/protocol/implementation/semantic fingerprints | `e4e6cef88490834a` / `7d5b8a909f00e6d8` / `1ebaf58000d16685dbb51609b3ce1489b4aaf5d51d3dadb66dd83b5418647ac9` / `e034c3f0668d8f9b85f196371b7562653a3aed8f23350eaa7c38e4bf7d8cfd81` |
| Benchmark completeness/uniqueness/champions | 35 expected/35 successful/35 unique, zero failed/extra/duplicate/stale; ensemble `ocsvm, iso, hbos, knn`; HGB depth 4, learning rate .05, 300 iterations |
| Manual-audit sample/definition/label-state hashes and URL counts | `5f355938…9120` / `b7daa09c…baa1f` / `662e9fba…b403`; 124 structural-valid-unverified, 26 invalid; 0/150 labels, awaiting human review |
| Notebook/stale-claim scans | Notebooks pass JSON/AST/no-output scan; active README/docs/dashboard/source claims pass stale-number/language scan. Remaining old values occur only in historical review/prompt or explicit before/after contexts. |
| Independent final contradiction/integrity audit | **Passed**: 50 unique findings = 14 P1 +29 P2 +7 P3; no unresolved P0–P2 contradiction; release, DQ, benchmark, manual audit, legal source, Docker distinction and post-fix test isolation rechecked |

## Acceptance decision

**Final decision: TECHNICALLY ACCEPTED ONLY FOR THE NARROWED THESIS CLAIM.** All identified actionable P0–P2 implementation, documentation and canonical-publication defects are remediated and verified, and the non-implementer audit found no remaining P0–P2 contradiction. The coherent release supports a thesis about descriptive procurement data engineering, transparent heuristic screening and exploratory retrospective anomaly ranking. It is **not accepted as fraud/corruption detection, calibrated or validated risk, legal-breach determination, causal inference, external validation, or measured detection performance**. Those stronger claims remain withdrawn until the documented human/external evidence exists.
