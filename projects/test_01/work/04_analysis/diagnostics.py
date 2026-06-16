#!/usr/bin/env python3
"""Identification diagnostics for H1 (chosen design):
 (a) attenuation plot: temp coef across specs (the core identification story),
 (b) raw binned temperature-vs-failrate figure,
 (c) PLACEBO: shuffled-weather re-estimate -> coef must be ~0,
 (d) seasonality robustness: day-of-year polynomial instead of month FE,
 (e) composition balance: does temperature predict inspection-type mix / daily volume?
All SE clustered by date. Appends claims; writes paper/figures/*.png."""
import os, json, sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.api as sm
from linearmodels.iv.absorbing import AbsorbingLS

sys.path.insert(0, os.path.dirname(__file__))
from prep import build_sample, SEED, ROOT

np.random.seed(SEED)
rng = np.random.default_rng(SEED)
FIG = os.path.join(ROOT, "paper/figures"); os.makedirs(FIG, exist_ok=True)
CLAIMS = os.path.join(ROOT, "validation/claims.json")
SCRIPT = "work/04_analysis/diagnostics.py"

store = json.load(open(CLAIMS))
def add_claim(key, value, **kw):
    store["claims"] = [c for c in store["claims"] if c["key"] != key]
    rec = {"key": key, "value": value, "script": SCRIPT}; rec.update(kw)
    store["claims"].append(rec)

df = build_sample()
df["day_code"] = df["day"].astype("category").cat.codes

def absorb_temp(d, absorb_cols, tempvar="temp10"):
    res = AbsorbingLS(d["fail"], d[[tempvar,"precip10"]],
                      absorb=d[absorb_cols].astype("category")).fit(
                      cov_type="clustered", clusters=d[["day_code"]])
    return float(res.params[tempvar]), float(res.std_errors[tempvar]), float(res.pvalues[tempvar])

# ---------- (a) attenuation plot across specs ----------
specs = []
X = sm.add_constant(df[["temp10","precip10"]])
m1 = sm.OLS(df["fail"], X).fit(cov_type="cluster", cov_kwds={"groups": df["day_code"]})
specs.append(("Pooled", float(m1.params["temp10"]), float(m1.bse["temp10"])))
dums = pd.get_dummies(df[["month","year","risk","inspection_type"]], drop_first=True, dtype=float)
d2 = pd.concat([df, dums], axis=1)
rhs2 = ["temp10","precip10","is_restaurant"]+list(dums.columns)
m2 = sm.OLS(d2["fail"], sm.add_constant(d2[rhs2])).fit(cov_type="cluster", cov_kwds={"groups": d2["day_code"]})
specs.append(("+Season/\nControls", float(m2.params["temp10"]), float(m2.bse["temp10"])))
b,s,_ = absorb_temp(df, ["estab","month","year"]); specs.append(("Estab FE", b, s))
b,s,_ = absorb_temp(df, ["estab","month","year","inspection_type"]); specs.append(("Estab FE\n+Type", b, s))

fig, ax = plt.subplots(figsize=(6,4))
xs = np.arange(len(specs))
ys = np.array([sp[1]*100 for sp in specs]); es = np.array([sp[2]*100*1.96 for sp in specs])
ax.errorbar(xs, ys, yerr=es, fmt="o", capsize=4, color="#1f3a5f")
ax.axhline(0, color="grey", lw=.8, ls="--")
ax.set_xticks(xs); ax.set_xticklabels([sp[0] for sp in specs], fontsize=9)
ax.set_ylabel("Effect of +10$^\\circ$C on P(fail), ppt")
ax.set_title("Temperature effect attenuates as confounders are absorbed")
fig.tight_layout(); fig.savefig(os.path.join(FIG,"fig1_attenuation.png"), dpi=150); plt.close(fig)

# ---------- (b) raw binned temperature vs fail rate ----------
df["tband"] = pd.cut(df["temp_mean"], bins=np.arange(-30,35,5))
g = df.groupby("tband", observed=True)["fail"].agg(["mean","count","sem"])
fig, ax = plt.subplots(figsize=(6,4))
centers = [iv.mid for iv in g.index]
ax.errorbar(centers, g["mean"]*100, yerr=g["sem"]*100*1.96, fmt="o-", color="#8c1d1d", capsize=3)
ax.set_xlabel("Inspection-day mean temperature ($^\\circ$C)")
ax.set_ylabel("Failure rate (%)")
ax.set_title("Raw failure rate vs temperature (unadjusted)")
fig.tight_layout(); fig.savefig(os.path.join(FIG,"fig2_raw_gradient.png"), dpi=150); plt.close(fig)

# ---------- (c) PLACEBO: shuffle weather across days ----------
# Map each unique day to a RANDOM other day's weather, keep estab structure.
day_w = df.groupby("day")[["temp10","precip10"]].first()
perm = rng.permutation(day_w.index.values)
shuffle_map = dict(zip(day_w.index.values, perm))
df["pl_day"] = df["day"].map(shuffle_map)
plw = day_w.rename(columns={"temp10":"temp10_pl","precip10":"precip10_pl"})
df = df.merge(plw, left_on="pl_day", right_index=True, how="left")
bp, sp_, pp = absorb_temp(df, ["estab","month","year","inspection_type"], tempvar="temp10_pl")
add_claim("placebo_temp_ppt_per10C", round(bp*100,3), se=round(sp_*100,3), p=round(pp,4),
          unit="percentage_points_per_10C", desc="PLACEBO: primary spec with weather randomly reassigned across days",
          log_line=f"placebo temp10 beta={bp:.5f} se={sp_:.5f} p={pp:.4f}")

# ---------- (d) seasonality robustness: day-of-year polynomial ----------
d3 = df.copy()
for k in (1,2,3): d3[f"doy{k}"] = (d3["doy"]/365.0)**k
# absorb estab + year + type; include doy poly as exog
res = AbsorbingLS(d3["fail"], d3[["temp10","precip10","doy1","doy2","doy3"]],
                  absorb=d3[["estab","year","inspection_type"]].astype("category")).fit(
                  cov_type="clustered", clusters=d3[["day_code"]])
bd, sd, pd_ = float(res.params["temp10"]), float(res.std_errors["temp10"]), float(res.pvalues["temp10"])
add_claim("seasonpoly_temp_ppt_per10C", round(bd*100,3), se=round(sd*100,3), p=round(pd_,4),
          unit="percentage_points_per_10C", desc="robustness: estab+year+type FE with cubic day-of-year polynomial",
          log_line=f"doypoly temp10 beta={bd:.5f} se={sd:.5f} p={pd_:.4f}")

# ---------- (e) composition balance: temp predicts inspection mix / volume? ----------
daily = df.groupby("day").agg(n=("fail","size"),
        temp10=("temp10","first"),
        share_complaint=("inspection_type", lambda s: float((s.astype(str).str.contains("Complaint")).mean())),
        share_canvass=("inspection_type", lambda s: float((s.astype(str)=="Canvass").mean()))).reset_index()
def simple_ols(y, x):
    m = sm.OLS(daily[y], sm.add_constant(daily[[x]])).fit(cov_type="HC1")
    return float(m.params[x]), float(m.bse[x]), float(m.pvalues[x])
for yv in ["n","share_complaint","share_canvass"]:
    b,s,p = simple_ols(yv,"temp10")
    add_claim(f"balance_{yv}_on_temp10", round(b,4), se=round(s,4), p=round(p,4),
              desc=f"day-level OLS of {yv} on temp(+10C): composition/volume balance",
              log_line=f"{yv} on temp10: beta={b:.4f} se={s:.4f} p={p:.4f}")

json.dump(store, open(CLAIMS,"w"), indent=2)

print("PLACEBO temp10 ppt/10C:", round(bp*100,3), "p=", round(pp,4))
print("DOY-poly temp10 ppt/10C:", round(bd*100,3), "p=", round(pd_,4))
print("Balance (day-level):")
for yv in ["n","share_complaint","share_canvass"]:
    c=[x for x in store["claims"] if x["key"]==f"balance_{yv}_on_temp10"][0]
    print(f"  {yv:16s} beta={c['value']:.4f} p={c['p']:.4f}")
print("Figures:", os.listdir(FIG))
print("claims now:", len(store["claims"]))
