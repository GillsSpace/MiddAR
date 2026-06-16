#!/usr/bin/env bash
#
# setup.sh — scaffolds the Framework 1 (gated pipeline) Claude Code config.
#
# WHERE THIS GOES / WHERE TO RUN IT:
#   Place this file in your PROJECT ROOT:  projects/test_01/setup.sh
#   Your data must already be at:          projects/test_01/data/raw/
#   Then run it from the project root:     cd projects/test_01 && bash setup.sh
#
# The script writes everything RELATIVE TO ITS OWN LOCATION, so the directory
# that contains setup.sh becomes the project root regardless of your shell's
# current working directory.
#
set -euo pipefail

# --- locate the project root (= directory containing this script) -----------
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
echo "Project root: $ROOT"

# --- sanity check: data must live at <root>/data/raw ------------------------
if [[ -d "data/raw" ]]; then
  echo "Found data/raw/ — good."
else
  echo "WARNING: data/raw/ not found under the project root."
  echo "         Expected your data file at: $ROOT/data/raw/"
  echo "         Create it and move your data there before running the pipeline."
fi

# --- create the directory skeleton ------------------------------------------
mkdir -p \
  .claude/agents .claude/hooks \
  work/01_audit work/02_profile work/03_design work/04_analysis work/05_robustness \
  paper/sections paper/tables paper/figures \
  replication validation

# === CLAUDE.md (project root) ===============================================
cat > CLAUDE.md << 'CLAUDEMD'
# Project: automated empirical-economics paper (Framework 1 — gated pipeline)

## Directory contract
data/raw/      immutable inputs — NEVER write here
work/          intermediates: 01_audit 02_profile 03_design 04_analysis 05_robustness
paper/         main.tex + sections/ + tables/ + figures/
replication/   run_all.sh + manifest.json + README.md (AEA-style)
validation/    claims.json (number -> provenance) + report.json (gate results)

## Non-negotiables (a violation HALTS the stage; never work around it)
1. No orphan numbers: every numeral in main.tex maps to an entry in validation/claims.json.
2. Fresh-env reproduction: "done" only when run_all.sh regenerates every table/figure and the values match the .tex within float tolerance.
3. Dataset-aware generation: never propose a hypothesis the data can't support (check work/02_profile/).
4. A different model criticizes: the referee subagent reviews before writing and before finalizing.
5. Validation data for any LLM-measured variable: no uncorrected coefficient on a model-generated regressor.
6. Diagnostics are reported, never hidden: a failed assumption becomes a visible limitation.

## Gate order (do not skip)
audit -> profile -> design -> estimate -> robustness -> referee -> write -> reproduce
Advance only when the prior stage's outputs exist on disk and its checks pass.
CLAUDEMD

# === .claude/settings.json ==================================================
cat > .claude/settings.json << 'JSON'
{
  "permissions": {
    "allow": [
      "Bash(python3:*)", "Bash(pip:*)", "Bash(pdflatex:*)", "Bash(latexmk:*)",
      "Bash(bash replication/run_all.sh)",
      "Read(./**)",
      "Write(./work/**)", "Write(./paper/**)", "Write(./replication/**)", "Write(./validation/**)",
      "Edit(./work/**)", "Edit(./paper/**)", "Edit(./replication/**)", "Edit(./validation/**)"
    ],
    "deny": ["Write(./data/**)", "Edit(./data/**)"]
  },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "command": "bash ./.claude/hooks/protect_raw.sh" }] }
    ]
  }
}
JSON

# === .claude/hooks/protect_raw.sh ===========================================
cat > .claude/hooks/protect_raw.sh << 'HOOK'
#!/usr/bin/env bash
input=$(cat)
path=$(printf '%s' "$input" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)
if [[ "$path" == *"data/raw/"* ]]; then
  echo "BLOCKED: data/raw is immutable. Write outputs to work/ or paper/ instead." >&2
  exit 2
fi
exit 0
HOOK
chmod +x .claude/hooks/protect_raw.sh

# === .claude/agents/data-profiler.md ========================================
cat > .claude/agents/data-profiler.md << 'AGENT'
---
name: data-profiler
description: Profiles raw datasets — schema, distributions, missingness, and a leakage scan. Use at the start before any hypotheses are formed. Read-heavy; isolates large data exploration from the main context.
tools: Read, Glob, Grep, Bash, Write
model: sonnet
---
You profile data for empirical economics. Given files in data/raw/:
1. Infer schema (types, units, key variables); record SHA-256 of each input.
2. Report N, missingness, distributions, and obvious outliers per variable.
3. LEAKAGE SCAN: flag any variable that is a near-deterministic function of a plausible outcome.
4. State per variable which designs the variation can support (e.g., enough treated x post cells for DiD?).
Write work/02_profile/profile.md and machine-readable work/02_profile/profile.json.
Report back only a short summary + the path. Never modify data/raw/.
AGENT

# === .claude/agents/econometrician.md =======================================
cat > .claude/agents/econometrician.md << 'AGENT'
---
name: econometrician
description: Writes and RUNS estimation and robustness code, then reports results computed from the data. Use for any step that produces a coefficient, table, or figure. Never reports a number it did not compute.
tools: Read, Glob, Grep, Bash, Write
model: sonnet
---
You are an applied econometrician. Rules:
- Every number you report must come from code you actually ran. Never invent or recall figures.
- Use a fixed random seed; record it in replication/manifest.json.
- Run identification diagnostics for the chosen design (parallel pre-trends for DiD, McCrary + covariate smoothness for RDD, first-stage F for IV). Report failures; never hide them.
- Emit tables to paper/tables/ and figures to paper/figures/, each produced by a script in work/04_analysis/ or work/05_robustness/.
- For every reported number, append an entry to validation/claims.json mapping it to the producing script + log line.
Report back a short summary and the artifact paths.
AGENT

# === .claude/agents/referee.md ==============================================
cat > .claude/agents/referee.md << 'AGENT'
---
name: referee
description: Adversarial reviewer. Attacks a design and its results for identification flaws, leakage, spec-searching, overclaiming, and unsupported numbers. Use before writing and before finalizing. Read-only.
tools: Read, Glob, Grep
model: opus
---
You are a hostile but fair referee for a top economics journal. You did NOT produce this work.
Given the design (work/03_design/), results (paper/tables, paper/figures), and draft (paper/):
- Find fatal flaws first: confounding, reverse causality, post-treatment conditioning, leakage, failed or missing diagnostics, p-hacking, overclaimed magnitude or external validity.
- Verify every number in the draft has a provenance entry in validation/claims.json.
- Output a numbered list of objections, each tagged [BLOCKING] or [minor], each with a concrete required fix.
Do not soften. If the identifying assumption is implausible, say so plainly.
AGENT

# --- done -------------------------------------------------------------------
echo ""
echo "Scaffold written under: $ROOT"
echo ""
echo "  CLAUDE.md"
echo "  .claude/settings.json"
echo "  .claude/hooks/protect_raw.sh   (executable)"
echo "  .claude/agents/data-profiler.md"
echo "  .claude/agents/econometrician.md"
echo "  .claude/agents/referee.md"
echo "  work/  paper/  replication/  validation/   (empty skeleton)"
echo ""
echo "Next steps:"
echo "  1. cd \"$ROOT\""
echo "  2. claude"
echo "  3. /agents          # confirm data-profiler, econometrician, referee are listed"
echo "  4. paste the orchestrator prompt"
echo ""
echo "Note: these config files were overwritten if they already existed."