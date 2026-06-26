# Project: automated empirical-economics paper (Framework 4 — spirit)

spirit keeps every rigor and contribution guarantee of grounded2 and reorganizes the
pipeline around three structural bets that grounded2 lacked:

1. **A parallel front end.** Data preparation (source→seal→audit→profile) and the
   literature survey run *concurrently and independently*, so the question set is
   informed by the field — not anchored on whatever the data happens to show.
2. **A ranked question *portfolio*** instead of a single frame. The question gate
   builds a portfolio ranked by CAN (feasibility) and SHOULD (importance),
   **pre-registers it as the multiple-comparison family**, and tests it with
   **multiplicity-corrected inference** — so trying many questions can't silently
   inflate false discovery.
3. **A reusable data module.** `source→seal→audit→profile` is a callable subroutine
   you re-enter whenever a chosen question needs data it lacks (per-dataset sealing
   keeps already-verified data frozen while a new dataset is acquired).

It also adds: an escalating **three-tier review** (a forward `design-checker` before
experiments, a hostile `referee` after results and again after the draft), an
**importance gate** that routes a disappointing result back to the portfolio, a
constructive `editor` in the draft loop, **"no shippable contribution" as a valid
terminus**, and an **orchestrator-authored introspection** at the end (you write it
yourself, with full run context — there is no introspector subagent).

Hold two opposing forces at once: the `referee` minimizes false claims (it only ever
makes the paper smaller); the `advisor` maximizes contribution (it pushes for a bigger,
identified, genuinely-important result). A flawless paper nobody needed is a failure.

## Inputs (≥1 of three; read EXPERIMENT.md first)
EXPERIMENT.md states which are present. Branch the front end on what you have:
- **research AREA / domain only** → run `literature-scout` GENERATIVELY in its
  domain/open-questions mode: mine recent papers' "future work / next-steps /
  limitations" to synthesize candidate questions. Acquire data LATE — only when a
  selected question needs it (the augmentation loop).
- **idea only** → self-source a fitting dataset (or profile provided data); seed the
  portfolio from the sharpened idea + adjacent open questions.
- **dataset only** → seal+audit+profile it; `literature-scout` infers the domain from
  the variables and surfaces open questions answerable by THIS data.
- **combinations** → union the seeds; the `question-ranker` dedups via its fingerprint.

## Directory contract
data/raw/<dataset>/      each provided OR self-sourced dataset in its own subdir. Immutable ONCE that subdir is sealed.
data/raw/<dataset>/.sealed   per-dataset seal: present => that dataset is frozen. NEVER delete or edit a .sealed file.
data/SOURCE.md           provenance of every dataset (one section each: URLs/API queries, retrieval date, license, shape)
api_keys.env             user-supplied API keys (KEY=VALUE). READ-ONLY to you. Use the keys; NEVER print, log, commit, or write a key value anywhere.
ledger.json              (project root) the typed carry-forward ledger — REUSABLE / INDEX-ONLY / QUARANTINED (see below). You maintain it.
work/                    00_source 01_audit 02_profile 03_questions 04_explore 05_design 06_literature 07_analysis 08_robustness 09_pivot
                         (per-question artifacts go in subdirs: 04_explore/q<k>/, 05_design/q<k>/, 07_analysis/q<k>/)
work/03_questions/       portfolio.json (the pre-registered ranked family) + lit_landscape.md + the dedup index
paper/                   main.tex + sections/ + tables/ + figures/ + references.bib
replication/             run_all.sh + manifest.json + README.md (AEA-style)
validation/              claims.json (number -> provenance) + data_check.json (source verdict) + report.json (gate results)
introspection.md         (project root) YOUR end-of-run report to the framework team — orchestrator-authored, NOT a subagent

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
  dataset at any gate after the first is sealed: the question gate or a design gate can
  call `data-finder` to deposit a NEW dataset into a fresh `data/raw/<name>/` subdir,
  have `data-checker` verify it, then seal that subdir. The already-sealed dataset(s)
  stay frozen; the new subdir is writable until you seal it. Do this whenever a second
  source would unlock identification (e.g. pairing the outcome data with weather, a
  policy-shock series, or a Census linkage).
- `.sealed` format (ONE format — match the control plane's `tool.py`, which seals
  provided data): a JSON object `{"sealed": <iso timestamp>, "dataset": "<name>",
  "files": [{"name": ..., "sha256": ..., "bytes": ...}, ...]}`. When YOU seal a
  self-sourced dataset, write this same JSON so tool-sealed and agent-sealed datasets are
  identical and run_all.sh can re-verify either.

## The carry-forward ledger (avoid duplication WITHOUT contaminating new inquiry)
Because spirit runs a *portfolio* of questions against the same sealed data, you reuse
work across questions — but reusing the wrong thing contaminates a fresh inquiry. Tag
every carried-forward artifact in `ledger.json` and respect who may read it:

| Tag | Examples | Who may read it |
|-----|----------|-----------------|
| `REUSABLE` | sealed data, schema/profile, leakage + contamination scan, literature, provenance, outcome-INDEPENDENT derived data (merges, deflation, geo crosswalks) | everyone, always |
| `INDEX-ONLY` | a tried question's fingerprint `(outcome, treatment, sample, estimand, identification)` + its verdict | the `question-ranker` only — for dedup/prioritization |
| `QUARANTINED` | effect sizes, p-values, WHICH spec/split lit up, prior result summaries | the importance gate, the referee, and the final write-up — **NEVER the design of a new question** |

- **Firewall (enforced by the `design-checker`):** a new question's design may justify
  itself ONLY from `REUSABLE` facts + its own explore pass + literature — never from a
  `QUARANTINED` prior result. This is what lets dedup learn "don't re-ask this" without
  feeding a prior answer into a new design.
- **Derived data earns `REUSABLE` only if its construction never touched the outcome.**
  A merge/deflation/crosswalk → REUSABLE. An outlier-drop or sample window chosen
  *because it showed an effect* → QUARANTINED. The `data-profiler`'s contamination scan
  sets the tag.

## Honest multiplicity (the portfolio's defining discipline)
A portfolio that tries N questions and ships the one that "worked" is N-question spec
search; false-discovery inflates across the portfolio. Defend it explicitly:
- **Pre-register the portfolio** at the question gate — the ranked list in
  `work/03_questions/portfolio.json` IS the multiple-comparison family.
- **Family size = the pre-registered portfolio size** (every registered question counts
  toward the correction, whether or not it is ultimately run).
- Each confirmatory experiment is one test in the family; the **importance gate judges
  significance against a corrected threshold** (Romano–Wolf or Benjamini–Hochberg FDR
  over the family size).
- **Mandatory disclosure:** the paper reports how many questions were examined; the
  final audit checks that count against `ledger.json`. Multiplicity disclosed is honest;
  multiplicity hidden is contamination.
- With no held-out partition, two firewalls are load-bearing: explore→confirm WITHIN a
  question (non-negotiable 10) and the QUARANTINED firewall ACROSS questions (above).

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
6. A different model criticizes: the referee subagent reviews after results and before finalizing.
7. Validation data for any LLM-measured variable: no uncorrected coefficient on a model-generated regressor.
8. Diagnostics are reported, never hidden: a failed assumption becomes a visible limitation.
9. Contribution is gated, not assumed: the QUESTION gate must establish — before any
   confirmatory design locks — that each ranked question is first-order important (SHOULD)
   AND feasibly identifiable (CAN), interesting under BOTH signs. The advisor can send a
   framing back, exactly like a BLOCKING referee objection but for triviality.
10. Explore then confirm: per-question exploration (work/04_explore/q<k>/) is clearly
    labeled and the confirmatory design is pre-registered AFTER it and cites what it
    found. No confirmatory claim on a spec chosen by peeking without re-registration.
11. Identification is the spine, ranked: work/05_design/q<k>/design.md enumerates candidate
    identification strategies ranked by credibility (RD / event-study / IV > descriptive
    TWFE) and makes the strongest feasible one PRIMARY — not a robustness afterthought.
12. A load-bearing analysis that fails to run is BLOCKING: never silently demote the
    registered identification strategy to a footnote because a tool wouldn't install.
    Fix it, implement it manually, or route the question back through the importance gate.
13. Portfolio pre-registered + multiplicity-corrected + disclosed: the ranked portfolio
    is the comparison family (family size = portfolio size); the importance gate judges
    significance against the corrected threshold; the paper discloses how many questions
    were examined, audited against ledger.json.
14. Carry-forward firewall: a new question's design may read ONLY `REUSABLE` facts + its
    own explore + literature — never a `QUARANTINED` prior result. The design-checker
    enforces this; a design traceable to a quarantined prior is BLOCKING.
15. "No contribution" is a valid terminus: when the portfolio is exhausted or the budget
    is hit, you MAY emit a documented "no shippable contribution found" record. NEVER
    manufacture importance. (An advisor-blessed null that overturns an ESTABLISHED claim
    is shippable; a foregone, uninteresting null is not.)
16. Introspection authored by the orchestrator: the run is not done until YOU have
    written introspection.md from full run context (not a subagent reading only outputs).

## Gate order (do not skip)
source||literature -> join -> question-gate -> [explore -> design -> design-check -> experiment -> summarize]* -> stage-referee -> importance-gate (loop to question-gate) -> draft<->editor -> final-referee -> reproduce+audit -> introspect(self)
Advance only when the prior stage's outputs exist on disk and its checks pass. The
bracketed block runs per popped question; the importance gate may send you back to the
portfolio for the next question.

### front end (parallel: data module || literature)
- **Data module** (callable subroutine): for each provided+sealed dataset, confirm files
  match its .sealed. For a --no-data / dataset-needing run: `data-finder` acquires a
  fitting dataset into a NEW subdir data/raw/<name>/ (documented in data/SOURCE.md, and
  it flags *what second dataset would make a question identifiable*); `data-checker`
  verifies correctness AND fitness into validation/data_check.json; loop on FAIL; on
  PASS, SEAL that subdir. Then `data-profiler` profiles it AND runs the contamination
  scan, tagging derived artifacts in ledger.json. (Domain-only runs may defer data
  acquisition until the question gate selects a question that needs it.)
- **Literature track** (run concurrently): `literature-scout` GENERATIVELY surveys the
  domain's live debates and highest-value OPEN questions — in domain-only mode it mines
  recent papers' next-steps/limitations to generate candidate questions. Writes
  work/03_questions/lit_landscape.md. Independent of the data so the questions aren't
  anchored on data peeking.
- JOIN BARRIER: proceed to the question gate only when both tracks have produced output.

### question gate (CAN ∧ SHOULD -> ranked portfolio, pre-register the family)
- Invoke the `question-ranker` (synthesizing the `advisor` on SHOULD and the profile +
  identification reasoning on CAN). Ranking is LEXICOGRAPHIC: a question must clear a
  feasibility floor (CAN) to enter, then is ranked by importance (SHOULD). Record BOTH
  scores. A high-SHOULD/low-CAN question is NOT discarded — it triggers the data module
  (augmentation) to acquire the dataset that would make it identifiable.
- Write the ranked portfolio to work/03_questions/portfolio.json and PRE-REGISTER it as
  the multiple-comparison family (family size = portfolio size). Maintain the dedup
  index. The advisor may SEND BACK a trivial framing (BLOCKING, like a referee objection).

### per-question inquiry block (explore -> design -> design-check -> experiment -> summarize)
- Pop the top-ranked unresolved question.
- **explore**: a clearly-labeled exploratory pass on the sealed data (splits by
  time/geography) → work/04_explore/q<k>/explore.md. NOT confirmatory.
- **design**: pre-register work/05_design/q<k>/design.md AFTER exploration; cite what
  explore found; rank identification strategies and make the strongest feasible one the
  PRIMARY spine; state must-pass diagnostics. May loop to the data module for a
  complementary identifying dataset before locking.
- **design-check** (forward gate, before compute): invoke the `design-checker` — it
  reviews identification soundness, explore→confirm integrity (registered after explore
  and cites it), and ENFORCES the carry-forward firewall (no design traceable to a
  QUARANTINED prior). Loop back to design until it passes.
- **experiment**: the `econometrician` runs the registered design with
  MULTIPLICITY-CORRECTED inference over the pre-registered family; reports diagnostics,
  never hiding failures; appends every number to validation/claims.json.
- **summarize**: write up the computed results for this question (work/07_analysis/q<k>/).

### literature gate (defensive positioning + citations, for the surviving question)
- Once a question survives to draft, `literature-scout` runs DEFENSIVELY: produces
  paper/references.bib (real works only) and work/06_literature/lit_review.md
  positioning the contribution. The write gate cites these; the referee checks them.

### stage referee (after summarize)
- Invoke the `referee` on the completed experimental stage: confounding, leakage,
  p-hacking, overclaiming, missing diagnostics, provenance. Resolve every [BLOCKING];
  loop back to experiment/design as needed.

### importance gate (after stage referee)
- Re-invoke the `advisor`: is the result interesting AND significant against the
  multiplicity-CORRECTED threshold? If NO → record the verdict as INDEX-ONLY in
  ledger.json (resolved-uninteresting) and loop back to the question gate to pop the next
  question (work/09_pivot/ records the loop-back decision). If YES → proceed to draft.
- If the portfolio is exhausted with nothing shippable, emit the "no contribution" record
  (non-negotiable 15).

### draft <-> editor
- Draft the paper; work the draft with the `editor` (constructive: clarity, structure,
  honest positioning). The editor may NOT introduce an unverified number — provenance
  discipline (non-negotiable 3) still applies.

### final referee
- Invoke the `referee` again on the full paper. Resolve every [BLOCKING].

### reproduce + audit
- run_all.sh regenerates every table/figure/PDF from the SEALED data; values must match
  the .tex within tolerance (for self-sourced data it verifies the per-dataset .sealed
  hashes, does NOT re-download). The audit also checks: orphan numbers (every numeral in
  claims.json), citation reality, seal integrity, and the MULTIPLICITY DISCLOSURE (the
  #questions-examined count matches ledger.json).

### introspect (last — YOU write it)
- YOU, the orchestrator, write introspection.md (project root) from full run context:
  what the framework's structure produced, what worked (preserve), and located problems +
  concrete suggestions for the framework team — including how the portfolio, the
  multiplicity correction, and the carry-forward firewall actually behaved. Do NOT
  delegate this to a subagent. The run is complete only once it exists.

When all gates pass AND introspection.md exists, write validation/report.json summarizing
each gate's status and evidence (include the source verdict, the pre-registered portfolio
+ family size, the question that shipped and its CAN/SHOULD scores, the identification
strategy used, the corrected-significance verdict, the #questions examined, any data
augmentation, and the advisor's question-gate + importance-gate verdicts), and stop.
