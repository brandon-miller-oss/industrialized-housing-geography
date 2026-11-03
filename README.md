# The Geography of Industrialized Housing

Mapping where modular and manufactured housing is produced and used across the U.S., with direct implications for Colorado policy.

University of Denver · Center for Housing Research and Innovative Solutions (CHRIS) · Graduate research project, 2026–27

## What this repo builds

A reproducible database with five linked layers:

| Layer | Question it answers | Main sources |
|---|---|---|
| **Producers / plants** | Who builds factory-built homes, and where? | MHI plant list, CO DOH certified manufacturers, state programs |
| **Distribution** | Where are the homes shipped? | Census/IBTS shipments by state, manufacturer survey |
| **Usage / stock** | Where are factory-built homes already on the ground? | ACS (mobile homes by tract), mobile home parks |
| **Policy** | What rules help or hinder them? | CO legislation (HB22-1282, SB25-002), multistate scan |
| **Need** | Where is affordability pressure highest? | ACS income, home values and rent burden; HUD AMI; CHAS |

The build produces `output/ihg.sqlite` (relational) and `output/ihg.gpkg` (opens directly in ArcGIS Pro or QGIS).

Start with [`docs/source_inventory.md`](docs/source_inventory.md), which lists every dataset, its geography and its gaps.

## Repo layout

```
data/
  reference/   source_inventory.csv, states.csv          (committed)
  seed/        hand-compiled records: policies, IHIP awards, CO producers (committed)
  raw/         downloads: PDFs, Excel, shapefiles          (git-ignored)
  processed/   script outputs, tidy CSVs                   (committed when small)
docs/          source inventory, data dictionary
schema/        schema.sql
scripts/       one script per source + build_db.py
survey/        manufacturer survey draft (responses are git-ignored)
tests/         offline tests with synthetic fixtures
output/        built database + GeoPackage                 (git-ignored)
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q                                     # sanity check

# 1. HUD-Code plants -> map points
#    download the MHI plant list PDF into data/raw/ (link in source inventory, SRC05)
python scripts/parse_mhi_plant_list.py data/raw/Plant-List-01_31_26-1.pdf --snapshot 2026-01-31
python scripts/geocode_plants.py data/processed/plants_mhi.csv
python scripts/geocode_plants.py data/seed/plants.csv

# 2. Shipments by state (download the Excel from the Census MHS shipments page, SRC01)
python scripts/load_shipments.py data/raw/<shipments_by_state>.xlsx

# 3. Demographics
export CENSUS_API_KEY=...                      # optional, free
python scripts/fetch_acs.py --year 2023 --level state
python scripts/fetch_acs.py --year 2023 --level county
python scripts/fetch_acs.py --year 2023 --level tract --state 08

# 4. Build
python scripts/build_db.py --states-shp data/raw/cb_2023_us_state_20m.zip
```

## Status

- [x] Source inventory, schema, data dictionary
- [x] Parsers: MHI plant list, Census shipments, ACS, geocoder, DB/GeoPackage build (tested on synthetic fixtures)
- [x] Seed: 3 Colorado policies, IHIP round 3 awards, 4 Colorado factory-built producers
- [ ] Run the parsers on real downloads and check totals against the source PDFs/tables
- [ ] Request the CO DOH certified manufacturer facility list
- [ ] Compile all IHIP rounds; add Fading West and other CO projects to `projects`
- [ ] Multistate policy scan (start with CO neighbors and the top producing states)
- [ ] Survey: review with faculty lead, check whether IRB review is needed, pilot

## Open questions for the faculty lead

1. Primary research question: production geography, flows versus need, or policy effects?
2. Unit of analysis for policy: state only, or also cities and counties (Colorado first)?
3. Do CHRIS or DU have existing industry contacts or data agreements (MHI, MBI, CO DOH)?
4. Is the survey in scope this year, and whose IRB covers it?
5. Deliverables: a public map or dashboard, a policy brief, a paper, or all three?
