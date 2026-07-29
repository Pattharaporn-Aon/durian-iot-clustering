# -*- coding: utf-8 -*-
"""
Cluster-stability / bootstrap validation for the durian spatial units
=====================================================================
With only n = 8 spatial units (Zone C excluded for data-quality reasons), the
silhouette coefficient and the K-means partition can be unstable. Before any
interpretation is drawn, the stability of the result is quantified with three
resampling checks, and -- crucially -- the checks are repeated across scalers so
that the paper's central methodological claim (scaling choice matters) is itself
tested for robustness rather than asserted.

  1. Non-parametric BOOTSTRAP Jaccard stability (Hennig 2007 clusterboot idea):
     resample the units with replacement, re-fit scaler + K-means on the
     resample, re-assign every original unit to its nearest resampled centroid,
     and measure how well each reference cluster is recovered (Jaccard index).
     Mean Jaccard > 0.75 = highly stable; 0.60-0.75 = a real but uncertain
     pattern; < 0.50 = essentially dissolved.

  2. BOOTSTRAP Adjusted Rand Index: agreement of each resampled partition with
     the reference partition on the original units (mean and 95% percentile CI).

  3. PERMUTATION test on the silhouette: the observed silhouette is compared
     with a null distribution obtained by independently permuting every feature
     column (which destroys any real unit structure). The one-sided p-value is
     (1 + #{null >= observed}) / (B + 1).

Outputs (./outputs_analysis/):
  - stability_by_scaler.csv     : mean Jaccard, bootstrap-ARI (mean/CI), sil p-value
  - stability_permutation.csv   : observed vs null silhouette per scaler
  - fig8_stability.png
"""
import os, warnings
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs_analysis"); os.makedirs(OUT, exist_ok=True)
PSN = os.path.join(HERE, "PSN.xlsx")
SEED, K, B = 0, 3, 2000
EXCLUDE_ZONES = ("C",)


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


def fit_labels(Xtrain, Xall, name, seed):
    """Fit scaler+K-means on Xtrain, return labels for every row of Xall."""
    sc = make_scaler(name)
    if sc is None:
        Xt, Xa = Xtrain, Xall
    else:
        Xt = sc.fit_transform(Xtrain); Xa = sc.transform(Xall)
    km = KMeans(n_clusters=K, n_init=10, random_state=seed).fit(Xt)
    return km.predict(Xa), Xa


def jaccard_recovery(ref, boot):
    """Size-weighted mean of the best Jaccard recovery of each reference
    cluster by any bootstrap cluster (both indexed on the same original units)."""
    ref, boot = np.asarray(ref), np.asarray(boot)
    tot, wsum = 0.0, 0
    per = {}
    for r in np.unique(ref):
        A = ref == r
        best = 0.0
        for b in np.unique(boot):
            Bset = boot == b
            inter = np.sum(A & Bset); union = np.sum(A | Bset)
            best = max(best, inter / union if union else 0.0)
        per[int(r)] = best
        tot += best * A.sum(); wsum += A.sum()
    return tot / wsum, per


def analyse(X):
    Xv = X.values.astype(float)
    n = Xv.shape[0]
    scalers = ["None (raw)", "Min-Max", "Standard", "Robust"]
    rng = np.random.RandomState(SEED)

    rows, perm_rows = [], []
    jac_dist = {}
    for name in scalers:
        # reference partition on the full sample
        ref, Xa = fit_labels(Xv, Xv, name, SEED)
        obs_sil = silhouette_score(Xa, ref)

        # ---- bootstrap Jaccard + ARI ----
        jac, ari = [], []
        for _ in range(B):
            idx = rng.randint(0, n, n)              # resample with replacement
            if len(np.unique(idx)) < K:             # need >=K distinct to fit
                continue
            boot, _ = fit_labels(Xv[idx], Xv, name, SEED)
            j, _ = jaccard_recovery(ref, boot)
            jac.append(j); ari.append(adjusted_rand_score(ref, boot))
        jac, ari = np.array(jac), np.array(ari)
        jac_dist[name] = jac

        # ---- permutation test on silhouette ----
        null = np.empty(B)
        for i in range(B):
            Xp = np.column_stack([rng.permutation(Xv[:, j]) for j in range(Xv.shape[1])])
            _, Xpa = fit_labels(Xp, Xp, name, SEED + i + 1)
            lab = KMeans(n_clusters=K, n_init=5, random_state=SEED).fit_predict(Xpa)
            null[i] = silhouette_score(Xpa, lab)
        pval = (1 + np.sum(null >= obs_sil)) / (B + 1)

        rows.append({
            "scaler": name,
            "silhouette": round(obs_sil, 3),
            "jaccard_mean": round(jac.mean(), 3),
            "jaccard_ci": f"[{np.percentile(jac,2.5):.2f}, {np.percentile(jac,97.5):.2f}]",
            "boot_ARI_mean": round(ari.mean(), 3),
            "boot_ARI_ci": f"[{np.percentile(ari,2.5):.2f}, {np.percentile(ari,97.5):.2f}]",
            "sil_p_value": round(pval, 3),
        })
        perm_rows.append({"scaler": name, "observed_sil": round(obs_sil, 3),
                          "null_sil_mean": round(null.mean(), 3),
                          "null_sil_95pct": round(np.percentile(null, 95), 3),
                          "p_value": round(pval, 3)})
    return pd.DataFrame(rows), pd.DataFrame(perm_rows), jac_dist


def fig_stability(summary, jac_dist):
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    order = summary["scaler"].tolist()
    col = {"None (raw)": "#bbb", "Min-Max": "#f39", "Standard": "#39f", "Robust": "#3b8"}
    # left: bootstrap Jaccard with 95% CI whiskers
    means = [jac_dist[s].mean() for s in order]
    los = [np.percentile(jac_dist[s], 2.5) for s in order]
    his = [np.percentile(jac_dist[s], 97.5) for s in order]
    err = [np.array(means) - np.array(los), np.array(his) - np.array(means)]
    ax[0].bar(order, means, color=[col[s] for s in order],
              yerr=err, capsize=5)
    ax[0].axhline(0.75, ls="--", color="k", alpha=.6)
    ax[0].axhline(0.60, ls=":", color="k", alpha=.5)
    ax[0].set_ylabel("Bootstrap Jaccard recovery")
    ax[0].set_title("Cluster stability by scaler\n(dashed 0.75 = stable, dotted 0.60 = pattern)")
    ax[0].set_ylim(0, 1); ax[0].set_xticklabels(order, rotation=15)
    ax[0].grid(alpha=.3, axis="y")
    # right: distribution of bootstrap Jaccard
    # (avoid boxplot(labels=...) which raises in matplotlib >= 3.9; set ticks manually)
    ax[1].boxplot([jac_dist[s] for s in order], showmeans=True)
    ax[1].axhline(0.75, ls="--", color="k", alpha=.6)
    ax[1].set_ylabel("Bootstrap Jaccard recovery")
    ax[1].set_title("Distribution over %d bootstrap resamples" % B)
    ax[1].set_ylim(0, 1)
    ax[1].set_xticks(range(1, len(order) + 1))
    ax[1].set_xticklabels(order, rotation=15)
    ax[1].grid(alpha=.3, axis="y")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig8_stability.png"), dpi=130)
    plt.close()


def main():
    X = unit_matrix()
    print(f"n units = {X.shape[0]}, features = {list(X.columns)}")
    summary, perm, jac_dist = analyse(X)
    summary.to_csv(os.path.join(OUT, "stability_by_scaler.csv"), index=False)
    perm.to_csv(os.path.join(OUT, "stability_permutation.csv"), index=False)
    fig_stability(summary, jac_dist)
    print("\n=== stability by scaler ===")
    print(summary.to_string(index=False))
    print("\n=== permutation test on silhouette ===")
    print(perm.to_string(index=False))


if __name__ == "__main__":
    main()
