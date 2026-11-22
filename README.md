# bdot10k-power-lines

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24408612.svg)](https://doi.org/10.5281/zenodo.24408612)

How many kilometres of overhead power lines are there in Poland, per voivodeship and per county?
One Python script, open data from GUGiK (BDOT10k), no API keys.

## Result (BDOT10k, November 2026)

| Voltage | km | segments |
|---|---:|---:|
| medium voltage, 15/20 kV | 222 110 | 380 254 |
| high voltage, 110 kV | 30 875 | 7 954 |
| extra-high voltage, 220/400 kV | 10 200 | 1 508 |
| **total** | **263 185** | 389 716 |

A 12 m corridor along the MV lines covers about 2 665 km² (km × 12 m, overlaps not removed).
That is roughly the size of Luxembourg.

Density of MV lines per voivodeship: [results/wojewodztwa.csv](results/wojewodztwa.csv).
Per county: [results/powiaty.csv](results/powiaty.csv). Chart: [results/linie_sn_wojewodztwa.png](results/linie_sn_wojewodztwa.png).

## Value of landowners' claims (November 2026)

Model estimate for MV overhead lines: about 21 bn PLN potential, about 6.3 bn PLN expected value,
compared with about 830 m PLN of provisions that operators report in their 2025 financial statements.
Method, calibration, sources and limits: [results/mv_claims_value_2026-11.md](results/mv_claims_value_2026-11.md).

## Data

Two national GeoParquet files from opendata.geoportal.gov.pl (GUGiK):

```
https://opendata.geoportal.gov.pl/bdot10k/schemat2021/GeoParquet/OT_SULN_L.parquet   overhead lines
https://opendata.geoportal.gov.pl/bdot10k/schemat2021/GeoParquet/OT_ADJA_A.parquet   administrative units
```

97% of the line geometry in OT_SULN_L was digitised from orthophoto. Expect a few metres of offset.
Good enough for regional numbers, not for a single plot.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install geopandas pyogrio pyarrow
mkdir -p kraj
wget -O kraj/OT_SULN_L.parquet https://opendata.geoportal.gov.pl/bdot10k/schemat2021/GeoParquet/OT_SULN_L.parquet
wget -O kraj/OT_ADJA_A.parquet https://opendata.geoportal.gov.pl/bdot10k/schemat2021/GeoParquet/OT_ADJA_A.parquet
.venv/bin/python linie_bdot.py rozpoznanie --bdot kraj    # what is in the data
.venv/bin/python linie_bdot.py kraj --bdot kraj           # km per voivodeship and county
```

Stages `powiat` and `gmina` need the full BDOT10k package of one county (buildings, built-up areas,
forests, water) and count buildings and plots under the corridor. Plots come from ULDK, one request
per plot, with a resume cache.

## Things I learned on the way

1. Voivodeship boundaries in OT_ADJA_A come in pieces, one per county. Summing feature by feature
   gives around 400 "voivodeships". Dissolve by TERYT first.
2. TERYT codes must stay text. Some codes in OT_ADJA_A lost their leading zero, and powiat nakielski
   has the code of another county. Details and how to check: [docs/teryt-errors.md](docs/teryt-errors.md).

## Author

Marcin Ruszczak · MR73BIIO · ORCID [0009-0004-0170-4277](https://orcid.org/0009-0004-0170-4277)

To cite: Ruszczak, M. (2026). bdot10k-power-lines v1.0.0. Zenodo. https://doi.org/10.5281/zenodo.24408612
Polish · German · Russian · English
