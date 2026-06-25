# How the `grounded2` Framework Works — A Step-by-Step Guide

`grounded2` (Framework 3) is the third MiddAR instruction-set. Like every framework,
it is a *directory-scoped bundle* — a `CLAUDE.md`, a `prompt.md`, a `.claude/`
folder of subagents + hooks + permissions, and a `framework.json` manifest — that
gets copied into a project directory and drives one Claude Code instance to produce
a reproducible empirical-economics paper.

This document explains the machinery: how it uses tool calls, how it enforces its
gate checks, how it delegates to subagents, what its design loop looks like, and
where (and where not) it allows non-linear research steps.

> **One-line thesis.** `grounded` reliably produced *impeccably-executed trivial
> papers* because every gate it owned was a rigor gate and its only adversary (the
> `referee`) could only ever make the claim **smaller**. `grounded2` adds an
> importance-maximizer (`advisor`) plus FRAME and PIVOT-CHECK gates to push the
> work toward being **important**, an explore→confirm discovery path, first-class
> ranked identification, mid-study data augmentation via *per-dataset* sealing, and
> a mandatory self-introspection at the end.

---

## 0. The files that make up the framework

```
frameworks/grounded2/
  framework.json              <- manifest: name, gate summary, skeleton dirs, capability flags
  prompt.md                   <- the kickoff message handed to the orchestrator Claude
  CLAUDE.md                   <- the always-loaded contract: non-negotiables + gate order
  .claude/
    settings.json             <- tool permissions (allow-list) + the PreToolUse hook wiring
    hooks/protect_raw.sh      <- the per-dataset immutability enforcer (the data "seal")
    agents/
      data-finder.md          <- acquires datasets (initial + complementary)      [sonnet]
      data-checker.md         <- verifies a dataset before it is sealed           [opus]
      data-profiler.md        <- schema / distributions / leakage scan            [sonnet]
      literature-scout.md     <- open-questions (generative) + citations (defensive) [opus]
      advisor.md              <- the contribution maximizer (frame + pivot gates)  [opus]
      econometrician.md       <- writes + RUNS estimation/robustness code          [sonnet]
      referee.md              <- hostile reviewer; only shrinks the claim          [opus]
      introspector.md         <- end-of-run critique of the FRAMEWORK              [opus]
```

There are two layers of "instructions" the orchestrator sees:

1. **`prompt.md`** — the opening user message. It tells the orchestrator to read
   `CLAUDE.md`, treat its non-negotiables and gate order as hard constraints, and
   states the rules of engagement gate by gate.
2. **`CLAUDE.md`** — the project memory file Claude Code auto-loads every turn. It
   holds the **directory contract**, the **per-dataset seal** rules, the **API-key**
   rules, the **14 non-negotiables**, and the canonical **gate order**. Because it
   reloads every turn, it is the durable constraint the orchestrator cannot drift away
   from as context grows.

`framework.json` is metadata for MiddAR's control plane (the `tool.py` CLI), not for
Claude. Its important flags:

```json
"supports_no_data": true,     // can self-source data if none is provided
"supports_augment": true,     // can acquire MORE data mid-study
"seal_mode": "per-dataset",   // each dataset frozen independently (enables augmentation)
"uses_api_keys": true         // may read api_keys.env for Census/FRED/BLS/etc.
```

It also lists the **skeleton directories** the project is scaffolded with — the
numbered `work/00_source … work/09_robustness` stages plus `paper/`, `replication/`,
and `validation/`. The numbered directories *are* the gate order made physical: a
gate "passing" means its output file exists on disk in the matching folder.

---

## 1. The design loop at a glance

The orchestrator advances through a **14-gate linear pipeline**, one gate at a time:

```
source -> audit -> profile -> frame -> explore -> design -> literature
       -> estimate -> pivot -> robustness -> referee -> write -> reproduce -> introspect
```

The governing rule (from both `prompt.md` and `CLAUDE.md`):

> **Advance to the next gate ONLY when the prior gate's outputs exist on disk and its
> checks pass. State which gate you are entering and why the prior one passed.**

So the loop is not "think then write" — it is **produce a disk artifact, verify it,
announce the transition, advance**. Each gate has a designated output path, and the
existence + validity of that file is the gate condition. This is what makes the
pipeline auditable after the fact: you can reconstruct exactly what happened by
reading `work/00_source/ … work/09_robustness/`, `validation/`, and `paper/`.

### What each gate does and what it must leave on disk

| # | Gate | What happens | Output artifact(s) | Driver |
|---|------|--------------|--------------------|--------|
| 1 | **source** | Acquire (if needed) + verify + **seal** each dataset | `data/raw/<name>/`, `data/SOURCE.md`, `validation/data_check.json`, `data/raw/<name>/.sealed` | `data-finder` → `data-checker` |
| 2 | **audit** | Sanity-check the sealed inputs before profiling | `work/01_audit/` | orchestrator |
| 3 | **profile** | Schema, distributions, missingness, **leakage scan** | `work/02_profile/profile.md` + `profile.json` | `data-profiler` |
| 4 | **frame** | Pick the *important* question; importance gate | `work/03_frame/frame.md` (+ `lit_landscape.md`) | `advisor` + `literature-scout` (generative) |
| 5 | **explore** | Labeled exploratory pass — find where the signal is | `work/04_explore/explore.md` | orchestrator / `econometrician` |
| 6 | **design** | Pre-register confirmatory design, **identification-first, ranked** | `work/05_design/design.md` | orchestrator (may loop to `data-finder`) |
| 7 | **literature** | Real citations + positioning | `paper/references.bib`, `work/06_literature/lit_review.md` | `literature-scout` (defensive) |
| 8 | **estimate** | Run the registered estimation + diagnostics | `paper/tables/`, `paper/figures/`, `validation/claims.json` | `econometrician` |
| 9 | **pivot** | Re-check importance against the result; re-scope if needed | `work/08_pivot/pivot.md` | `advisor` |
| 10 | **robustness** | Robustness checks for the primary spine | `work/09_robustness/` | `econometrician` |
| 11 | **referee** | Hostile review; resolve every `[BLOCKING]` | referee objections resolved | `referee` |
| 12 | **write** | Draft the paper; every numeral has provenance | `paper/main.tex` (+ `sections/`) | orchestrator |
| 13 | **reproduce** | `run_all.sh` regenerates everything from sealed data | `replication/run_all.sh` run clean | orchestrator |
| 14 | **introspect** | Critique the **framework** for the next version | `introspection.md` (project root) | `introspector` |

When all gates pass **and** `introspection.md` exists, the orchestrator writes
`validation/report.json` (a per-gate status summary including the source verdict, the
advisor's frame + pivot verdicts, the identification strategy used, the citation
count, and any augmentation) and **stops**.

---

## 2. How it uses tool calls

The orchestrator is a normal Claude Code agent: it acts only through tool calls
(`Bash`, `Read`, `Write`, `Edit`, `WebSearch`, `WebFetch`, and the `Agent`/Task tool
to spawn subagents). `grounded2` shapes those tool calls in three ways.

### (a) A permission allow-list (`.claude/settings.json`)

Tool calls are constrained by an explicit allow-list, so the framework's guarantees
don't depend on the model "remembering" to behave:

```jsonc
"allow": [
  "Bash(python3:*)", "Bash(pip:*)", "Bash(pdflatex:*)", "Bash(latexmk:*)",
  "Bash(curl:*)", "Bash(wget:*)",
  "Bash(bash replication/run_all.sh)",
  "WebSearch", "WebFetch",
  "Read(./**)",                                    // read anywhere in the project
  "Write(./data/raw/**)", "Write(./data/SOURCE.md)", "Write(./data/.sealed)",
  "Edit(./data/raw/**)",
  "Write(./work/**)", "Write(./paper/**)", "Write(./replication/**)", "Write(./validation/**)",
  "Edit(./work/**)",  "Edit(./paper/**)",  "Edit(./replication/**)",  "Edit(./validation/**)"
]
```

Notable consequences:

- **Computation is real.** Numbers come from `python3` runs, not from the model's
  head. PDF building uses `pdflatex`/`latexmk`. Data is pulled with `curl`/`wget` or
  Python API clients.
- **Writes are scoped to the output tree.** The model can write into `data/raw/**`,
  `work/**`, `paper/**`, `replication/**`, and `validation/**` — and nowhere else.
- **Reads are unrestricted** within the project (`Read(./**)`), so any subagent or the
  orchestrator can inspect any prior artifact. The pipeline is transparent to itself.

### (b) Every coefficient is a *computed* tool call, never a recalled number

Non-negotiable #3 ("no orphan numbers") plus the `econometrician`'s mandate make this
concrete: **every numeral that lands in `paper/main.tex` must have a provenance entry
in `validation/claims.json`** mapping it to the producing script + log line. The
`econometrician` subagent's first rule is *"Every number you report must come from
code you actually ran. Never invent or recall figures."* It also fixes a random seed
(recorded in `replication/manifest.json`) so runs are deterministic.

This is checked mechanically: `validation/orphan_check.py` must be run before the
"write" gate is declared done, and `referee` independently verifies every draft
number has a `claims.json` entry.

### (c) Web tool calls are gated to *real* artifacts

`WebSearch`/`WebFetch` are how `data-finder` acquires data and how `literature-scout`
finds papers — but citation integrity is a non-negotiable: a DOI/URL must be one the
scout *actually retrieved*, never a plausible-looking guess. The `referee` spot-checks
that `references.bib` entries are real.

---

## 3. How it enforces gate checks

There are **three independent enforcement mechanisms**, layered so that a failure of
one is caught by another.

### Mechanism 1 — The deterministic hook (`protect_raw.sh`): the data seal

This is the only enforcement that is *outside the model's control entirely*. It is a
`PreToolUse` hook wired in `settings.json`:

```jsonc
"hooks": {
  "PreToolUse": [
    { "matcher": "Write|Edit",
      "hooks": [{ "type": "command", "command": "bash ./.claude/hooks/protect_raw.sh" }] }
  ]
}
```

Before **every** `Write` or `Edit`, Claude Code pipes the tool input (as JSON) into
`protect_raw.sh`. The script extracts the target `file_path` and decides ALLOW or
BLOCK. Exit code `2` blocks the tool call; the model sees the stderr message and must
adapt. Its logic, in order:

1. **A `.sealed` file that already exists can never be edited or deleted.** The seal
   itself is immutable — you cannot "unseal" data to get around the freeze.
2. Writes **outside `data/raw/`** are always allowed (work/, paper/, etc. are free).
3. If a **legacy global `data/.sealed`** exists, *all* of `data/raw` is frozen.
4. **Per-dataset seal:** a write to `data/raw/<dataset>/<file>` is blocked **iff**
   `data/raw/<dataset>/.sealed` exists. Other, unsealed datasets stay writable.

This per-dataset design is the load-bearing trick behind **data augmentation** (see
§6). Because each dataset is frozen independently, you can add a *second* dataset into
a fresh `data/raw/<name>/` subdir mid-study while the already-sealed dataset stays
provably untouched. The enforcement is structural, not a promise: once verified data
is sealed, no later tool call can silently alter it.

### Mechanism 2 — The "artifact must exist on disk" rule

Each gate's pass condition is the existence + validity of a named file. The
orchestrator is required to **state which gate it is entering and why the prior one
passed**, and may only advance when the prior stage's output file is present and its
checks pass. There is no "I'll come back to it" — a missing `work/0X_*/...` file means
the gate is not passed. `validation/report.json` at the end records each gate's status
and the evidence for it.

### Mechanism 3 — Adversarial subagents as gate-keepers

Several gates are guarded by a *different model instance* whose job is to try to fail
the work:

- **`data-checker`** (source gate) writes a `PASS`/`FAIL` verdict to
  `validation/data_check.json`. Non-negotiable #1: *no analysis on a dataset until its
  verdict is PASS and that dataset is sealed.* On `FAIL` the run loops back to
  `data-finder`.
- **`advisor`** (frame + pivot gates) can issue a **SEND BACK** verdict that functions
  exactly like a blocking objection — but for *triviality* rather than for error.
- **`referee`** (before write + before finalize) emits a numbered list of objections,
  each tagged `[BLOCKING]` or `[minor]`. Every `[BLOCKING]` must be resolved before
  proceeding. Non-negotiable #6 requires this critic to be a *different model* than the
  one that produced the work.

The `[BLOCKING]` tag is the universal "halt" signal. A non-negotiable violation
*HALTS the stage* — the contract explicitly says never to work around it.

---

## 4. How it uses subagents

`grounded2` is built around an 8-member subagent roster. The orchestrator delegates
to them via the Task/`Agent` tool; each runs in its own context with its own tool
allow-list and its own model tier (declared in the agent's front-matter). Delegation
serves two purposes: **isolation** (keep large data dumps out of the orchestrator's
context) and **adversarial independence** (a fresh model that did not produce the work
reviews it).

| Subagent | Model | Tools | Role | Invoked at |
|----------|-------|-------|------|------------|
| `data-finder` | sonnet | Read, Bash, Write, WebSearch, WebFetch, … | Acquires datasets into `data/raw/<name>/` + writes provenance; flags the *second* dataset that would unlock identification | source gate; any checker FAIL; any augmentation loop |
| `data-checker` | opus | Read, Bash, Write, … | Skeptical gatekeeper: correctness **and** fitness → `data_check.json` PASS/FAIL | after `data-finder`, before sealing |
| `data-profiler` | sonnet | Read, Bash, Write, … | Schema, distributions, missingness, **leakage scan**; says which designs the variation can support | profile gate |
| `literature-scout` | opus | Read, Bash, Write, WebSearch, WebFetch | **Two modes:** (A) generative — surface high-value open questions; (B) defensive — build real `references.bib` + positioning | frame gate (A); literature gate (B) |
| `advisor` | opus | Read, Glob, Grep, WebSearch, WebFetch (**read-only**) | The **importance maximizer**; attacks triviality; can SEND BACK | frame gate; pivot-check gate |
| `econometrician` | sonnet | Read, Bash, Write, … | Writes **and runs** estimation/robustness code; never reports an uncomputed number | estimate + robustness gates |
| `referee` | opus | Read, Glob, Grep (**read-only**) | Hostile reviewer; finds fatal flaws; only ever shrinks the claim | before write; before finalize |
| `introspector` | opus | Read, Glob, Grep (**read-only**) | End-of-run critique of the **framework itself** for the next version | introspect gate (last) |

Three design points worth calling out:

- **The advisor and referee are deliberate opposites.** The `referee` minimizes false
  claims and *only ever makes the paper smaller*; the `advisor` maximizes contribution
  and pushes for a *bigger, identified, genuinely-interesting* result. The
  orchestrator's standing instruction is to **hold both** tensions at once. This
  two-sided adversarial pressure is the central innovation over `grounded`, which had
  only the shrinking force.
- **Reviewers are read-only.** `advisor`, `referee`, and `introspector` have no
  `Write`/`Bash` — they cannot fix the work, only judge it. This keeps the critique
  honest and prevents a reviewer from quietly "patching" what it was supposed to flag.
- **Model tiers are matched to the job.** Cheaper `sonnet` does the mechanical
  acquire/compute/profile work; `opus` does the judgment-heavy gatekeeping (check,
  advise, referee, introspect, literature).

---

## 5. The design loop in detail — the importance machinery

The defining feature of `grounded2` is that **contribution is gated, not assumed**
(non-negotiable #9). Two new gates wrap the rigor pipeline:

### Frame gate (before design locks) — "is this worth doing?"

1. `literature-scout` runs **generatively** (Mode A): it surveys the domain's live
   debates and highest-value *open* questions and writes
   `work/03_frame/lit_landscape.md` — explicitly *not* to defend a pre-chosen question.
2. `advisor` interrogates the candidate question along five axes: first-order
   importance, **interesting under BOTH signs** of the result, the identification
   ceiling of the available data, whether a *better* question exists (possibly via a
   data **pairing** it names concretely), and the strongest honest version of the
   contribution.
3. Output `work/03_frame/frame.md` with the chosen question and the advisor's verdict
   — **PROCEED** (with the sharpened question) or **SEND BACK** (with the concrete
   re-scope or data augmentation required). A question that is *only* interesting if
   non-null is flagged as the weakest kind, because it tends to die as a null.

### Explore → confirm — "find the signal, then pre-register"

This enforces a separation that prevents p-hacking (non-negotiable #10):

- **Explore gate:** a *clearly-labeled* exploratory pass on the sealed data (splits by
  time/geography) writes `work/04_explore/explore.md`. These are explicitly **NOT
  confirmatory results.**
- **Design gate:** the confirmatory `work/05_design/design.md` is pre-registered
  **AFTER** exploration and must *cite what explore found*. The `referee` later checks
  this integrity — any confirmatory claim resting on a spec chosen by peeking *without
  re-registration* is a blocking flaw.

### Identification-first, ranked design (non-negotiable #11)

`design.md` must **enumerate candidate identification strategies ranked by
credibility** (RD / event-study / IV > descriptive TWFE) and make the strongest
feasible one the **PRIMARY spine — not a robustness afterthought.** And
non-negotiable #12: if that load-bearing analysis fails to *run* (e.g. a package won't
install), that is **BLOCKING** — the orchestrator must fix it, implement it manually,
or trigger the pivot-check, but **never silently demote it to a footnote.**

### Pivot-check gate (after estimate) — "did importance survive contact with the result?"

The `advisor` is re-invoked. If the primary result is null **and** the question was
only-interesting-if-non-null, the run must make an explicit re-scope decision
(non-negotiable #13), recorded in `work/08_pivot/pivot.md`. The options:

1. Promote a discovered result via **re-registration**, or
2. Pursue the identification extension, or
3. **Augment data** (loop back to `data-finder`), or
4. Accept and write the null — but **only if** the advisor genuinely judges the null to
   overturn an *established* claim, not a speculative worry.

This is the mechanism that stops the pipeline from marching to a polished, rigorous,
useless null — the exact failure mode `grounded` exhibited.

---

## 6. Does it allow non-linear research steps?

**The gate *order* is strictly linear and may not be skipped** — but `grounded2` builds
in several **controlled backward loops**. Non-linearity is allowed only as *explicit,
recorded re-entry into an earlier gate*, never as freelancing.

The sanctioned loops:

1. **Source verification loop.** `data-finder` → `data-checker` → on `FAIL`, back to
   `data-finder`; repeat until `PASS`, then seal. (Gate 1 ↔ itself.)
2. **Data augmentation loop (the big one).** Because sealing is **per-dataset**, the
   **frame, design, OR pivot gate** may call `data-finder` to deposit a *new* dataset
   into a fresh `data/raw/<name>/` subdir, have `data-checker` verify it, and seal it —
   *while the already-sealed datasets stay frozen.* This is how identification gets
   unlocked mid-study (e.g. pairing a provided outcome series with weather, a
   policy-shock series, or a Census linkage). Crucially, **augmentation is always
   available — even when the initial data was PROVIDED** — precisely because the seal is
   per-dataset rather than one global freeze.
3. **Pivot re-scope loop.** The pivot-check can send the run back to re-registration,
   identification work, or augmentation (options above).
4. **Referee resolution loop.** Each `[BLOCKING]` objection sends work back until
   resolved; the referee runs *twice* (before write, before finalize).

What is **not** allowed: jumping ahead of a gate whose artifact doesn't yet exist,
running a confirmatory spec before the design is pre-registered, analyzing unsealed
data, or demoting the registered identification strategy without going through the
pivot-check. So: **non-linear in its loops, strictly ordered in its progression.** The
loops always re-enter a *named earlier gate* and leave a *recorded artifact* (a new
`data_check.json`, a `pivot.md`, an updated `design.md`), so even the non-linear moves
are auditable.

---

## 7. Closing the run

The pipeline does not end at "the paper compiles." Two final gates make the run
*reproducible* and *self-critical*:

- **Reproduce (gate 13).** `replication/run_all.sh` must regenerate every table,
  figure, and the PDF **from the sealed data**, and the regenerated values must match
  `main.tex` within float tolerance (non-negotiable #4). For self-sourced data it
  *verifies* `data/raw` against the per-dataset `.sealed` hashes and must **not
  re-download**.
- **Introspect (gate 14, mandatory).** The `introspector` — a fresh model that did not
  orchestrate the run — writes `introspection.md` at the project root. It reviews what
  the **framework's structure** caused (not the paper's economics): what worked and
  must be preserved, and located problems + concrete suggestions tagged to a specific
  gate/agent/non-negotiable. This is MiddAR's improvement flywheel — `grounded2` itself
  was driven by the introspection.md of an earlier `grounded` run.

Only once **all gates pass AND `introspection.md` exists** does the orchestrator write
`validation/report.json` and stop.

---

## 8. Mental model in one paragraph

`grounded2` is a linear 14-gate pipeline where each gate must leave a verifiable file
on disk before the next begins, guarded by three layers of enforcement: a deterministic
`PreToolUse` hook that makes verified data physically immutable (per-dataset, so more
data can still be added later), a permission allow-list that forces real computation
and scopes writes, and a roster of adversarial subagents — most importantly the
**advisor** (maximize importance) set against the **referee** (minimize false claims) —
that can block progress on either *triviality* or *error*. It self-sources data when
none is given, finds the signal by exploring before it pre-registers a confirmatory
identification-first design, can acquire complementary data mid-study to unlock
identification, pivots when a result turns out null-and-uninteresting, reproduces
everything from sealed data with one button, and finishes by critiquing its own
framework for the next version.
