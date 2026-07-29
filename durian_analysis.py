# -*- coding: utf-8 -*-
"""
Durian Orchard Analysis — linking IoT microclimate to C/N ratio, flowering and fruit set
=========================================================================================

Two data sources from the SAME orchard:
  1) IoT_Sensor_Hourly.csv  : hourly microclimate (Temp, Humidity, Rain, Wind, VPD, Lux),
                              4,409 rows, 2025-12-13 .. 2026-06-15
  2) PSN.xlsx               : 4 field visits x 3 zones (A/B/C) x 2 groups x 2 directions (E/W)
                              C/N ratio (all visits), Flower count (visit 3 only),
                              Durian count (visit 4 only)  -> 48 rows; Zone C excluded -> 32 used

GOAL: connect weather conditions to C/N ratio, flowering, and fruit set.

IMPORTANT STATISTICAL NOTE
--------------------------
The field dataset is TINY (48 rows; Flower & Durian each observed only once).
Deep-learning / complex supervised models to predict flower/fruit counts are NOT
appropriate here — they would overfit and give meaningless "accuracy".
So this script does what the data honestly supports:
  * rich feature engineering + unsupervised ML on the DATA-RICH IoT stream,
  * interpretable statistics (correlation, simple regression, effect sizes) to LINK
    the aggregated weather to the field measurements,
  * a reusable pipeline so that when more field visits are collected, the same code
    scales up to real predictive modelling.

Outputs (written to ./outputs_analysis/):
  - merged_field_weather.csv     : field data + preceding-weather features
  - daily_weather.csv            : daily aggregated IoT weather
  - figures: *.png
  - correlations_*.csv
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

warnings.filterwarnings("ignore")

# ----------------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
IOT_CSV = os.path.join(HERE, "IoT_Sensor_Hourly.csv")
PSN_XLSX = os.path.join(HERE, "PSN.xlsx")

OUT = os.path.join(HERE, "outputs_analysis")
os.makedirs(OUT, exist_ok=True)

# Agronomic constant: base temperature for durian growing-degree-days (GDD).
# Durian is tropical; 10C is a common, conservative base. Adjust if you have a better value.
GDD_BASE = 10.0
# VPD threshold (kPa) above which the canopy is considered under moisture/heat stress.
VPD_STRESS = 2.0
# Temperature (C) above which an hour counts as "hot stress".
HOT_HR = 35.0
# Night temperature (C) below which we count a "cool night" (relevant to flower induction).
COOL_NIGHT = 22.0


# ==================================================================================
# 1. LOAD & CLEAN
# ==================================================================================
def load_iot():
    df = pd.read_csv(IOT_CSV, parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    df = df.rename(columns={
        "Temp(C)": "temp", "Humid(%RH)": "humid", "Rain(mm)": "rain",
        "WindSpeed(m/s)": "wind", "VPD(kpa)": "vpd", "Lux(klux)": "lux",
    })
    # Regular hourly index so gaps are explicit, then interpolate short gaps.
    df = df.set_index("datetime").asfreq("1h")
    # rain: a missing rain reading almost certainly means "no rain" -> 0
    df["rain"] = df["rain"].fillna(0.0)
    # continuous variables: time-interpolate short gaps, then ffill/bfill edges
    for c in ["temp", "humid", "wind", "vpd", "lux"]:
        df[c] = df[c].interpolate(method="time", limit=6).ffill().bfill()
    df = df.reset_index()
    return df


def cn_to_float(x):
    """'22:1' -> 22.0 ; already-numeric stays; '-' -> NaN."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    if s in ("-", "", "nan"):
        return np.nan
    if ":" in s:
        a, b = s.split(":")
        try:
            return float(a) / float(b)
        except ZeroDivisionError:
            return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def num_or_nan(x):
    try:
        f = float(x)
        return f
    except (ValueError, TypeError):
        return np.nan


# Zones excluded for data-quality reasons (Zone C counts recorded with a known
# observer/counting error). Set to () to include all zones.
EXCLUDE_ZONES = ("C",)


def load_field():
    df = pd.read_excel(PSN_XLSX)
    df = df.rename(columns={"Gorup": "Group"})  # fix the typo in the source header
    df["Date"] = pd.to_datetime(df["Date"])
    df["visit"] = df["Time"].astype(int)
    df["cn"] = df["C/N"].apply(cn_to_float)        # numeric C:N ratio
    df["flower"] = df["Flower"].apply(num_or_nan)  # count (visit 3 only)
    df["durian"] = df["Durian"].apply(num_or_nan)  # count (visit 4 only)
    df["unit"] = df["Zone"] + "-G" + df["Group"].astype(int).astype(str) + "-" + df["Direction"]
    if EXCLUDE_ZONES:
        df = df[~df["Zone"].isin(EXCLUDE_ZONES)].reset_index(drop=True)
    return df


# ==================================================================================
# 2. WEATHER FEATURE ENGINEERING
# ==================================================================================
def daily_weather(iot):
    """Aggregate hourly -> daily. Split day/night for temperature-derived features."""
    d = iot.copy()
    d["date"] = d["datetime"].dt.normalize()
    d["hour"] = d["datetime"].dt.hour
    is_night = (d["hour"] < 6) | (d["hour"] >= 19)
    d["temp_night"] = d["temp"].where(is_night)
    daily = d.groupby("date").agg(
        temp_mean=("temp", "mean"), temp_max=("temp", "max"), temp_min=("temp", "min"),
        humid_mean=("humid", "mean"),
        rain_sum=("rain", "sum"),
        wind_mean=("wind", "mean"),
        vpd_mean=("vpd", "mean"), vpd_max=("vpd", "max"),
        lux_sum=("lux", "sum"),               # daily light integral (proxy)
        night_temp_min=("temp_night", "min"),
    ).reset_index()
    # Growing-degree-days for the day
    daily["gdd"] = ((daily["temp_max"] + daily["temp_min"]) / 2.0 - GDD_BASE).clip(lower=0)
    # count-style stress flags need the hourly frame:
    hot = d.assign(hot=(d["temp"] > HOT_HR)).groupby("date")["hot"].sum().rename("hot_hours")
    vst = d.assign(v=(d["vpd"] > VPD_STRESS)).groupby("date")["v"].sum().rename("vpd_stress_hours")
    daily = daily.merge(hot, on="date").merge(vst, on="date")
    daily["cool_night"] = (daily["night_temp_min"] < COOL_NIGHT).astype(int)
    return daily


def window_features(daily, end_date, days):
    """Aggregate the `days` calendar days ending the day BEFORE a field visit."""
    start = end_date - pd.Timedelta(days=days)
    w = daily[(daily["date"] >= start) & (daily["date"] < end_date)]
    if w.empty:
        return {}
    return {
        f"w{days}_temp_mean": w["temp_mean"].mean(),
        f"w{days}_temp_max": w["temp_max"].max(),
        f"w{days}_temp_min": w["temp_min"].min(),
        f"w{days}_humid_mean": w["humid_mean"].mean(),
        f"w{days}_rain_sum": w["rain_sum"].sum(),
        f"w{days}_vpd_mean": w["vpd_mean"].mean(),
        f"w{days}_vpd_stress_hours": w["vpd_stress_hours"].sum(),
        f"w{days}_hot_hours": w["hot_hours"].sum(),
        f"w{days}_gdd_sum": w["gdd"].sum(),
        f"w{days}_lux_sum": w["lux_sum"].sum(),
        f"w{days}_cool_nights": w["cool_night"].sum(),
        f"w{days}_ndays": len(w),
    }


def build_merged(field, daily):
    """Attach preceding-weather features (30 & 60 day windows) to every field row."""
    windows = [30, 60]
    feat_rows = []
    for visit, date in field.groupby("visit")["Date"].first().items():
        row = {"visit": visit}
        for wd in windows:
            row.update(window_features(daily, date.normalize(), wd))
        feat_rows.append(row)
    feats = pd.DataFrame(feat_rows)
    merged = field.merge(feats, on="visit", how="left")
    return merged


# ==================================================================================
# 3. ANALYSIS
# ==================================================================================
def corr_table(df, target, feat_cols, min_n=6):
    rows = []
    sub = df.dropna(subset=[target])
    for c in feat_cols:
        s = sub[[c, target]].dropna()
        if len(s) < min_n or s[c].nunique() < 2:
            continue
        r, p = stats.pearsonr(s[c], s[target])
        rows.append({"feature": c, "pearson_r": round(r, 3),
                     "p_value": round(p, 4), "n": len(s)})
    out = pd.DataFrame(rows).sort_values("pearson_r", key=lambda x: x.abs(), ascending=False)
    return out


ASPECT_COLOR = {"East": "tab:red", "West": "tab:blue"}


def fig_cn_trajectory(field):
    piv = field.pivot_table(index="visit", columns="Direction", values="cn", aggfunc="mean")
    dates = field.groupby("visit")["Date"].first()
    plt.figure(figsize=(8, 5))
    for d in piv.columns:
        plt.plot(piv.index, piv[d], marker="o", color=ASPECT_COLOR.get(d),
                 label=f"{d}-facing")
    plt.xticks(piv.index, [dt.strftime("%b %d") for dt in dates.loc[piv.index]])
    plt.ylabel("C/N ratio (leaf)")
    plt.title("C/N ratio across field visits, by canopy aspect (East vs West)")
    plt.legend()
    plt.grid(alpha=.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig1_cn_trajectory.png"), dpi=130)
    plt.close()


def fig_weather_context(daily, field):
    fig, ax = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    ax[0].plot(daily["date"], daily["temp_mean"], color="tab:red", lw=.8, label="mean")
    ax[0].fill_between(daily["date"], daily["temp_min"], daily["temp_max"],
                       color="tab:red", alpha=.15)
    ax[0].set_ylabel("Temp (C)"); ax[0].legend(loc="upper left")
    ax[1].plot(daily["date"], daily["vpd_mean"], color="tab:orange", lw=.9)
    ax[1].set_ylabel("VPD (kPa)")
    ax[2].bar(daily["date"], daily["rain_sum"], color="tab:blue", width=1.0)
    ax[2].set_ylabel("Rain (mm/day)")
    for a in ax:
        for _, d in field.groupby("visit")["Date"].first().items():
            a.axvline(d, color="k", ls="--", alpha=.5)
    ax[0].set_title("Daily microclimate with field-visit dates (dashed)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig2_weather_context.png"), dpi=130)
    plt.close()


def fig_flower_fruit(field):
    f3 = field[field["visit"] == 3][["unit", "Zone", "Direction", "cn", "flower"]]
    f4 = field[field["visit"] == 4][["unit", "durian"]]
    m = f3.merge(f4, on="unit", how="inner")
    m["fruit_set_pct"] = 100 * m["durian"] / m["flower"]
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.5))
    # flower vs durian, coloured by canopy aspect
    for d in ["East", "West"]:
        s = m[m["Direction"] == d]
        ax[0].scatter(s["flower"], s["durian"], s=80, color=ASPECT_COLOR[d],
                      label=f"{d}-facing")
    ax[0].set_xlabel("Flower count (Feb)"); ax[0].set_ylabel("Durian count (Apr)")
    ax[0].set_title("Flowers -> fruit"); ax[0].legend(); ax[0].grid(alpha=.3)
    # C/N (Feb) vs flower, coloured by aspect
    for d in ["East", "West"]:
        s = m[m["Direction"] == d]
        ax[1].scatter(s["cn"], s["flower"], s=80, color=ASPECT_COLOR[d], label=f"{d}-facing")
    ax[1].set_xlabel("C/N ratio (Feb)"); ax[1].set_ylabel("Flower count")
    ax[1].set_title("C/N vs flowering"); ax[1].legend(); ax[1].grid(alpha=.3)
    # flower / durian / fruit-set means by aspect
    order = ["East", "West"]
    x = np.arange(len(order))
    fl = [m[m["Direction"] == d]["flower"].mean() for d in order]
    fs = [m[m["Direction"] == d]["fruit_set_pct"].mean() for d in order]
    ax2 = ax[2].twinx()
    ax[2].bar(x - 0.2, fl, width=0.4, color="tab:orange", label="Flower (mean)")
    ax2.bar(x + 0.2, fs, width=0.4, color="tab:purple", label="Fruit-set %")
    ax[2].set_xticks(x); ax[2].set_xticklabels([f"{d}" for d in order])
    ax[2].set_ylabel("Mean flower count"); ax2.set_ylabel("Mean fruit-set %")
    ax[2].set_title("Flowering & fruit set by aspect")
    ax[2].legend(loc="upper left"); ax2.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig3_flower_fruit.png"), dpi=130)
    plt.close()
    return m


def aspect_summary(field):
    """East vs West comparison of C/N (all visits), flower, fruit, fruit-set."""
    rows = []
    e = field[field["Direction"] == "East"]; w = field[field["Direction"] == "West"]
    def _cmp(name, es, ws):
        es, ws = es.dropna(), ws.dropna()
        t, p = stats.ttest_ind(es, ws, equal_var=False)
        rows.append({"variable": name, "East_mean": round(es.mean(), 2),
                     "West_mean": round(ws.mean(), 2), "t_pvalue": round(p, 3),
                     "n_per_group": min(len(es), len(ws))})
    _cmp("C/N (all visits)", e["cn"], w["cn"])
    _cmp("Flower (Feb)", e[e.visit == 3]["flower"], w[w.visit == 3]["flower"])
    _cmp("Durian (Apr)", e[e.visit == 4]["durian"], w[w.visit == 4]["durian"])
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(OUT, "aspect_east_west_summary.csv"), index=False)
    return out


def cluster_units(field):
    """Cluster the 8 spatial units by their C/N trajectory + yield signals."""
    cn = field.pivot_table(index="unit", columns="visit", values="cn")
    cn.columns = [f"cn_v{c}" for c in cn.columns]
    fl = field[field["visit"] == 3].set_index("unit")["flower"].rename("flower")
    du = field[field["visit"] == 4].set_index("unit")["durian"].rename("durian")
    X = cn.join(fl).join(du).dropna()
    if len(X) < 4:
        return None
    Xs = StandardScaler().fit_transform(X)
    k = 3
    km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(Xs)
    X = X.copy()
    X["cluster"] = km.labels_
    X.to_csv(os.path.join(OUT, "unit_clusters.csv"))
    # 2D view: mean C/N vs durian, coloured by canopy aspect, marker = cluster
    plt.figure(figsize=(7, 5))
    cn_cols = [c for c in X.columns if c.startswith("cn_v")]
    X["cn_mean"] = X[cn_cols].mean(axis=1)
    X["aspect"] = ["East" if "East" in u else "West" for u in X.index]
    markers = {0: "o", 1: "s", 2: "^"}
    for u, r in X.iterrows():
        plt.scatter(r["cn_mean"], r["durian"], s=110,
                    color=ASPECT_COLOR[r["aspect"]], marker=markers.get(r["cluster"], "o"),
                    edgecolor="k", linewidth=.5)
        plt.annotate(u, (r["cn_mean"], r["durian"]), fontsize=7,
                     xytext=(4, 4), textcoords="offset points")
    handles = [plt.Line2D([0], [0], marker="o", ls="", color=ASPECT_COLOR[a], label=f"{a}-facing")
               for a in ["East", "West"]]
    handles += [plt.Line2D([0], [0], marker=markers[k], ls="", color="gray",
                           label=f"cluster {k}") for k in sorted(X["cluster"].unique())]
    plt.legend(handles=handles, fontsize=8)
    plt.xlabel("Mean C/N ratio"); plt.ylabel("Durian count (Apr)")
    plt.title("Spatial units by C/N and yield (colour = aspect, marker = cluster)")
    plt.grid(alpha=.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig4_unit_clusters.png"), dpi=130)
    plt.close()
    return X


# ==================================================================================
# MAIN
# ==================================================================================
def main():
    print(">> loading data")
    iot = load_iot()
    field = load_field()
    daily = daily_weather(iot)
    daily.to_csv(os.path.join(OUT, "daily_weather.csv"), index=False)

    print(">> feature engineering + merge")
    merged = build_merged(field, daily)
    merged.to_csv(os.path.join(OUT, "merged_field_weather.csv"), index=False)

    print(">> figures")
    fig_cn_trajectory(field)
    fig_weather_context(daily, field)
    ff = fig_flower_fruit(field)
    cluster_units(field)

    asp = aspect_summary(field)
    print("\n=== East vs West (canopy aspect) ===")
    print(asp.to_string(index=False))

    print(">> correlations: weather (preceding window) vs C/N")
    wcols = [c for c in merged.columns if c.startswith("w30_") or c.startswith("w60_")]
    cn_corr = corr_table(merged, "cn", wcols, min_n=12)
    cn_corr.to_csv(os.path.join(OUT, "correlations_weather_vs_cn.csv"), index=False)

    # flower (visit 3) vs weather + C/N  (n = 12, exploratory only)
    v3 = merged[merged["visit"] == 3]
    fl_corr = corr_table(v3, "flower", wcols + ["cn"], min_n=8)
    fl_corr.to_csv(os.path.join(OUT, "correlations_flower.csv"), index=False)

    # fruit set: durian vs flower & C/N
    if ff is not None and len(ff) > 4:
        r_ff, p_ff = stats.pearsonr(ff["flower"], ff["durian"])
        r_cf, p_cf = stats.pearsonr(ff["cn"], ff["flower"])
        summary = pd.DataFrame({
            "relationship": ["flower(Feb) -> durian(Apr)", "C/N(Feb) -> flower(Feb)"],
            "pearson_r": [round(r_ff, 3), round(r_cf, 3)],
            "p_value": [round(p_ff, 4), round(p_cf, 4)],
            "n": [len(ff), len(ff)],
        })
        summary.to_csv(os.path.join(OUT, "key_relationships.csv"), index=False)
        print(summary.to_string(index=False))

    # console recap
    print("\n=== C/N summary by visit ===")
    print(field.groupby("visit").agg(
        date=("Date", "first"), cn_mean=("cn", "mean"),
        cn_min=("cn", "min"), cn_max=("cn", "max")).round(2).to_string())
    print("\n=== top weather<->C/N correlations ===")
    print(cn_corr.head(8).to_string(index=False))
    print("\nAll outputs written to:", OUT)


if __name__ == "__main__":
    main()
