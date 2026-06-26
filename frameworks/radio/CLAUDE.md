# Project: automated empirical-economics paper (Framework 5 — radio)

radio keeps every rigor and contribution guarantee of spirit and reorganizes the run
around one diagnosis from the last two introspections: **we spend our most expensive
tokens committing to questions we cannot yet tell are feasible.** It rests on three
structural bets:

1. **Cheap previews before expensive commitment.** Before any question is pursued, a
   lightweight per-candidate *preview* (a quick novelty check + a design skeleton + an
   *opportunistic* back-of-napkin data probe) tells the scorers what is actually
   promising — so under-powered or non-novel questions are demoted BEFORE a single full
   inquiry cycle is spent.
2. **Ensemble generation + scoring against a publication ladder.** Three `question-proposer`
   sub-agents (top-3 ideas each → collate) and three `question-scorer` sub-agents (1–10
   each → sum, max 30) replace a single ranker. They judge against `guides/QUESTION_GUIDES.md`:
   *Tier 1* = publishable in a top-5 journal; if nothing clears that gate, the same candidates
   are re-scored at *Tier 2* (strong field/applied) — which relaxes importance and the leap but
   NEVER identification or honesty. "No viable paper" fires only when both tiers fail.
3. **Slim the heavyweight discipline, keep the adversarial backstop.** spirit's
   pre-registered multiplicity portfolio and typed carry-forward ledger are both trimmed
   (pursuing one de-risked question shrinks the need for both). The different-model
   `referee` and the named `design-audit` / `experiment-audit` gates remain the
   load-bearing guard, and **"no viable paper"** stays a first-class terminus.

**Operating doctrine — always prefer sub-agents, and fan out wherever work is
independent:** data scans, question proposal (×3), previews (×candidate), scoring (×3),
experiments (×N), and paper sections (×N) all run as parallel sub-agents. Many *cheap*
agents up front buy the information that avoids the *expensive* dead ends downstream.

Hold two opposing forces: the `referee` minimizes false claims (it only ever shrinks the
paper); the `experiment-reviewer` maximizes contribution (it pushes for a bigger,
identified, genuinely-important result). A flawless paper nobody needed is a failure.

## Inputs (≥1 of three; read EXPERIMENT.md first)
EXPERIMENT.md states which are present, plus `settings`. Branch the front end on what you have:
- **research AREA / domain only** → run the Lit-Domain track GENERATIVELY (mine recent
  papers' future-work / next-steps / limitations to synthesize candidate questions);
  Data Scan surveys what data exists. Acquire data LATE — only when the chosen question
  needs it (the augmentation loop).
- **idea only** → Data Scan + Lit-Domain around the idea; seed proposers from the
  sharpened idea + adjacent open questions.
- **dataset only** → seal+audit+profile it; Lit-Domain infers the domain from the
  variables and surfaces open questions answerable by THIS data.
- **combinations** → union the seeds.

## Settings (EXPERIMENT.md `settings` block)
- `augment-data` (on/off): whether mid-run acquisition of a complementary dataset is allowed.
- `iteration-limits`: max question-attempts (how many ranked questions you may pursue),
  max design-audit loops, max experiment-audit loops. Every backward loop below is bounded
  by these. If unspecified, default to: 5 question-attempts, 3 design-audit loops,
  3 experiment-audit loops.
- `target-tier`: `ladder` (DEFAULT) — score Tier 1 (top-5) first, and if nothing clears the
  gate, re-score the same candidates at Tier 2 (strong field/applied) and pursue a Tier-2
  winner; "no viable paper" only when BOTH tiers fail. Set `top-5-only` to keep the old
  behavior (stop the moment Tier 1 fails, no fallback). See the publication ladder below.

## Directory contract
data/raw/<dataset>/      each provided OR self-sourced dataset in its own subdir. Immutable ONCE that subdir is sealed.
data/raw/<dataset>/.sealed   per-dataset seal: present => that dataset is frozen. NEVER delete or edit a .sealed file.
data/SOURCE.md           provenance of every dataset (one section each: URLs/API queries, retrieval date, license, shape)
api_keys.env             user-supplied API keys (KEY=VALUE). READ-ONLY to you. Use the keys; NEVER print, log, commit, or write a key value anywhere.
guides/                  SHIPPED reference rubrics — QUESTION_GUIDES.md (the top-journal question/scoring bar) and PAPER_GUIDES.md (the writing bar). Read-only inputs.
ledger.json              (project root) the SLIM no-peek record (see below). You maintain it.
work/                    00_scan 01_questions 02_data 03_design 04_experiments 05_review 06_literature
                         (per-attempt artifacts go in subdirs: 01_questions/previews/q<k>.md, 03_design/q<k>/, 04_experiments/q<k>/)
work/00_scan/            data_landscape.md + lit_landscape.md + gaps.md (the parallel front end's output)
work/01_questions/       candidates.json + previews/q<k>.md + scores.json + ranked.json
paper/                   main.tex + sections/ + tables/ + figures/ + references.bib
replication/             run_all.sh + orphan_check.py + verify_seals.py + manifest.json (SHIPPED primitives — extend, don't re-author)
validation/              claims.json (number -> provenance) + data_check.json (source verdict) + report.json (per-stage gate ledger)
introspection.md         (project root) YOUR end-of-run report to the framework team — orchestrator-authored, NOT a subagent

## The data seal (per-dataset, so augmentation stays possible)
- Datasets live in subdirectories: `data/raw/<dataset>/`. Each is sealed independently.
- Until `data/raw/<dataset>/.sealed` exists, you MAY write that dataset's files. The
  instant it exists, a PreToolUse hook blocks every write to that dataset. Other
  (unsealed) datasets stay writable — which is what lets you add a SECOND dataset later.
- Data enters `data/raw/` ONLY at a Data Source step (when the chosen question needs it),
  and each dataset MUST be sealed right after its data-checker verdict passes. NEVER
  delete or edit a `.sealed` to get around the freeze.
- `.sealed` format (ONE format — match the control plane's `tool.py`, which seals provided
  data): `{"sealed": <iso timestamp>, "dataset": "<name>", "files": [{"name": ...,
  "sha256": ..., "bytes": ...}, ...]}`. When YOU seal a self-sourced dataset, write this
  same JSON so tool-sealed and agent-sealed datasets are identical and verify_seals.py /
  run_all.sh can re-verify either.

## Data handling discipline (token cost)
Sealed datasets are large (often multi-MB / 10^5+ rows). Loading a file into a Python/pandas
process is free; only what an agent PRINTS or Reads into context costs tokens — and a full file
can be millions of tokens. So everywhere data is touched (data-scout, data-finder, data-checker,
data-profiler, question-previewer's probe, econometrician), the rule is the same: pull to disk
(`curl -sS -o`), compute IN CODE, and emit only BOUNDED summaries (`df.shape`, `df.dtypes`,
`df.head(10)`, `df.describe()`, recomputed hashes; tables capped to ≤20 rows / ~30 cols). NEVER
`cat`, `Read`-in-full, or `print()` a whole dataframe; write big profiles/logs to a file and read
back only the small summary. This is quality-neutral — correctness needs shape/schema/sample/hash,
not the raw rows in context.

## The slim no-peek firewall (replaces spirit's typed ledger)
radio pursues ONE question at a time, so cross-question contamination risk is low — but the
loop-back from Experiment Review can spawn a fresh question, and a fresh question's design
must not inherit a prior attempt's ANSWER. Keep it light:
- `ledger.json` is a thin record: for each attempted question, store its fingerprint
  `(outcome, treatment, sample, estimand, identification)`, its verdict, and a `no_peek`
  list of the prior attempt's result dirs (`work/04_experiments/q<k>/`,
  `work/05_review/q<k>.md`).
- **Firewall:** when you develop the design for a NEW question, that design may justify
  itself ONLY from the sealed data + its own preview/explore + literature — NEVER from a
  `no_peek` prior result (another attempt's effect size, p-value, or which-spec-lit-up).
  The `design-auditor` enforces this and the `referee` re-checks it. A design traceable to
  a no-peek prior is BLOCKING.
- Outcome-INDEPENDENT derived data (merges, deflation, geo crosswalks, schema/profile
  facts) is freely reusable. Only outcome-DEPENDENT results are no-peek.

## Honest multiplicity (slimmed — within-design, conditional)
radio does not pre-register a cross-question family. The comparison family is the set of
hypotheses actually tested WITHIN the shipped design:
- If the shipped design tests >1 hypothesis, the `econometrician` applies a correction
  (Benjamini–Hochberg FDR) over that within-design family and reports raw AND corrected
  significance; the `experiment-reviewer` judges the corrected one.
- The paper DISCLOSES how many questions were generated, previewed, and pursued (audited
  against `ledger.json`). Multiplicity disclosed is honest; multiplicity hidden is
  contamination. The previews already prune most dead ends before estimation, so the
  surviving family is small — but disclosure is still mandatory.

## API keys (api_keys.env)
- A user maintains `api_keys.env` at the project root (e.g. `CENSUS_API_KEY=...`,
  `FRED_API_KEY=...`, `BLS_API_KEY=...`). When a source needs a key, READ it from
  api_keys.env (parse KEY=VALUE lines, e.g. in Python) and pass it to the client. Prefer a
  keyed official source when its key is present.
- NEVER print, echo, log, hard-code, or write any key value into code, data, SOURCE.md,
  the paper, replication scripts, or anywhere on disk. If a needed key is absent, fall back
  to a keyless source or report the gap — never invent a key.

## Non-negotiables (a violation HALTS the stage; never work around it)
Inherited (keep):
1. Verified data only: no analysis on a dataset until its data-checker verdict in
   validation/data_check.json is PASS and that dataset is sealed.
2. Real citations only: every paper/references.bib entry is a real, verifiable work you
   located. NEVER fabricate a citation, DOI, author, year, or venue. Every prior-knowledge
   claim in the draft cites a references.bib entry.
3. No orphan numbers: every numeral in main.tex maps to an entry in validation/claims.json.
4. Fresh-env reproduction: "done" only when run_all.sh regenerates every table/figure and
   the values match the .tex within tolerance. For self-sourced data, run_all.sh verifies
   data/raw against the per-dataset .sealed hashes (it does NOT re-download).
5. Dataset-aware generation: never propose a hypothesis the data can't support.
6. A different model criticizes: the referee reviews after the draft (and the design /
   experiment audits use a different model than the producer).
7. Diagnostics are reported, never hidden: a failed assumption becomes a visible limitation.
8. Load-bearing analysis that fails to run is BLOCKING: never silently demote the registered
   identification strategy to a footnote because a tool wouldn't install. Fix it, implement
   it manually, or route the question back through Experiment Review.
9. "No viable paper" is a valid terminus — but only after the LADDER is exhausted: under the
   default `target-tier: ladder`, it fires when neither Tier 1 nor Tier 2 produced a candidate
   above the gate, or the ranked list and question-attempts are exhausted with nothing
   shippable. Emit a documented, GRADED run summary (the best candidate and the tier it would
   realistically reach with better data). NEVER manufacture importance, and NEVER roll extra
   generation rounds just to clear a gate.
10. Introspection authored by the orchestrator: the run is not done until YOU have written
    introspection.md from full run context (not a subagent reading only outputs).
11. Per-dataset seal hook: data/raw/<dataset>/ is frozen once sealed; never edit/delete a .sealed.

New in radio:
12. The publication ladder: proposers and scorers judge every question against
    guides/QUESTION_GUIDES.md. Score Tier 1 (top-5) first; if nothing clears the >20 gate,
    re-score the SAME candidates at Tier 2 (strong field/applied — AEJ:Applied/Policy,
    AER:Insights, JHR/JPubE/JOLE/JEEM/REStat). Tier 2 relaxes IMPORTANCE and the LEAP, and
    NOTHING ELSE — identification, feasibility, and honesty hold at full strength (a
    rigor/feasibility failure caps the score at ~4 on BOTH tiers). The >20 gate at each tier is
    a real bar, not a "good enough" bar; the active tier propagates to the experiment-reviewer
    and the writer so a Tier-2 question is judged and framed as a Tier-2 paper, not top-5.
13. Preview before commit: no full inquiry cycle begins until the chosen question carries a
    preview (work/01_questions/previews/q<k>.md) that the scorers read.
14. Opportunistic power signal: the preview's data probe runs LIVE only if data is on hand
    or fetchable+analyzable in < ~1 min (identifying variation? N? a basic correlation?);
    otherwise reason qualitatively. Never block a preview on a heavy data pull.
15. Claims registered at estimate time: each analysis/robustness script writes its
    validation/claims.json entries AS it produces numbers — not retro-registered at write
    time. orphan_check.py is the final safety net, not the registration mechanism.
16. Units field mandatory: every numeric column/claim carries an explicit `units` field,
    cross-checked against the level tables (catches the share-vs-pp / 100x error class).
17. Conservative SE for null/robustness claims: any "precise null" or "robust across specs"
    claim must use the MOST CONSERVATIVE credible standard error reported, never the
    tightest. Verified in code before the experiment-auditor sees it.
18. Mandatory executable confound test before any causal bless: the design must name the
    single most obvious confound test for its identification strategy as a must-pass
    diagnostic (e.g. for DiD: drop never-treated controls + among-treated/timing-only ATT +
    randomization inference; report treated-vs-control pre-period balance on the outcome);
    the econometrician RUNS it; the experiment-reviewer may not bless a causal headline until
    it has passed. (Fixes test_04's read-only-advisor gap.)
19. Registered-deviation re-validation: any post-registration substitution of a PRIMARY
    estimator or inference method must be named in a fallback ladder written in the design,
    and re-checked as a deviation. A FAILED registered diagnostic may NOT be re-scored PASS
    by switching estimators.
20. Resource discipline: split any script that could time out into checkpointed pieces;
    update validation/report.json at every stage boundary so a crash resumes, not restarts.
21. Paper checked against guides/PAPER_GUIDES.md (the condensed rubric), not raw PDFs;
    citations alphabetical.

## Model tiers (cost discipline)
- haiku: cheap fan-out — data-scout, question-proposer (×3), question-scorer (×3).
- sonnet: mechanical compute/acquire/profile/draft — data-finder, data-profiler,
  question-previewer, econometrician, writer, editor, final-editor.
- opus: judgment gates and adversarial review — data-checker, literature-scout,
  design-auditor, experiment-reviewer, referee. (experiment-auditor: opus.)
The two pure reviewers (referee; design-auditor) are read-only — they judge, they don't patch.

## Gate order (do not skip)
data-scan || lit-domain -> generate(3 proposers) -> preview(parallel) -> score@Tier1(3 scorers) -> GATE(>20)
  -> if no Tier-1 winner: re-score@Tier2(3 scorers, same candidates) -> GATE(>20)   [unless target-tier=top-5-only]
  -> [ data-source(if needed) -> develop-design -> design-audit -> experiments(parallel) -> experiment-audit -> experiment-review@active-tier ]*
  -> draft<->editors -> final-editor -> openaireview -> final-referee -> reproduce+audit -> introspect(self)

Advance only when the prior stage's outputs exist on disk and its checks pass; state which
gate you are entering and why the prior one passed. Record each stage boundary in
validation/report.json. The bracketed block runs per pursued question; Experiment Review
routes a non-shippable result to the NEXT ranked question (see below).

### front end (parallel: data scan || lit-domain)
- **Data Scan** (subroutine, fan out `data-scout` ×N over different data angles): search
  (web + API endpoints) → evaluate reliability → summarise available data, with NO
  acquisition yet. Write work/00_scan/data_landscape.md.
- **Lit-Domain** (`literature-scout` in GENERATIVE mode, concurrent): find recent/impactful
  lit → evaluate → summarise to a lit list → identify gaps & "next steps" → audit. Write
  work/00_scan/lit_landscape.md + gaps.md. Keep independent of the data so questions aren't
  anchored on data peeking.
- JOIN BARRIER: proceed to generation only when both tracks have produced output.

### generate questions (3 proposers, then collate)
- Fan out three `question-proposer` sub-agents; each returns its TOP 3 questions, judged
  against guides/QUESTION_GUIDES.md and informed by the scan + lit landscapes.
- Collate / combine / dedup into a candidate pool (~5–9) → work/01_questions/candidates.json
  (each as a precise estimand: outcome, treatment/regressor, sample, identification).

### preview each candidate (parallel — the new core)
- Fan out one `question-previewer` per candidate (parallel). Each produces a one-page
  work/01_questions/previews/q<k>.md with: (1) a quick novelty verdict (novel /
  partly-covered / done-already), (2) a design skeleton (estimand + what would identify it +
  data needed), (3) an OPPORTUNISTIC feasibility/power signal — run a tiny live probe only
  if data is on hand or fetchable+analyzable in < ~1 min (non-negotiable 14), else reason.

### score & rank (3 scorers, then the ladder gate)
- **Tier 1.** Fan out three `question-scorer` sub-agents at **Tier 1** (top-5); each scores
  EVERY candidate 1–10 reading the previews, against §5 of guides/QUESTION_GUIDES.md. Sum
  (max 30) → work/01_questions/scores.json + ranked.json. Keep the top 5.
- **GATE (Tier 1):** if the top score is > 20 AND question-attempts remain → pursue with
  `active_tier = 1`.
- **Tier-2 fallback** (default `target-tier: ladder`; skip if `top-5-only`): if no Tier-1
  winner, RE-SCORE the SAME candidates ONCE at **Tier 2** (§6 anchors — three scorers, reuse
  the existing previews, NO new generation), recording the tier-2 scores alongside in
  scores.json and re-ranking. **GATE (Tier 2):** if a candidate now clears > 20 on the Tier-2
  scale → pursue with `active_tier = 2`. Set `active_tier` in validation/report.json and
  ledger.json so it propagates to the experiment-reviewer and writer.
- **The cheap re-score is the ONLY sanctioned fallback — no sharpening rounds.** When Tier 1
  fails, the next move is the Tier-2 re-score (3 haiku scorers over the EXISTING candidates +
  previews — a few ×10k tokens), NOT a regeneration/"sharpening" round (new proposers + new
  previews, which cost ~300k and tend not to move the gate). Regenerating identification-upgraded
  reframes to chase a bar is the exact spec-search non-negotiable 9 forbids. A bounded regeneration
  (≤1 round) is permissible ONLY if BOTH tiers have failed AND the scorers name a specific,
  concrete reframe that would plausibly clear — never as a default, never to roll the dice.
- **No viable paper:** only if BOTH tiers fail (or the ranked list / question-attempts are
  exhausted). Emit the GRADED "no viable paper" run summary (non-negotiable 9): what was
  scanned, proposed, the best candidate, and the tier it could realistically reach with better
  data. Do NOT roll extra generation rounds to clear a gate.

### per-question inquiry block (pop the top-ranked unpursued question)
- **data-source** (only if the question needs data not yet sealed, and `augment-data` is
  on): `data-finder` acquires into a NEW data/raw/<name>/ subdir (provenance in
  data/SOURCE.md); `data-checker` verifies correctness AND fitness into
  validation/data_check.json; loop on FAIL; on PASS, SEAL that subdir; `data-profiler`
  profiles it. Write work/02_data/.
- **develop-design**: pre-register work/03_design/q<k>/design.md — rank identification
  strategies and make the strongest feasible one the PRIMARY spine; state must-pass
  diagnostics INCLUDING the mandatory confound test (non-negotiable 18); write a fallback
  ladder for any primary estimator (non-negotiable 19).
- **design-audit** (forward gate, before compute): invoke `design-auditor` — sound
  identification? will it actually answer the question? obvious improvements? Does it name
  the confound test? Does it read only sealed-data + preview + literature (no no-peek prior)?
  Loop back to develop-design on FAIL (bounded by max design-audit loops).
- **experiments** (parallel): fan out `econometrician` sub-agents to code & conduct the
  registered experiments — each registering claims at estimate time (15), carrying a units
  field (16), using conservative SEs for null/robust claims (17), running the confound test
  (18), and splitting long scripts (20). Then document & summarise → work/04_experiments/q<k>/summary.md.
- **experiment-audit** (Pass/Fail): invoke `experiment-auditor` — correctness (code does
  what it claims), units consistency (16), conservative-SE (17), confound test actually ran
  (18), deviation re-validation (19). Loop back to experiments on FAIL (bounded).
- **experiment-review**: invoke `experiment-reviewer` — significant contribution? deserves a
  paper **at the run's `active_tier`** (Tier 1 top-5, or Tier 2 field/applied — judged on the
  matching §5/§6 anchors; rigor + the confound test hold regardless of tier)? Routing:
  * **No** → "any NEW interesting question raised?"
    - YES → score ONLY the new question (one `question-scorer` pass each, or a single pass)
      and merge it into ranked.json; mark this attempt's dirs no_peek in ledger.json; pop
      the new top.
    - NO → drop this question, mark it no_peek, and take the NEXT question already on
      ranked.json (no re-scoring). Terminate as "no viable paper" only when the ranked list
      is exhausted or question-attempts run out.
  * **Yes** → proceed to the literature gate + draft.

### literature gate (defensive positioning + citations, for the surviving question)
- `literature-scout` runs DEFENSIVELY (Lit-Checker / positioning mode): produces
  paper/references.bib (REAL works only) and work/06_literature/lit_review.md positioning the
  contribution. The draft cites these; the referee checks them.

### draft <-> editors (parallel sections)
- `writer` drafts & revises, spawning `editor` advisories; draft multiple sections in
  PARALLEL. Editors may NOT introduce an unverified number (non-negotiable 3). Run
  python3 replication/orphan_check.py before declaring the draft done.

### final-editor (vs PAPER_GUIDES)
- `final-editor` checks the full draft against guides/PAPER_GUIDES.md (the condensed rubric,
  not the source PDFs): structure, the intro recipe, the contribution statement, table/figure
  self-containedness, the red-flag list. Citations alphabetical.

### openaireview (final pass)
- Run the `/openaireview` skill on the assembled paper; fold its findings into a revision pass.

### final referee
- Invoke the `referee` on the full paper. Resolve every [BLOCKING]; loop back to draft.

### reproduce + audit (shipped primitives)
- bash replication/run_all.sh regenerates every table/figure/PDF from the SEALED data; values
  must match the .tex within tolerance (self-sourced data: python3 replication/verify_seals.py
  re-verifies the per-dataset .sealed hashes, does NOT re-download). python3
  replication/orphan_check.py confirms every numeral has provenance. The audit also checks
  citation reality, seal integrity, units consistency, and the MULTIPLICITY DISCLOSURE
  (#questions generated/previewed/pursued matches ledger.json). Extend these shipped scripts;
  do not re-author them from scratch.

### introspect (last — YOU write it)
- YOU, the orchestrator, write introspection.md (project root) from full run context: what
  the framework's STRUCTURE produced, what worked (preserve), and located problems + concrete
  suggestions for the framework team — including how the previews, the ensemble
  generation/scoring, the top-journal bar, and the slim firewall actually behaved, and where
  tokens went. Do NOT delegate this to a subagent. The run is complete only once it exists.

When all gates pass AND introspection.md exists, write validation/report.json summarizing each
stage's status and evidence (the data/lit scan, the candidate count, the previews, the Tier-1
scores AND any Tier-2 re-score, the `active_tier` and the question that shipped, the
identification strategy used, the confound-test result, the within-design multiplicity verdict,
any data augmentation, the experiment-review verdict, and the #questions generated/previewed/
pursued), and stop.
