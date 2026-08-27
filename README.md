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

| File | Rows | Description |
| --- | --- | --- |
| `IoT_Sensor_Hourly.csv` | 4,409 | Raw hourly orchard microclimate record, 13 Dec 2025 – 15 Jun 2026: air temperature (°C), relative humidity (% RH), rainfall (mm), wind speed (m s⁻¹), vapour-pressure deficit (kPa) and light intensity (klx). |
| `PSN.xlsx` | 32 | Raw field-measurement workbook: leaf C/N ratio at each of four visits, flower count (visit 3 only) and fruit count (visit 4 only), by zone × group × canopy aspect. |
| `merged_field_weather.csv` | 32 | Analysis-ready table produced from the two files above. One row per canopy unit × field visit (8 units × 4 visits), with IoT features summarised over 30-day (`w30_`) and 60-day (`w60_`) windows preceding each visit. |

**Design.** 2 zones (A, B) × 2 tree groups (1, 2) × 2 canopy aspects (East, West)
= 8 canopy units, each observed at 4 field visits (12 Nov 2025, 17 Dec 2025,
11 Feb 2026, 8 Apr 2026).

**Missing values.** Empty cells indicate either that the microclimate window had
insufficient sensor coverage for that visit (visit 1 predates the sensor record), or
that the field variable was not recorded at that visit. In the raw string columns
(`C/N`, `Flower`, `Durian`) a hyphen `-` is the not-recorded marker.

**Archive.** The dataset is also deposited on OSF:
<https://osf.io/68fc5/> (DOI: 10.17605/OSF.IO/68FC5), CC-BY 4.0.

---

## Code Information

| Script | What it does | Produces |
| --- | --- | --- |
| `durian_analysis.py` | Builds the 30/60-day weather feature windows from the hourly stream, merges them with the field visits, and computes the C/N trend and canopy-aspect contrasts. | Figures 1–3; Tables: data sources, visit schedule, canopy-aspect contrasts |
| `scaling_comparison.py` | Compares StandardScaler, MinMaxScaler, RobustScaler and no scaling; compares global, per-visit and per-group scaling scope. | Figures 5–6; Tables: column profile, scaler comparison |
| `clustering_models.py` | Clusters the 8 canopy units and benchmarks *k*-means against a Gaussian mixture model, Ward agglomerative clustering and further alternatives. | Figures 4, 7; Table: clustering algorithms |
| `stability_analysis.py` | Bootstrap resampling of cluster assignments and a permutation test of the silhouette coefficient against a null distribution. | Figures 8–9; Table: stability and significance |

Outputs (figures as PNG, tables as CSV) are written to `outputs_analysis/`.

---

## Requirements

- Python 3.10 or newer
- Package versions as pinned in [`requirements.txt`](requirements.txt):

```
numpy>=1.24
pandas>=2.0
scipy>=1.10
scikit-learn>=1.3
matplotlib>=3.7
openpyxl>=3.1
```

No GPU is required. The full pipeline runs in under a minute on a standard laptop.

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

Run the scripts **in this order** — `durian_analysis.py` regenerates
`merged_field_weather.csv`, which the other three scripts consume:

```bash
python durian_analysis.py
python scaling_comparison.py
python clustering_models.py
python stability_analysis.py
```

All figures and tables are written to `outputs_analysis/`. Random seeds are fixed
inside each script, so repeated runs reproduce the published values exactly.

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
