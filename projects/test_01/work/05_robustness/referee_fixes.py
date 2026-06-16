#!/usr/bin/env python3
"""Referee round-1 BLOCKING fixes (computational parts).
 #1 reconcile/label estimation-sample vs profile-level N (distinct claim keys)
 #3 CIs with small-sample t(G-1) critical values; record df
 #4 coarser clustering (ISO-week, year-month) + wild-cluster bootstrap for contested cells
 #6 co-primary estab+Month+Year WITHOUT inspection-type FE (type is a mediator/collider)
 #7 multiplicity: Bonferroni-adjusted p for the 13 robustness tests; coarse-cluster re-test of Canvass/Risk1
 #9 genuine WITHIN-establishment intensive margin (linear FE on violation_count and asinh); demote Poisson
 #13 add an explicit 'sig_vs_zero' flag on headline magnitude keys
All SE clustered by date (or coarser, as noted)."""
import os, json, sys
import numpy as np, pandas as pd
from scipy import stats
import pyhdfe
from linearmodels.iv.absorbing import AbsorbingLS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04_analysis"))
from prep import build_sample, SEED, ROOT

np.random.seed(SEED)
rng = np.random.default_rng(SEED)
CLAIMS = os.path.join(ROOT, "validation/claims.json")
TAB = os.path.join(ROOT, "paper/tables")
SCRIPT = "work/05_robustness/referee_fixes.py"
store = json.load(open(CLAIMS))
def add_claim(key, value, **kw):
    store["claims"] = [c for c in store["claims"] if c["key"] != key]
    rec = {"key": key, "value": value, "script": SCRIPT}; rec.update(kw)
    store["claims"].append(rec)
def getc(k): return next((c for c in store["claims"] if c["key"]==k), {})

df = build_sample()
df["day_code"] = df["day"].astype("category").cat.codes
df["week"] = df["date"].dt.strftime("%G-%V")          # ISO year-week
df["ym"]   = df["date"].dt.strftime("%Y-%m")          # year-month of sample
df["vc"]   = pd.to_numeric(df["violation_count"], errors="coerce").fillna(0.0)
df["asinh_vc"] = np.arcsinh(df["vc"])

def absorb_fit(d, dep, exog, absorb_cols, cluster):
    d = d.dropna(subset=[dep]+exog+list(absorb_cols)+[cluster]).copy()
    ab=[]
    for c in absorb_cols:
        col=d[c].astype("category").cat.remove_unused_categories()
        if col.nunique()>1: d[c]=col; ab.append(c)
    res = AbsorbingLS(d[dep], d[exog], absorb=d[ab]).fit(cov_type="clustered", clusters=d[[cluster]])
    G = d[cluster].nunique()
    return res, G, d

def coefrow(res, G, v):
    b, se = float(res.params[v]), float(res.std_errors[v])
    tcrit = stats.t.ppf(.975, G-1)
    return b, se, float(res.pvalues[v]), G, b-tcrit*se, b+tcrit*se

# ---------- #1 reconcile N: estimation-sample vs profile-level ----------
prof = json.load(open(os.path.join(ROOT,"work/02_profile/profile.json")))
add_claim("profile_n_estab", prof["repeat_structure"]["n_unique_establishments_dba_address"],
          desc="PROFILE-LEVEL unique establishments (full file, before substantive-sample restriction)")
add_claim("profile_n_weatherdays", prof["weather_variation"]["unique_weather_days"],
          desc="PROFILE-LEVEL unique weather-days (full file)")
add_claim("est_n_estab", int(df["estab"].nunique()), desc="ESTIMATION-SAMPLE establishments (substantive sample)")
add_claim("est_n_dayclusters", int(df["day"].nunique()), desc="ESTIMATION-SAMPLE day-clusters; governs inference")

# ---------- #3 + #6: co-primary specs with t(G-1) CIs ----------
# primary WITH type (direct effect, net of mediator)
rW,GW,_ = absorb_fit(df,"fail",["temp10","precip10"],("estab","month","year","inspection_type"),"day_code")
bW,seW,pW,GW,loW,hiW = coefrow(rW,GW,"temp10")
add_claim("primaryB_temp_ppt_per10C", round(bW*100,3), se=round(seW*100,3), p=round(pW,4),
          df_clusters=GW, ci_t=[round(loW*100,3),round(hiW*100,3)], unit="ppt_per_10C",
          spec="Estab+Month+Year+Type FE (direct, conditions on mediator type)",
          sig_vs_zero=False, desc="co-primary WITH type FE; t(G-1) CI",
          log_line=f"primaryB temp10={bW:.5f} se={seW:.5f} p={pW:.4f} G={GW} tCI=[{loW*100:.3f},{hiW*100:.3f}]")
# primary WITHOUT type (reduced-form total effect; type is a mediator/collider -> do not condition)
rA,GA,_ = absorb_fit(df,"fail",["temp10","precip10"],("estab","month","year"),"day_code")
bA,seA,pA,GA,loA,hiA = coefrow(rA,GA,"temp10")
add_claim("primaryA_temp_ppt_per10C", round(bA*100,3), se=round(seA*100,3), p=round(pA,4),
          df_clusters=GA, ci_t=[round(loA*100,3),round(hiA*100,3)], unit="ppt_per_10C",
          spec="Estab+Month+Year FE (reduced-form total effect, no mediator conditioning)",
          sig_vs_zero=False, desc="CO-PRIMARY without type FE (preferred: type is a mediator); t(G-1) CI",
          log_line=f"primaryA temp10={bA:.5f} se={seA:.5f} p={pA:.4f} G={GA} tCI=[{loA*100:.3f},{hiA*100:.3f}]")

# ---------- #4 coarse clustering for the co-primary specs ----------
for lab,absorb_cols in [("A_estabMY",("estab","month","year")),("B_estabMYType",("estab","month","year","inspection_type"))]:
    for cl in ["week","ym"]:
        r,G,_ = absorb_fit(df,"fail",["temp10","precip10"],absorb_cols,cl)
        b,se,p,G,lo,hi = coefrow(r,G,"temp10")
        add_claim(f"coarse_{lab}_cluster_{cl}", round(b*100,3), se=round(se*100,3), p=round(p,4),
                  df_clusters=G, desc=f"co-primary {lab} clustered by {cl} (coarser, weather autocorrelation)",
                  log_line=f"{lab}/{cl}: b={b*100:.3f}ppt se={se*100:.3f} p={p:.4f} G={G}")

# ---------- #7 coarse-cluster re-test of the contested significant subsamples ----------
contested = {"Canvass_only": df[df["inspection_type"]=="Canvass"].copy(),
             "Risk1_only":  df[df["risk1"]==1].copy()}
for name,d in contested.items():
    for cl in ["day_code","week","ym"]:
        ab = ("estab","month","year") if name=="Canvass_only" else ("estab","month","year","inspection_type")
        r,G,_ = absorb_fit(d,"fail",["temp10","precip10"],ab,cl)
        b,se,p,G,lo,hi = coefrow(r,G,"temp10")
        tag = {"day_code":"day","week":"week","ym":"ym"}[cl]
        add_claim(f"contested_{name}_cluster_{tag}", round(b*100,3), se=round(se*100,3), p=round(p,4),
                  df_clusters=G, desc=f"{name} temp effect clustered by {tag}",
                  log_line=f"{name}/{tag}: b={b*100:.3f} se={se*100:.3f} p={p:.4f} G={G}")

# ---------- #4 wild-cluster bootstrap (Rademacher, impose null) for Canvass-only, month clusters ----------
def wild_boot_p(d, absorb_cols, cluster, nboot=999):
    d = d.dropna(subset=["fail","temp10","precip10"]+list(absorb_cols)+[cluster]).copy()
    ids = d[list(absorb_cols)].astype("category").apply(lambda s:s.cat.codes).values
    alg = pyhdfe.create(ids, drop_singletons=False)
    M = alg.residualize(d[["fail","temp10","precip10"]].to_numpy(float))
    y, x = M[:,0], M[:,1:]               # x = [temp10, precip10] residualized
    # full fit
    XtX = x.T@x; beta = np.linalg.solve(XtX, x.T@y)
    resid = y - x@beta
    # cluster-robust t on temp10 (coef 0)
    cl = d[cluster].astype("category").cat.codes.to_numpy()
    def crve_t(y_, x_, b_):
        r_ = y_ - x_@b_
        meat = np.zeros((x_.shape[1],x_.shape[1]))
        for g in np.unique(cl):
            xi = x_[cl==g]; ri = r_[cl==g]
            sg = xi.T@ri; meat += np.outer(sg,sg)
        bread = np.linalg.inv(x_.T@x_)
        V = bread@meat@bread
        return b_[0]/np.sqrt(V[0,0])
    t0 = crve_t(y, x, beta)
    # restricted (impose temp10=0): regress y on precip10 only
    xr = x[:,[1]]; br = np.linalg.solve(xr.T@xr, xr.T@y); rr = y - xr@br
    G = len(np.unique(cl)); tb = np.empty(nboot)
    gmap = {g:i for i,g in enumerate(np.unique(cl))}
    gidx = np.array([gmap[c] for c in cl])
    for bi in range(nboot):
        w = rng.choice([-1.0,1.0], size=G)[gidx]
        yb = xr@br + rr*w
        bb = np.linalg.solve(XtX, x.T@yb)
        tb[bi] = crve_t(yb, x, bb)
    p = (np.sum(np.abs(tb) >= abs(t0)) + 1) / (nboot + 1)
    return float(t0), float(p), int(G)
t0,wp,Gw = wild_boot_p(df[df["inspection_type"]=="Canvass"].copy(), ("estab","month","year"), "ym")
add_claim("contested_Canvass_wildboot_p_ym", round(wp,4), t_stat=round(t0,3), df_clusters=Gw,
          desc="Canvass-only: wild-cluster bootstrap p (Rademacher, null imposed, month clusters, 999 reps)",
          log_line=f"Canvass wild-cluster boot: t={t0:.3f} p={wp:.4f} G={Gw}")

# ---------- #7 multiplicity: Bonferroni on the 13 robustness tests ----------
rp = sorted(float(getc(f"robust_spec{i:02d}_temp_ppt10C").get("p",1)) for i in range(13))
minp = rp[0]; m = len(rp)
add_claim("robust_min_p", round(minp,4), desc="smallest p among 13 robustness specs")
add_claim("robust_min_p_bonferroni", round(min(1.0, minp*m),4),
          desc=f"Bonferroni-adjusted smallest p across {m} robustness tests")
add_claim("robust_expected_false_pos_at05", round(0.05*m,2),
          desc=f"expected number of false positives at alpha=.05 across {m} tests")

# ---------- #9 genuine WITHIN-establishment intensive margin ----------
for dep,lbl in [("vc","H5b_within_vc_count"),("asinh_vc","H5b_within_asinh")]:
    r,G,_ = absorb_fit(df,dep,["temp10","precip10"],("estab","month","year","inspection_type"),"day_code")
    b,se,p,G,lo,hi = coefrow(r,G,"temp10")
    add_claim(lbl+"_per10C", round(b,4), se=round(se,4), p=round(p,4), df_clusters=G, sig_vs_zero=(p<0.05),
              desc=f"WITHIN-estab linear FE intensive margin: {dep} on temp(+10C), estab+month+year+type FE, cluster date",
              log_line=f"{lbl}: b={b:.5f} se={se:.5f} p={p:.4f} G={G}")
# flag the pooled Poisson as cross-sectional (not within)
h5 = getc("H5_count_temp_irr_per10C")
if h5: add_claim("H5_count_temp_irr_per10C", h5["value"], **{k:v for k,v in h5.items() if k not in ("key","value")},
                 cross_sectional_only=True, sig_vs_zero=False,
                 note="POOLED cross-sectional (no estab FE); NOT the within-establishment estimand. See H5b_* for within.")

# ---------- #13 overclaim flag on the relative-effect key ----------
rel = getc("primary_temp_pct_of_baserate_per10C")
if rel: add_claim("primary_temp_pct_of_baserate_per10C", rel["value"],
                  **{k:v for k,v in rel.items() if k not in ("key","value")},
                  sig_vs_zero=False, note="point estimate ONLY; not significantly different from zero; quote with CI.")

json.dump(store, open(CLAIMS,"w"), indent=2)

print("=== #1 N reconciliation ===")
print(f"  profile-level: {getc('profile_n_estab')['value']:,} estab / {getc('profile_n_weatherdays')['value']:,} weather-days")
print(f"  estimation:    {getc('est_n_estab')['value']:,} estab / {getc('est_n_dayclusters')['value']:,} day-clusters")
print("=== #6 co-primary (t(G-1) CIs) ===")
print(f"  A no-Type (preferred): {bA*100:+.3f} ppt/10C  p={pA:.3f}  CI[{loA*100:.2f},{hiA*100:.2f}]  G={GA}")
print(f"  B with-Type:           {bW*100:+.3f} ppt/10C  p={pW:.3f}  CI[{loW*100:.2f},{hiW*100:.2f}]  G={GW}")
print("=== #4 coarse clustering (co-primary A) ===")
for cl in ["week","ym"]:
    c=getc(f"coarse_A_estabMY_cluster_{cl}"); print(f"  cluster {cl:5s}: {c['value']:+.3f} ppt p={c['p']:.3f} G={c['df_clusters']}")
print("=== #7 contested subsamples under coarser clusters ===")
for name in contested:
    row=" ".join(f"{tag}:p={getc(f'contested_{name}_cluster_{tag}')['p']:.3f}(G={getc(f'contested_{name}_cluster_{tag}')['df_clusters']})" for tag in ["day","week","ym"])
    print(f"  {name:13s} {row}")
print(f"  Canvass wild-cluster-boot p (month) = {wp:.3f} (t={t0:.2f}, G={Gw})")
print(f"  multiplicity: min p={minp:.3f}, Bonferroni={min(1,minp*m):.3f}, expected FP@.05={0.05*m:.2f}")
print("=== #9 within-estab intensive margin ===")
for lbl in ["H5b_within_vc_count","H5b_within_asinh"]:
    c=getc(lbl+"_per10C"); print(f"  {lbl}: {c['value']:+.4f} (p={c['p']:.3f})  [pooled Poisson IRR was {getc('H5_count_temp_irr_per10C')['value']}, flagged cross-sectional]")
print("claims now:", len(store["claims"]))
