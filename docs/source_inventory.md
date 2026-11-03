# Source Inventory

Machine-readable version: [`data/reference/source_inventory.csv`](../data/reference/source_inventory.csv). Each row has a `source_id` (SRC01–SRC24), and every database table cites it in its `source_id` column.

Last reviewed: October 2026.

## Key findings

1. **There are two data worlds.** HUD-Code manufactured housing has federal data on plants, monthly shipments by state and prices. Modular and panelized housing built to state or local codes has almost none. Census reports construction method only by region (SRC07), and only for single-family.
2. **Colorado has no HUD-Code plants.** MHI's January 2026 plant list (SRC05) shows 147 plants nationwide, with Texas (26), Alabama (19) and Pennsylvania (12) the largest. None are in Colorado, Wyoming or Utah. Every new manufactured home placed in Colorado is imported. Plants in AZ, NM, NE, KS, OK, TX and ID are the likely origins, but no public data confirms this, which makes it a good survey question. Colorado's own factory production is modular and panelized (Fading West, IHIP recipients and others).
3. **No public source reports where a specific company's homes are shipped.** Public shipment data is aggregated by state. To get manufacturer → destination flows, especially for modular, the project needs an original survey (SRC19), plus project-level records such as press releases, IHIP reports and permits.
4. **Colorado policy is active and recent.** HB22-1282 (2022) created the Innovative Housing Incentive Program: $40M in grants and loans for Colorado factory-built manufacturers with 500 or fewer employees. SB25-002 (signed May 8, 2025) directs regional building codes for factory-built structures and bars local governments from applying stricter standards to factory-built homes than to site-built homes in the same zones. The State Housing Board rules were due July 1, 2026, so check whether they were adopted.
5. **CHFA, a CHRIS funder, is already financing factories.** Its Prop 123 Modular Finance Program (2023, $18M) and the combined IHIP/Prop 123 factory loans (2025 guidelines: up to $8M, 1.5–1.75%) lend directly to Colorado manufacturers (SRC20). CHFA's 2027–28 draft QAP also revises its scoring language on factory-built and modular construction (SRC21). The recipients and outcomes of these loans are a natural data request through CHRIS.
6. **The Terner simulator works in development cost per unit** (land, construction, parking, fees, carrying costs) and covers Denver (SRC24). Factory-built cost and schedule data collected in `cost_schedule` can be expressed in that unit.

## Coverage by database layer

| Layer | Best sources | Geography | Gap |
|---|---|---|---|
| **Producers / plants** | MHI Plant List (SRC05), CO DOH certified manufacturers (SRC09), other state programs (SRC10) | Plant city | No capacity or parent-company data; modular plant list must be compiled state by state |
| **Distribution** | Census/IBTS shipments by state (SRC01), MHI monthly reports (SRC04), SOC construction method (SRC07) | State (HUD-Code); region (modular) | No firm → destination flows; modular state-level data must come from the survey |
| **Usage / stock** | ACS B25024 mobile homes (SRC14), mobile home parks (SRC17) | Tract / point | ACS counts mobile homes, not modular units, because modular homes look like site-built in the data |
| **Policy** | CO bills and rules (SRC11–12), multistate scan (SRC13) | State / city | Must be hand-coded with a consistent scheme |
| **Demographics / need** | ACS (SRC14), HUD income limits (SRC15), CHAS (SRC16) | Tract → state | Margins of error at the tract level |
| **Finance** | CHFA Prop 123 Modular / IHIP loans (SRC20), CHFA QAP (SRC21) | Firm / state | Loan recipients and outcomes not published in the guidelines |
| **Hazards** | FEMA NRI (SRC22), USFS Wildfire Risk to Communities (SRC23) | Tract / county / community | Modeled estimates; versions change |
| **Cost / schedule** | Survey (SRC19), pro formas; output aligned to Terner simulator (SRC24) | Project | No public source; must be collected |

## Suggested first pulls (priority 1)

1. Parse the MHI Plant List and geocode the plants (`scripts/parse_mhi_plant_list.py`, `scripts/geocode_plants.py`). This produces the first map.
2. Download the Census annual shipments-by-state Excel file and load it (`scripts/load_shipments.py`).
3. Pull ACS state and county indicators (`scripts/fetch_acs.py`).
4. Email Colorado DOH for the certified factory-built manufacturer facility list (SRC09).
5. Hand-compile IHIP award rounds into `data/seed/ihip_awards.csv`.

## Sources

- [Census MHS – about](https://census.gov/programs-surveys/mhs/about.html) · [MHS data](https://www.census.gov/programs-surveys/mhs/data.html) · [MHS tables](https://www.census.gov/programs-surveys/mhs/data/tables.html) · [MHS datasets](https://www.census.gov/programs-surveys/mhs/data/datasets.html) · [MHS FAQ](https://www.census.gov/programs-surveys/mhs/about/faq.html)
- [MHI Plant List, Jan 2026](https://www.manufacturedhousing.org/wp-content/uploads/2026/03/Plant-List-01_31_26-1.pdf) · [MHI Economic Report, Mar 2026](https://www.manufacturedhousing.org/wp-content/uploads/2026/05/MHI-Economic-Report-March-2026.pdf)
- [HUD Office of Manufactured Housing Programs](https://hud.gov/program_offices/housing/mhs/csp/mfsheet)
- [NAHB – modular market share 2024](https://eyeonhousing.org/2025/08/market-share-for-modular-and-other-non-site-built-housing-in-2024/)
- [CO DOH Factory Built Structures](https://doh.colorado.gov/factory-built-structures) · [Manufacturers – Modulars](https://doh.colorado.gov/manufacturers-modulars) · [Manufacturers – HUD Code](https://doh.colorado.gov/manufacturers-hud-code-homes) · [Certified manufacturer status](https://doh.colorado.gov/certified-manufacturer-status)
- [SB25-002](https://leg.colorado.gov/bills/sb25-002) · [HB22-1282](https://leg.colorado.gov/bills/HB22-1282) · [IHIP round 3 recipients](https://governorsoffice.colorado.gov/news/10871-polis-administration-announces-latest-round-ihip-grant-recipients-supporting-creation)
- [CHFA Prop 123 Modular Finance guidelines (2023)](https://www.chfainfo.com/getattachment/885e2858-84f8-40e9-b76a-bb37e74e7ed6/Prop123-CO-AHFF-Modular-ProgramGuidelines.pdf) · [IHIP/Prop 123 Modular guidelines (2025)](https://www.chfainfo.com/getattachment/908b63d5-8512-4f6d-b6af-b2101d732f48/IHIP-P123Modular-Program-Guidelines.pdf) · [CHFA 2027–28 QAP draft summary](https://www.chfainfo.com/getattachment/5009a3ed-67ee-4609-9786-bed573d45b6b/2027-2028-QAP-First-Draft-Summary-of-Changes.pdf)
- [FEMA NRI data](https://hazards.fema.gov/nri/data-resources) · [USFS Wildfire Risk to Communities](https://www.fs.usda.gov/rds/archive/catalog/RDS-2024-0030)
- [Terner Labs](https://ternercenter.berkeley.edu/terner-labs) · [Terner: local market conditions (2026)](https://ternercenter.berkeley.edu/wp-content/uploads/2026/05/HowLocalMarketConditionsShapePolicyOutcomes2026.pdf) · [DU Magazine on CHRIS](https://stories.du.edu/magazine/departments/features/can-colorado-solve-its-housing-crisis-du-launches-new-center-to-help-find-answers/index.html)
- [NY Manufactured Housing Program certified entities](https://catalog.data.gov/dataset/manufactured-housing-program-certified-entities)
