# Project review — 18 September 2026

> **Update, 22 October 2026.** The final pre-submission review verified the
> full 378-test suite and two subsequently added date regressions: **380 passing
> tests in total** (303 unit/contract, 12 integration, 65 dashboard). Ruff and
> mypy are clean, and all five releases validate. The date regressions cover
> local month/year boundaries, the fixed summer offset, missing dates, filtering
> and aggregation, and preservation of scores, instants and input data. The
> continuation review also corrected the date-shift counts and annual-rate
> comparison in the methodology. It found issues that need a new
> publication to fix (a rule overlap that inflates the review queue, UTC date
> bucketing, and a narrow award de-duplication case). They are documented in
> [the methodology's known issues](methodology.md#known-issues-in-the-published-release).
> The counts below are as of 18 September.

## Assessment

This is a strong bachelor-level **data-engineering and explainability project**.
It has a working pipeline, explicit data contracts, reproducible model selection,
checks that bind published results to their inputs, and explanations that reconstruct
the actual published scores. The backend checks below found no failing tests or
invalid published releases.

Its main research limitation is **independent evaluation**, not implementation
completeness. The bundled manual-review queue contains 150 sampled tenders but
zero completed outcome labels. The model metrics compare predictions with rules
created from overlapping input features. They do not establish detection accuracy,
a false-positive rate, or an improvement over human review or the rule-only baseline.
The thesis is defensible when presented as transparent screening and exploratory
ranking; claims of demonstrated fraud or corruption detection would exceed the evidence.

The highest-value next research step is to complete the documented manual audit
against original tender documents, with blinded review and independent agreement
checks, then compare reviewed outcomes across the sampled groups. See
[the manual audit protocol](manual_audit_protocol.md).

## Verified dataset and publication

- 75,710 procurement-process records in the static KRPP/OCP Publication 115 snapshot.
- 62,129 award-supplier rows after the project's deduplication.
- Data in 118 of 121 calendar months from March 2016 to March 2026. This is the
  publication's coverage, not a verified census of all procurement in Kosovo.
- Bidder data is observed for 69,603 records (91.9%); missing bidder data is not zero bidders.
- 205 populated contracting-authority IDs, plus a separate missing-identity group
  in the authority summary; 9,940 supplier keys under the documented identity rules.
- 235 records have a rule score of at least 0.5. All rule, ensemble, and context
  scores are populated. These scores are screening priorities, not probabilities.
- The full stored benchmark contains all 35 successful configurations: 23
  unsupervised and 12 supervised. The deployed ensemble uses One-Class SVM,
  Isolation Forest, HBOS, and KNN.
- All five publication stages — bronze, silver, gold, benchmark, and ML — pass
  their artifact-hash, upstream-chain, implementation, configuration, and runtime
  checks. All five stages are reported as fresh.

Award values describe recorded award decisions. The extract does not establish
that corresponding contracts were signed, performed, or paid.

## Checks actually run

Checks used the existing local environment, Python 3.9.6 on macOS.

| Check | Result |
|---|---|
| `.venv/bin/python -m pytest tests/unit tests/contracts tests/integration -q` | **312 passed**, no skips or failures, in 173.93 seconds: 303 unit/contract tests and 9 integration tests |
| `.venv/bin/python -m pytest tests/test_streamlit_pages.py tests/test_dashboard_presentations.py -q` | **63 passed** in 144.51 seconds, including all 9 pages, literal search, result selection, filter interactions and chart calculations |
| `.venv/bin/python -m thesis pipeline validate-releases` | All 5 releases valid against current implementation and runtime |
| `.venv/bin/python -m thesis pipeline status` | All 5 stages fresh; all declared outputs present |
| Fresh in-memory data-quality evaluation of all 7 table suites, including source-aware reconciliation checks | **68 checks: 64 passed, 0 errors, 4 warnings**; no evidence files overwritten |
| Fresh SHAP artifact checks, including predictions from the persisted HGB model | **6 of 6 passed** for all 75,710 records; maximum raw-output reconstruction difference `3.375077994860476e-14` |
| `.venv/bin/python -m ruff check src/thesis tests/unit tests/contracts tests/integration` | Passed |
| `.venv/bin/python -m ruff format --check src/thesis tests/unit tests/contracts tests/integration` | All 77 files already formatted |
| `.venv/bin/python -m mypy src/thesis` | Passed: 45 source files |
| `.venv/bin/python -m pip check` | No broken installed requirements |
| `uv lock --check` | Passed; lock resolves 261 packages |
| `docker version` and `docker compose config --quiet` | Local Docker engine available; Compose configuration valid |
| Final full-project Ruff checks and formatting | Passed; all 95 Python files formatted |

Together the completed suites cover **375 passing tests**. After the UI changes,
all five publication stages were validated again successfully.

The integration suite exercises a synthetic bronze→silver→gold run, checks that
the committed findings report matches a fresh deterministic rendering (apart
from its input-timestamp line), and reconstructs ensemble scores for every
published record to a tolerance of
`1e-12`. The separate SHAP check verifies the rule-proxy model's raw log-odds;
SHAP is not presented as an explanation of the ensemble score.

## Source-data warnings that remain

These are detected source limitations, not silently repaired data or failing
publication checks. The table-level suites allow warnings under the current policy.

| Warning | Current observation | Meaning |
|---|---:|---|
| Missing release date | 31 tender records | These records cannot be assigned to a release month without inventing a date |
| Price-quotation/value-band conflict | 7 tender records | Published procedure and value require documentary review; not an automated legal finding |
| Contracting-authority name/ID collision | 2 normalized names across 4 source IDs | The same normalized name occurs under different source IDs; the project keeps those IDs separate |
| Award-to-lot title linkage | 869 award rows without one exact unique match | 505 unmatched, 244 ambiguous, 120 missing titles; 61,260 rows do have a unique exact title match |

The award-value comparisons remain at tender level. A title match is not proof
of a shared, verified lot identifier. Supplier keys also require care: a fallback
name or source-party identifier is not an independently verified legal identity.

## Performance observation

The release validation is thorough but costly for interactive pages. A local
measurement with a warm filesystem took approximately 0.93 seconds for silver,
1.23 seconds for gold, and 2.92 seconds for ML validation. The guarded dashboard
reader took 10.44 seconds; reading its four Parquet tables alone took 0.17 seconds.
The initial UI loader implementation therefore added roughly 5.1 seconds for
validation even on a cached rerun, and roughly 15.5 seconds on a cold dashboard
load. These are one-run local observations, not a formal performance benchmark.

Validation recursively rechecks the same upstream files and fingerprints complete
tables. Any future performance work must preserve rejection of modified artifacts,
even when their manifest is unchanged, and prevent mixing publication generations.
Caching only by time would weaken that contract.

## Scope of this review

The bundled dataset, trained models, release manifests, and backend source were
preserved. Pipeline-generated artifacts are bound to the exact backend source,
including package-level presentation helpers; changing those files would require
an intentional new publication. UI changes can live in the Streamlit application
without changing the statistical results.

This review did **not** download a newer dataset, rerun the full multi-hour model
benchmark or model-training pipeline, build/run the Docker image, execute the
remote CI matrix, check every external document link, or create human review labels.
The Docker availability/configuration checks are not evidence that the image was
built successfully. The stored benchmark was validated and its tests run; its
35 configurations were not all retrained during this review.

## Dashboard improvements

All nine pages were reviewed and revised around the questions an outside visitor
would ask. Navigation is now in Albanian, with analysis pages separated from
methodology and technical checks. The landing page starts with four meaningful
indicators and two charts. Detailed formulas, identifiers, sensitivity analysis,
and research explanations remain available in optional sections.

Concrete correctness and usability fixes include:

- Overview time-series and competition denominators now come from the selected
  records. Previously, category, authority, method and value filters did not
  change those charts. Missing dates and bidder counts stay explicitly missing.
- Value filters use euro amounts, category labels use Albanian, and distributions
  use readable euro bands. The median is identified as the median, not an average.
- Tender search treats punctuation literally and supports selecting a result
  directly, with clear empty and invalid-identifier states.
- Negative date differences are displayed as dates requiring verification,
  rather than as a valid negative period for submitting offers.
- Charts and explanatory text distinguish award decisions, estimated amounts,
  signed contracts and actual payments. Supplier competition percentages disclose
  when their denominator is award rows instead of distinct tenders.
- Entity charts preserve separate source identities even when names coincide.
  The authority count excludes the unknown-identity bucket. Score tooltips keep
  decimals instead of rounding small scores to zero.
- Validation charts use the full 0–1 scale. Missing later-period evaluations are
  no longer replaced by cross-validation scores. Best-model rows remain intact
  configurations rather than combinations of values from different rows.
- The glossary explains statistical and procurement terms with examples. It uses
  the current ensemble definition rather than a fixed model-agreement count.

Albanian terminology was checked against official Kosovo sources, including
[e-Prokurimi's separate award and signing notices](https://e-prokurimi.rks-gov.net/SPIN_PROD/application/ipn/DocumentManagement/DokumentPodaciFrm.aspx?id=2577669),
[KRPP procurement guidance](https://e-prokurimi.rks-gov.net/Home/ClanakItemNew.aspx?id=268),
and [BQK statistical terminology](https://bqk-kos.org/wp-content/uploads/2025/08/BQK_FSR_21.pdf).
Source tender titles and organization names remain as published; the interface
does not silently rewrite evidence.

The application was started at `http://127.0.0.1:8501` and inspected in a browser.
Live checks confirmed that selecting **Shërbime** changes the overview to
**20,910** tenders and approximately **€2.17 billion** in estimated value,
updates the charts, and carries the selection into tender search.
