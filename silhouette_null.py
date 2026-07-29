# -*- coding: utf-8 -*-
"""
Silhouette permutation null distribution (per scaler)
=====================================================
For the n = 8 spatial units (Zone C excluded), the observed silhouette of the
K-means partition is compared with a null distribution built by independently
permuting every feature column (which destroys any real multivariate unit
structure) and re-clustering. This visualises, for each scaler, whether the
observed silhouette is stronger than expected by chance.

One-sided p-value: (1 + #{null >= observed}) / (B + 1).

Output: fig9_silhouette_null.png  and  silhouette_null_summary.csv
Reuses the exact unit matrix and null procedure as stability_analysis.py so the
numbers match Table (stability) in the paper.
"""
import os, warnings
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
PSN = os.path.join(HERE, "PSN.xlsx")
OUT = os.path.join(HERE, "outputs_analysis"); os.makedirs(OUT, exist_ok=True)
SEED, K, B = 0, 3, 2000
EXCLUDE_ZONES = ("C",)
SCALERS = ["None (raw)", "Min-Max", "Standard", "Robust"]
COL = {"None (raw)": "#999999", "Min-Max": "#e05a8a",
       "Standard": "#3f7fd0", "Robust": "#2f9e77"}


def cn_to_float(x):
    s = str(x).strip()
    return float(s.split(":")[0]) / float(s.split(":")[1]) if ":" in s else np.nan


def unit_matrix():
    df = pd.read_excel(PSN).rename(columns={"Gorup": "Group"})
    df = df[~df["Zone"].isin(EXCLUDE_ZONES)]
    df["visit"] = df["Time"].astype(int)
    df["cn"] = df["C/N"].apply(cn_to_float)
    df["flower"] = pd.to_numeric(df["Flower"], errors="coerce")
    df["durian"] = pd.to_numeric(df["Durian"], errors="coerce")
    df["unit"] = df["Zone"] + "-G" + df["Group"].astype(int).astype(str) + "-" + df["Direction"]
    cn = df.pivot_table(index="unit", columns="visit", values="cn")
    cn.columns = [f"cn_v{c}" for c in cn.columns]
    fl = df[df.visit == 3].set_index("unit")["flower"].rename("flower")
    du = df[df.visit == 4].set_index("unit")["durian"].rename("durian")
    return cn.join(fl).join(du).dropna()


def make_scaler(name):
    return {"None (raw)": None, "Min-Max": MinMaxScaler(),
            "Standard": StandardScaler(), "Robust": RobustScaler()}[name]


def scale(X, name):
    sc = make_scaler(name)
    return X if sc is None else sc.fit_transform(X)


def null_and_observed(Xv, name):
    rng = np.random.RandomState(SEED)
    Xa = scale(Xv, name)
    ref = KMeans(n_clusters=K, n_init=10, random_state=SEED).fit_predict(Xa)
    obs = silhouette_score(Xa, ref)
    null = np.empty(B)
    for i in range(B):
        Xp = np.column_stack([rng.permutation(Xv[:, j]) for j in range(Xv.shape[1])])
        Xpa = scale(Xp, name)
        lab = KMeans(n_clusters=K, n_init=5, random_state=SEED).fit_predict(Xpa)
        null[i] = silhouette_score(Xpa, lab)
    pval = (1 + np.sum(null >= obs)) / (B + 1)
    return obs, null, pval


def main():
    X = unit_matrix()
    Xv = X.values.astype(float)
    print(f"n units = {Xv.shape[0]}, features = {list(X.columns)}")

    fig, axes = plt.subplots(2, 2, figsize=(11, 7.6))
    rows = []
    for ax, name in zip(axes.ravel(), SCALERS):
        obs, null, pval = null_and_observed(Xv, name)
        rows.append({"scaler": name, "observed_sil": round(obs, 3),
                     "null_mean": round(null.mean(), 3),
                     "null_95pct": round(np.percentile(null, 95), 3),
                     "p_value": round(pval, 3)})
        ax.hist(null, bins=40, color=COL[name], alpha=0.65,
                edgecolor="white", linewidth=0.3)
        ax.axvline(obs, color="black", lw=2.2)
        ax.axvline(np.percentile(null, 95), color="black", ls=":", lw=1.3, alpha=0.7)
        sig = "" if pval > 0.05 else "  (artefact)" if name == "None (raw)" else ""
        ax.set_title(f"{name}\nobserved = {obs:.3f},  $p$ = {pval:.3f}{sig}",
                     fontsize=11)
        ax.set_xlabel("silhouette")
        ax.set_ylabel("permutations")
        ax.grid(alpha=0.25, axis="y")
        # annotate legend once
        ax.plot([], [], color="black", lw=2.2, label="observed")
        ax.plot([], [], color="black", ls=":", lw=1.3, label="null 95th pct")
        ax.hist([], color=COL[name], alpha=0.65, label="permutation null")
        ax.legend(fontsize=8, loc="upper right")
    fig.suptitle("Silhouette vs permutation null distribution (2000 permutations, $n=8$ units)",
                 fontsize=13, y=1.005)
    plt.tight_layout()
    out_png = os.path.join(OUT, "fig9_silhouette_null.png")
    plt.savefig(out_png, dpi=140, bbox_inches="tight")
    plt.close()

    summary = pd.DataFrame(rows)
    summary.to_csv(os.path.join(OUT, "silhouette_null_summary.csv"), index=False)
    print("\n=== silhouette null summary ===")
    print(summary.to_string(index=False))
    print("\nsaved:", out_png)


if __name__ == "__main__":
    main()
