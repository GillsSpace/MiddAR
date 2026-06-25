You are orchestrating an automated empirical-economics paper under the grounded
pipeline defined in CLAUDE.md. Read CLAUDE.md now and treat its non-negotiables
and gate order as hard constraints.

The research idea, dataset status, and data mode for this run are described in
EXPERIMENT.md — read it first. It tells you whether a dataset was PROVIDED or
whether this is a SELF-SOURCED (--no-data) run in which you must acquire the data.

Proceed one gate at a time:

    source -> audit -> profile -> design -> literature -> estimate -> robustness -> referee -> write -> reproduce

Rules of engagement:
- Advance to the next gate ONLY when the prior gate's outputs exist on disk and
  its checks pass. State which gate you are entering and why the prior one passed.

- SOURCE gate first:
  - If data/raw/ already holds the provided dataset and data/.sealed exists,
    confirm the files match the seal and pass the gate.
  - If data/raw/ is empty (self-sourced run): invoke the `data-finder` subagent to
    download or generate a fitting dataset (web, or an API/library such as Census,
    FRED, World Bank, BLS) into data/raw/ with provenance in data/SOURCE.md; then
    invoke the `data-checker` subagent to verify correctness AND fitness, writing
    validation/data_check.json. Loop finder<->checker until the verdict is PASS,
    then SEAL data/raw (write data/.sealed with each file's sha256). Never analyze
    unsealed or unverified data.

- Delegate large data exploration to the `data-profiler` subagent (gate: profile).

- LITERATURE gate (after design): invoke the `literature-scout` subagent to find
  REAL prior work, produce paper/references.bib (verifiable entries only — never
  fabricate a citation), and write work/04_literature/lit_review.md positioning
  this paper's contribution. The draft's related-work must cite these entries.

- Delegate every coefficient/table/figure to the `econometrician` subagent — it
  must RUN code and never report a number it did not compute.

- Before writing and again before finalizing, invoke the `referee` subagent and
  resolve every [BLOCKING] objection before continuing. The referee also checks
  that prior-work claims are cited and that every references.bib entry is real.

- Every numeral that lands in paper/main.tex must have a provenance entry in
  validation/claims.json. Run validation/orphan_check.py before declaring "write" done.

- "reproduce" passes only when replication/run_all.sh regenerates all tables,
  figures, and the PDF from the sealed data/raw/ and the values match the .tex.
  For self-sourced data, run_all.sh verifies data/raw against data/.sealed hashes;
  it must NOT re-download (the sealed copy is the system of record).

When all ten gates pass, write validation/report.json summarizing each gate's
status and evidence (include the source verdict and the citation count), and stop.
