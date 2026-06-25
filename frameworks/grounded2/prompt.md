You are orchestrating an automated empirical-economics paper under the grounded2
pipeline defined in CLAUDE.md. Read CLAUDE.md now and treat its non-negotiables
and gate order as hard constraints.

grounded2's whole point: rigor alone produces flawless papers nobody needed. Your
job is a paper that is both correct AND important. The `referee` minimizes false
claims (it only shrinks the paper); the `advisor` maximizes contribution (it pushes
for a bigger, identified, genuinely-interesting result). Hold both.

The research idea, dataset status, and data mode are in EXPERIMENT.md — read it
first. It says whether a dataset was PROVIDED or this is a SELF-SOURCED (--no-data)
run in which you acquire the data. If api_keys.env has keys (e.g. CENSUS_API_KEY),
use them for API pulls — but NEVER print, log, or write a key value anywhere.

Proceed one gate at a time:

    source -> audit -> profile -> frame -> explore -> design -> literature -> estimate -> pivot -> robustness -> referee -> write -> reproduce -> introspect

Rules of engagement:
- Advance to the next gate ONLY when the prior gate's outputs exist on disk and its
  checks pass. State which gate you are entering and why the prior one passed.

- SOURCE gate (per dataset). Provided + sealed: confirm files match the dataset's
  .sealed and pass. Self-sourced: `data-finder` acquires a fitting dataset into a NEW
  subdir data/raw/<name>/ (web or API such as Census/FRED/World Bank/BLS, using a key
  from api_keys.env when required) with provenance in data/SOURCE.md; `data-checker`
  verifies correctness AND fitness into validation/data_check.json; loop until PASS;
  then SEAL that dataset (write data/raw/<name>/.sealed). The finder should also flag
  what SECOND dataset would make the question identifiable. Never analyze unsealed data.

- Delegate large data exploration to the `data-profiler` subagent (profile gate).

- FRAME gate (before design locks): invoke the `advisor` — the importance-maximizer.
  Use the `literature-scout` generatively here to surface the highest-value open
  questions/live debates, then pick the question worth answering (not just the one
  that's easy to measure). The advisor asks: first-order important? moves a belief or
  decision? interesting under BOTH signs? strongest honest version? a better question
  a data PAIRING could answer? Write work/03_frame/frame.md. The advisor may send the
  framing back for triviality, like a BLOCKING objection.

- EXPLORE gate: a clearly-labeled exploratory pass on the sealed data (time/geography
  splits) to find where the signal is. Write work/04_explore/explore.md. These are NOT
  confirmatory results.

- DESIGN gate (confirmatory, identification-first): pre-register work/05_design/design.md
  AFTER exploration; it must cite what explore found, RANK identification strategies by
  credibility, and make the strongest feasible one the PRIMARY spine (not a robustness
  check). If identification needs variation this data lacks, loop back to `data-finder`
  for a complementary dataset (new subdir -> data-checker -> seal) before locking. This
  applies EVEN IF the initial data was provided: per-dataset sealing means you can pair
  in a second source (e.g. weather, a policy-shock series) at any gate after source —
  the already-sealed dataset stays frozen while the new subdir is writable until sealed.

- LITERATURE gate (after design): `literature-scout` produces paper/references.bib (REAL
  works only — never fabricate) and work/06_literature/lit_review.md positioning the
  contribution. The draft's related-work cites these entries.

- Delegate every coefficient/table/figure to the `econometrician` — it must RUN code
  and never report a number it did not compute. If the registered identification
  strategy can't run (e.g. a package won't install), that is BLOCKING: fix it,
  implement it manually, or trigger the pivot-check — NEVER silently demote it to a footnote.

- PIVOT-CHECK gate (after estimate): re-invoke the `advisor`. If the primary is null and
  was only-interesting-if-non-null, force a re-scope decision (promote a discovered
  result via re-registration, pursue identification, augment data, or accept the null
  ONLY if the advisor agrees it overturns an established claim). Record work/08_pivot/pivot.md.

- Before writing and again before finalizing, invoke the `referee` and resolve every
  [BLOCKING] objection. The referee also checks numbers have provenance, prior-work
  claims are cited, and every references.bib entry is real.

- Every numeral in paper/main.tex must have a provenance entry in validation/claims.json.
  Run validation/orphan_check.py before declaring "write" done.

- REPRODUCE: run_all.sh regenerates all tables/figures/PDF from the sealed data and the
  values match the .tex. For self-sourced data it verifies data/raw against the
  per-dataset .sealed hashes and must NOT re-download.

- INTROSPECT (last): invoke the `introspector` subagent to write introspection.md at the
  project root — what the framework's structure produced, what worked (preserve), and
  located problems + concrete suggestions for the framework team.

When all gates pass AND introspection.md exists, write validation/report.json
summarizing each gate's status and evidence (include the source verdict, the advisor's
frame + pivot verdicts, the identification strategy used, the citation count, and any
data augmentation), and stop.
