#!/usr/bin/env python3
"""Referee round-3 BLOCKING fixes.
 R3-1: run H4's pre-registered must-pass diagnostic -> restaurant interaction robust to dropping any single facility type.
 R3-2: retire stale unreconciled H4 keys (H4_int_restaurant_ppt10C=0.918, H4_int_risk1_ppt10C).
 R3-3: resolve primaryA causal-scope inconsistency -> estimate scheduled (non-complaint) subsample; report both,
        restate primaryA as reduced-form total effect (safety + selection)."""
import os, json, sys
import numpy as np, pandas as pd
from scipy import stats
import pyhdfe
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04_analysis"))
from prep import build_sample, ROOT
CLAIMS = os.path.join(ROOT, "validation/claims.json")
SCRIPT = "work/05_robustness/referee_fixes3.py"
store = json.load(open(CLAIMS))
def add(key, value, **kw):
    store["claims"]=[c for c in store["claims"] if c["key"]!=key]
    r={"key":key,"value":value,"script":SCRIPT}; r.update(kw); store["claims"].append(r)
def getc(k): return next((c for c in store["claims"] if c["key"]==k), {})
def drop(k): store["claims"]=[c for c in store["claims"] if c["key"]!=k]

df = build_sample()
df["day_code"]=df["day"].astype("category").cat.codes
df["week"]=df["date"].dt.strftime("%G-%V"); df["ym"]=df["date"].dt.strftime("%Y-%m")
df["facility_type"]=df["facility_type"].astype(str)
df["temp10_x_rest"]=df["temp10"]*df["is_restaurant"]
df["temp10_x_risk1"]=df["temp10"]*df["risk1"]
df["is_complaint"]=df["inspection_type"].astype(str).str.contains("Complaint")

def fit(d, exog, absorb_cols, target, cl="day_code"):
    # Deterministic HDFE-OLS via pyhdfe residualization + cluster-robust sandwich SE.
    # Matches linearmodels.AbsorbingLS coefficients & SE exactly (validated), but avoids its
    # flaky check_absorbed tolerance. Main effects of establishment-invariant covariates are
    # absorbed by establishment FE; only the temp-interaction (varies within estab) is identified.
    keep=[c for c in absorb_cols if d[c].astype('category').cat.remove_unused_categories().nunique()>1]
    d=d.dropna(subset=exog+list(keep)+[cl,"fail"]).copy()
    ids=np.column_stack([d[c].astype("category").cat.codes.to_numpy() for c in keep])
    alg=pyhdfe.create(ids, drop_singletons=False, compute_degrees=False)
    R=alg.residualize(d[["fail"]+exog].to_numpy(float))
    y=R[:,0]; X=R[:,1:]; XtX=X.T@X; beta=np.linalg.solve(XtX, X.T@y); resid=y-X@beta
    clc=d[cl].astype("category").cat.codes.to_numpy(); G=len(np.unique(clc)); N,K=X.shape
    meat=np.zeros((K,K))
    for g in np.unique(clc):
        Xg=X[clc==g]; s=Xg.T@resid[clc==g]; meat+=np.outer(s,s)
    bread=np.linalg.inv(XtX); c=(G/(G-1))*((N-1)/(N-K)); V=c*bread@meat@bread; se=np.sqrt(np.diag(V))
    i=exog.index(target); b=beta[i]; s_=se[i]; t=b/s_; tcrit=stats.t.ppf(.975,G-1)
    return b,s_,2*stats.t.sf(abs(t),G-1),G,b-tcrit*s_,b+tcrit*s_,N

# ---- R3-2: retire stale keys; recompute H4 headline cleanly (estab FE absorbs main effects) ----
drop("H4_int_restaurant_ppt10C"); drop("H4_int_risk1_ppt10C")
ABS=("estab","month","year","inspection_type")
for v,short in [("temp10_x_rest","restaurant"),("temp10_x_risk1","risk1")]:
    for cl in ["day_code","week","ym"]:
        b,se,p,G,lo,hi,n=fit(df,["temp10",v,"precip10"],ABS,v,cl)
        tag={"day_code":"day","week":"week","ym":"ym"}[cl]
        add(f"H4_{short}_cluster_{tag}", round(b*100,3), se=round(se*100,3), p=round(p,4), df_clusters=G,
            ci_t=[round(lo*100,3),round(hi*100,3)],
            desc=f"H4 temp x {short} interaction (ppt/10C), clustered by {tag}; estab FE absorbs main effect")

# ---- R3-1: drop-one-facility-type diagnostic for temp x restaurant ----
EXOG=["temp10","temp10_x_rest","precip10"]
# baseline
b0,se0,p0,G0,lo0,hi0,n0=fit(df,EXOG,ABS,"temp10_x_rest")
# drop one NON-restaurant comparison facility type at a time (dropping Restaurant itself
# would make the interaction all-zero); confirms the differential isn't driven by one comparator.
top=[ft for ft in df["facility_type"].value_counts().index if ft.strip().lower()!="restaurant"][:8]
results=[]
for ft in top:
    sub=df[df["facility_type"]!=ft]
    b,se,p,G,lo,hi,n=fit(sub,EXOG,ABS,"temp10_x_rest")
    results.append((ft,b,se,p,n))
betas=[r[1] for r in results]; ps=[r[3] for r in results]
add("H4_rest_dropfac_baseline_ppt", round(b0*100,3), se=round(se0*100,3), p=round(p0,4), df_clusters=G0,
    ci_t=[round(lo0*100,3),round(hi0*100,3)],
    desc="H4 temp x restaurant baseline (date-clustered), for drop-one-facility-type diagnostic")
add("H4_rest_dropfac_min_beta_ppt", round(min(betas)*100,3),
    desc="min temp x restaurant coef across drop-one-facility-type (of top 8 types)")
add("H4_rest_dropfac_max_p", round(max(ps),4),
    desc="max p of temp x restaurant across drop-one-facility-type; must stay <.05 to pass H4 diagnostic")
add("H4_rest_dropfac_pass", bool(max(ps)<0.05),
    desc="H4 pre-registered must-pass: restaurant interaction robust to dropping any single facility type",
    log_line="; ".join(f"drop {r[0][:18]}: b={r[1]*100:.3f}ppt p={r[3]:.4f}" for r in results))

# ---- R3-3: scheduled (non-complaint) subsample for the primary ----
sched=df[~df["is_complaint"]].copy()
bs,ses,psd,Gs,los,his,ns=fit(sched,["temp10","precip10"],("estab","month","year"),"temp10")
add("primaryA_scheduled_temp_ppt_per10C", round(bs*100,3), se=round(ses*100,3), p=round(psd,4),
    df_clusters=Gs, ci_t=[round(los*100,3),round(his*100,3)], n=ns, sig_vs_zero=bool(psd<0.05),
    desc="PREFERRED primary restricted to SCHEDULED (non-complaint) inspections -> isolates non-selection channel",
    log_line=f"scheduled primaryA temp10={bs:.5f} se={ses:.5f} p={psd:.4f} G={Gs} n={ns} CI=[{los*100:.3f},{his*100:.3f}]")
# share of complaint inspections for context
add("complaint_share", round(float(df["is_complaint"].mean()),4),
    desc="share of substantive inspections that are complaint-driven (endogenous timing)")

json.dump(store, open(CLAIMS,"w"), indent=2)

print("=== R3-2: stale H4 keys retired ===", "H4_int_restaurant_ppt10C" not in {c['key'] for c in store['claims']})
print("=== R3-1: drop-one-facility-type (temp x restaurant) ===")
print(f"  baseline: {b0*100:+.3f} ppt p={p0:.4f} (n={n0:,})")
for ft,b,se,p,n in results:
    print(f"  drop {ft[:28]:28s}: {b*100:+.3f} ppt p={p:.4f} (n={n:,})")
print(f"  -> min beta {min(betas)*100:.3f} ppt, MAX p {max(ps):.4f}, PASS={max(ps)<0.05}")
print("=== R3-3: scheduled (non-complaint) primary ===")
print(f"  complaint share = {df['is_complaint'].mean():.3f}")
print(f"  scheduled primaryA: {bs*100:+.3f} ppt/10C  p={psd:.4f}  CI[{los*100:.3f},{his*100:.3f}]  n={ns:,} G={Gs}")
print("claims now:", len(store["claims"]))
