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
  frameworks/               <- versioned instruction-sets (the part you iterate on)
    gated/                  <- Framework 1: the gated pipeline (CLAUDE.md, agents, hooks, prompt)
  projects/                 <- one sealed experiment per dir
    test_01/                <- a completed run (8/8 gates PASS)
    test_02/                <- ...
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

Run from this directory (`MiddAR/`):

```bash
python tool.py frameworks                 # list available frameworks
python tool.py new <name> \               # scaffold a sealed experiment
    --framework gated \                    #   (default: gated)
    --data ../data \                       #   file(s)/dir(s) copied into data/raw/
    --idea "your research question"        #   written into EXPERIMENT.md
python tool.py list                       # all experiments + gate status
python tool.py verify <name>              # run that experiment's replication/run_all.sh
python tool.py clean <name>               # delete generated artifacts (keeps config + data)
```

`new` does all of this for `projects/<name>/`:
- copies the framework's `CLAUDE.md`, `prompt.md`, and `.claude/` (agents + hooks; hooks made executable);
- creates the empty `work/ paper/ replication/ validation/` skeleton;
- **copies** the dataset into `data/raw/` (full isolation — each experiment owns a frozen snapshot) and records each file's SHA-256;
- writes `EXPERIMENT.md` (idea + input provenance) and adds an entry to `projects/registry.json`.

## Running an experiment

```bash
python tool.py new my_run --data ../data --idea "Does X affect Y?"
cd projects/my_run
claude
/agents          # confirm data-profiler, econometrician, referee are listed
# paste prompt.md as the first message; Claude works the gates to a finished paper
```

When it finishes, check it from the control plane:

```bash
cd ../..              # back to MiddAR/
python tool.py verify my_run    # re-runs the pipeline from data/raw/ and recompiles
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

## Note on disk usage

Experiments copy their data for full isolation, so each run costs the size of its
inputs (~45 MB for the Chicago dataset). `tool.py clean <name>` reclaims generated
artifacts without touching `data/raw/` or the config.
