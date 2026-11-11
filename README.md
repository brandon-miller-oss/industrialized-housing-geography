# The Geography of Industrialized Housing

Mapping where modular and manufactured housing is produced and used across the U.S., with direct implications for Colorado policy.

University of Denver · Center for Housing Research and Innovative Solutions (CHRIS) · Graduate research project, 2026–27

**Created and maintained by:** Brandon Miller, Graduate Research Associate, CHRIS, University of Denver · Brandon.miller65@du.edu

## Scope and fit with CHRIS

- **Core region: the Mountain West** (AZ, CO, ID, MT, NV, NM, UT, WY; flagged `mountain_west` in `states`), with Colorado in the greatest depth. National plant and shipment data are kept as context because the region imports most of its manufactured homes.
- **Regional data library:** every table is sourced, documented and reproducible, so the outputs can go into the CHRIS data library and an industrialized-housing chapter of the annual *State of Housing in Colorado* report.
- **Terner Housing Policy Simulator:** the `cost_schedule` table collects factory-built vs. site-built cost and schedule observations in the simulator's unit (development cost per unit). These can inform a factory-built scenario for Denver, one of the simulator's covered cities.
- **CHFA:** tracks CHFA's Prop 123 Modular Finance and IHIP factory loans, plus factory-built language in the LIHTC Qualified Allocation Plan.
- **Climate resilience:** FEMA National Risk Index and USFS wildfire layers at the county and tract level, plus a `resilience` policy category (SB25-002 includes wildfire-risk provisions).

## What this repo builds

A reproducible database with five linked layers:

| Layer | Question it answers | Main sources |
|---|---|---|
| **Producers / plants** | Who builds factory-built homes, and where? | MHI plant list, CO DOH certified manufacturers, state programs |
| **Distribution** | Where are the homes shipped? | Census/IBTS shipments by state, manufacturer survey |
| **Usage / stock** | Where are factory-built homes already on the ground? | ACS (mobile homes by tract), mobile home parks |
| **Policy** | What rules help or hinder them? | CO legislation (HB22-1282, SB25-002), multistate scan |
| **Need** | Where is affordability pressure highest? | ACS income, home values and rent burden; HUD AMI; CHAS |
| **Cost / schedule** | How much cheaper or faster is factory-built here? | Survey, developer pro formas, project records |
| **Hazards** | Where do wildfire risk and housing need overlap? | FEMA National Risk Index, USFS Wildfire Risk to Communities |

The build produces `output/ihg.sqlite` (relational) and `output/ihg.gpkg` (opens directly in ArcGIS Pro or QGIS).

Start with [`docs/source_inventory.md`](docs/source_inventory.md), which lists every dataset, its geography and its gaps.

## Factory database workflow (current priority)

Goal: a complete, de-duplicated list of factories producing residential modular products (single-family and multifamily), with contacts, ready for the manufacturer survey.

**Current data:** the team's Excel workbook is exported to `data/processed/factory_db/` (one CSV per tab, contacts removed) and `data/processed/plants_modular.csv` by `scripts/export_factory_db.py`. See [`docs/factory_database.md`](docs/factory_database.md) for files, row IDs, scope rules and how to update the export.

The master table is `data/processed/plants_modular.csv`. Contacts are kept separately in `data/private/contacts.csv`, which is git-ignored, and follow the column template in `data/reference/contacts_template.csv`.

```bash
# 1. Import the team's existing factory list (first run: everything comes in as "new")
python scripts/ingest_list.py data/private/team_factory_list.xlsx --kind directory \
    --name-col "Company" --state-col "State" --city-col "City"

# 2. Merge the Housing Innovation Alliance database (fills hia_id, flags near-duplicates)
python scripts/ingest_list.py data/private/hia_export.csv --kind hia \
    --name-col "Company" --state-col "State" --city-col "City" --id-col "ID" --source-id SRC26

# 3. Add each state's approved-manufacturer list (also records factory -> approved state)
python scripts/ingest_list.py data/raw/ny_certified_entities.csv --kind state_list --approving-state NY \
    --program "NY Manufactured Housing Program" --name-col "<name col>" --state-col "<state col>" \
    --city-col "<city col>" --source-id SRC10

# 4. Benchmark coverage by state against Census County Business Patterns (NAICS 321992)
python scripts/fetch_cbp.py --year 2023
python scripts/completeness_check.py --year 2023      # -> output/completeness_2023.csv

# 5. Export the survey mailing list (output is git-ignored)
python scripts/export_survey_frame.py
```

Matching rules: a name/state score of 0.92 or higher merges automatically. A score from 0.75 to 0.92 is added but flagged `review`, with the likely duplicate listed in `output/review_*.csv`. Anything lower becomes a new plant. Generic words ("Homes", "Modular", "Inc.") are ignored when comparing names. Nothing is ever deleted automatically.

`state_approvals` records which states have approved each factory to ship in. This is a public proxy for cross-state shipment flows until survey results arrive.

## Repo layout

```
data/
  reference/   source_inventory.csv, states.csv          (committed)
  seed/        hand-compiled records: policies, IHIP awards, CO producers (committed)
  raw/         downloads: PDFs, Excel, shapefiles          (git-ignored)
  processed/   script outputs, tidy CSVs; plants_modular.csv = factory master
  private/     contacts, partner exports                   (git-ignored)
docs/          source inventory, data dictionary
schema/        schema.sql
scripts/       one script per source + build_db.py
survey/        early draft questions, kept for reference (the project survey is led by the survey consultant)
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

# 4. Hazards (download the NRI county / tract CSV from hazards.fema.gov/nri/data-resources)
python scripts/load_nri.py data/raw/NRI_Table_Counties.zip --level county --version <release>

# 5. Build
python scripts/build_db.py --states-shp data/raw/cb_2023_us_state_20m.zip
```

## Status

- [x] Source inventory, schema, data dictionary
- [x] Parsers: MHI plant list, Census shipments, ACS, geocoder, DB/GeoPackage build (tested on synthetic fixtures)
- [x] Seed: 6 Colorado policies (incl. CHFA Prop 123 Modular, IHIP/P123 2025, 2027-28 QAP draft), IHIP round 3 awards, 4 Colorado factory-built producers
- [x] CHRIS alignment: Mountain West flag, cost_schedule table (Terner inputs), hazards table + NRI loader
- [ ] Ask CHRIS which Terner simulator inputs (cost, timeline) can be adjusted for a factory-built scenario
- [ ] Compile CHFA Prop 123 Modular / IHIP loan recipients; read the full 2027-28 QAP once final
- [x] Factory database tooling: list ingest and matching, state approvals, CBP benchmark, survey frame export
- [ ] Import the team's existing factory list and the HIA database; resolve review flags
- [ ] Collect state approved-manufacturer lists (start with the largest importing states)
- [ ] Finalize the survey frame for the end-of-November launch
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
5. Deliverables: a public map or dashboard, a policy brief, a paper, or all three? Could this be a chapter of the *State of Housing in Colorado* report?
6. Can the project run a factory-built scenario in the Terner simulator for Denver, and which inputs would it need?
7. Is CHFA (a CHRIS funder) open to sharing Prop 123 Modular / IHIP loan outcomes?
