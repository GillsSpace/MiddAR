# Findings summary (FINAL, after referee rounds 1-3) — on-disk artifacts only

Sample (estimation): 116,466 substantive inspections, 20,994 establishments, 1,969 day-clusters, base fail rate 0.2276. Profile-level: 23,737 estab / 1,983 weather-days.

## HEADLINE: no robust effect of inspection-day weather on inspection failure
- Pooled (confounded) gradient 0.615 ppt/10C (p=0.0) -> attenuates to null once establishment + seasonal FE are added.
- Preferred primary (Estab+Month+Year FE, full sample, type excluded as a mediator): **0.443 ppt/10C, p=0.1507** (date); robust to coarse clustering (week p=0.2236, month p=0.2392).
  - As % of base rate 1.95% (CI [-0.71, 4.6]%). Bounded null: rules out average effects above +1.189 ppt/10C (5.22% of base rate).
- +Type FE (direct effect): 0.329 ppt/10C, p=0.2398.
- Scheduled (non-complaint) subsample, isolating the non-selection channel: 0.674 ppt/10C, p=0.0526 (date) -> borderline but NOT significant; coarse clustering week p=0.0959, month p=0.1006.
- Precipitation null: -0.118 ppt/10mm (p=0.5852).

## Why the naive gradient is biased (mechanism, all on disk)
- Placebo (shuffled weather): 0.158 ppt (p=0.2189); cubic-DOY seasonality: 0.166 (p=0.5432).
- Temperature shifts the inspection MIX (complaint share +0.0148, p=0.0; canvass -0.0256, p=0.0) but not daily volume (p=0.7632). Complaints fail more, so warm-day cross-sections look worse. Type is therefore a mediator -> preferred primary excludes it.

## Robustness & inference
- 13-spec robustness: 12/13 positive sign, 2/13 significant@.10; min p 0.0312, Bonferroni 0.4056; 0.65 false positives expected at .05.
- Post-hoc significant subsamples collapse under correct inference: Canvass day p=0.0312->month 0.0688 (wild-boot 0.082); Risk1 day 0.0612->month 0.1025.

## H4 heterogeneity — TESTED AND DEMOTED (not a headline result)
- Temp x Restaurant interaction is significant in baseline (+0.863 ppt, p=0.0037) and under coarse clustering (week 0.0047, month 0.014).
- BUT it FAILS its pre-registered must-pass diagnostic: leave-one-facility-out coef ranges 0.43-0.86 ppt, MAX p 0.1711 (drops to non-significant when Schools are excluded from the comparison group). pass=False.
- Temp x Risk1 interaction: -0.176 ppt, p=0.5845 -> null.
- Conclusion: reported as a non-robust, exploratory pattern, NOT evidence of a restaurant heat effect.

## Secondary outcome (violation count) — NOT robust
- Within-estab no-Type: asinh 0.0173 (date p=0.0105, month p=0.0508); count 0.0617 (date p=0.0216, month p=0.0834).
- Count-family multiplicity: 12 tests, min p 0.007, Bonferroni 0.084 (>.05). Reported as null. violation_count is also a partial-leakage outcome. Pooled Poisson IRR 1.0169 flagged cross-sectional only.

## Limitations (honest)
- Identification ceiling: weather constant within calendar day -> Estab+Day FE infeasible (collinear); cannot net out arbitrary daily shocks.
- Preferred primary is a reduced-form total effect bundling any food-safety channel with temperature-driven inspection selection; the scheduled-only subsample isolates the non-selection channel and is also null.
- Bounded null only rules out large average effects (>~5% of base rate); underpowered for modest effects.
- violation_count is mechanically tied to fail (partial leakage); never used on RHS or as corroboration.
- Weather is keyed to date only (not establishment location/time); intra-city/intra-day weather heterogeneity is unobserved.