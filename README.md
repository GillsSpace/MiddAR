# MiddAR

An application that takes a **research idea + a dataset** and drives Claude Code
to produce a reproducible empirical-economics paper.

MiddAR is the **control plane**. It does not write papers itself — it scaffolds
and tracks *experiments*, each of which is a sealed runtime where one Claude Code
instance does the work under a chosen **framework** (instruction-set).

## Mental model

```
MiddAR/                     <- control plane. Run tool.py here. Do NOT run Claude here.
  tool.py                   <- the CLI
  api_keys.env              <- single user-editable master list of API keys (synced into each project)
  frameworks/               <- versioned instruction-sets (the part you iterate on)
    gated/                  <- Framework 1: the gated pipeline (CLAUDE.md, agents, hooks, prompt)
    grounded/               <- Framework 2: gated + self-sourcing data + literature/citations
    grounded2/              <- Framework 3: grounded + contribution/advisor + explore→confirm
                               + data augmentation + auto-introspection
  projects/                 <- one sealed experiment per dir
    test_01/                <- a completed run (8/8 gates PASS)
    test_03/                <- a grounded run; its introspection.md drove grounded2
    registry.json           <- index: which framework + data + idea each used
```

### Why Claude runs at the *project* level, not at MiddAR level

Everything that defines an experiment is **directory-scoped**: `.claude/settings.json`
(permissions + the raw-data hook), `.claude/agents/*` (referee / econometrician /
profiler), `CLAUDE.md` (the rules), and the conversation context itself.

Running one Claude at `MiddAR/` would pour every experiment into **one shared
context and one shared config** — you'd lose isolation and couldn't vary
instructions per run. So each experiment gets its own working directory and its
own Claude. That is exactly what the first test run did, and it is the right call.

MiddAR-level work is orchestration only, and that is what `tool.py` is for.

### How to iterate on the process

The thing you tune between experiments is a **framework** under `frameworks/`.
To try a new process: copy `frameworks/gated/` to `frameworks/<your-idea>/`, edit
its `CLAUDE.md` / `prompt.md` / agents, then stamp a fresh experiment from it.
Each experiment stays a sealed context; the only things shared are the framework
template you chose and the (copied, immutable) data.

## CLI

Run from this directory (`MiddAR/`). There are **two main commands** — `gen` and
`run` — bracketing the step where you drop in this experiment's dataset.

```bash
# 1. generate the project folder structure from a framework (no data yet)
python tool.py gen <name> --framework gated --idea "your research question"

# 2. copy THIS experiment's dataset into the project's data/raw/
cp /path/to/your_dataset.parquet projects/<name>/data/raw/

# 3. finish setup and print the command/prompt to paste into Claude Code
python tool.py run <name>
```

**Don't have a dataset?** With a self-sourcing framework (e.g. `grounded`) you can
skip step 2 and let the run acquire its own data:

```bash
python tool.py gen <name> --framework grounded --idea "your research question"
python tool.py run <name> --no-data          # source gate finds/downloads/generates, verifies, AND seals the data
# (optional) mirror the self-sourced provenance into the registry from the control plane:
python tool.py seal <name>
```

`gen` creates `projects/<name>/`: it copies the framework's `CLAUDE.md`,
`prompt.md`, and `.claude/` (agents + hooks, made executable), builds the empty
`work/ paper/ replication/ validation/` skeleton plus an empty `data/raw/`, writes
an `EXPERIMENT.md` stub, and registers the experiment. It does **not** touch data
— each experiment gets its own dataset, copied in by you before the run.

`run` finishes setup: it verifies `data/raw/` is non-empty, records each input
file's SHA-256 into `EXPERIMENT.md` + `projects/registry.json`, **seals** the data
(writes `data/.sealed` so the raw-data hook freezes `data/raw/`), ensures the hooks
are executable, then prints the launch command and the ready-to-paste prompt.

`run --no-data` (self-sourcing frameworks only) skips the "data must be present"
check: the run's *source gate* acquires the dataset itself (web download or an
API/library like the Census) and **the agent seals it** after the `data-checker`
verifies it.

**Sealing is automatic — there is no manual seal step.** For a provided-data run,
`run` seals the data for you; for a `--no-data` run, the agent seals it at the source
gate. `tool.py seal` is **optional** control-plane bookkeeping: it re-hashes `data/raw/`
and mirrors the provenance into `registry.json` + `EXPERIMENT.md` after a self-sourced
run. You never need it to make the data immutable.

**Per-dataset frameworks (`grounded2`):** datasets live in subdirs, so paste your data
into `data/raw/primary/` (created for you by `gen`), or make additional
`data/raw/<name>/` subdirs. You can also add data **mid-study** — see Augmentation below.

Helpers:

```bash
python tool.py list                       # all experiments + status
python tool.py frameworks                 # available frameworks
python tool.py verify <name>              # re-run replication/run_all.sh (reproduction check)
python tool.py seal <name>                # record data/raw/ provenance + freeze it (after a --no-data run sources its data)
python tool.py augment <name> --data PATH [--name SLUG]   # pair in an additional dataset mid-study (per-dataset frameworks)
python tool.py keys                       # show the master API-keys file + which keys are set
python tool.py clean <name>               # delete generated artifacts (keeps config + data)
```

## API keys

Some sources need an API key (e.g. the Census Bureau). Keep keys in ONE place —
`MiddAR/api_keys.env` (created on first `tool.py keys`/`gen`) — as `KEY=VALUE` lines:

```
CENSUS_API_KEY=your-key-here
FRED_API_KEY=...
```

`gen` and `run` copy this master into each project's `api_keys.env` (the model can
only read files inside its own working dir). Frameworks that use keys (`grounded2`)
instruct the model to read the key it needs and **never print, log, or commit a key
value**. Keep `api_keys.env` out of version control. `tool.py keys` shows *which*
keys are set, never the values.

## Running an experiment

```bash
python tool.py gen my_run --framework gated --idea "Does X affect Y?"
cp /path/to/dataset.parquet projects/my_run/data/raw/
python tool.py run my_run        # prints the command below

# paste what `run` gave you:
cd projects/my_run && claude "$(cat prompt.md)"
# (or start `claude` there and paste the prompt manually)
```

Claude then works the gates to a finished paper. Check reproduction afterward
from the control plane:

```bash
python tool.py verify my_run     # re-runs the pipeline from data/raw/ and recompiles
```

## Frameworks

### `gated` — Framework 1 (gated pipeline)
`audit → profile → design → estimate → robustness → referee → write → reproduce`,
with these guarantees baked in:
- `data/raw/` is immutable (a `PreToolUse` hook blocks any write to it);
- no orphan numbers — every numeral in `main.tex` maps to `validation/claims.json`;
- a different model (the `referee` subagent) criticizes before writing and before finalizing;
- "done" means `replication/run_all.sh` regenerates every table/figure from `data/raw/` and the values match the draft.

See `frameworks/gated/CLAUDE.md` for the full contract.

### `grounded` — Framework 2 (gated + self-sourcing + literature)
Everything `gated` guarantees, plus two new gates:
`source → audit → profile → design → literature → estimate → robustness → referee → write → reproduce`.
- **source gate** — when run with `--no-data`, a `data-finder` subagent acquires a
  fitting dataset (web download, or an API/library such as Census/FRED/World Bank)
  into `data/raw/`, and a `data-checker` subagent gates it: the data must be both
  *correct* (parses, plausible, complete) and *fit for purpose* (has the variables,
  coverage, and sample the design needs). Only on a `PASS` is the data **sealed**
  (`data/.sealed`) and frozen — the same immutability guarantee as provided data,
  but reached by verified self-sourcing. Provenance lands in `data/SOURCE.md`.
- **literature gate** — a `literature-scout` subagent researches real prior work,
  produces verifiable BibTeX in `paper/references.bib` (no fabricated citations),
  and positions the contribution in `work/04_literature/lit_review.md`. The referee
  then checks that prior-work claims are cited and that every reference is real.
  (This is the gap Framework 1 left: papers with no citations or related-work.)

The seal lets `data/raw/` start empty and still end immutable: it's writable only
until `data/.sealed` exists, after which the `PreToolUse` hook blocks every write.

See `frameworks/grounded/CLAUDE.md` for the full contract.

### `grounded2` — Framework 3 (grounded + a contribution force)
`source → audit → profile → frame → explore → design → literature → estimate → pivot → robustness → referee → write → reproduce → introspect`.

`grounded`'s own `test_03/introspection.md` diagnosed the flaw: every gate it owned
maximized *rigor*, and its only adversary (the `referee`) only ever made the paper
*smaller* — so it reliably shipped impeccably-executed trivial nulls. grounded2 adds
the missing **importance-maximizer** and the structure to act on it:

- **`advisor` subagent + FRAME and PIVOT-CHECK gates** — the adversarial opposite of
  the referee. Before design locks, the advisor asks: is this first-order important,
  and *interesting under both signs of the result?* It can send the framing back for
  triviality. After estimation, the pivot-check forces a re-scope when the primary is
  a null that was only interesting if non-null.
- **explore → confirm** — a labeled exploratory pass (`work/04_explore/`) finds where
  the signal is; the confirmatory design is pre-registered *after* and must cite it.
- **identification-first design** — `design.md` ranks identification strategies by
  credibility and makes the strongest feasible one the spine, not a robustness
  afterthought; a load-bearing analysis that won't run is BLOCKING, never a footnote.
- **mid-study data augmentation** — sealing is now **per-dataset**: each dataset lives
  in `data/raw/<name>/` with its own `.sealed`. Whether your initial data was
  **provided or self-sourced**, you can pair in a second dataset — weather, a
  policy-shock series, a Census linkage — *after* the first is frozen, because only the
  sealed subdir is immutable; a new subdir is writable until sealed. Two ways:
  the **agent does it mid-run** (the frame/design/pivot gate calls `data-finder` into a
  new subdir → `data-checker` → seal), or **you do it from the control plane**:
  `python tool.py augment <name> --data /path/to/more.csv --name weather`.
- **auto-introspection** — a final `introspect` gate: the `introspector` subagent
  writes `introspection.md` for the framework team (what the structure produced, what
  to preserve, located fixes), closing the loop that produced grounded2 itself.

Self-source it (no dataset needed) and pair data in mid-study:

```bash
python tool.py gen study --framework grounded2 --idea "Do local labor shocks change firm entry?"
python tool.py run study --no-data        # source gate finds + verifies + seals the primary dataset
# ...later, to add identifying variation:
python tool.py augment study --data /path/to/shocks.csv --name policy_shocks
```

See `frameworks/grounded2/CLAUDE.md` for the full contract.

## Note on disk usage

Each experiment owns its dataset in `data/raw/` (you copy it in before `run`, or the
source gate self-sources it), so a run costs the size of its inputs. `tool.py clean
<name>` reclaims generated artifacts without touching `data/raw/` or the config.
