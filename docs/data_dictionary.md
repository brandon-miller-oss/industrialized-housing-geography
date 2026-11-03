# Data Dictionary

The full column definitions are in [`schema/schema.sql`](../schema/schema.sql). This page covers the conventions and code lists.

## Conventions

- **Geography keys** are Census GEOIDs stored as text with leading zeros: state `08`, county `08031`, tract `08031000102`, place `0820000`.
- **Every row has a `source_id`** pointing to [`source_inventory.csv`](../data/reference/source_inventory.csv). Add a new SRC row before loading a new source.
- **`verified_date`** is the date a person last checked the record against its source.
- **Survey data is confidential.** Rows in `producer_distribution` with `confidential = 1` are never exported below an aggregate of 3 or more firms.

## Table relationships

```
producers 1──* plants 1──* producer_distribution *──1 (destination geography)
plants 1──* state_approvals (factory -> states approved to ship into) | contacts (private)
states 1──* cbp_establishments (completeness benchmark)
producers 1──* projects 1──* cost_schedule
states 1──* shipments_state_year | policies | demographics | hazards (geo_level='state')
county / tract GEOIDs join demographics <-> hazards <-> projects
sources 1──* every table
```

## Code lists

**`code_basis`**: `HUD_CODE` (federal manufactured housing code, 24 CFR 3280) · `STATE_MODULAR` (built to the IRC/IBC under a state factory-built program) · `BOTH` · `UNKNOWN`

**`product_type`**: `manufactured` · `modular_volumetric` (3D boxes) · `panelized` (wall, floor or roof panels) · `tiny_home` · `mixed`

**`certifications`** (semicolon list): `HUD` · `CO_DOH_FB` (CO factory-built residential) · `CO_DOH_FBNR` (CO non-residential, including multifamily) · `CO_DOH_TH` (CO tiny home) · other states as `<ST>_<PROGRAM>`

**Policy `category`** (semicolon list allowed):

| Code | Meaning |
|---|---|
| `zoning_parity` | Local governments must treat factory-built/manufactured homes like site-built |
| `code_preemption` | A state code overrides local building codes for factory-built |
| `incentive_grant_loan` | Grants, loans or per-unit incentives to manufacturers or buyers |
| `construction_standard` | State placement or design criteria (wind, snow, thermal) |
| `adu` | Accessory dwelling unit enablement (factory-built ADUs) |
| `park_protection` | Mobile home park resident protections, right of first refusal |
| `finance_titling` | Real-property titling and chattel vs. mortgage financing rules |
| `funding_program` | Affordable housing funds usable for factory-built (e.g., Prop 123, LIHTC QAP points) |
| `resilience` | Wildfire/disaster rebuilding, hazard-specific construction standards |

**`market_segment`** (plants): `SF` · `MF` · `SF_MF` · `COMMERCIAL` (out of scope unless also residential) · `UNKNOWN`

**`match_status`** (plants): `matched` (merged automatically) · `review` (possible duplicate, needs a person) · `new`

**`found_via`** (plants): `directory` · `state_list` · `hia` · `web_search` · `cbp_followup`

**`construction_method`** (cost_schedule): `site_built` · `manufactured` · `modular_volumetric` · `panelized` · `hybrid`

**`mountain_west`** (states): 1 for AZ, CO, ID, MT, NV, NM, UT and WY, the CHRIS core region. Other states are national context.

**Policy `status`**: `proposed` · `enacted` · `rules_pending` · `in_effect` · `repealed`

**`data_origin`** (distribution): `survey` · `press_release` · `project_record` · `permit` · `estimate`
