#!/usr/bin/env python3
"""Consolidated extra-inference computations (folded from interactive steps so run_all.sh
regenerates every claim):
 (a) within-establishment intensive-margin (violation count) under week/month clustering,
 (b) scheduled (non-complaint) primary under week/month clustering,
 (c) AbsorbingLS-vs-pyhdfe estimator equivalence check on the primary cell.
All SE clustered as noted. Appends to validation/claims.json."""
import os, sys, json
import numpy as np, pandas as pd
from scipy import stats
import pyhdfe
from linearmodels.iv.absorbing import AbsorbingLS
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04_analysis"))
from prep import build_sample, ROOT
CLAIMS = os.path.join(ROOT, "validation/claims.json")
SCRIPT = "work/05_robustness/extra_inference.py"
store = json.load(open(CLAIMS))
def add(key, value, **kw):
    store["claims"]=[c for c in store["claims"] if c["key"]!=key]
    r={"key":key,"value":value,"script":SCRIPT}; r.update(kw); store["claims"].append(r)

df = build_sample()
df["day_code"]=df["day"].astype("category").cat.codes
df["week"]=df["date"].dt.strftime("%G-%V"); df["ym"]=df["date"].dt.strftime("%Y-%m")
df["vc"]=pd.to_numeric(df["violation_count"],errors="coerce").fillna(0.0)
df["asinh_vc"]=np.arcsinh(df["vc"])
df["is_complaint"]=df["inspection_type"].astype(str).str.contains("Complaint")

def fit(d, dep, exog, absorb_cols, cl, target, scale=1.0):
    keep=[c for c in absorb_cols if d[c].astype('category').cat.remove_unused_categories().nunique()>1]
    d=d.dropna(subset=[dep]+exog+list(keep)+[cl]).copy()
    ids=np.column_stack([d[c].astype("category").cat.codes.to_numpy() for c in keep])
    alg=pyhdfe.create(ids,drop_singletons=False,compute_degrees=False)
    R=alg.residualize(d[[dep]+exog].to_numpy(float)); y=R[:,0];X=R[:,1:]
    XtX=X.T@X;beta=np.linalg.solve(XtX,X.T@y);resid=y-X@beta
    clc=d[cl].astype("category").cat.codes.to_numpy();G=len(np.unique(clc));N,K=X.shape
    meat=np.zeros((K,K))
    for g in np.unique(clc):
        Xg=X[clc==g];s=Xg.T@resid[clc==g];meat+=np.outer(s,s)
    bread=np.linalg.inv(XtX);c=(G/(G-1))*((N-1)/(N-K));V=c*bread@meat@bread;se=np.sqrt(np.diag(V))
    i=exog.index(target);b=beta[i]*scale;s_=se[i]*scale;t=beta[i]/se[i]
    return b,s_,2*stats.t.sf(abs(t),G-1),G

# (a) within intensive margin coarse clustering (with type FE, matches H5b spec)
for dep,short in [("vc","H5b_within_vc_count"),("asinh_vc","H5b_within_asinh")]:
    for cl in ["week","ym"]:
        b,se,p,G=fit(df,dep,["temp10","precip10"],("estab","month","year","inspection_type"),cl,"temp10")
        add(f"{short}_cluster_{cl}", round(b,4), se=round(se,4), p=round(p,4), df_clusters=G,
            desc=f"within-estab intensive margin {dep} on temp(+10C), clustered by {cl}")

# (b) scheduled (non-complaint) primary coarse clustering
sched=df[~df["is_complaint"]].copy()
for cl in ["week","ym"]:
    b,se,p,G=fit(sched,"fail",["temp10","precip10"],("estab","month","year"),cl,"temp10",scale=100.0)
    add(f"primaryA_scheduled_cluster_{cl}", round(b,3), se=round(se,3), p=round(p,4), df_clusters=G,
        desc=f"scheduled (non-complaint) primary clustered by {cl}")

# (c) estimator equivalence (AbsorbingLS vs pyhdfe) on the primary cell
r=AbsorbingLS(df["fail"],df[["temp10","precip10"]],absorb=df[["estab","month","year"]].astype("category")).fit(
    cov_type="clustered",clusters=df[["day_code"]])
b_a=float(r.params["temp10"])*100; se_a=float(r.std_errors["temp10"])*100
b_p,se_p,_,_=fit(df,"fail",["temp10","precip10"],("estab","month","year"),"day_code","temp10",scale=100.0)
add("estimator_equiv_maxdelta", round(max(abs(b_a-b_p),abs(se_a-se_p)),5),
    coef_AbsorbingLS=round(b_a,4), coef_pyhdfe=round(b_p,4),
    se_AbsorbingLS=round(se_a,4), se_pyhdfe=round(se_p,4),
    desc="max abs delta (ppt) between linearmodels.AbsorbingLS and manual pyhdfe HDFE-OLS on primary cell")

# (d) count-family multiplicity over ALL count-outcome tests now present (order-independent:
#     this step runs after every count key has been created). 2 outcomes x {with,without type}
#     x {date,week,month} = 12 tests.
fam_keys = ([f"H5b_within_{o}_per10C" for o in ["vc_count","asinh"]]
          + [f"H5b_within_{o}_cluster_{cl}" for o in ["vc_count","asinh"] for cl in ["week","ym"]]
          + [f"H5c_noType_{o}_cluster_{cl}" for o in ["count","asinh"] for cl in ["day","week","ym"]])
fam_ps = [c["p"] for k in fam_keys for c in store["claims"] if c["key"]==k and "p" in c]
minp = min(fam_ps); ntests = len(fam_ps)
add("H5_family_min_p", round(minp,4), n_tests=ntests, bonferroni=round(min(1.0,minp*ntests),4),
    desc="count-outcome family: smallest p over with/without-type x {asinh,count} x {date,week,month}; Bonferroni-adjusted")

json.dump(store, open(CLAIMS,"w"), indent=2)
print(f"extra_inference: count family = {ntests} tests, min p={minp:.4f}, Bonferroni={min(1.0,minp*ntests):.4f}")
print("extra_inference: intensive-margin + scheduled coarse clustering + estimator equiv logged")
print(f"  estimator max delta = {max(abs(b_a-b_p),abs(se_a-se_p)):.6f} ppt")
print("claims now:", len(store["claims"]))
