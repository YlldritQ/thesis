> **Historical review — superseded.** This document describes an earlier
> repository state; its counts, artifacts, and verdicts are not current. See
> [THESIS_REVIEW_R3.md](THESIS_REVIEW_R3.md) and
> [THESIS_REMEDIATION_R3.md](THESIS_REMEDIATION_R3.md) for the verified final
> review and remediation record.

# Multi-Agent Review — Kosovo Procurement Anomaly-Detection Thesis

> **How this was produced.** A 5-persona adversarial review orchestrated as a 54-agent
> workflow: an evidence phase (5 code-grounded scouts) → independent reviews by a *normal user*,
> a *tender/procurement expert*, a *senior data engineer*, and a *combined AI+procurement expert*
> → a cross-persona **roundtable** where the experts rebutted each other → **adversarial
> verification** of every finding against the actual code/data (48 raw → 42 consolidated →
> **40 verified, 0 refuted**) → a *total-amateur* usability pass → synthesis.
> The orchestrator then **independently re-computed every load-bearing number** below against the
> shipped Parquet before publishing.

## Verification ledger (orchestrator's independent re-computation)

Every quantitative claim the report leans on was re-run against `data/gold/tender_summary.parquet`
(75,710 rows) and `data/silver/awards.parquet` — **all confirmed exactly**:

| Claim (finding) | Document / code says | Shipped data says | Status |
|---|---|---|---|
| Single-bidder by method (C-5 / M-06) | pooled **35.8%**, "well above EU 20–25%" | open **23.44%**, minimum 77.23%, limited 85.45%; pooled 35.84% | ✅ confirmed — headline is a pooling artifact; open-only (23.4%) is *in* the EU norm |
| Home flagged-KPI population (M-06) | 22.38% shown beside the 35.8% headline | `rule_score≥0.5` = 16,945 = **22.38%** (a different population) | ✅ confirmed |
| Triage vs rules disagreement (H-1 / M-07) | ADR-0002: "two layers must agree" | `ensemble≥0.7` = **10,889**; **67.2%** ML-only (no rule flag); **78.9%** of rule-flags demoted | ✅ confirmed |
| Award count (C-6 / M-09) | findings.md: **65,721** awards | silver awards = **62,128** (raw vs post-dedup mixed) | ✅ confirmed |
| Total awarded value (M-09) | findings.md: **€4.98 bn** | **€4.77 bn** | ✅ confirmed |
| Rule-count drift (M-10) | docs: **11 rules** | code: **13**; SINGLE_BIDDER_OPEN (**18.06%**, 2nd-most-frequent) absent from doc table | ✅ confirmed |
| Per-rule counts (M-09) | RATIO_BELOW_50 4,956 · WINNER_TAKES_ALL 1,545 | **3,669** · **1,000** (stale in doc) | ✅ confirmed |
| Triage size (M-09) | findings.md: "`ensemble≥0.7` ≈ 7,000 = 9%" | that is actually `rule_score≥0.7` = 6,249; real `ensemble≥0.7` = **10,889 = 14.4%** (mislabeled) | ✅ confirmed |
| Supervised leaderboard (H-2 / M-08) | champion hgb, OOT ROC-AUC = 1.0 | **8 of 12 configs tie at OOT=CV=PR-AUC=1.0, std=0**; champion picked by sort order | ✅ confirmed |
| OOT ROC-AUC (C-1 / M-03) | leaderboard: 1.0 | champions.json `supervised_champion.oot_rocauc = 1.0` | ✅ confirmed (vacuous — see C-1/C-3) |
| Caveat coverage (M-24) | ADR-0005/responsible_use: "every page" | `show_caveat()` on **5 of 9** pages; missing on Overview, Explore, Entities, Methodology | ✅ confirmed |
| Temporal span (M-23) | findings.md: "exactly 121 months, no gap" | **118** distinct months with data (3 missing) | ✅ confirmed |
| Supplier concentration (M-09) | findings.md: top-10 **8.5%**, HHI **14** | shipped `supplier_summary`: top-10 **17.5%**, HHI ≈ 61 | ✅ confirmed (doc numbers stale) |

*Note on HHI (H-6 / M-18):* the number is method-fragile — doc (14), shipped gold rollup (~61), and a
naïve raw-award recompute (~2,400) all differ. That fragility is itself the point: a **single national
HHI is the wrong statistic**; report concentration per category/CPV.

---

# Final Review — Kosovo Procurement Anomaly-Detection Thesis

*Prepared by the lead reviewer (Data/AI + procurement), for the author, ahead of submission and defense.*

---

## 1. Verdict

This is a strong **engineering** project wrapped around an **evaluation that does not survive contact with an examiner**. The pipeline, rule battery, dashboard, and reproducibility scaffolding are genuinely well built, but every headline performance number the thesis leans on — 0.9999 ROC-AUC, OOT ROC-AUC = 1.0, the "8-family benchmark ensemble," the champion-selection composite — is **circular**: the supervised model predicts the rules from the rules' own input features, and the "validation" targets are those same deterministic rule labels. As written, the thesis is **not defensible as-is**, because the core ML contribution is presented as detection/temporal-generalization performance when it measures only how faithfully a surrogate reproduces a deterministic weighted sum. **The one thing that must be fixed before submission** is the framing of the entire evaluation: stop presenting any rule-label metric (AUC, OOT, precision@K vs rules) as evidence that the system *detects* anything, and either (a) add genuine external validation against the public KRPP debarment / PRB-OSHP decision data, or (b) explicitly and consistently downgrade the ML layer to "exploratory, added value not yet validated." Everything else in this report is secondary to that reframe — but the flagship single-bidder statistic (M-06) and the mismatched `findings.md` numbers (M-09) are close behind, because those are the two things an examiner will quote back at you first.

---

## 2. Critical issues (must fix before submission)

### C-1 — "Out-of-time validation" (OOT ROC-AUC = 1.0) is vacuous three times over  *(M-03)*
**What's wrong.** The OOT experiment reports ROC-AUC = 1.0 and CV ROC-AUC = 1.0 for all 6 HGB and both RF configs (`leaderboard.parquet` rows 31-38; `champions.json` `supervised_champion.oot_rocauc = 1.0`). It is empty for three independent reasons: (1) the label is a **deterministic** function of the features — `y_04 = (rule_score >= 0.4)` at `benchmark.py:424`, `config.py:68`, and `rule_score` (`rules.py:188-190`) is a weighted boolean of the same columns that appear in `X = gold[ML_FEATURES]` (`features.py:167-188`), so a tree simply reconstructs the label; (2) the "temporal" split trains on `yr<=2023`, tests on `yr>2023` (`benchmark.py:378-396`, `config.py:75`) but the target carries no temporal signal; (3) `val99`/`val95` quantiles are computed over the **whole frame** (`rules.py:168,183`), leaking future-period distribution into the labels.
**Why it sinks the thesis.** OOT validation is the single experiment meant to demonstrate temporal generalization — the core requirement of a *monitoring* tool. Presenting 1.0 as robustness invites a one-sentence demolition at the viva.
**Fix.** Remove OOT-on-rule-labels as evidence. If you want a temporal claim, define a genuinely out-of-sample target and recompute all quantile thresholds / context z-scores from **train-period statistics only**. Otherwise state plainly that no temporal-generalization claim is supported.

### C-2 — The headline 0.9999 ROC-AUC is circular: predicting the rules from the rules' own inputs  *(M-01)*
**What's wrong.** `validation_report.json:53` reports `rocauc_mean = 0.999925`, with `supervised_model = "hgb on rule_score >= threshold"` and a feature list identical to the rule inputs. The model at `models.py:245-260` is explicitly "for SHAP only," and `6_Validation.py:50-55` already carries a caption saying the high AUC only means the surrogate approximates the rule layer.
**Why it sinks the thesis.** A committee's first question on 0.9999 is "predicting *what*?" The honest answer — "the rules, from the rule inputs" — means the number says nothing about anomaly or fraud. Read as detection performance (which the abstract/findings framing invites), it collapses the ML contribution.
**Fix.** Never present the AUC as a performance metric. State the circularity **in the same sentence as the number**: "the surrogate reproduces the deterministic rule score with AUC ≈ 1.0, by construction, so SHAP can attribute it." The honest caption already on the Validation page should be promoted everywhere the number appears.

### C-3 — Zero external / ground-truth validation and no baseline  *(M-05)*
**What's wrong.** Every metric in the system is internal self-consistency: proxy AUC vs rules, Jaccard stability, seed consistency, Spearman-with-rules (`benchmark.py:267-306`, `424-425`). There is no external label and no rule_score-only baseline the ensemble must beat (confirmed by grep across `src/` and `docs/`).
**Why it sinks the thesis.** A system marketed as procurement anomaly detection has made *no* attempt to check any output against reality, and offers no baseline showing the ML earns its complexity. The procurement reviewer established that the usual escape hatch is invalid: **external validation is feasible here** — KRPP publishes an exclusion/debarment list and the PRB/OSHP publishes complaint decisions and annulments, both public and matchable on supplier business-id.
**Fix.** Either (a) match a sample of high-ensemble flags against KRPP debarment + PRB/OSHP decisions and report hit rate, or (b) declare the ML layer exploratory and unvalidated. "No ground truth available" is **not** a defensible fallback. Report a rule_score-only baseline in either case.

### C-4 — Champion-selection composite elects detectors for determinism and rule-mimicry, not detection  *(M-02)*
**What's wrong.** `benchmark.py:313-315`: `composite = 0.45*proxy_auc_07 + 0.35*jaccard + 0.20*seed_consistency`. `proxy_auc_07` is agreement with `rule_score>=0.7` (`benchmark.py:268`, circular); `seed_consistency = 1.0` is handed free to every non-stochastic family (`benchmark.py:308-309`); `proxy_auc_04`, precision@K, and Spearman are **excluded** from the objective. The detector best at the benchmark's own precision@500 (LOF `n_neighbors=50`, 0.308) is **thrown out** — the shipped ensemble is `[pca, iso, ocsvm, gmm]`.
**Why it sinks the thesis.** The "8-family benchmark ensemble" is the central methodological contribution, sold as principled model selection. The objective actually rewards reproducing the rules and being a stable/deterministic arbitrary ranking, then discards the detector that scored best on the metric it does compute. An examiner shows this in one question.
**Fix.** Drop proxy-AUC-vs-rules as a selection criterion; stop awarding deterministic families a free 1.0; select against an external/hand-labelled set, or reframe honestly as "the most *reproducible* detectors, with no evidence they detect procurement anomalies." Report AUC(0.4), precision@K, and Spearman next to the composite.

### C-5 — Flagship "single-bidder 35.8%, well above EU" is a pooling artifact refuted by your own data three lines down  *(M-06)*
**What's wrong.** `findings.md:40-41` reports 35.8% and calls it "well above 20-25% of EU-directive-compliant systems." But that 35.8% pools open + minimum + limited procedures (`method_risk_profile.csv`: open **23.44%**, minimum 77.23%, limited 85.45%). Minimum/limited procedures are single-bidder **by design**. Kosovo's open-procedure rate (23.4%) sits *inside* the EU norm. Worse, the Home KPI (`Home.py:48`) shows `rule_score>=0.5 = 16,945 = 22.38%` — a **different population** displayed next to the alarming 35.8% headline.
**Why it sinks the thesis.** This is the single most-cited substantive procurement finding, on the landing page, and it is methodologically wrong (mixed-procedure pooled rate vs an open-procedure benchmark). Both the procurement and combined examiners flag it as the most important substantive issue.
**Fix.** Compare single-bidding **within open procedures only** to EU norms; state that minimum/limited are single-bidder by design and that the operational flag runs on open procedures. Reframe the headline as "open-procedure single-bidding 23.4%, in line with EU norms."

### C-6 — `findings.md` headline numbers do not match the shipped data  *(M-09)*
**What's wrong.** Live parquet vs document: awards 62,128 vs 65,721; total awarded €4.766bn vs €4.98bn; `RATIO_BELOW_50` 3,669/4.85% vs 4,956/6.55%; `WINNER_TAKES_ALL_LARGE` 1,000 vs 1,545; `ensemble>=0.7` 10,889/14.4% vs ~7,000/9%; supplier top-10 17.5% vs 8.5%. The raw-vs-deduplicated award count (65,721 raw → 62,128 post-dedup, `silver.py:57,157`) is being mixed.
**Why it sinks the thesis.** These are the numbers a committee quotes. Once two are shown wrong, every other number is distrusted, and the document explicitly claims figures refresh on `make all` — they clearly weren't.
**Fix.** Regenerate `findings.md` from the current gold layer; add a CI check that fails if figures drift from the post-dedup parquet; stop mixing raw and deduplicated award counts. This is low-effort and buys back credibility immediately.

---

## 3. High-priority issues

- **H-1 — Deployed triage set and rule set substantially DISAGREE  *(M-07)***. On `tender_summary.parquet` (75,710 rows): `ensemble>=0.7` = 10,889, of which **7,312 (67%)** are ML-only (not rule-flagged), while **78.9%** of rule-flagged tenders are demoted below the triage line. The ensemble is an equal-weight mean of four rank-percentile detector columns **plus** `rule_score` and `context_score` on incommensurable scales (`ml.py:156-160`), and `rule_score` is double-used as both the HGB label and an ensemble term. The "two layers must agree" framing (ADR-0002) is contradicted by the shipped data. **Fix:** report the {rule-flagged}×{ensemble-flagged} confusion matrix; decide semantics (if rules are the auditable source of truth, the ensemble must not demote them); rank-transform *all six* components.

- **H-2 — Supervised leaderboard is saturated at 1.0; the champion is arbitrary  *(M-08)***. Eight configs tie at OOT=1.0 / PR-AUC=1.0 / CV=1.0 / std=0 (`leaderboard.md:57-64`); selection sorts on `[oot_rank, cv_rocauc_mean]` (`benchmark.py:591-599`), both pinned at the ceiling, so `pandas.sort_values` (not stable) picks the winner by row order. **Fix:** when a metric saturates, add a discriminating objective (calibration under shift, cost-sensitive metric on an external set) or state all configs are equivalent under the proxy and the choice is parsimony.

- **H-3 — The value-ratio rule family has four compounding defects at once  *(M-11)***. `awarded_value_ratio` (`features.py:120-124`) is simultaneously mis-aggregated (numerator sums award rows, denominator is whole-tender value), under-counted by date-blind dedup, **fabricated for ~28.5% of rows** via median imputation (`models.py:47`), and semantically compared against the entity's own price-only estimate. Three of the highest-weighted rules and the "awarded < estimate" statistics rest on this quotient, and those labels feed the ML target. **Fix:** rebuild the ratio at lot level for fully-awarded single-lot tenders; exclude unawarded rather than impute; benchmark against category/CPV distributions; demote `RATIO_BELOW_50` to a data-quality tier until numerator/denominator are provably comparable.

- **H-4 — Population-relative features make scores non-reproducible while the docstring claims "no train/serve skew"  *(M-13)***. `value_rank_within_*` and the six `CONTEXT_FEATURES` use `groupby().rank(pct=True)` / within-group z-scores (`features.py:141-151`), rolled into the persisted `ensemble_score`, recomputed on every daily full rebuild (`airflow_dags/…:65`). The score attached to a named tender **drifts every rebuild**, directly undermining the lineage/provenance story. **Fix:** persist fitted group statistics as model artifacts and apply them at score time (like the imputer); freeze the reference population; correct the docstring.

- **H-5 — Canonical red flags are missing: contract-splitting / threshold bunching and captive buyer-supplier pairing  *(M-16)***. None of the 13 rules test sub-threshold value bunching or cross-tender buyer-supplier concentration (`WINNER_TAKES_ALL_LARGE` is intra-tender only). These are among the most-cited flags in the OECD/World Bank/Fazekas CRI literature the thesis leans on. **Fix:** add a same-buyer/same-supplier value-bunching rule keyed on clustering below KRPP thresholds, and a buyer-supplier concentration rule; document which flags are out of scope and why.

- **H-6 — Headline national HHI is the wrong statistic  *(M-18)***. `1_Overview.py:115-116` computes one national HHI over all suppliers and `findings.md:53-60` concludes "the national picture is healthy." A competition economist rejects a national HHI regardless of value. **Fix:** report HHI per category/CPV (and per entity-category); drop or heavily caveat the "healthy national market" conclusion.

- **H-7 — DQ suites are advisory, not gates  *(M-19)***. `config.py:91 fail_fast_on_dq = False`; only `Severity.ERROR` affects `passed` (`framework.py:146-157`); currency/future-date/method/supplier-id checks are all WARNING. In the shipped default config, **bad data flows straight to gold and into the models** while "PASS" badges render. **Fix:** default `fail_fast_on_dq = True` for batch builds (or per-severity gating so ERROR always aborts); promote currency/future-date to ERROR; record gating state in the run manifest.

- **H-8 — `num_bidders` is a single point of failure never coverage-checked  *(M-12)***. Every competition figure, single-bidder flag, and ML label keys off `num_bidders` (`silver.py:76,101`), yet the repo never measures tenderer-role completeness by publisher/method. (Refuting note: `tender.tenderers` corroborates `num_bidders` in the 2,000 records sampled, so this is a *coverage-reporting* gap, not a proven parsing bug.) **Fix:** quantify tenderer-role coverage and report it as a caveat before trusting any single-bidder statistic; treat `num_bidders==0`-with-award as a data-quality flag, not `ZERO_BIDDER`.

- **H-9 — Median imputation poisons detectors on ~28.5% of tenders  *(M-32)***. Award-derived features are NaN for unawarded tenders and median-filled across 8 detectors (`models.py:44-49`, `detectors.py`). This teaches the models a distorted "normal" manifold and, worse, imputes unawarded high-value tenders *toward* normal — actively suppressing the exact signal `UNAWARDED_HIGH_VALUE` raises. **Fix:** add missingness-indicator columns and impute with a sentinel, or model award-derived features only on awarded tenders.

- **H-10 — Global quantile thresholds leak future distribution and use the wrong peer group  *(M-30)***. `val99`/`val95` (`rules.py:168,183`) are national tail cutoffs applied once over the whole frame, so `HIGH_VALUE_SINGLE`/`UNAWARDED_HIGH_VALUE` are peer-group-blind and leak into OOT labels. **Fix:** compute high-value thresholds within category/method from a fixed reference period; persist as constants.

---

## 4. Medium / polish

- **M-24 / caveat coverage** — "Every page shows the anomaly-is-not-fraud caveat" (ADR-0005, `responsible_use.md`) is false: 4 of 9 pages omit `show_caveat()`, including Explore and Entities, which pair **named** suppliers/authorities with scores. Emit the caveat structurally from `page_header` and fix the ADR text. *(Also AM-01 — ethical exposure, treat as high.)*
- **M-10 / rule count** — Docs say "11 rules," code has 13 (`rules.py:42-118`); the `findings.md` table hides `SINGLE_BIDDER_OPEN` (weight 0.7, 2nd-most-frequent rule, 18.06%). Update all docs to 13, surface the two missing rules, fix stale module paths.
- **M-28 / RATIO_ABOVE_ESTIMATE** — max weight (1.0) with no dead-band: `ratio > 1.0` fires full weight, so 1.001 alone reaches the flag threshold. Add a minimum overshoot margin (~1.05-1.10) and lower the weight.
- **M-29 / WINNER_TAKES_ALL_LARGE** — no value gate despite "_LARGE"; fires on tiny multi-award tenders. Add a value floor or rename.
- **M-27 / IMPLAUSIBLE_ESTIMATE** — the threshold-dodge pattern is downweighted to 0.4 and mis-labelled "data quality," inverting the risk ordering below single-bidding. Separate genuine data errors from threshold manipulation and reweight.
- **M-26 / method taxonomy** — non-standard vocabulary hard-coded into three open-gated rules; "minimum" is not an OCDS code, "direct" awards absent, 532 None-method tenders escape the open-gated rules while counted in the headline. Map to the OCDS codelist and reconcile against `procurementMethodDetails`.
- **M-17 / ULTRA_SHORT_OPEN** — enforces `<7 days` while citing the EU 35-day minimum (`rules.py:91,161-166`). Set to the applicable legal minimum, ideally graded.
- **M-14 / dedup discards award date** — 2,056 collapses merge awards with *different* dates (`silver.py:30-67`), conflating republication with genuine second awards/amendments and understating spend. Add a within-tender discriminator; audit a sample before trusting €4.77bn.
- **M-15 / amendments** — `contracts[]`/amendment layer never parsed, so cost overruns are invisible. (Note: the current feed contains zero `contracts[]` blocks, so this is a *documented-scope* fix — state it's out of scope and that award dedup may mask modifications.)
- **M-34 / min-max normalization** — persisted per-detector `*_score` columns are batch-relative and set by single extreme records (`models.py:52-58`); rendered as progress bars to auditors. Persist rank-percentile scores instead; winsorize inputs.
- **M-35 / LOF fork** — the shipped `lof` column uses a cached in-sample path; any re-score uses a different formula/scale (`models.py:141-154`), making its reported stability (0.519) path-dependent. Pick one definition and store the fitted min/max.
- **M-38 / ensemble.py** — the module named "ensemble" documents min-max weighted-average scoring at threshold 0.7, but production uses rank-percentile mean at vote quantile 0.95 (`ml.py:156-163`) and never calls it. Rewrite it to be the single source of truth `ml.py` calls.
- **M-36 / Pydantic validation** — checks only the first 200 rows (deterministic `head()`), stops after 10 errors, never gates (`silver.py:200-209`, `contracts.py:96,111`). Make it a uniform random sample and gate, or drop it.
- **M-33 / DQ evidence fixture** — committed `.dq.json` artifacts describe an 8/11-row synthetic fixture, not the 75,710-row population. Regenerate from a full-population `make all` and fail the build on row-count mismatch.
- **M-21 / M-22 / thresholds and inconsistent numbers** — three thresholds (0.4/0.5/0.7) plus an undefended `/2.0` divisor with no sensitivity analysis; the same fact reported as different numbers (e.g., `NEGATIVE_DAYS_TO_AWARD` 19 vs 6; below-50% as 26% vs 6.55%). Pick one primary threshold, justify it, reconcile counts to one number each with a stated per-award-vs-per-tender definition.
- **M-23 / temporal claims** — "no structural gap month" and "exactly 121 calendar months" are both false; 118 months have data, with a 2016 mid-year publishing gap. Correct and document the gap as a coverage caveat.
- **M-31 / end_before_start** — the 22.9% "data-quality crisis" is largely a procedure-semantics artifact of minimal-value procedures; report only within open procedures (13 cases) or label it "expected for minimal-value procedures."
- **M-25 / SHAP framing** — `findings.md:137` and Home sell SHAP as explanation with no caveat, but it only explains why the *rules* fired (`ml.py:146`). Reframe as "shows which rules drove the score," matching the honest caption already on the Anomalies page.
- **M-20 / tests** — smoke-testing only; would pass even if scoring formulas were materially wrong. Add tests pinning exact `rule_score` values, `context_score` at z=1 → tanh(0.5)=0.462, and a fixed end-to-end fixture through the ensemble.
- **M-40 / docstring examples** — worked examples cite wrong numbers (`SINGLE_BIDDER` alone = 0.25 not 0.5; context tanh(z/2) values), breaking the "reproduce with a calculator" promise. Fix comments and add the pinning tests above.
- **M-39 / placeholder** — `findings.md:12` still contains a literal `€[X] billion` placeholder. Fill it and grep for other unresolved `[ ]` placeholders.
- **M-37 / lineage** — `git_sha` resolves to "unknown" in all 8 sidecars and input `rows` are null. Embed a build-time commit hash and populate input row counts.

---

## 5. Amateur / communication gaps

A layperson opening this cold cannot answer their own question — "what is this and can I trust it?" — and several gaps are also *ethical* exposure:

- **Safety promise broken where it matters most (AM-01 / M-24, high).** The "Anomaly ≠ fraud" banner is promised on every page but missing on Overview, Explore, Entities, Methodology — exactly the two pages that name real companies next to red "single-bidder win %" bars. **Fix:** render the caveat from `page_header` (verbose on entity-naming pages) and add the promised PR-blocking test.
- **Named-entity ranking is one click from libel (AM-07, ethics).** Entities lets a user sort suppliers by a risk-flavoured metric and read a real company name beside a scary red bar — the "suspect contractor list" `responsible_use.md` explicitly forbids. **Fix:** add the caveat, an inline note that high single-bidder rates are often legitimate (niche/technical markets), and gate name-level risk sorting behind an acknowledgement.
- **The big scary number has no context beside it (AM-08).** "A third of tenders flagged" is screenshot-bait; the explanation that it's mostly single-bidder prevalence (not a fraud rate) lives in a separate Albanian doc. **Fix:** tooltip on the KPI stating it's a prevalence dominated by single-bidding, not a fraud rate.
- **Two languages split the trust story (AM-02).** README + UI are Albanian; methodology/architecture/findings are English, and the Methodology page renders English docs beside Albanian ones in the same tab strip. No single reader can follow it. **Fix:** bilingual README, one language per audience.
- **"Start here" is unreachable or bewildering (AM-03 / AM-04 / AM-05 / AM-14).** Quick-start is developer-only with no demo link or screenshots; the glossary it tells you to "start at" is the *last* sidebar item; `responsible_use.md` sends careful reviewers straight into the Validation page's ROC-AUC/ECE/Jaccard jargon; and the mandatory `pipeline run` step re-downloads ~200MB even though the app runs off committed gold. **Fix:** add a hosted demo/screenshots + prerequisites box; renumber the glossary to page 1; add a plain-language "what a good/bad number looks like" box on Validation/Krahasimi; tell readers `python -m thesis ui` works out of the box.
- **A flagged tender is a dead end (AM-06).** Every surface says "an auditor should pull the documents," but the app gives an OCID and no link/portal/recipe. **Fix:** a "Next steps" box with a deep link (or exact search recipe) to the KRPP portal and OCP release, plus a one-line "what an auditor would request" checklist.
- **Undefined jargon and inconsistent traffic-lights (AM-09 / AM-11 / AM-12).** Eight undefined model names/metrics before the glossary loads; two different severity colour systems (blue exists in one, not the other) with no on-screen numeric cut-offs; and a panel of 11 near-identical 0-1 scores with no indication which is authoritative. **Fix:** one-line glosses on first use; a single severity function with its thresholds shown in the legend; collapse the model scores by default and label rules as source-of-truth with "disagreement is normal."
- **No "this is a student thesis, not an official tool" statement (AM-10, ethics).** With real government data and grand framing, an amateur can easily cite this as authoritative. **Fix:** a one-line disclaimer at the top of README and Home.

---

## 6. What the thesis CAN vs CANNOT claim — honest rewrite of `findings.md` §8-9

The current §8 ("what we built / can claim") items 4-5 assert a working ML **detector** that "complements rules and surfaces multi-feature anomalies" and SHAP explainability "usable by non-data stakeholders." Given the rule-label circularity, those overclaim. Rewrite as follows.

### §8 — What the thesis CAN legitimately claim
1. A reproducible **medallion data pipeline** (bronze→silver→gold) over the Kosovo OCDS feed, with lineage sidecars, typed contracts, and a DQ framework. *(True; see §8 caveats on gating, M-19, and provenance gaps, M-37.)*
2. A **transparent, literature-grounded rule battery** (13 boolean rules, Fazekas/OECD/World-Bank references) producing an auditable, hand-reproducible `rule_score`. *(True once the docstring/threshold/count inconsistencies M-10/M-21/M-40 are fixed.)*
3. **Descriptive statistics** on Kosovo procurement — competition, concentration, timing, data quality — *reported at the correct unit of analysis*: single-bidding within open procedures (23.4%, in line with EU norms), concentration per category/CPV, not a national HHI.
4. A **surrogate supervised model** that reproduces the deterministic `rule_score` almost perfectly (AUC ≈ 1.0 **by construction**), used **solely** to attribute the rule score via SHAP — i.e., "which rules drove this score," not independent evidence.
5. An **exploratory unsupervised layer** (a 4-model ensemble — pca/iso/ocsvm/gmm, *not* "Isolation Forest") that produces a ranking whose added value over the rules is **not yet validated**.

### §9 — What the thesis CANNOT claim
1. **Cannot** claim any measured *detection* performance. The 0.9999 ROC-AUC, OOT = 1.0, and proxy-AUC/precision@K figures are agreement with the model's own deterministic inputs, not detection of anomaly or fraud (M-01/M-02/M-03/M-08).
2. **Cannot** claim temporal generalization. The OOT experiment is vacuous (deterministic label + feature=label + full-period quantile leakage), so no robustness-over-time claim is supported (M-03/M-30).
3. **Cannot** claim the unsupervised layer "surfaces real anomalies the rules miss." 67% of the triage inbox is ML-only with Spearman-with-rules ~0.05-0.33 and **no** ground-truth check; the claim is currently unfalsifiable (M-04/M-05/M-07).
4. **Cannot** claim the ML "complements" or is validated against the rules as a baseline — no rule_score-only baseline was run, and the ensemble in fact *demotes* 79% of rule-flagged tenders (M-05/M-07).
5. **Cannot** claim "principled model selection." The champion is chosen by a composite that rewards rule-mimicry and free determinism, from a leaderboard saturated at 1.0 (M-02/M-08).
6. **Cannot** claim SHAP gives stakeholders independent evidence of wrongdoing — it restates the rules (M-25).
7. **Cannot** claim the flags/statistics are free of measurement error — they inherit `num_bidders` coverage risk, ratio mis-aggregation, ~28.5% imputation, and non-reproducible population-relative scores (M-11/M-12/M-13/M-32).

The honest positioning that *is* defensible: **"a transparent, reproducible rule-based triage system with an exploratory unsupervised layer and a SHAP-attributable surrogate, whose ML components are engineered but not yet validated against external ground truth."** That framing loses no real contribution and closes every attack vector above.

---

## 7. Prioritized action list

**Do before submission (defense-blocking):**
1. ☐ Reframe every rule-label metric (AUC, OOT, proxy-AUC, precision@K) as faithfulness-to-rules, stated with the circularity in the same sentence — remove them as performance evidence. *(C-1/C-2/C-4/H-2)* **[effort: M] [impact: high]**
2. ☐ Add external validation (KRPP debarment + PRB/OSHP match on a flag sample) **or** explicitly downgrade the ML layer to "exploratory, unvalidated," plus a rule_score-only baseline. *(C-3)* **[effort: L / S for the downgrade path] [impact: high]**
3. ☐ Fix the single-bidder headline to open-procedures-only (23.4%, in-norm); separate it from the 22.38% flagged-KPI population. *(C-5)* **[effort: S] [impact: high]**
4. ☐ Regenerate `findings.md` from current gold; reconcile all headline numbers; fill the `[X]` placeholder; add a drift CI check. *(C-6, M-22, M-39)* **[effort: S] [impact: high]**
5. ☐ Rewrite `findings.md` §8-9 as the honest CAN/CANNOT above. **[effort: S] [impact: high]**
6. ☐ Emit `show_caveat()` from `page_header` so it appears on all 9 pages; add the promised PR-blocking test. *(M-24 / AM-01 / AM-07)* **[effort: S] [impact: high — ethical]**

**High-priority (strongly recommended before defense):**
7. ☐ Report the {rule-flagged}×{ensemble-flagged} confusion matrix and rank-transform all six ensemble components; decide triage semantics. *(H-1)* **[effort: M] [impact: high]**
8. ☐ Report HHI per category/CPV; drop the "healthy national market" line. *(H-6)* **[effort: S] [impact: high]**
9. ☐ Rebuild the value-ratio at lot level, exclude unawarded, demote `RATIO_BELOW_50` to a DQ tier. *(H-3)* **[effort: M] [impact: high]**
10. ☐ Default `fail_fast_on_dq=True` / per-severity ERROR gating; regenerate DQ evidence on the full population. *(H-7, M-33)* **[effort: S] [impact: high]**
11. ☐ Persist group statistics / freeze reference population so scores are reproducible; correct the "no train/serve skew" docstring. *(H-4)* **[effort: M] [impact: high]**
12. ☐ Add missingness indicators instead of median-imputing structurally-missing award features. *(H-9)* **[effort: M] [impact: med]**
13. ☐ Add contract-splitting/threshold-bunching and buyer-supplier concentration rules; document out-of-scope flags. *(H-5, M-16)* **[effort: L] [impact: high]**
14. ☐ Report tenderer-role coverage by publisher/method as a caveat. *(H-8)* **[effort: S] [impact: med]**
15. ☐ Compute high-value thresholds within category/method from a fixed reference period. *(H-10)* **[effort: M] [impact: med]**

**Medium / polish (batchable):**
16. ☐ Docs → 13 rules; surface `SINGLE_BIDDER_OPEN`; fix stale paths. *(M-10)* **[effort: S] [impact: med]**
17. ☐ Add dead-band / value floors / reweight to M-27/M-28/M-29/M-17. **[effort: S] [impact: med]**
18. ☐ Map method vocabulary to OCDS; handle 532 None-method tenders. *(M-26)* **[effort: S] [impact: med]**
19. ☐ Add discriminator to award dedup; audit the 2,056 date-differing collapses. *(M-14)* **[effort: M] [impact: med]**
20. ☐ Make `ensemble.py` the single source of truth; persist rank/robust detector scores; unify LOF path. *(M-38, M-34, M-35)* **[effort: M] [impact: med]**
21. ☐ Add value-pinning unit tests; fix docstring worked examples. *(M-20, M-40)* **[effort: S] [impact: med]**
22. ☐ Fix Pydantic sampling+gating; populate lineage git_sha/rows; correct temporal + end_before_start claims. *(M-36, M-37, M-23, M-31)* **[effort: S] [impact: low-med]**

**Communication (parallel track):**
23. ☐ Bilingual README + demo link/screenshots + prerequisites; "app runs out of the box." *(AM-02/03/14)* **[effort: M] [impact: med]**
24. ☐ Glossary → page 1; plain-language boxes on Validation/Krahasimi; "Next steps" box with KRPP deep link; one severity system with visible thresholds; student-thesis disclaimer. *(AM-04/05/06/08/09/10/11/12)* **[effort: M] [impact: med]**

---

## 8. What's genuinely GOOD — keep this

Be reassured: the engineering is real and above the bar for a master's thesis. Specifically worth defending and keeping:

- **A clean, layered, reproducible pipeline.** The medallion architecture, typed schemas, lineage sidecars, fixed seeds, `make all` reproducibility, and Airflow DAG are professional-grade data engineering. The instinct to make everything reproducible is exactly right — the fix is to make the *scores* honor it (M-13), not to abandon the scaffolding.
- **A transparent, literature-grounded rule layer.** A hand-reproducible weighted-boolean `rule_score` with explicit Fazekas/OECD/World-Bank citations is genuinely the strongest part of the contribution and the honest core the thesis should be built around. The `/2.0` divisor rationale, the open-procedure gating on the right rules, and the auditable design are good instincts.
- **Real intellectual honesty already in the code.** The Validation-page caption (`6_Validation.py:50-55`), the Anomalies-page "not an independent fraud signal" note (`3_Anomalies.py:180-182`), the `benchmark.py:27-31` docstring admitting it measures rule-agreement not fraud, and the `models.py:245` "for SHAP only" comment show the author *already understood* the circularity. The problem is that this honesty lives in captions while the headline framing overclaims — closing that gap is mostly a writing fix, not new research.
- **A serious, well-organized DQ apparatus** (Pydantic + Pandera, suite framework, integrity reports) — the design is sound; it just needs to be *gated* and run on the full population.
- **A thoughtful ethics posture.** The "anomaly ≠ fraud" framing, the responsible-use doc, the glossary, and the cautious-framing ADR reflect exactly the right sensibility for a public-procurement tool. The fixes here are about *enforcing* promises you already made, not inventing new ones.
- **Breadth executed competently.** Ingest → clean → dedup → feature engineering → rules → 8-detector benchmark → ensemble → SHAP → multi-page dashboard is a large, coherent system delivered end-to-end. The volume and integration of work is not in question.

The through-line: you built a solid transparent triage system and an honest surrogate/exploratory ML layer, then oversold the ML as validated detection. Reframe the claims to match what the code actually does, add one genuine external check (or the honest downgrade), and fix the flagship stat and the mismatched numbers — and this becomes a defensible, and in places genuinely good, thesis.

---

## Appendix — 40 verified findings (0 refuted)

| ID | Sev | Verdict | Finding |
|---|---|---|---|
| M-03 | critical | CONFIRMED | 'Out-of-time validation' (OOT ROC-AUC = 1.0) is vacuous three times over |
| M-02 | high | CONFIRMED | Champion-selection composite elects detectors for determinism/rule-mimicry, not for detecting anything |
| M-05 | high | CONFIRMED | Zero external/ground-truth validation and no baseline — the entire evaluation is internal self-consistency |
| M-06 | high | CONFIRMED | Flagship 'single-bidder 35.8%, well above EU' is a pooling artifact — the thesis's own data (open 23.4%) refutes it three lines down |
| M-07 | high | CONFIRMED | Deployed triage set and rule set substantially DISAGREE — 67% of ensemble≥0.7 is unvalidated ML-only, 79% of rule flags are demoted |
| M-08 | high | CONFIRMED | Supervised leaderboard is saturated at 1.0 — the 'champion' choice is arbitrary |
| M-09 | high | CONFIRMED | findings.md headline numbers do not match the shipped data |
| M-11 | high | PARTIAL | The value-ratio rule family is compromised by four compounding defects at once — no single fix rescues it |
| M-13 | high | CONFIRMED | Population-relative features make scores non-reproducible and drift every rebuild — while the docstring claims 'no train/serve skew' |
| M-16 | high | CONFIRMED | Canonical procurement red flags are missing: contract-splitting/threshold bunching and captive buyer-supplier pairing |
| M-18 | high | CONFIRMED | Headline national HHI is the wrong statistic — concentration must be measured per relevant market |
| M-19 | high | CONFIRMED | DQ suites are advisory, not gates — the pipeline persists on any DQ failure in the shipped default config |
| M-01 | medium | PARTIAL | Headline 0.9999 ROC-AUC is circular — the model predicts the rules from the rules' own inputs |
| M-04 | medium | PARTIAL | No evidence the unsupervised layer surfaces anything real — the affirmative 'ML complements rules' claim is unfalsifiable |
| M-10 | medium | CONFIRMED | Docs say 11 rules, code has 13 — and the rule table hides the most consequential detector (SINGLE_BIDDER_OPEN) |
| M-12 | medium | PARTIAL | The whole flag and evaluation layer is hostage to num_bidders as the sole competition proxy, while OCDS fields that would validate it are never parsed |
| M-14 | medium | PARTIAL | Award dedup discards award date and conflates republication with genuine second awards/amendments |
| M-20 | medium | PARTIAL | Test suite is smoke-testing only — it never validates any claim the thesis makes |
| M-24 | medium | CONFIRMED | Governance promise 'every page shows the anomaly-is-not-fraud caveat' is false — 4 of 9 pages omit it, including ones pairing named entities with scores |
| M-26 | medium | CONFIRMED | Non-standard method taxonomy hard-coded into three rules; 'minimum' is not an OCDS code and 'direct' awards are absent |
| M-28 | medium | CONFIRMED | RATIO_ABOVE_ESTIMATE carries the maximum weight (1.0) with no minimum margin — a 0.1% overshoot fires a full-weight flag |
| M-29 | medium | CONFIRMED | WINNER_TAKES_ALL_LARGE has no value threshold despite the '_LARGE' name — fires on tiny multi-award tenders |
| M-30 | medium | CONFIRMED | val99/val95 quantiles computed inside apply_rules over the whole frame — wrong peer group AND future-distribution leak into OOT labels |
| M-32 | medium | CONFIRMED | Median imputation conflates 'missing because unawarded' with a typical value, poisoning the detectors on ~28% of tenders |
| M-34 | medium | CONFIRMED | Min-max normalization of detector scores is non-robust and batch-relative; persisted per-detector *_score columns are set by single extreme records |
| M-35 | medium | CONFIRMED | LOF's in-sample cache creates a train/serve fork — the shipped score uses a different code path and normalization than any re-score |
| M-36 | medium | CONFIRMED | Pydantic contract validation checks only the first 200 rows via a non-random head() and never gates |
| M-39 | medium | CONFIRMED | An unfilled '€[X] billion estimated' placeholder sits in the findings document |
| M-15 | low | PARTIAL | OCDS contracts[]/amendment layer is never parsed — award-low-then-amend-up cost inflation is invisible |
| M-17 | low | PARTIAL | ULTRA_SHORT_OPEN threshold (<7 days) contradicts its own EU 2014/24 citation (35-day minimum) |
| M-21 | low | PARTIAL | Three inconsistent rule_score thresholds (0.4 / 0.5 / 0.7) plus an arbitrary /2.0 divisor, with no sensitivity analysis |
| M-22 | low | PARTIAL | The same fact is reported with several different numbers across findings — internal inconsistency |
| M-23 | low | PARTIAL | Temporal section makes two checkable claims that are both false |
| M-25 | low | PARTIAL | SHAP is presented as explanation but only explains 'why the rules fired', not why anything is anomalous |
| M-27 | low | PARTIAL | IMPLAUSIBLE_ESTIMATE (the threshold-dodge pattern) is downweighted to 0.4 and mis-framed as 'data quality' |
| M-33 | low | PARTIAL | Committed DQ evidence is an 8/11-row smoke fixture, not the 75,710-row population it purports to validate |
| M-37 | low | CONFIRMED | Lineage provenance is partly empty: git_sha resolves to 'unknown' and input row counts are never recorded |
| M-38 | low | CONFIRMED | ensemble.py documents min-max weighted-average scoring while the shipped path uses rank-percentile mean — the reference module contradicts production |
| M-40 | low | CONFIRMED | context_score / rule_score docstring worked examples cite wrong numbers, breaking the 'reproduce with a calculator' promise |
| M-31 | nit | PARTIAL | The 22.9% end_before_start 'data-quality crisis' is largely a procedure-semantics artifact of minimal-value procedures, not a data defect |
