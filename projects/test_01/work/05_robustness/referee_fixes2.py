#!/usr/bin/env python3
"""Referee round-2 BLOCKING fixes.
 NEW-A: within violation-count intensive margin estimated WITHOUT type FE (consistency w/ no-Type primary), all clusterings.
 NEW-B: count family multiplicity (Bonferroni over the outcome family); demote to NOT robust; month-clustered headline.
 NEW-C: coarse-clustered t(G-1) CIs for the preferred primary; widest honest bound.
 NEW-D: retire stale ambiguous 'primary_*' keys; recompute %-of-base-rate from primaryA.
 NEW-E: H4 restaurant/risk1 interactions under week/month clustering; surface honestly."""
import os, json, sys
import numpy as np, pandas as pd
from scipy import stats
from linearmodels.iv.absorbing import AbsorbingLS
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "04_analysis"))
from prep import build_sample, ROOT
CLAIMS = os.path.join(ROOT, "validation/claims.json")
SCRIPT = "work/05_robustness/referee_fixes2.py"
store = json.load(open(CLAIMS))
def add(key, value, **kw):
    store["claims"] = [c for c in store["claims"] if c["key"] != key]
    r = {"key": key, "value": value, "script": SCRIPT}; r.update(kw); store["claims"].append(r)
def getc(k): return next((c for c in store["claims"] if c["key"]==k), {})
def drop(k): store["claims"] = [c for c in store["claims"] if c["key"]!=k]

df = build_sample()
df["day"]=df["date"].dt.normalize()
df["day_code"]=df["day"].astype("category").cat.codes
df["week"]=df["date"].dt.strftime("%G-%V"); df["ym"]=df["date"].dt.strftime("%Y-%m")
df["vc"]=pd.to_numeric(df["violation_count"],errors="coerce").fillna(0.0)
df["asinh_vc"]=np.arcsinh(df["vc"])
df["temp10_x_rest"]=df["temp10"]*df["is_restaurant"]
df["temp10_x_risk1"]=df["temp10"]*df["risk1"]

def fit(dep, exog, absorb_cols, cl, target):
    d=df.dropna(subset=[dep]+exog+list(absorb_cols)+[cl]).copy()
    ab=[]
    for c in absorb_cols:
        col=d[c].astype("category").cat.remove_unused_categories()
        if col.nunique()>1: d[c]=col; ab.append(c)
    r=AbsorbingLS(d[dep],d[exog],absorb=d[ab]).fit(cov_type="clustered",clusters=d[[cl]])
    G=d[cl].nunique(); b=float(r.params[target]); se=float(r.std_errors[target]); p=float(r.pvalues[target])
    tcrit=stats.t.ppf(.975,G-1)
    return b,se,p,G,b-tcrit*se,b+tcrit*se

# ----- NEW-A: within count WITHOUT type FE -----
countfam_ps=[]
for dep,short in [("vc","count"),("asinh_vc","asinh")]:
    for cl in ["day_code","week","ym"]:
        b,se,p,G,lo,hi=fit(dep,["temp10","precip10"],("estab","month","year"),cl,"temp10")
        tag={"day_code":"day","week":"week","ym":"ym"}[cl]
        add(f"H5c_noType_{short}_cluster_{tag}", round(b,4), se=round(se,4), p=round(p,4), df_clusters=G,
            desc=f"within-estab intensive margin {dep} on temp(+10C), NO type FE, cluster {tag}",
            log_line=f"H5c noType {short}/{tag}: b={b:.4f} se={se:.4f} p={p:.4f} G={G}")
        countfam_ps.append(p)
        # also overwrite the with-type H5b month value note (already exists); keep
# multiplicity over count family: with-type (6) + no-type (6) = 12 tests
withtype_ps=[getc(f"H5b_within_{o}_per10C").get("p") for o in ["vc_count","asinh"]]
withtype_ps+=[getc(f"H5b_within_{o}_cluster_{cl}").get("p") for o in ["vc_count","asinh"] for cl in ["week","ym"]]
allps=[x for x in (withtype_ps+countfam_ps) if x is not None]
minp=min(allps)
add("H5_family_min_p", round(minp,4), n_tests=len(allps),
    bonferroni=round(min(1.0,minp*len(allps)),4),
    desc="count-outcome family: smallest p over with/without-type x {asinh,count} x {date,week,month}; Bonferroni-adjusted",
    log_line=f"count family: {len(allps)} tests, min p={minp:.4f}, Bonferroni={min(1,minp*len(allps)):.4f}")

# ----- NEW-C: coarse-clustered CIs for preferred primary -----
for cl,tag in [("week","week"),("ym","ym")]:
    b,se,p,G,lo,hi=fit("fail",["temp10","precip10"],("estab","month","year"),cl,"temp10")
    add(f"coarse_A_estabMY_cluster_{tag}_ci", [round(lo*100,3),round(hi*100,3)], se=round(se*100,3),
        df_clusters=G, p=round(p,4), value_ppt=round(b*100,3),
        desc=f"preferred primary t(G-1) CI under {tag} clustering (honest serially-robust inference)",
        log_line=f"primaryA {tag}: b={b*100:.3f}ppt CI=[{lo*100:.3f},{hi*100:.3f}] G={G}")
# widest honest upper bound
hi_week=getc("coarse_A_estabMY_cluster_week_ci")["value"][1]
hi_ym=getc("coarse_A_estabMY_cluster_ym_ci")["value"][1]
base=getc("fail_rate")["value"]
widest=max(hi_week,hi_ym)
add("primaryA_widest_upper_ppt", round(widest,3),
    pct_of_baserate=round(widest/(base*100)*100,2),
    desc="widest honest upper 95% bound on temp effect across date/week/month clustering (largest effect NOT ruled out)",
    log_line=f"widest upper bound = {widest:.3f} ppt/10C = {widest/(base*100)*100:.2f}% of base rate")

# ----- NEW-D: retire stale ambiguous PRIMARY keys; recompute %-of-base from primaryA -----
for stale in ["primary_temp_ppt_per10C","primary_precip_ppt_per10mm","primary_temp_pct_of_baserate_per10C"]:
    drop(stale)
A=getc("primaryA_temp_ppt_per10C")
add("primaryA_pct_of_baserate_per10C", round(A["value"]/(base*100)*100,2),
    sig_vs_zero=False, ci_pct=[round(A["ci_t"][0]/(base*100)*100,2), round(A["ci_t"][1]/(base*100)*100,2)],
    desc="preferred primary temp effect as % of base fail rate; NOT sig diff from zero; quote with CI",
    log_line=f"primaryA %base = {A['value']}/{base*100:.3f}*100 = {A['value']/(base*100)*100:.2f}%")

# ----- NEW-E: H4 interactions under coarse clustering -----
for v,short in [("temp10_x_rest","restaurant"),("temp10_x_risk1","risk1")]:
    for cl in ["day_code","week","ym"]:
        b,se,p,G,lo,hi=fit("fail",["temp10",v,"precip10","is_restaurant","risk1"],
                            ("estab","month","year","inspection_type"),cl,v)
        tag={"day_code":"day","week":"week","ym":"ym"}[cl]
        add(f"H4_{short}_cluster_{tag}", round(b*100,3), se=round(se*100,3), p=round(p,4), df_clusters=G,
            ci_t=[round(lo*100,3),round(hi*100,3)],
            desc=f"H4 temp x {short} interaction (ppt/10C) clustered by {tag}",
            log_line=f"H4 {short}/{tag}: b={b*100:.3f}ppt se={se*100:.3f} p={p:.4f} G={G}")

json.dump(store, open(CLAIMS,"w"), indent=2)

print("=== NEW-A: within count WITHOUT type FE ===")
for short in ["count","asinh"]:
    row=" ".join(f"{tag}:b={getc(f'H5c_noType_{short}_cluster_{tag}')['value']:.4f},p={getc(f'H5c_noType_{short}_cluster_{tag}')['p']:.3f}" for tag in ["day","week","ym"])
    print(f"  {short:6s} {row}")
print(f"=== NEW-B: count family multiplicity: {getc('H5_family_min_p')['n_tests']} tests, min p={getc('H5_family_min_p')['value']}, Bonferroni={getc('H5_family_min_p')['bonferroni']} ===")
print("=== NEW-C: preferred-primary coarse CIs ===")
for tag in ["week","ym"]:
    ci=getc(f"coarse_A_estabMY_cluster_{tag}_ci"); print(f"  {tag}: CI {ci['value']} ppt (p={ci['p']}, G={ci['df_clusters']})")
print(f"  widest upper bound NOT ruled out: {getc('primaryA_widest_upper_ppt')['value']} ppt/10C = {getc('primaryA_widest_upper_ppt')['pct_of_baserate']}% of base rate")
print("=== NEW-D: stale keys retired; primaryA %base =", getc("primaryA_pct_of_baserate_per10C")['value'], "% CI", getc("primaryA_pct_of_baserate_per10C")['ci_pct'])
print("=== NEW-E: H4 interactions under coarse clustering ===")
for short in ["restaurant","risk1"]:
    row=" ".join(f"{tag}:b={getc(f'H4_{short}_cluster_{tag}')['value']:+.3f},p={getc(f'H4_{short}_cluster_{tag}')['p']:.3f}" for tag in ["day","week","ym"])
    print(f"  {short:10s} {row}")
print("claims now:", len(store["claims"]))
