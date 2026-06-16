#!/usr/bin/env python3
"""Regenerate all paper tables from validation/claims.json (single source of truth).
Tables: table1_main (co-primary specs), table2_robustness (13 specs, corrected caption),
table3_inference (coarse clustering + contested subsamples + multiplicity + intensive margin)."""
import os, json
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TAB = os.path.join(ROOT, "paper/tables")
store = json.load(open(os.path.join(ROOT, "validation/claims.json")))
c = {x["key"]: x for x in store["claims"]}
def g(k): return c.get(k, {})
def st(p): return "***" if p<.01 else "**" if p<.05 else "*" if p<.1 else ""

# ---------- Table 1: main / co-primary ----------
# columns: (1) pooled, (2) +controls, (3) Estab+M+Y [primary A], (4) +Type [primary B]
s1=g("temp10_beta_spec1"); s2=g("temp10_beta_spec2"); A=g("primaryA_temp_ppt_per10C"); B=g("primaryB_temp_ppt_per10C")
p1=g("precip10_beta_spec1"); p2=g("precip10_beta_spec2")
# precip for A,B from spec3/spec4 stored as fraction
pA=g("precip10_beta_spec3"); pB=g("precip10_beta_spec4")
def cell_b(d, scale=1.0):
    b=d["value"]*scale if abs(d["value"])<1 else d["value"]
    return f"{b:.3f}{st(d['p'])}"
def cell_se(d, scale=1.0):
    se=d["se"]*scale if d.get('se',0)<1 else d.get('se',0)
    return f"({se:.3f})"
L=[r"\begin{tabular}{lcccc}", r"\hline\hline",
   r" & (1) & (2) & (3) & (4) \\",
   r" & Pooled & +Controls & \textbf{Estab FE} & Estab FE \\",
   r" &  &  & \textbf{(primary)} & +Type \\", r"\hline",
   # temperature row: spec1/spec2 stored as fractions (ppt = *100); A/B already in ppt
   f"Temperature (+10$^\\circ$C) & {s1['value']*100:.3f}{st(s1['p'])} & {s2['value']*100:.3f}{st(s2['p'])} & {A['value']:.3f}{st(A['p'])} & {B['value']:.3f}{st(B['p'])} \\\\",
   f" & ({s1['se']*100:.3f}) & ({s2['se']*100:.3f}) & ({A['se']:.3f}) & ({B['se']:.3f}) \\\\",
   f"Precipitation (+10mm) & {p1['value']*100:.3f}{st(p1['p'])} & {p2['value']*100:.3f}{st(p2['p'])} & {pA['value']*100:.3f}{st(pA['p'])} & {pB['value']*100:.3f}{st(pB['p'])} \\\\",
   f" & ({p1['se']*100:.3f}) & ({p2['se']*100:.3f}) & ({pA['se']*100:.3f}) & ({pB['se']*100:.3f}) \\\\",
   r"\hline",
   r"Establishment FE & no & no & yes & yes \\",
   r"Month-of-year, Year FE & no & yes & yes & yes \\",
   r"Inspection-type FE & no & yes & no & yes \\",
   f"N & {g('n_sample')['value']:,} & {g('n_sample')['value']:,} & {g('n_sample')['value']:,} & {g('n_sample')['value']:,} \\\\",
   r"\hline\hline",
   r"\multicolumn{5}{p{0.92\linewidth}}{\footnotesize Dep.\ var.: \emph{fail} (=1). Coefficients in percentage points; SE clustered by calendar date in parentheses (G="+str(g('est_n_dayclusters')['value'])+r" day-clusters). Column (3) is the preferred primary: it does not condition on inspection type, which is a downstream mediator of weather (warm days shift the inspection mix). Column (4) conditions on type. *** p$<$.01, ** p$<$.05, * p$<$.1.}\\",
   r"\end{tabular}"]
open(os.path.join(TAB,"table1_main.tex"),"w").write("\n".join(L))

# ---------- Table 2: robustness 13 specs (corrected caption) ----------
specs=[g(f"robust_spec{i:02d}_temp_ppt10C") for i in range(13)]
npos=g("robust_share_positive"); nsig=g("robust_share_sig"); nps=g("robust_share_pos_and_sig")
N=13; npos_c=round(npos['value']*N); nsig_c=round(nsig['value']*N); nps_c=round(nps['value']*N)
L=[r"\begin{tabular}{lcccc}", r"\hline\hline",
   r"Specification & $\hat\beta$ (ppt/10$^\circ$C) & SE & p & N \\", r"\hline"]
for s in specs:
    L.append(f"{s['spec']} & {s['value']:.3f}{st(s['p'])} & ({s['se']:.3f}) & {s['p']:.3f} & {s['n']:,} \\\\")
L+=[r"\hline",
    f"\\multicolumn{{5}}{{p{{0.92\\linewidth}}}}{{\\footnotesize Sign/significance agreement: {npos_c}/{N} ({npos['value']*100:.0f}\\%) positive; {nsig_c}/{N} ({nsig['value']*100:.0f}\\%) significant at .10; {nps_c}/{N} ({nps['value']*100:.0f}\\%) positive \\emph{{and}} significant. The smallest p is {g('robust_min_p')['value']:.3f} (Bonferroni-adjusted {g('robust_min_p_bonferroni')['value']:.3f}); {g('robust_expected_false_pos_at05')['value']} false positives are expected at $\\alpha$=.05 across {N} tests. SE clustered by date unless noted. *** p$<$.01, ** p$<$.05, * p$<$.1.}}\\\\",
    r"\end{tabular}"]
open(os.path.join(TAB,"table2_robustness.tex"),"w").write("\n".join(L))

# ---------- Table 3: inference robustness ----------
def row(label, day, week, ym):
    def f(d): return f"{d['value']:.3f}{st(d['p'])} ({d['p']:.3f})" if d else "--"
    return f"{label} & {f(day)} & {f(week)} & {f(ym)} \\\\"
L=[r"\begin{tabular}{lccc}", r"\hline\hline",
   r"\multicolumn{4}{l}{\emph{Panel A. Primary effect under coarser clustering (weather is autocorrelated)}}\\",
   r"Clustering $\rightarrow$ & Date & ISO-week & Year-month \\",
   r" & (G="+str(g('est_n_dayclusters')['value'])+r") & (G="+str(g('coarse_A_estabMY_cluster_week')['df_clusters'])+r") & (G="+str(g('coarse_A_estabMY_cluster_ym')['df_clusters'])+r") \\", r"\hline",
   row("Primary (Estab+M+Y), full sample", {**g('primaryA_temp_ppt_per10C')}, g('coarse_A_estabMY_cluster_week'), g('coarse_A_estabMY_cluster_ym')),
   row("Scheduled (non-complaint) only", {'value':g('primaryA_scheduled_temp_ppt_per10C')['value'],'p':g('primaryA_scheduled_temp_ppt_per10C')['p']}, g('primaryA_scheduled_cluster_week'), g('primaryA_scheduled_cluster_ym')),
   r"\hline",
   r"\multicolumn{4}{l}{\emph{Panel B. Post hoc ``significant'' subsamples lose significance under correct inference}}\\",
   row("Canvass-only", g('contested_Canvass_only_cluster_day'), g('contested_Canvass_only_cluster_week'), g('contested_Canvass_only_cluster_ym')),
   row("Risk 1 (high) only", g('contested_Risk1_only_cluster_day'), g('contested_Risk1_only_cluster_week'), g('contested_Risk1_only_cluster_ym')),
   f"Canvass-only wild-cluster bootstrap p (month) & \\multicolumn{{3}}{{c}}{{{g('contested_Canvass_wildboot_p_ym')['value']:.3f}}} \\\\",
   r"\hline",
   r"\multicolumn{4}{l}{\emph{Panel C. Secondary outcome: within-establishment violation count (NOT robust)}}\\",
   row("asinh(violations), no-Type FE", g('H5c_noType_asinh_cluster_day'), g('H5c_noType_asinh_cluster_week'), g('H5c_noType_asinh_cluster_ym')),
   row("violations (level), no-Type FE", g('H5c_noType_count_cluster_day'), g('H5c_noType_count_cluster_week'), g('H5c_noType_count_cluster_ym')),
   f"\\multicolumn{{4}}{{l}}{{\\footnotesize \\quad Count-family multiplicity: {g('H5_family_min_p')['n_tests']} tests, min p={g('H5_family_min_p')['value']:.3f}, Bonferroni={g('H5_family_min_p')['bonferroni']:.3f} ($>$.05).}}\\\\",
   r"\hline",
   r"\multicolumn{4}{l}{\emph{Panel D. Heterogeneity (H4, fail outcome): significant in baseline but NOT robust}}\\",
   row("$\\times$ Restaurant$^\\dagger$ (vs other facility)", g('H4_restaurant_cluster_day'), g('H4_restaurant_cluster_week'), g('H4_restaurant_cluster_ym')),
   row("$\\times$ Risk~1 (vs lower risk)", g('H4_risk1_cluster_day'), g('H4_risk1_cluster_week'), g('H4_risk1_cluster_ym')),
   f"\\multicolumn{{4}}{{l}}{{\\footnotesize $^\\dagger$Pre-registered leave-one-facility-out check FAILS: restaurant coef ranges {g('H4_rest_dropfac_min_beta_ppt')['value']:.2f}--{g('H4_rest_dropfac_baseline_ppt')['value']:.2f} ppt, max p={g('H4_rest_dropfac_max_p')['value']:.3f} (n.s.\\ when Schools excluded). Stars notwithstanding, demoted to non-robust.}}\\\\",
   r"\hline\hline",
   r"\multicolumn{4}{p{0.92\linewidth}}{\footnotesize Cells: coefficient with significance stars and (p-value). Panel A dep.\ var.\ \emph{fail}; B \emph{fail}; C as labeled (asinh / level of violation count); D interaction terms, dep.\ var.\ \emph{fail}. Panel A/B/D coefficients in percentage points. Coarser clusters guard against serial correlation in weather across adjacent days. *** p$<$.01, ** p$<$.05, * p$<$.1.}\\",
   r"\end{tabular}"]
open(os.path.join(TAB,"table3_inference.tex"),"w").write("\n".join(L))
print("Wrote table1_main.tex, table2_robustness.tex, table3_inference.tex")
print("Table1 temp row: pooled",round(s1['value']*100,3),"| primaryA",A['value'],"| primaryB",B['value'])
