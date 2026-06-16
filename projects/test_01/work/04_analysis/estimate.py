#!/usr/bin/env python3
"""ESTIMATE gate (H1): LPM of inspection FAIL on inspection-day temperature.
Fixed seed. SE clustered by calendar date throughout (weather is constant within day).
Emits paper/tables/table1_main.tex and appends every number to validation/claims.json."""
import os, json, sys
import numpy as np, pandas as pd
import statsmodels.api as sm
from linearmodels.iv.absorbing import AbsorbingLS

sys.path.insert(0, os.path.dirname(__file__))
from prep import build_sample, SEED, ROOT

np.random.seed(SEED)
TAB = os.path.join(ROOT, "paper/tables"); os.makedirs(TAB, exist_ok=True)
CLAIMS = os.path.join(ROOT, "validation/claims.json")
SCRIPT = "work/04_analysis/estimate.py"

def load_claims():
    if os.path.exists(CLAIMS):
        return json.load(open(CLAIMS))
    return {"claims": []}

def add_claim(store, key, value, **kw):
    store["claims"] = [c for c in store["claims"] if c["key"] != key]  # idempotent
    rec = {"key": key, "value": value, "script": SCRIPT}
    rec.update(kw)
    store["claims"].append(rec)

def star(p):
    return "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""

# ---------- pooled LPM via statsmodels, cluster by date ----------
def pooled(df, rhs, label):
    X = sm.add_constant(df[rhs]); y = df["fail"]
    m = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": df["day_code"]})
    return m

# ---------- absorbing FE via linearmodels, cluster by date ----------
def absorb(df, exog_cols, absorb_cols, label):
    dep = df["fail"]
    exog = df[exog_cols]
    ab = df[absorb_cols].astype("category")
    mod = AbsorbingLS(dep, exog, absorb=ab)
    res = mod.fit(cov_type="clustered", clusters=df[["day_code"]])
    return res

def main():
    df = build_sample()
    df["day_code"] = df["day"].astype("category").cat.codes
    store = load_claims()

    add_claim(store, "n_sample", int(len(df)), unit="inspections",
              desc="substantive inspections (pass/pass_w_conditions/fail)")
    add_claim(store, "fail_rate", round(float(df["fail"].mean()), 4), unit="share",
              desc="mean of fail outcome")
    add_claim(store, "n_estab", int(df["estab"].nunique()), desc="unique establishments")
    add_claim(store, "n_dayclusters", int(df["day"].nunique()), desc="calendar-date clusters")
    add_claim(store, "temp_mean_mean", round(float(df["temp_mean"].mean()), 2), unit="degC",
              desc="mean inspection-day temperature")
    add_claim(store, "temp_mean_sd", round(float(df["temp_mean"].std()), 2), unit="degC",
              desc="sd inspection-day temperature")

    rows = []  # (specname, beta_temp10, se, p, beta_precip10, se_p, n, fe)

    # Spec 1: pooled, temp + precip only
    m1 = pooled(df, ["temp10", "precip10"], "pooled")
    # Spec 2: pooled + month + year dummies + risk + inspection_type + restaurant
    d2 = df.copy()
    dums = pd.get_dummies(d2[["month","year","risk","inspection_type"]], drop_first=True, dtype=float)
    d2 = pd.concat([d2, dums], axis=1)
    rhs2 = ["temp10","precip10","is_restaurant"] + list(dums.columns)
    m2 = pooled(d2, rhs2, "pooled+controls")
    # Spec 3: establishment FE + month + year (absorb estab, month, year)
    m3 = absorb(df, ["temp10","precip10"], ["estab","month","year"], "estabFE+monthFE+yearFE")
    # Spec 4 (PRIMARY): + inspection_type absorbed too
    m4 = absorb(df, ["temp10","precip10"], ["estab","month","year","inspection_type"], "primary")

    def get_sm(m, v):
        return float(m.params[v]), float(m.bse[v]), float(m.pvalues[v])
    def get_ab(m, v):
        return float(m.params[v]), float(m.std_errors[v]), float(m.pvalues[v])

    specs = [
        ("(1) Pooled", *get_sm(m1,"temp10"), *get_sm(m1,"precip10"), int(m1.nobs), "none"),
        ("(2) +Controls", *get_sm(m2,"temp10"), *get_sm(m2,"precip10"), int(m2.nobs), "Month,Year,Risk,Type"),
        ("(3) Estab FE", *get_ab(m3,"temp10"), *get_ab(m3,"precip10"), int(m3.nobs), "Estab,Month,Year"),
        ("(4) Estab FE +Type", *get_ab(m4,"temp10"), *get_ab(m4,"precip10"), int(m4.nobs), "Estab,Month,Year,Type"),
    ]

    # log claims for every coefficient
    for sp in specs:
        name, bt, st, pt, bp, spp, pp, n, fe = sp
        tag = name.split()[0].strip("()")
        add_claim(store, f"temp10_beta_spec{tag}", round(bt,5), se=round(st,5), p=round(pt,4),
                  unit="ppt_per_10C", spec=name, fe=fe, n=n,
                  desc=f"LPM coef on temperature(+10C) for fail, spec {name}",
                  log_line=f"{name}: temp10 beta={bt:.5f} se={st:.5f} p={pt:.4f}")
        add_claim(store, f"precip10_beta_spec{tag}", round(bp,5), se=round(spp,5), p=round(pp,4),
                  unit="ppt_per_10mm", spec=name, fe=fe, n=n,
                  desc=f"LPM coef on precipitation(+10mm) for fail, spec {name}",
                  log_line=f"{name}: precip10 beta={bp:.5f} se={spp:.5f} p={pp:.4f}")

    # headline numbers from PRIMARY spec (4)
    b4, s4, p4 = get_ab(m4, "temp10")
    ci_lo, ci_hi = b4 - 1.96*s4, b4 + 1.96*s4
    add_claim(store, "primary_temp_ppt_per10C", round(b4*100,3), se=round(s4*100,3), p=round(p4,4),
              ci=[round(ci_lo*100,3), round(ci_hi*100,3)], unit="percentage_points_per_10C",
              spec="(4) Estab FE +Type", desc="PRIMARY: change in fail probability (ppt) per +10C inspection-day temp",
              log_line=f"PRIMARY temp10 beta={b4:.5f} se={s4:.5f} -> {b4*100:.3f} ppt/10C p={p4:.4f}")
    # relative to base rate
    rel = b4 / float(df["fail"].mean()) * 100
    add_claim(store, "primary_temp_pct_of_baserate_per10C", round(rel,2), unit="pct_of_baseline_failrate_per10C",
              desc="primary temp effect per +10C as % of baseline 22.76% fail rate",
              log_line=f"rel effect = {b4:.5f}/{df['fail'].mean():.5f}*100 = {rel:.2f}%")
    bp4, sp4, pp4 = get_ab(m4, "precip10")
    add_claim(store, "primary_precip_ppt_per10mm", round(bp4*100,3), se=round(sp4*100,3), p=round(pp4,4),
              unit="percentage_points_per_10mm", spec="(4) Estab FE +Type",
              desc="PRIMARY: change in fail probability (ppt) per +10mm precip",
              log_line=f"PRIMARY precip10 beta={bp4:.5f} se={sp4:.5f} -> {bp4*100:.3f} ppt/10mm p={pp4:.4f}")

    json.dump(store, open(CLAIMS,"w"), indent=2)

    # ---------- write Table 1 ----------
    def fmt(b, s, p): return f"{b*100:.3f}{star(p)}\\\\ \n & ({s*100:.3f})"
    lines = [r"\begin{tabular}{lcccc}", r"\hline\hline",
             r" & (1) & (2) & (3) & (4) \\",
             r" & Pooled & +Controls & Estab FE & Estab FE \\",
             r"\hline"]
    # temperature row
    tcells = " & ".join(f"{sp[1]*100:.3f}{star(sp[3])}" for sp in specs)
    tse    = " & ".join(f"({sp[2]*100:.3f})" for sp in specs)
    pcells = " & ".join(f"{sp[4]*100:.3f}{star(sp[6])}" for sp in specs)
    pse    = " & ".join(f"({sp[5]*100:.3f})" for sp in specs)
    lines += [f"Temperature (+10$^\\circ$C) & {tcells} \\\\",
              f" & {tse} \\\\",
              f"Precipitation (+10mm) & {pcells} \\\\",
              f" & {pse} \\\\",
              r"\hline"]
    lines += [r"Fixed effects & none & M,Y,R,T & E,M,Y & E,M,Y,T \\",
              "N & " + " & ".join(f"{sp[7]:,}" for sp in specs) + r" \\",
              r"\hline\hline",
              r"\multicolumn{5}{l}{\footnotesize Dep. var.: fail (=1). Coefs in percentage points. SE clustered by date in ().}\\",
              r"\multicolumn{5}{l}{\footnotesize FE: E=Establishment, M=Month-of-year, Y=Year, R=Risk, T=Inspection type. *** p$<$.01, ** p$<$.05, * p$<$.1}\\",
              r"\end{tabular}"]
    open(os.path.join(TAB,"table1_main.tex"),"w").write("\n".join(lines))

    print("=== PRIMARY (spec 4) ===")
    print(f"temp10  beta={b4:.5f} se={s4:.5f} p={p4:.4f}  -> {b4*100:.3f} ppt per +10C  ({rel:.1f}% of base rate)")
    print(f"precip10 beta={bp4:.5f} se={sp4:.5f} p={pp4:.4f} -> {bp4*100:.3f} ppt per +10mm")
    print("\nAll specs (temp10 ppt per +10C):")
    for sp in specs:
        print(f"  {sp[0]:22s} {sp[1]*100:+.3f}{star(sp[3]):3s} se={sp[2]*100:.3f} p={sp[3]:.4f} N={sp[7]:,} FE={sp[8]}")
    print("\nWROTE", os.path.join(TAB,"table1_main.tex"))
    print("claims now:", len(store["claims"]))

if __name__ == "__main__":
    main()
