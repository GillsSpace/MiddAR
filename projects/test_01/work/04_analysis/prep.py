"""Shared sample builder for ESTIMATE + ROBUSTNESS. Reads data/raw only."""
import os
import numpy as np, pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(ROOT, "data/raw/chicago_inspections_weather.parquet")
SEED = 20260613

SUBSTANTIVE = ["pass", "pass_w_conditions", "fail"]

def build_sample():
    df = pd.read_parquet(RAW)
    df["res"] = df["results"].astype(str).str.lower()
    df = df[df["res"].isin(SUBSTANTIVE)].copy()
    df["fail"] = (df["res"] == "fail").astype(float)
    df["date"] = pd.to_datetime(df["inspection_date"])
    df["day"] = df["date"].dt.normalize()
    df["month"] = df["date"].dt.month.astype("category")          # month-of-year
    df["year"] = df["date"].dt.year.astype("category")
    df["doy"] = df["date"].dt.dayofyear.astype(float)
    df["estab"] = (df["dba_name"].astype(str).str.upper().str.strip() + "@" +
                   df["address"].astype(str).str.upper().str.strip()).astype("category")
    # weather, scaled
    df["temp_mean"] = pd.to_numeric(df["temperature_2m_mean"], errors="coerce")
    df["temp10"] = df["temp_mean"] / 10.0                          # per +10 degC
    df["precip"] = pd.to_numeric(df["precipitation_sum"], errors="coerce")
    df["precip10"] = df["precip"] / 10.0                          # per +10 mm
    # controls
    df["risk"] = df["risk"].astype("category")
    df["inspection_type"] = df["inspection_type"].astype("category")
    df["zip"] = df["zip"].astype("category")
    df["is_restaurant"] = (df["facility_type"].astype(str).str.lower() == "restaurant").astype(float)
    df["risk1"] = df["risk"].astype(str).str.contains("Risk 1", case=False, na=False).astype(float)
    # temperature bins for H3
    bins = [-100, 0, 10, 20, 25, 30, 100]
    labels = ["lt0", "0_10", "10_20", "20_25", "25_30", "gt30"]
    df["tbin"] = pd.cut(df["temp_mean"], bins=bins, labels=labels, right=False)
    df = df.dropna(subset=["temp10", "precip", "fail", "estab", "month", "year"]).copy()
    return df

if __name__ == "__main__":
    d = build_sample()
    print("N", len(d), "fail_rate", round(d['fail'].mean(),4),
          "n_estab", d['estab'].nunique(), "n_days", d['day'].nunique())
    print(d[["temp_mean","temp10","precip"]].describe().round(2).to_string())
