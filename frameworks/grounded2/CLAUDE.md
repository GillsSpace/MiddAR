# Project: automated empirical-economics paper (Framework 3 — grounded2)

grounded2 keeps every rigor guarantee of the grounded pipeline and adds the thing
grounded lacked: a force that pushes the work toward being *important*, not just
*correct*. grounded reliably produced impeccably-executed trivial papers because
every gate it owned was a rigor gate (and the single adversary, the referee, only
ever made the claim smaller). grounded2 adds an importance-maximizer, an
explore-then-confirm discovery path, first-class ranked identification, the ability
to acquire MORE data mid-study, and a mandatory self-introspection at the end.

It extends grounded with:
- **self-sourcing data** (kept): acquire the dataset yourself if none was provided,
  under a source gate that verifies it before use.
- **literature grounding** (kept): real, verifiable citations only.
- **a contribution counterweight** (NEW): an `advisor` subagent and a FRAME gate +
  PIVOT-CHECK gate whose objective is "is this first-order important and interesting
  under BOTH signs of the result?" — the adversarial opposite of the referee.
- **explore → confirm** (NEW): a labeled exploratory pass finds where the signal is;
  the confirmatory design is pre-registered *after* and must cite what exploration found.
- **data augmentation** (NEW): you may acquire additional/complementary datasets
  mid-study (e.g. pair the outcome source with a source of identifying variation, or
  add weather/Census data) because sealing is now PER-DATASET, not one global seal.
- **auto-introspection** (NEW): when the work is done, an `introspector` subagent
  writes introspection.md for the framework team.

## Directory contract
data/raw/<dataset>/      each provided OR self-sourced dataset in its own subdir. Immutable ONCE that subdir is sealed.
data/raw/<dataset>/.sealed   per-dataset seal: present => that dataset is frozen. NEVER delete or edit a .sealed file.
data/SOURCE.md           provenance of every dataset (one section each: URLs/API queries, retrieval date, license, shape)
api_keys.env             user-supplied API keys (KEY=VALUE). READ-ONLY to you. Use the keys; NEVER print, log, commit, or write a key value anywhere.
work/                    00_source 01_audit 02_profile 03_frame 04_explore 05_design 06_literature 07_analysis 08_pivot 09_robustness
paper/                   main.tex + sections/ + tables/ + figures/ + references.bib
replication/             run_all.sh + manifest.json + README.md (AEA-style)
validation/              claims.json (number -> provenance) + data_check.json (source verdict) + report.json (gate results)
introspection.md         (project root) the introspector's end-of-run report to the framework team

## The data seal (per-dataset, so augmentation stays possible)
- Datasets live in subdirectories: `data/raw/<dataset>/`. Each is sealed independently.
- Until `data/raw/<dataset>/.sealed` exists, you MAY write that dataset's files.
- The instant `data/raw/<dataset>/.sealed` exists, that dataset is frozen — a
  PreToolUse hook blocks every write to it. Other (unsealed) datasets stay writable,
  which is exactly what lets you add a SECOND dataset later. Do NOT delete or edit
  any `.sealed` to get around this.
- Data enters `data/raw/` ONLY at the source gate or a later augmentation loop, and
  each dataset MUST be sealed right after its data-checker verdict passes.
- AUGMENTATION IS ALWAYS AVAILABLE — whether the initial dataset was PROVIDED or
  self-sourced. Because the seal is per-dataset, you may acquire a complementary
  dataset at any gate after the first is sealed: the frame, design, or pivot gate can
  call `data-finder` to deposit a NEW dataset into a fresh `data/raw/<name>/` subdir,
  have `data-checker` verify it, then seal that subdir. The already-sealed dataset(s)
  stay frozen; the new subdir is writable until you seal it. Do this whenever a second
  source would unlock identification (e.g. pairing the provided outcome data with
  weather, a policy-shock series, or a Census linkage).

## API keys (api_keys.env)
- A user maintains `api_keys.env` at the project root with available keys, e.g.
  `CENSUS_API_KEY=...`, `FRED_API_KEY=...`, `BLS_API_KEY=...`.
- When a source needs a key, READ it from api_keys.env (parse KEY=VALUE lines — e.g.
  in Python) and pass it to the API client. Prefer a keyed official source when its
  key is present.
- NEVER print, echo, log, hard-code, or write any key value into code, data,
  SOURCE.md, the paper, replication scripts, or anywhere on disk. If a needed key is
  absent, fall back to a keyless source or report the gap — never invent a key.

## Non-negotiables (a violation HALTS the stage; never work around it)
1. Verified data only: no analysis on a dataset until its data-checker verdict in
   validation/data_check.json is PASS and that dataset is sealed.
2. Real citations only: every paper/references.bib entry is a real, verifiable work
   you located. NEVER fabricate a citation, DOI, author, year, or venue. Every
   prior-knowledge claim in the draft cites a references.bib entry.
3. No orphan numbers: every numeral in main.tex maps to an entry in validation/claims.json.
4. Fresh-env reproduction: "done" only when run_all.sh regenerates every table/figure
   and the values match the .tex within float tolerance. For self-sourced data,
   run_all.sh verifies data/raw against the per-dataset .sealed hashes (it does NOT re-download).
5. Dataset-aware generation: never propose a hypothesis the data can't support (check work/02_profile/).
6. A different model criticizes: the referee subagent reviews before writing and before finalizing.
7. Validation data for any LLM-measured variable: no uncorrected coefficient on a model-generated regressor.
8. Diagnostics are reported, never hidden: a failed assumption becomes a visible limitation.
9. Contribution is gated, not assumed: the FRAME gate must establish — before design
   locks — that the question is first-order important AND interesting under BOTH signs
   of the result. The advisor can send the framing back, exactly like a BLOCKING
   referee objection but for triviality.
10. Explore then confirm: exploration (work/04_explore/) is clearly labeled and the
    confirmatory design is pre-registered AFTER it and cites what it found. No
    confirmatory claim on a spec chosen by peeking without re-registration.
11. Identification is the spine, ranked: work/05_design/design.md enumerates candidate
    identification strategies ranked by credibility (RD / event-study / IV > descriptive
    TWFE) and makes the strongest feasible one PRIMARY — not a robustness afterthought.
12. A load-bearing analysis that fails to run is BLOCKING: never silently demote the
    registered identification strategy to a footnote because a tool wouldn't install.
    Fix it, implement it manually, or trigger the pivot-check.
13. Pivot when importance fails: if the primary result is null AND the question is only
    interesting if non-null, the PIVOT-CHECK gate must re-scope (promote a discovered
    result via re-registration, pursue the identification extension, augment data, or
    accept-and-write the null ONLY if the advisor agrees the null overturns an
    *established* claim — not a speculative worry).
14. Auto-introspection: the run is not done until the introspector subagent has written
    introspection.md.

## Gate order (do not skip)
source -> audit -> profile -> frame -> explore -> design -> literature -> estimate -> pivot -> robustness -> referee -> write -> reproduce -> introspect
Advance only when the prior stage's outputs exist on disk and its checks pass.

### source gate (acquire + verify + seal, per dataset)
- For each provided dataset already in data/raw/<name>/ and sealed: confirm files
  match its .sealed and pass.
- For a --no-data / self-sourced run:
  1. `data-finder` acquires a dataset fitting EXPERIMENT.md into a NEW subdir
     data/raw/<name>/ (web download or API such as Census/FRED/World Bank/BLS, using
     a key from api_keys.env when required), and documents it in data/SOURCE.md.
     Beyond the outcome source, it should ask the contribution-unlocking question:
     *what second dataset would make this identifiable?* and flag candidate pairings.
  2. `data-checker` verifies correctness AND fitness, writing validation/data_check.json.
  3. On FAIL, loop back to data-finder. On PASS, SEAL that dataset:
     write data/raw/<name>/.sealed listing each file's sha256 + byte size.

### frame gate (NEW — the contribution counterweight, before design locks)
- Invoke the `advisor` subagent (and use the `literature-scout` generatively here, to
  surface the highest-value open questions and live debates in the domain — not to
  position a pre-chosen question). The advisor must answer:
  is this first-order important? does it move a belief or a decision? is it interesting
  under BOTH signs? what is the strongest honest version? is there a more important
  question this data — or a data PAIRING — could answer?
- Output work/03_frame/frame.md with the chosen high-value question and the advisor's
  verdict. If the data (even paired) can only support a descriptive estimand for a
  question that is only interesting if non-null, that is a go/no-go signal: re-scope,
  augment data (loop to data-finder), or stop — do not march to a foregone null.

### explore gate (NEW — find the signal before pre-registering)
- A clearly-labeled exploratory pass on the sealed data (splits by time/geography) to
  locate where the signal is. Write work/04_explore/explore.md. Findings here inform
  the confirmatory design but are NOT themselves confirmatory results.

### design gate (confirmatory, identification-first)
- Pre-register work/05_design/design.md AFTER exploration; it must cite what explore
  found, rank identification strategies by credibility with the strongest feasible one
  as the primary spine, and state must-pass diagnostics. The design MAY loop back to
  the source gate / data-finder to acquire a complementary identifying dataset into a
  new data/raw/<name>/ subdir (then checked + sealed) before locking.

### literature gate (defensive positioning + citations, after design)
- `literature-scout` produces paper/references.bib (real works only) and
  work/06_literature/lit_review.md positioning the contribution. The write gate cites
  these; the referee checks positioning claims are cited and references are real.

### pivot-check gate (NEW — after estimate, before robustness)
- Re-invoke the `advisor`. If the primary is null and was only-interesting-if-non-null
  (per the frame gate), force an explicit re-scope decision per non-negotiable 13.
  Record the decision in work/08_pivot/pivot.md.

### introspect gate (NEW — last)
- Invoke the `introspector` subagent. It writes introspection.md (project root): what
  the framework's structure produced, what worked (preserve), and located problems +
  concrete suggestions for the framework team. The run is complete only once it exists.
