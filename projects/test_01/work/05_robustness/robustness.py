#!/usr/bin/env python3
"""ROBUSTNESS gate. Perturbs the primary within-establishment design many ways and
reports the share of specs agreeing in SIGN and in SIGNIFICANCE on the temperature effect.
Also: nonlinearity (temp bins, H3), heterogeneity (H4), count outcome (H5, Poisson FE),
alternative clustering, alternative temp measures, sample restrictions, falsification.
All SE clustered by date unless noted. Appends claims; writes paper/tables/table2_robustness.tex."""
import os, json, sys, warnings
import numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from linearmodels.iv.absorbing import AbsorbingLS
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04_analysis"))
from prep import build_sample, SEED, ROOT

np.random.seed(SEED)
TAB = os.path.join(ROOT, "paper/tables")
CLAIMS = os.path.join(ROOT, "validation/claims.json")
SCRIPT = "work/05_robustness/robustness.py"

store = json.load(open(CLAIMS))
def add_claim(key, value, **kw):
    store["claims"] = [c for c in store["claims"] if c["key"] != key]
    rec = {"key": key, "value": value, "script": SCRIPT}; rec.update(kw)
    store["claims"].append(rec)

df = build_sample()
df["day_code"] = df["day"].astype("category").cat.codes
df["estab_code"] = df["estab"].cat.codes
df["zip"] = df["zip"].astype("category")

def fe_coef(d, tempvar="temp10", absorb_cols=("estab","month","year","inspection_type"),
            extra_exog=None, clusters="day_code"):
    exog = [tempvar, "precip10"] + (extra_exog or [])
    used = ["fail"] + exog + list(absorb_cols) + [clusters]
    d = d.dropna(subset=[c for c in used if c in d.columns]).copy()
    # keep only FE columns that retain >1 level in this (sub)sample
    ab = []
    for c in absorb_cols:
        col = d[c].astype("category").cat.remove_unused_categories()
        if col.nunique() > 1:
            d[c] = col; ab.append(c)
    res = AbsorbingLS(d["fail"], d[exog], absorb=d[ab]).fit(
          cov_type="clustered", clusters=d[[clusters]])
    return float(res.params[tempvar]), float(res.std_errors[tempvar]), float(res.pvalues[tempvar]), int(res.nobs)

robust = []  # (name, beta, se, p, n)

# --- baseline primary (for the table top) ---
robust.append(("Primary (Estab+Month+Year+Type FE)", *fe_coef(df)))
# --- alternative clustering ---
robust.append(("Cluster by establishment", *fe_coef(df, clusters="estab_code")))
robust.append(("Cluster by ZIP", *fe_coef(df.assign(zip_code=df['zip'].cat.codes), clusters="zip_code")))
# --- alternative temperature measures ---
df["tmax10"] = df["temperature_2m_max"]/10.0
df["app10"]  = df["apparent_temperature_mean"]/10.0
robust.append(("Use daily MAX temp", *fe_coef(df, tempvar="tmax10")))
robust.append(("Use apparent temp", *fe_coef(df, tempvar="app10")))
# --- FE variations ---
robust.append(("Drop Type FE (Estab+Month+Year)", *fe_coef(df, absorb_cols=("estab","month","year"))))
robust.append(("Add ZIP FE", *fe_coef(df, absorb_cols=("estab","month","year","inspection_type","zip"))))
# NOTE: Estab + calendar-day FE is INFEASIBLE -- weather is constant within day, so day FE
# absorbs 100% of weather variation (AbsorbingEffectError). This is the identification ceiling
# and is reported as a limitation, not a spec.
# --- sample restrictions ---
robust.append(("Canvass inspections only", *fe_coef(df[df['inspection_type']=='Canvass'].copy())))
robust.append(("Restaurants only", *fe_coef(df[df['is_restaurant']==1].copy())))
robust.append(("Risk 1 (high) only", *fe_coef(df[df['risk1']==1].copy())))
robust.append(("Pre-2020 only", *fe_coef(df[df['year'].astype(int)<2020].copy())))
robust.append(("2020+ only", *fe_coef(df[df['year'].astype(int)>=2020].copy())))
qlo, qhi = df['temp_mean'].quantile([.01,.99])
robust.append(("Trim temp 1/99 pct", *fe_coef(df[(df.temp_mean>=qlo)&(df.temp_mean<=qhi)].copy())))

# --- log all + compute agreement ---
sig = 0.10
pos = sum(1 for r in robust if r[1] > 0)
sig_any = sum(1 for r in robust if r[3] < sig)
pos_sig = sum(1 for r in robust if r[1] > 0 and r[3] < sig)
nspec = len(robust)
for i, r in enumerate(robust):
    add_claim(f"robust_spec{i:02d}_temp_ppt10C", round(r[1]*100,3), se=round(r[2]*100,3), p=round(r[3],4),
              n=r[4], spec=r[0], desc=f"robustness temp(+10C) effect: {r[0]}",
              log_line=f"{r[0]}: beta={r[1]:.5f} se={r[2]:.5f} p={r[3]:.4f} n={r[4]}")
add_claim("robust_n_specs", nspec, desc="number of robustness specs on temp effect")
add_claim("robust_share_positive", round(pos/nspec,3), desc="share of robustness specs with positive temp sign")
add_claim("robust_share_sig", round(sig_any/nspec,3), desc=f"share significant at {sig}")
add_claim("robust_share_pos_and_sig", round(pos_sig/nspec,3), desc=f"share positive AND significant at {sig}")

# --- H3 nonlinearity: temperature bins, joint test ---
dd = df.copy()
tb = pd.get_dummies(dd["tbin"], drop_first=True, dtype=float)  # ref = lt0
tb.columns = [f"tb_{c}" for c in tb.columns]
dd = pd.concat([dd, tb], axis=1)
resb = AbsorbingLS(dd["fail"], dd[list(tb.columns)+["precip10"]],
                   absorb=dd[["estab","month","year","inspection_type"]].astype("category")).fit(
                   cov_type="clustered", clusters=dd[["day_code"]])
# joint Wald that all bin coefs = 0
R = np.zeros((len(tb.columns), len(resb.params)))
names = list(resb.params.index)
for j,c in enumerate(tb.columns): R[j, names.index(c)] = 1
wald = resb.wald_test(R, np.zeros(len(tb.columns)))
add_claim("H3_bins_joint_p", round(float(wald.pval),4),
          desc="joint Wald p that all temperature-bin coefs=0 (test of any nonlinear temp effect)",
          log_line=f"temp-bin joint Wald stat={float(wald.stat):.3f} p={float(wald.pval):.4f}")
add_claim("H3_gt30_vs_lt0_ppt", round(float(resb.params.get('tb_gt30',np.nan))*100,3),
          se=round(float(resb.std_errors.get('tb_gt30',np.nan))*100,3),
          p=round(float(resb.pvalues.get('tb_gt30',np.nan)),4),
          desc="fail-prob gap (ppt) for >30C days vs <0C days, within estab")

# --- H4 heterogeneity: temp x risk1, temp x restaurant ---
dh = df.copy()
dh["temp10_x_risk1"] = dh["temp10"]*dh["risk1"]
dh["temp10_x_rest"]  = dh["temp10"]*dh["is_restaurant"]
resh = AbsorbingLS(dh["fail"], dh[["temp10","temp10_x_risk1","temp10_x_rest","precip10","risk1","is_restaurant"]],
                   absorb=dh[["estab","month","year","inspection_type"]].astype("category")).fit(
                   cov_type="clustered", clusters=dh[["day_code"]])
for v,lbl in [("temp10_x_risk1","H4_int_risk1"),("temp10_x_rest","H4_int_restaurant")]:
    add_claim(lbl+"_ppt10C", round(float(resh.params[v])*100,3), se=round(float(resh.std_errors[v])*100,3),
              p=round(float(resh.pvalues[v]),4), desc=f"H4 interaction {v}: differential temp effect (ppt/10C)",
              log_line=f"{v}: beta={float(resh.params[v]):.5f} p={float(resh.pvalues[v]):.4f}")

# --- H5 secondary count outcome: violation_count, Poisson with estab FE (PPML-style) ---
# Use statsmodels Poisson with estab dummies is infeasible (20k); use within-estab via high-dim:
# fall back to Poisson with month+year+type FE + estab via demeaning is non-trivial; run Poisson
# with month/year/type FE and cluster by date (no estab FE) and report as descriptive secondary.
dc = df.copy()
dc["vc"] = pd.to_numeric(dc["violation_count"], errors="coerce").fillna(0)
poiss = smf.poisson("vc ~ temp10 + precip10 + C(month) + C(year) + C(inspection_type)", data=dc).fit(
        cov_type="cluster", cov_kwds={"groups": dc["day_code"]}, disp=0, maxiter=100)
add_claim("H5_count_temp_irr_per10C", round(float(np.exp(poiss.params['temp10'])),4),
          p=round(float(poiss.pvalues['temp10']),4),
          desc="H5 secondary: Poisson IRR of violation_count per +10C (month/year/type FE, NO estab FE), cluster date",
          log_line=f"poisson temp10 coef={float(poiss.params['temp10']):.5f} IRR={np.exp(poiss.params['temp10']):.4f} p={float(poiss.pvalues['temp10']):.4f}")

json.dump(store, open(CLAIMS,"w"), indent=2)

# --- write Table 2 ---
def st(p): return "***" if p<.01 else "**" if p<.05 else "*" if p<.1 else ""
lines = [r"\begin{tabular}{lcccc}", r"\hline\hline",
         r"Specification & $\hat\beta$ (ppt/10$^\circ$C) & SE & p & N \\", r"\hline"]
for r in robust:
    lines.append(f"{r[0]} & {r[1]*100:.3f}{st(r[3])} & ({r[2]*100:.3f}) & {r[3]:.3f} & {r[4]:,} \\\\")
lines += [r"\hline",
          f"\\multicolumn{{5}}{{l}}{{\\footnotesize {pos}/{nspec} positive; {sig_any}/{nspec} significant at .10; {pos_sig}/{nspec} positive \\& significant.}}\\\\",
          r"\multicolumn{5}{l}{\footnotesize Dep. var.: fail. SE clustered by date (unless noted). *** p$<$.01, ** p$<$.05, * p$<$.1}\\",
          r"\end{tabular}"]
open(os.path.join(TAB,"table2_robustness.tex"),"w").write("\n".join(lines))

print(f"=== ROBUSTNESS: {nspec} specs ===")
for r in robust:
    print(f"  {r[0]:36s} {r[1]*100:+.3f}{st(r[3]):3s} se={r[2]*100:.3f} p={r[3]:.3f} N={r[4]:,}")
print(f"\nAgreement: positive {pos}/{nspec} ({pos/nspec:.0%}); sig@.10 {sig_any}/{nspec} ({sig_any/nspec:.0%}); pos&sig {pos_sig}/{nspec} ({pos_sig/nspec:.0%})")
print(f"H3 bins joint p = {float(wald.pval):.4f};  >30C vs <0C gap = {float(resb.params.get('tb_gt30',np.nan))*100:.3f} ppt")
print(f"H4 temp x risk1 = {float(resh.params['temp10_x_risk1'])*100:+.3f} ppt (p={float(resh.pvalues['temp10_x_risk1']):.3f}); temp x restaurant = {float(resh.params['temp10_x_rest'])*100:+.3f} ppt (p={float(resh.pvalues['temp10_x_rest']):.3f})")
print(f"H5 Poisson IRR/10C = {np.exp(poiss.params['temp10']):.4f} (p={float(poiss.pvalues['temp10']):.3f})")
print("claims now:", len(store["claims"]))
