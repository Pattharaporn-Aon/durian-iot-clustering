# A Feature-Scaling and Stability-Testing Pipeline for Clustering Small Orchard IoT Datasets

Analysis code and data for the manuscript:

> Thongnim, P., Piladaeng, J., & Srinil, P. *A feature-scaling and stability-testing
> pipeline for clustering small orchard IoT datasets.* Submitted to **PeerJ Computer Science**.

---

## Description

Small agricultural IoT studies often produce datasets with very few observational
units but many derived features. In this setting, clustering results are highly
sensitive to two decisions that are usually left implicit: (i) **which scaler** is
applied to the features, and (ii) **the scope over which scaling is computed**
(globally, per visit, or per group).

This repository implements a reproducible pipeline that treats feature scaling as an
explicit modelling decision and tests cluster stability *before* the clusters are
interpreted. It couples an hourly IoT orchard-microclimate stream with periodic field
measurements (leaf C/N ratio, flower count, fruit set) from a durian orchard in
Chanthaburi, Thailand, and evaluates:

- how different scalers change the variance share of each feature and the resulting silhouette score;
- how the scope of scaling can remove the very effect under study;
- whether the recovered grouping survives a change of clustering algorithm;
- whether the grouping is stable under bootstrap resampling and significant against a permutation null.

All figures and tables in the manuscript are reproduced by the four scripts below.

---

## Dataset Information

Three data files are included. Full column definitions are in
[`DATA_README.md`](DATA_README.md); the coding of all categorical variables is in
[`CODEBOOK.md`](CODEBOOK.md).

| File | Role | Description |
| --- | --- | --- |
| `IoT_Sensor_Hourly.csv` | Raw input | Hourly orchard microclimate record (4,409 rows), 13 Dec 2025 – 15 Jun 2026: air temperature (°C), relative humidity (% RH), rainfall (mm), wind speed (m s⁻¹), vapour-pressure deficit (kPa) and light intensity (klx). |
| `PSN.xlsx` | Raw input | Field-measurement workbook, read directly by every analysis script: leaf C/N ratio at each of four visits, flower count (visit 3 only) and fruit count (visit 4 only), by zone × group × canopy aspect. |
| `merged_field_weather.csv` | Derived | Analysis-ready table (32 rows) produced by `durian_analysis.py`. One row per canopy unit × field visit (8 units × 4 visits), with IoT features summarised over 30-day (`w30_`) and 60-day (`w60_`) windows preceding each visit. Provided for convenience and re-use; the scripts do not depend on it. |

**Design.** The orchard block was laid out as 3 zones × 2 tree groups × 2 canopy
aspects (East, West), observed at 4 field visits (12 Nov 2025, 17 Dec 2025,
11 Feb 2026, 8 Apr 2026). **Zone C is excluded from all analyses for
data-quality reasons** — every script applies `EXCLUDE_ZONES = ("C",)` to the
raw workbook — leaving 2 zones × 2 groups × 2 aspects = **8 canopy units**.
`PSN.xlsx` is the workbook as recorded in the field; `merged_field_weather.csv`
contains the 8 retained units only.

**Missing values.** Empty cells indicate either that the microclimate window had
insufficient sensor coverage for that visit (visit 1 predates the sensor record), or
that the field variable was not recorded at that visit. In the raw string columns
(`C/N`, `Flower`, `Durian`) a hyphen `-` is the not-recorded marker.

**Archive.** The dataset is also deposited on OSF:
<https://osf.io/68fc5/> (DOI: 10.17605/OSF.IO/68FC5), CC-BY 4.0.

---

## Code Information

Five scripts. **Each one is self-contained**: it reads the raw data files
(`PSN.xlsx`, and `IoT_Sensor_Hourly.csv` where weather features are needed) and
writes its own outputs, so they can be run in any order or individually.

| Script | Reads | What it does | Writes |
| --- | --- | --- | --- |
| `durian_analysis.py` | `PSN.xlsx`, `IoT_Sensor_Hourly.csv` | Builds the 30/60-day weather feature windows from the hourly stream, merges them with the field visits, and computes the C/N trend and canopy-aspect contrasts. | `fig1`–`fig4`; `merged_field_weather.csv`, `daily_weather.csv`, `aspect_east_west_summary.csv`, `unit_clusters.csv`, `correlations_weather_vs_cn.csv`, `correlations_flower.csv`, `key_relationships.csv` |
| `scaling_comparison.py` | `PSN.xlsx`, `IoT_Sensor_Hourly.csv` | Compares StandardScaler, MinMaxScaler, RobustScaler and no scaling; compares global, per-visit and per-group scaling scope. | `fig5`, `fig6`; `scaling_column_profile.csv`, `scaling_cluster_comparison.csv`, `scaling_scope_comparison.csv` |
| `clustering_models.py` | `PSN.xlsx` | Clusters the 8 canopy units and benchmarks *k*-means against a Gaussian mixture model and Ward agglomerative clustering. | `fig7`; `clustering_models_summary.csv`, `clustering_models_ari.csv` |
| `stability_analysis.py` | `PSN.xlsx` | Bootstrap Jaccard recovery and bootstrap ARI over 2,000 resamples, plus a permutation test of the silhouette coefficient. | `fig8`; `stability_by_scaler.csv`, `stability_permutation.csv` |
| `silhouette_null.py` | `PSN.xlsx` | Builds the per-scaler permutation null distribution of the silhouette coefficient (2,000 permutations) and the one-sided *p*-value. | `fig9`; `silhouette_null_summary.csv` |

Outputs (figures as PNG, tables as CSV) are written to `outputs_analysis/`.

**Analysis parameters** shared by the clustering scripts: `SEED = 0`, `K = 3`
clusters, `B = 2000` resamples, and `EXCLUDE_ZONES = ("C",)` — Zone C is dropped
for data-quality reasons, leaving the 8 canopy units (2 zones × 2 groups ×
2 aspects) analysed in the paper.

---

## Requirements

- Python 3.11 (the version used for the published results; 3.10+ should also work)
- Package versions as pinned in [`requirements.txt`](requirements.txt):

```
numpy==2.4.6
pandas==3.0.5
scipy==1.17.1
scikit-learn==1.9.0
matplotlib==3.11.1
openpyxl==3.1.5
```

These are the exact versions used by the continuous-integration run that produced
the figures and tables committed to `outputs_analysis/`.

No GPU is required. The full pipeline runs in about three minutes on a standard
laptop; `stability_analysis.py` and `silhouette_null.py` account for most of that,
since each performs 2,000 resamples for every scaler.

---

## Usage Instructions

Clone the repository and create an isolated environment:

```bash
git clone https://github.com/Pattharaporn-Aon/durian-iot-clustering.git
cd durian-iot-clustering

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Then run the five scripts. They are independent of one another — each reads the
raw data directly — so any order works and any single script can be run on its
own to reproduce just its own figures:

```bash
python durian_analysis.py
python scaling_comparison.py
python clustering_models.py
python stability_analysis.py
python silhouette_null.py
```

All figures and tables are written to `outputs_analysis/`. Random seeds are fixed
inside each script (`SEED = 0`), so repeated runs reproduce the published values
exactly.

The same five commands are run automatically on every push by the GitHub Actions
workflow in [`.github/workflows/run-pipeline.yml`](.github/workflows/run-pipeline.yml),
which re-generates `outputs_analysis/` and commits it back — so the outputs in
this repository always match the current code.

To load the analysis table directly instead of re-running the pipeline:

```python
import pandas as pd
df = pd.read_csv("merged_field_weather.csv")
print(df.shape)          # (32, 37)
print(df["unit"].unique())
```

---

## Methodology

1. **Feature engineering.** The hourly IoT stream is aggregated into 30-day and
   60-day windows ending at each field-visit date, yielding means, extrema, sums and
   threshold-crossing counts (VPD stress hours, hot hours, growing degree days,
   accumulated light, cool nights).
2. **Data cleaning.** The `C/N` field is parsed from its `"22:1"` string form to a
   numeric ratio; not-recorded markers (`-`) are converted to missing; windows with
   insufficient sensor coverage are flagged via `ndays`.
3. **Grouping.** Because a single small block provides too few zones for a zone-level
   contrast, zones are pooled and canopy aspect (East vs. West) is used as the primary
   grouping, giving 8 units of 2 zones × 2 groups × 2 aspects.
4. **Feature scaling.** Four scalers are compared on the variance share held by the
   dominant column and on the resulting silhouette coefficient. Three scaling scopes
   (global, per visit, per canopy-aspect group) are compared to show that the scope
   can remove the effect of interest.
5. **Clustering.** *k*-means on the scaled unit-level features, benchmarked against a
   Gaussian mixture model and Ward agglomerative clustering to check that the grouping
   does not depend on the algorithm.
6. **Stability testing.** Bootstrap resampling measures assignment stability, and a
   permutation test compares the observed silhouette coefficient with a null
   distribution generated by shuffling the labels.

---

## Citation

If you use this code or dataset, please cite both the article and the archived
software release:

```bibtex
@article{thongnim_scaling_2026,
  author  = {Thongnim, Pattharaporn and Piladaeng, Janjira and Srinil, Phaitoon},
  title   = {A feature-scaling and stability-testing pipeline for clustering
             small orchard {IoT} datasets},
  journal = {PeerJ Computer Science},
  year    = {2026},
  note    = {Under review}
}
```

Machine-readable metadata is in [`CITATION.cff`](CITATION.cff). The dataset DOI is
[10.17605/OSF.IO/68FC5](https://doi.org/10.17605/OSF.IO/68FC5).

---

## License

- **Code:** MIT License — see [`LICENSE`](LICENSE).
- **Data:** Creative Commons Attribution 4.0 International (CC-BY 4.0).

## Contributing

Questions, bug reports and suggested improvements are welcome via
[GitHub Issues](https://github.com/Pattharaporn-Aon/durian-iot-clustering/issues).
For pull requests, please open an issue first to describe the proposed change.

## Contact

Pattharaporn Thongnim — Department of Mathematics, Faculty of Science,
Burapha University, Chon Buri, Thailand — <pattharaporn@go.buu.ac.th>
