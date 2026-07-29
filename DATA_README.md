# Durian orchard IoT: leaf C/N and flowering dataset

`merged_field_weather.csv` is the merged daily feature table used in the paper
"A Feature-Scaling and Stability-Testing Pipeline for Clustering Small Orchard
IoT Datasets".

Each row is one canopy unit at one field visit (unit = Zone-Group-Direction).
Field measurements are joined to orchard IoT microclimate features summarised
over 30-day and 60-day windows before each visit.

## Columns

Identifiers and field measurements:
- `Date`, `Time`, `visit` — visit date and visit index
- `Zone`, `Group`, `Direction` — orchard zone, tree group, canopy aspect (East/West)
- `unit` — combined unit label (Zone-Group-Direction)
- `C/N`, `cn` — leaf carbon-to-nitrogen ratio (raw string and numeric)
- `Flower`, `flower` — flowering observation
- `Durian`, `durian` — fruit-set observation

IoT microclimate features (prefix `w30_` = 30-day window, `w60_` = 60-day window):
- `temp_mean`, `temp_max`, `temp_min` — air temperature (deg C)
- `humid_mean` — relative humidity (%)
- `rain_sum` — total rainfall
- `vpd_mean` — mean vapour pressure deficit (kPa)
- `vpd_stress_hours` — hours above the VPD stress threshold
- `hot_hours` — hours above the high-temperature threshold
- `gdd_sum` — accumulated growing degree days
- `lux_sum` — accumulated light
- `cool_nights` — count of cool nights
- `ndays` — number of days with sensor data in the window

## Notes

Empty cells indicate the microclimate window had insufficient sensor coverage
for that visit, or the field variable was not recorded on that visit.

Source: https://osf.io/68fc5/ (DOI: 10.17605/OSF.IO/68FC5), CC-BY 4.0.
