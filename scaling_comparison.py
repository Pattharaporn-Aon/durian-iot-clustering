# -*- coding: utf-8 -*-
"""
Feature-scaling / data-management comparison for the durian dataset
===================================================================
Addresses three practical questions when preparing the data for clustering:

  1. Which SCALER suits each column, given very different distributions
     (temperature ~ normal; rainfall & light ~ strongly right-skewed / zero-
     inflated; flower/fruit counts on totally different magnitudes)?
  2. Does the choice of scaler bias the unsupervised clustering of the 12
     spatial units (does one high-magnitude column dominate the distance)?
  3. What is the right SCOPE of scaling for a variable with a strong temporal
     trend (leaf C/N rises through the season): global, per-visit (temporal),
     or per-group? Per-visit scaling removes the seasonal offset so that
     spatial (unit) contrasts are compared without temporal bias.

Outputs (./outputs_analysis/):
  - scaling_column_profile.csv     : skew, %zeros, outlier fraction, recommended scaler
  - scaling_cluster_comparison.csv : silhouette, cluster sizes, ARI vs Robust
  - scaling_scope_comparison.csv    : global vs per-visit vs per-group
  - fig5_scaler_comparison.png
  - fig6_scaling_scope.png
"""
import os, warnings
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs_analysis"); os.makedirs(OUT, exist_ok=True)
IOT = os.path.join(HERE, "IoT_Sensor_Hourly.csv")
PSN = os.path.join(HERE, "PSN.xlsx")
SEED = 0; K = 3


# ---- reuse the loaders from the main analysis (kept local for a standalone run) ----
def cn_to_float(x):
    s = str(x).strip()
    if ":" in s:
        a, b = s.split(":");  return float(a) / float(b)
    try: return float(s)
    except ValueError: return np.nan

EXCLUDE_ZONES = ("C",)  # data-quality exclusion (see durian_analysis.py)


def load_field():
    df = pd.read_excel(PSN).rename(columns={"Gorup": "Group"})
    df["visit"] = df["Time"].astype(int)
    df["cn"] = df["C/N"].apply(cn_to_float)
    df["flower"] = pd.to_numeric(df["Flower"], errors="coerce")
    df["durian"] = pd.to_numeric(df["Durian"], errors="coerce")
    df["unit"] = df["Zone"] + "-G" + df["Group"].astype(int).astype(str) + "-" + df["Direction"]
    if EXCLUDE_ZONES:
        df = df[~df["Zone"].isin(EXCLUDE_ZONES)].reset_index(drop=True)
    return df

def daily_weather():
    d = pd.read_csv(IOT, parse_dates=["datetime"]).rename(columns={
        "Temp(C)": "temp", "Humid(%RH)": "humid", "Rain(mm)": "rain",
        "WindSpeed(m/s)": "wind", "VPD(kpa)": "vpd", "Lux(klux)": "lux"})
    d["rain"] = d["rain"].fillna(0.0)
    for c in ["temp", "humid", "wind", "vpd", "lux"]:
        d[c] = d[c].interpolate().ffill().bfill()
    d["date"] = d["datetime"].dt.normalize()
    return d.groupby("date").agg(
        temp_mean=("temp", "mean"), humid_mean=("humid", "mean"),
        rain_sum=("rain", "sum"), wind_mean=("wind", "mean"),
        vpd_mean=("vpd", "mean"), lux_sum=("lux", "sum")).reset_index()


# =====================================================================
# 1. Per-column distribution profile -> recommended scaler
# =====================================================================
def column_profile(daily):
    cols = ["temp_mean", "humid_mean", "rain_sum", "wind_mean", "vpd_mean", "lux_sum"]
    rows = []
    for c in cols:
        x = daily[c].dropna().values
        q1, q3 = np.percentile(x, [25, 75]); iqr = q3 - q1
        out_frac = np.mean((x < q1 - 1.5 * iqr) | (x > q3 + 1.5 * iqr))
        sk = stats.skew(x)
        pzero = np.mean(x == 0)
        if pzero > 0.3 or abs(sk) > 1.5 or out_frac > 0.1:
            rec = "Robust (median/IQR)"
        elif abs(sk) < 0.5:
            rec = "Standard (z-score)"
        else:
            rec = "Robust or log+Standard"
        rows.append({"column": c, "skewness": round(sk, 2),
                     "pct_zero": round(100 * pzero, 1),
                     "outlier_frac_%": round(100 * out_frac, 1),
                     "recommended": rec})
    return pd.DataFrame(rows)


# =====================================================================
# 2. Scaler comparison on the 8-unit clustering feature matrix
# =====================================================================
def unit_matrix(field):
    cn = field.pivot_table(index="unit", columns="visit", values="cn")
    cn.columns = [f"cn_v{c}" for c in cn.columns]
    fl = field[field["visit"] == 3].set_index("unit")["flower"].rename("flower")
    du = field[field["visit"] == 4].set_index("unit")["durian"].rename("durian")
    return cn.join(fl).join(du).dropna()

def cluster_metrics(Xs):
    km = KMeans(n_clusters=K, n_init=10, random_state=SEED).fit(Xs)
    sizes = np.bincount(km.labels_, minlength=K)
    sil = silhouette_score(Xs, km.labels_)
    return km.labels_, sil, sizes

def scaler_comparison(X):
    scalers = {"None (raw)": None, "MinMax": MinMaxScaler(),
               "Standard": StandardScaler(), "Robust": RobustScaler()}
    results, labels_by = [], {}
    for name, sc in scalers.items():
        Xs = X.values.astype(float) if sc is None else sc.fit_transform(X)
        labels, sil, sizes = cluster_metrics(Xs)
        labels_by[name] = labels
        # how much a single column dominates the distance (variance share)
        var = np.var(Xs, axis=0); dom = X.columns[np.argmax(var)]
        results.append({"scaler": name, "silhouette": round(sil, 3),
                        "cluster_sizes": "/".join(map(str, sizes)),
                        "dominant_feature": dom,
                        "dominant_var_share_%": round(100 * var.max() / var.sum(), 1)})
    df = pd.DataFrame(results)
    ref = labels_by["Robust"]
    df["ARI_vs_Robust"] = [round(adjusted_rand_score(ref, labels_by[n]), 3)
                           for n in df["scaler"]]
    return df, labels_by


# =====================================================================
# 3. Scaling SCOPE for a temporally-trending variable (leaf C/N)
# =====================================================================
def scope_comparison(field):
    """Cluster units on their C/N trajectory under three scaling scopes."""
    cn = field.pivot_table(index="unit", columns="visit", values="cn")
    cn.columns = [f"v{c}" for c in cn.columns]
    aspect = field.groupby("unit")["Direction"].first()

    # GLOBAL: one mean/std over the whole matrix (keeps the seasonal level -> temporal bias)
    g = (cn.values - np.nanmean(cn.values)) / np.nanstd(cn.values)

    # PER-VISIT (temporal): z-score within each visit-column -> removes seasonal offset
    pv = cn.apply(lambda col: (col - col.mean()) / col.std(), axis=0).values

    # PER-GROUP (aspect): z-score within each canopy aspect -> removes the East/West signal
    pg = cn.copy()
    for a in aspect.unique():
        idx = aspect[aspect == a].index
        pg.loc[idx] = (cn.loc[idx] - cn.loc[idx].values.mean()) / cn.loc[idx].values.std()
    pg = pg.values

    out = []
    scopes = {"Global": g, "Per-visit (temporal)": pv, "Per-group (aspect)": pg}
    labels_by = {}
    for name, Xs in scopes.items():
        labels, sil, sizes = cluster_metrics(np.nan_to_num(Xs))
        labels_by[name] = labels
        out.append({"scope": name, "silhouette": round(sil, 3),
                    "cluster_sizes": "/".join(map(str, sizes))})
    df = pd.DataFrame(out)
    df.attrs["temporal_var"] = np.var(np.nanmean(cn.values, axis=0))
    df.attrs["spatial_var"] = np.var(np.nanmean(cn.values, axis=1))
    return df, cn, pv, aspect


# =====================================================================
# Figures
# =====================================================================
def fig_scaler(df):
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    ax[0].bar(df["scaler"], df["silhouette"], color=["#bbb", "#f39", "#39f", "#3b8"])
    ax[0].set_ylabel("Silhouette score"); ax[0].set_title("Cluster quality by scaler")
    ax[0].grid(alpha=.3, axis="y")
    ax[1].bar(df["scaler"], df["dominant_var_share_%"],
              color=["#bbb", "#f39", "#39f", "#3b8"])
    ax[1].axhline(100 / 6, ls="--", color="k", alpha=.6)  # 6 features -> even share
    ax[1].set_ylabel("Variance share of dominant feature (%)")
    ax[1].set_title("Single-column dominance (bias)\n dashed = even 1/6 share")
    ax[1].grid(alpha=.3, axis="y")
    for a in ax:
        a.set_xticklabels(df["scaler"], rotation=20)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig5_scaler_comparison.png"), dpi=130)
    plt.close()

def fig_scope(cn, pv, aspect):
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5), sharex=True)
    ac = {"East": "tab:red", "West": "tab:blue"}
    for u in cn.index:
        ax[0].plot(cn.columns, cn.loc[u], color=ac[aspect[u]], alpha=.6)
    ax[0].set_title("Raw C/N (global level dominates)\nseasonal rise masks aspect contrasts")
    ax[0].set_ylabel("C/N ratio"); ax[0].set_xlabel("visit")
    pv_df = pd.DataFrame(pv, index=cn.index, columns=cn.columns)
    for u in pv_df.index:
        ax[1].plot(pv_df.columns, pv_df.loc[u], color=ac[aspect[u]], alpha=.6)
    ax[1].axhline(0, ls="--", color="k", alpha=.5)
    ax[1].set_title("Per-visit z-score (temporal offset removed)\naspect contrasts now comparable")
    ax[1].set_xlabel("visit")
    handles = [plt.Line2D([0], [0], color=ac[a], label=f"{a}-facing") for a in ac]
    ax[1].legend(handles=handles, fontsize=8)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig6_scaling_scope.png"), dpi=130)
    plt.close()


def main():
    field = load_field(); daily = daily_weather()

    prof = column_profile(daily)
    prof.to_csv(os.path.join(OUT, "scaling_column_profile.csv"), index=False)

    X = unit_matrix(field)
    sc_df, _ = scaler_comparison(X)
    sc_df.to_csv(os.path.join(OUT, "scaling_cluster_comparison.csv"), index=False)
    fig_scaler(sc_df)

    scope_df, cn, pv, aspect = scope_comparison(field)
    scope_df.to_csv(os.path.join(OUT, "scaling_scope_comparison.csv"), index=False)
    fig_scope(cn, pv, aspect)

    print("=== per-column profile ===\n", prof.to_string(index=False))
    print("\n=== scaler comparison (clustering of 8 units) ===\n", sc_df.to_string(index=False))
    print("\n=== scope comparison (C/N trajectory) ===\n", scope_df.to_string(index=False))
    print(f"\nBetween-visit (temporal) variance of C/N: {scope_df.attrs['temporal_var']:.3f}")
    print(f"Between-unit  (spatial)  variance of C/N: {scope_df.attrs['spatial_var']:.3f}")


if __name__ == "__main__":
    main()
