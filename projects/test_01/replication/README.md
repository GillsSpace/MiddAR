# Replication package — Inspection-day weather and food-safety inspection outcomes (Chicago)

## One-command reproduction
```
bash replication/run_all.sh
```
Regenerates, from `data/raw/` only: `replication/manifest.json`, `validation/claims.json`,
all tables (`paper/tables/table{1,2,3}.tex`), figures (`paper/figures/*.png`), and the PDF
(`paper/main.pdf`). The script resets every generated artifact first; `data/raw/` is never
written (enforced by a permission deny-rule and a pre-write hook).

## Inputs (immutable)
- `data/raw/chicago_inspections_weather.parquet` — 138,896 × 24; Chicago food inspections
  2018-07-03–2026-06-12 matched to daily Open-Meteo weather. SHA-256 in `manifest.json`.
- `data/raw/chicago_inspections_weather_sample.csv` — CSV sample (not used by the pipeline).

## Environment
- Python 3.13; pandas, numpy, scipy, statsmodels, matplotlib, pyarrow, linearmodels, pyhdfe
  (exact versions in `manifest.json`). Global seed **20260613**. `PYTHONHASHSEED=0` for determinism.
- LaTeX (`pdflatex`) optional; the pipeline completes without it (PDF step is skipped).

## Pipeline (gate order)
1. `work/01_audit/audit.py` — hashes, schema, seed, versions → `manifest.json`
2. `work/02_profile/profile.py` — schema, distributions, leakage scan, design feasibility
3. `work/04_analysis/prep.py` — shared sample builder (substantive inspections; `fail` outcome)
4. `work/04_analysis/estimate.py` — main LPM specs → `table1_main.tex` (+claims)
5. `work/04_analysis/diagnostics.py` — placebo, seasonality, balance → figures (+claims)
6. `work/05_robustness/robustness.py` — 13 specs, H3/H4/H5 → `table2_robustness.tex` (+claims)
7. `work/05_robustness/referee_fixes.py`, `referee_fixes2.py`, `extra_inference.py`,
   `referee_fixes3.py` — referee-mandated coarse clustering, wild bootstrap, multiplicity,
   within-establishment intensive margin, scheduled-only subsample, H4 leave-one-out diagnostic,
   estimator-equivalence check (+claims)
8. `work/05_robustness/make_tables.py` — rebuild all tables from `claims.json`
9. `validation/orphan_check.py` — every numeral in `main.tex` maps to a claim or whitelisted constant

## Provenance
`validation/claims.json` maps every reported number to its producing script and a log line.
`validation/report.json` records the pass/fail of every gate. The headline within-establishment
estimator is `linearmodels.AbsorbingLS`; round-3 additions use a manual `pyhdfe` HDFE-OLS,
validated to reproduce AbsorbingLS coefficients and SE to within 1e-4 ppt (`estimator_equiv_maxdelta`).

## Headline result
No robust effect of inspection-day weather on inspection failure. Preferred within-establishment
estimate: **0.443 ppt per +10°C (95% CI [-0.16, 1.05], p=0.15)** — a bounded null ruling out
average effects above ~5.2% of the base failure rate. The naive +0.615 ppt cross-sectional
gradient is seasonal/compositional confounding.
