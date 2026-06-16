#!/usr/bin/env python3
"""AUDIT gate: hash inputs, infer schema, record global seed + package versions -> manifest.json."""
import hashlib, json, sys, platform, os
import pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GLOBAL_SEED = 20260613

def sha256(path, buf=1<<20):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(buf),b''): h.update(b)
    return h.hexdigest()

raw=[os.path.join(ROOT,'data/raw/chicago_inspections_weather.parquet'),
     os.path.join(ROOT,'data/raw/chicago_inspections_weather_sample.csv')]
inputs=[{"path":os.path.relpath(p,ROOT),"bytes":os.path.getsize(p),"sha256":sha256(p)} for p in raw]
df=pd.read_parquet(raw[0])
schema=[{"name":c,"dtype":str(df[c].dtype),"n_missing":int(df[c].isna().sum()),
         "pct_missing":round(100*df[c].isna().mean(),3),"n_unique":int(df[c].nunique(dropna=True))}
        for c in df.columns]
def ver(m):
    try: return __import__(m).__version__
    except Exception: return None
pkgs={m:ver(m) for m in ['pandas','numpy','scipy','statsmodels','matplotlib','pyarrow','linearmodels','pyhdfe']}
manifest={"project":"chicago_inspections_weather_paper","created":"2026-06-13","global_seed":GLOBAL_SEED,
  "python":sys.version.split()[0],"platform":platform.platform(),"packages":pkgs,"inputs":inputs,
  "primary_dataset":{"path":inputs[0]["path"],"n_rows":int(df.shape[0]),"n_cols":int(df.shape[1])},
  "schema":schema,
  "scripts":{
    "audit":"work/01_audit/audit.py -> replication/manifest.json",
    "profile":"work/02_profile/profile.py -> work/02_profile/profile.{md,json}",
    "estimate":"work/04_analysis/estimate.py -> paper/tables/table1_main.tex (+claims)",
    "diagnostics":"work/04_analysis/diagnostics.py -> paper/figures/fig1,fig2 (+claims)",
    "robustness":"work/05_robustness/robustness.py -> paper/tables/table2 (+claims)",
    "referee_fixes_r1":"work/05_robustness/referee_fixes.py (+claims)",
    "referee_fixes_r2":"work/05_robustness/referee_fixes2.py (+claims)",
    "extra_inference":"work/05_robustness/extra_inference.py (+claims)",
    "referee_fixes_r3":"work/05_robustness/referee_fixes3.py (+claims)",
    "make_tables":"work/05_robustness/make_tables.py -> paper/tables/table1,2,3",
    "orphan_check":"validation/orphan_check.py"}}
os.makedirs(os.path.join(ROOT,'work/01_audit'),exist_ok=True)
json.dump(manifest,open(os.path.join(ROOT,'replication/manifest.json'),'w'),indent=2)
json.dump({"inputs":inputs,"n_rows":int(df.shape[0]),"global_seed":GLOBAL_SEED,"packages":pkgs},
          open(os.path.join(ROOT,'work/01_audit/audit.json'),'w'),indent=2)
print("AUDIT: seed",GLOBAL_SEED,"| rows",df.shape[0],"| parquet sha256",inputs[0]["sha256"][:16])
