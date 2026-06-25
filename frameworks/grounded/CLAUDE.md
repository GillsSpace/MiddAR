# Project: automated empirical-economics paper (Framework 2 — grounded pipeline)

This extends the gated pipeline with two added capabilities:
- **self-sourcing data**: if no dataset was provided, you acquire one yourself
  (download from the web or generate it from an API such as the Census Bureau,
  FRED, World Bank, BLS) under a source gate that *verifies* it before use.
- **literature grounding**: the paper must situate itself in prior work with
  real, verifiable citations — no uncited claims, no invented references.

## Directory contract
data/raw/      the dataset (provided OR self-sourced). Immutable ONCE SEALED.
data/.sealed   seal file: present => data/raw is frozen. NEVER delete or edit it.
data/SOURCE.md provenance of a self-sourced dataset (URLs, API queries, retrieval date, license)
work/          intermediates: 00_source 01_audit 02_profile 03_design 04_literature 05_analysis 06_robustness
paper/         main.tex + sections/ + tables/ + figures/ + references.bib
replication/   run_all.sh + manifest.json + README.md (AEA-style)
validation/    claims.json (number -> provenance) + data_check.json (source verdict) + report.json (gate results)

## The data seal (how raw stays immutable while still being self-sourceable)
- Until `data/.sealed` exists, you MAY write the dataset into `data/raw/`.
- The instant `data/.sealed` exists, `data/raw/` is frozen — a PreToolUse hook
  blocks every write to it. Do NOT delete or edit `data/.sealed` to get around this.
- The source gate is the ONLY place data enters `data/raw/`, and it MUST end by
  sealing. After that, raw data is read-only for the rest of the run, exactly as
  in a provided-data run.

## Non-negotiables (a violation HALTS the stage; never work around it)
1. Verified data only: no analysis until the source gate passes — data-checker
   wrote validation/data_check.json with "verdict": "PASS", and data is sealed.
2. Real citations only: every reference in paper/references.bib must be a real,
   verifiable work (you fetched/located it). NEVER fabricate a citation, DOI,
   author, year, or venue. Every empirical/positioning claim in the draft that
   asserts prior knowledge must cite a references.bib entry.
3. No orphan numbers: every numeral in main.tex maps to an entry in validation/claims.json.
4. Fresh-env reproduction: "done" only when run_all.sh regenerates every table/figure and the values match the .tex within float tolerance. For self-sourced data, run_all.sh must verify data/raw against the hashes in data/.sealed (it does NOT re-download).
5. Dataset-aware generation: never propose a hypothesis the data can't support (check work/02_profile/).
6. A different model criticizes: the referee subagent reviews before writing and before finalizing.
7. Validation data for any LLM-measured variable: no uncorrected coefficient on a model-generated regressor.
8. Diagnostics are reported, never hidden: a failed assumption becomes a visible limitation.

## Gate order (do not skip)
source -> audit -> profile -> design -> literature -> estimate -> robustness -> referee -> write -> reproduce
Advance only when the prior stage's outputs exist on disk and its checks pass.

### source gate (NEW)
- If data/raw/ is already non-empty and sealed (a provided-data run): confirm the
  files match data/.sealed and PASS the gate immediately.
- Otherwise (a --no-data / self-sourced run):
  1. Delegate to the `data-finder` subagent: it locates and acquires a dataset
     fitting the research idea in EXPERIMENT.md (web download or API/library such
     as the Census, FRED, World Bank), writes it to data/raw/, and records full
     provenance in data/SOURCE.md.
  2. Delegate to the `data-checker` subagent: it verifies the data is (a) correct
     (parses, plausible ranges/units, documented missingness, not truncated/corrupt)
     and (b) fit for purpose (has the variables, coverage, granularity, and sample
     size the design needs). It writes validation/data_check.json with a verdict.
  3. If the verdict is FAIL, loop back to data-finder with the checker's reasons.
     Do NOT proceed on a FAIL.
  4. On PASS, SEAL the data: write data/.sealed as JSON listing each file in
     data/raw/ with its sha256 and byte size, e.g.
     `python3 -c "import json,hashlib,glob,os; ..."`. From here data/raw is frozen.

### literature gate (NEW, after design)
- Delegate to the `literature-scout` subagent. Given the design (work/03_design/),
  it researches existing work on the question/method, fetches/locates real sources,
  and produces paper/references.bib (valid BibTeX, real works only) plus
  work/04_literature/lit_review.md positioning this paper's contribution relative
  to that work (what is new, what is replicated, what gap it fills).
- The gate passes only when references.bib is non-empty, every entry is a real
  work the scout actually located, and lit_review.md names the contribution.
- The write gate must use these: the related-work section cites references.bib,
  and the referee checks that positioning claims are cited and references are real.
