# -*- coding: utf-8 -*-
"""
Comparison of clustering algorithms on the durian spatial units
===============================================================
Extends the K-means analysis with two additional, methodologically different
clustering models and compares their agreement:

  1. K-means               - centroid / spherical clusters (reference)
  2. Gaussian Mixture (GMM) - soft, elliptical clusters (probabilistic)
  3. Agglomerative (Ward)   - hierarchical, no centroid assumption
  4. Random-Forest cluster  - unsupervised RF proximity -> distance -> average-
                              linkage clustering (captures non-linear structure)

All run on the SAME robust-scaled 8-unit feature matrix (C/N at each visit +
flower + fruit), Zone C excluded. We report the silhouette coefficient, the
cluster sizes, and the adjusted Rand index (ARI) of every pair of algorithms to
show how much the partitions agree.

CAVEAT: with only 8 units this is an exploratory, methods-level demonstration,
not a basis for strong biological claims.
"""
import os, warnings
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import RobustScaler
from sklearn.cluster import KMeans, AgglomerativeClustering, SpectralClustering
from sklearn.mixture import GaussianMixture
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import silhouette_score, adjusted_rand_score
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "outputs_analysis"); os.makedirs(OUT, exist_ok=True)
PSN = os.path.join(HERE, "PSN.xlsx")
SEED, K = 0, 3
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


def rf_cluster(X, k, seed):
    """Unsupervised Random Forest: separate real data from a permuted synthetic
    copy, then cluster the leaf-co-occurrence (proximity) distance matrix."""
    n, p = X.shape
    rng = np.random.RandomState(seed)
    Xsyn = np.column_stack([rng.permutation(X[:, j]) for j in range(p)])
    Xall = np.vstack([X, Xsyn])
    y = np.array([1] * n + [0] * n)
    rf = RandomForestClassifier(n_estimators=1000, random_state=seed).fit(Xall, y)
    leaves = rf.apply(X)                       # n x n_trees
    prox = np.mean(leaves[:, None, :] == leaves[None, :, :], axis=2)
    dist = 1.0 - prox
    labels = AgglomerativeClustering(
        n_clusters=k, metric="precomputed", linkage="average").fit_predict(dist)
    return labels, dist


def main():
    X = unit_matrix()
    Xs = RobustScaler().fit_transform(X)

    labels = {}
    labels["K-means"] = KMeans(n_clusters=K, n_init=10, random_state=SEED).fit_predict(Xs)
    labels["GMM"] = GaussianMixture(n_components=K, covariance_type="full",
                                    random_state=SEED).fit_predict(Xs)
    labels["Agglomerative"] = AgglomerativeClustering(n_clusters=K).fit_predict(Xs)
    labels["Spectral"] = SpectralClustering(
        n_clusters=K, affinity="rbf", assign_labels="discretize",
        random_state=SEED).fit_predict(Xs)
    rf_labels, rf_dist = rf_cluster(Xs, K, SEED)
    labels["RandomForest"] = rf_labels

    # per-model summary
    rows = []
    for name, lab in labels.items():
        if name == "RandomForest":
            sil = silhouette_score(rf_dist, lab, metric="precomputed")
        else:
            sil = silhouette_score(Xs, lab)
        sizes = np.bincount(lab, minlength=K)
        rows.append({"model": name, "silhouette": round(sil, 3),
                     "cluster_sizes": "/".join(map(str, sorted(sizes, reverse=True)))})
    summary = pd.DataFrame(rows)
    summary.to_csv(os.path.join(OUT, "clustering_models_summary.csv"), index=False)

    # pairwise ARI agreement matrix
    names = list(labels.keys())
    ari = pd.DataFrame(index=names, columns=names, dtype=float)
    for a in names:
        for b in names:
            ari.loc[a, b] = round(adjusted_rand_score(labels[a], labels[b]), 2)
    ari.to_csv(os.path.join(OUT, "clustering_models_ari.csv"))

    # figure: silhouette bars + ARI heatmap
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    ax[0].bar(summary["model"], summary["silhouette"],
              color=["#3b8", "#38f", "#f83", "#e6b", "#a5d"])
    ax[0].set_ylabel("Silhouette score")
    ax[0].set_title("Cluster quality by algorithm")
    ax[0].grid(alpha=.3, axis="y")
    ax[0].set_xticklabels(summary["model"], rotation=15)
    im = ax[1].imshow(ari.values.astype(float), vmin=0, vmax=1, cmap="Greens")
    ax[1].set_xticks(range(len(names))); ax[1].set_xticklabels(names, rotation=25)
    ax[1].set_yticks(range(len(names))); ax[1].set_yticklabels(names)
    for i in range(len(names)):
        for j in range(len(names)):
            ax[1].text(j, i, f"{ari.values[i, j]:.2f}", ha="center", va="center",
                       color="black", fontsize=9)
    ax[1].set_title("Pairwise agreement (Adjusted Rand Index)")
    fig.colorbar(im, ax=ax[1], fraction=0.046)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT, "fig7_clustering_models.png"), dpi=130)
    plt.close()

    print("=== per-model summary ===")
    print(summary.to_string(index=False))
    print("\n=== pairwise ARI ===")
    print(ari.to_string())


if __name__ == "__main__":
    main()
