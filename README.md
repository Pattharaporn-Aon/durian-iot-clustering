# durian-iot-clustering

Analysis code and data for the paper:

> Thongnim P., Piladaeng J., Srinil P.
> *A Feature-Scaling and Stability-Testing Pipeline for Clustering Small Orchard IoT Datasets.*
> Submitted to **MethodsX**.

The pipeline couples hourly IoT orchard-microclimate data with periodic field
measurements (leaf C/N ratio, flowering, fruit set) and clusters a small,
heterogeneous dataset **without bias**, by treating feature scaling as an
explicit modelling decision and testing cluster stability before interpretation.

## Data

- `merged_field_weather.csv` — analysis-ready table, one row per canopy unit × field visit (32 rows).
- `DATA_README.md` — column dictionary.
- Also archived on OSF: https://osf.io/68fc5/ (DOI: 10.17605/OSF.IO/68FC5)

## Code

Add your four analysis scripts to this repository:

- `durian_analysis.py` — weather feature engineering, C/N trend, canopy contrasts
- `scaling_comparison.py` — feature-scaling comparison (scalers + scope)
- `clustering_models.py` — clustering of the 8 units + algorithm benchmark
- `stability_analysis.py` — bootstrap + permutation stability testing

## Install & run

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python durian_analysis.py
python scaling_comparison.py
python clustering_models.py
python stability_analysis.py
```

## Which script produces which figure / table

| Script | Figures | Tables |
|---|---|---|
| `durian_analysis.py` | Fig 1–3 | Data sources, Visit schedule, Canopy-aspect contrasts |
| `scaling_comparison.py` | Fig 5–6 | Column profile, Scaler comparison |
| `clustering_models.py` | Fig 4, 7 | Clustering algorithms |
| `stability_analysis.py` | Fig 8–9 | Stability & significance |

## License

Code: MIT (see `LICENSE`). Dataset: CC-BY 4.0.

## Citation

Please cite both the article and the archived software release (see `CITATION.cff`
and the Zenodo DOI once minted).
