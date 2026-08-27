# Codebook — `merged_field_weather.csv`

Companion to the manuscript *"A feature-scaling and stability-testing pipeline for
clustering small orchard IoT datasets"* (Thongnim, Piladaeng & Srinil).

This codebook lists every variable in the raw data file, states its type, and gives
the factor level that each stored code represents. It is provided in response to the
PeerJ request for a codebook converting numerically-recorded categorical data to its
respective factors.

**File:** `merged_field_weather.csv` — 32 rows × 37 columns.
**Unit of observation:** one canopy unit at one field visit (8 units × 4 visits).
**Encoding:** UTF-8. **Delimiter:** comma. **Decimal separator:** period.

---

## 1. Categorical and identifier variables

### `Zone` — orchard zone (nominal, stored as a letter)

| Code | Factor level |
| --- | --- |
| `A` | Zone A of the orchard block |
| `B` | Zone B of the orchard block |

Zones are pooled in the analysis; see Materials and Methods, *Grouping by canopy aspect*.

### `Group` — tree group within a zone (nominal, **stored numerically**)

| Code | Factor level |
| --- | --- |
| `1` | Tree group 1 |
| `2` | Tree group 2 |

The numbers are arbitrary labels, not an ordering or a quantity.

### `Direction` — canopy aspect (nominal, stored as text)

| Code | Factor level |
| --- | --- |
| `East` | East-facing canopy (direct radiation in the morning) |
| `West` | West-facing canopy (direct radiation in the afternoon) |

This is the primary grouping variable of the study.

### `Time` — field-visit index (ordinal, **stored numerically**)

| Code | Factor level |
| --- | --- |
| `1` | Visit 1 |
| `2` | Visit 2 |
| `3` | Visit 3 |
| `4` | Visit 4 |

`Time` is a visit counter, **not** a clock time. It is identical to `visit`; both are
retained for backward compatibility with the raw field workbook (`PSN.xlsx`).

### `visit` — field-visit index (ordinal, **stored numerically**)

| Code | Factor level | Date | Phenological note |
| --- | --- | --- | --- |
| `1` | Visit 1 | 2025-11-12 | Pre-sensor baseline; no IoT window available |
| `2` | Visit 2 | 2025-12-17 | Early season |
| `3` | Visit 3 | 2026-02-11 | Flowering — flower counts recorded |
| `4` | Visit 4 | 2026-04-08 | Fruit set — fruit counts recorded |

### `unit` — canopy unit label (nominal, composite key)

Constructed as `Zone-G{Group}-{Direction}`. Eight levels:

| Code | Zone | Group | Aspect |
| --- | --- | --- | --- |
| `A-G1-East` | A | 1 | East |
| `A-G1-West` | A | 1 | West |
| `A-G2-East` | A | 2 | East |
| `A-G2-West` | A | 2 | West |
| `B-G1-East` | B | 1 | East |
| `B-G1-West` | B | 1 | West |
| `B-G2-East` | B | 2 | East |
| `B-G2-West` | B | 2 | West |

### `Date` — field-visit date (date, ISO 8601 `YYYY-MM-DD`)

Four levels: `2025-11-12`, `2025-12-17`, `2026-02-11`, `2026-04-08`.

---

## 2. Field measurements

Each field measurement appears twice: a raw column exactly as transcribed from the
field workbook, and a cleaned numeric column used in the analysis.

| Raw column | Cleaned column | Type | Units | Notes |
| --- | --- | --- | --- | --- |
| `C/N` | `cn` | Continuous | dimensionless ratio | Raw is a **string in `"N:1"` form** (e.g. `"22:1"`); cleaned is the numeric ratio (e.g. `22.0`). Recorded at all four visits. |
| `Flower` | `flower` | Count | flowers per unit | Recorded at **visit 3 only**. Observed range 862–2768. |
| `Durian` | `durian` | Count | fruits per unit | Recorded at **visit 4 only**. Observed range 24–49. |

### Missing-value codes

| Code | Meaning | Where it appears |
| --- | --- | --- |
| `-` (hyphen) | Variable not recorded at this visit by design | Raw columns `C/N`, `Flower`, `Durian` |
| *(empty cell)* | Missing / not applicable | Cleaned columns `cn`, `flower`, `durian`, and all `w30_*` / `w60_*` columns |

An empty cell in a `w30_*` or `w60_*` column means the microclimate window preceding
that visit had insufficient sensor coverage — this affects all of visit 1, which
precedes the start of the IoT record (13 Dec 2025).

---

## 3. IoT microclimate features (continuous, no categorical coding)

Two window lengths precede each visit date: `w30_` = 30 days, `w60_` = 60 days.
All are continuous or count variables derived from the hourly sensor stream; none is
a coded categorical variable.

| Suffix | Description | Units |
| --- | --- | --- |
| `temp_mean` | Mean air temperature over the window | °C |
| `temp_max` | Maximum air temperature over the window | °C |
| `temp_min` | Minimum air temperature over the window | °C |
| `humid_mean` | Mean relative humidity over the window | % RH |
| `rain_sum` | Total rainfall over the window | mm |
| `vpd_mean` | Mean vapour-pressure deficit over the window | kPa |
| `vpd_stress_hours` | Count of hours above the VPD stress threshold | hours |
| `hot_hours` | Count of hours above the high-temperature threshold | hours |
| `gdd_sum` | Accumulated growing degree days over the window | °C·day |
| `lux_sum` | Accumulated light over the window | klx·h |
| `cool_nights` | Count of nights below the cool-night threshold | nights |
| `ndays` | Number of days in the window with usable sensor data | days |

`ndays` is a data-coverage indicator, not a treatment variable: `ndays` = 30 (`w30_`)
or 60 (`w60_`) indicates complete coverage; smaller values indicate partial coverage.

---

## 4. Loading the file with factors applied

```python
import pandas as pd

df = pd.read_csv("merged_field_weather.csv", parse_dates=["Date"])

# Apply the codebook: declare the coded columns as categorical factors
df["Zone"]      = df["Zone"].astype("category")
df["Group"]     = df["Group"].map({1: "Group 1", 2: "Group 2"}).astype("category")
df["Direction"] = pd.Categorical(df["Direction"], categories=["East", "West"])
df["visit"]     = pd.Categorical(df["visit"], categories=[1, 2, 3, 4], ordered=True)
df["Time"]      = df["visit"]          # Time is a duplicate of visit
df["unit"]      = df["unit"].astype("category")
```

---

*Prepared as a Supplemental File for PeerJ Computer Science submission #147214.*
