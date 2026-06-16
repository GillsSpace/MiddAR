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
