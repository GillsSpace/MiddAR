# Orchestrator prompt — Framework 1 (gated pipeline)

Paste this as your first message after running `claude` in the project root.
Edit it freely per experiment — this is the main lever for trying new processes.

---

You are orchestrating an automated empirical-economics paper under the gated
pipeline defined in CLAUDE.md. Read CLAUDE.md now and treat its non-negotiables
and gate order as hard constraints.

The research idea / dataset for this run is described in EXPERIMENT.md — read it.

Proceed one gate at a time:

    audit -> profile -> design -> estimate -> robustness -> referee -> write -> reproduce

Rules of engagement:
- Advance to the next gate ONLY when the prior gate's outputs exist on disk and
  its checks pass. State which gate you are entering and why the prior one passed.
- Delegate large data exploration to the `data-profiler` subagent (gate: profile).
- Delegate every coefficient/table/figure to the `econometrician` subagent — it
  must RUN code and never report a number it did not compute.
- Before writing and again before finalizing, invoke the `referee` subagent and
  resolve every [BLOCKING] objection before continuing.
- Every numeral that lands in paper/main.tex must have a provenance entry in
  validation/claims.json. Run validation/orphan_check.py before declaring "write" done.
- "reproduce" passes only when replication/run_all.sh regenerates all tables,
  figures, and the PDF from data/raw/ and the values match the .tex.

When all eight gates pass, write validation/report.json summarizing each gate's
status and evidence, and stop.
