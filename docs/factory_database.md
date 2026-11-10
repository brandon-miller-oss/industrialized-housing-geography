# Residential Modular Factory Database

The factory database lists U.S. factories that build residential volumetric modular housing, with the contacts used for the manufacturer survey. The working copy is an Excel workbook kept in the CHRIS shared folder; this repo holds a version-controlled export of it.

## Files

| Path | What it is | In git? |
|---|---|---|
| `data/processed/factory_db/manufacturers.csv` | Confirmed factory rows, one row per factory | Yes |
| `data/processed/factory_db/candidates_to_verify.csv` | Possible factories still being verified (ZeeMap, RFP list, Colorado registry, replies) | Yes |
| `data/processed/factory_db/builders_deployers.csv` | Builders and developers that use modular but don't run factories (low priority) | Yes |
| `data/processed/factory_db/excluded.csv` | Rows removed from scope (non-U.S., commercial-only, closed, duplicates) | Yes |
| `data/processed/factory_db/state_registry_co.csv` | Colorado DOLA factory-built registry (FB Manufacturers + Multi-Family Factory), pulled 11/08/2026 | Yes |
| `data/processed/factory_db/change_log.csv` | Every edit made to the workbook, with old value, new value and reason | Yes |
| `data/processed/plants_modular.csv` | Master plant table (Manufacturers + Candidates) in the `plants` schema used by `build_db.py` and `export_survey_frame.py` | Yes |
| `data/private/ResidentialModular_Factory_Database_<date>.xlsx` | The workbook itself | No (has contacts) |
| `data/private/contacts.csv` | Emails, named contacts and confirmed survey contacts | No (PII) |
| `data/private/outreach_log.csv` | Outreach status, date and latest note for every row | No (PII) |

Email addresses are removed from the committed CSVs; notes that quoted an address show `[email]`.

## Row IDs

Each row keeps the ID used in the outreach tracker: a tab prefix plus the workbook row number (`M162` = Manufacturers row 162, `C96` = Candidates row 96, `B6` = Builders row 6). Rows are never deleted from the workbook, so IDs stay stable; closed and duplicate rows are renamed (for example "Heibar (CLOSED)") and copied to Excluded.

## Scope and classification

A factory is in scope for the survey when it is in the U.S., builds **volumetric** modules (complete 3D boxes), builds **residential** units and is **not HUD-code only**. Mixed modular/HUD plants are in. Panelized-only plants are out.

| Workbook column | Values | `plants_modular.csv` field |
|---|---|---|
| Build_Method | Volumetric · Volumetric + Panelized · Panelized-Only · Likely Panelized - verify · Unknown | `product_type`: modular_volumetric · mixed · panelized |
| Regulatory_Basis | IRC-Modular · HUD-Code · IRC-Modular; HUD-Code · Unknown | `code_basis`: STATE_MODULAR · HUD_CODE · BOTH · UNKNOWN |
| Residential_Type | SF-Only · MF-Only · SF-and-MF · Mixed-Modular-and-MH · MH-Only · Commercial-Only · Unknown | `market_segment`: SF · MF · SF_MF · COMMERCIAL · UNKNOWN |
| Active | YES · NO · UNKNOWN | `status`: active · closed · unknown |
| Survey_Eligible (formula) | Eligible · Check · Not eligible | `in_survey_frame` = 1 when Eligible |

**Open question for the team:** RV and park-model units (ANSI 119.5 / NFPA 1192), tiny homes on wheels, and unfinished kits, shells or chassis aren't covered by the categories above. Colorado shops such as Trailer Made, Fading West and Wind River build some of each. Confirm with Solomon and Marina whether these count before the survey goes out.

## Updating the export

1. Save the latest workbook into `data/private/` (it must have been opened and saved in Excel, or recalculated, so formula columns have values).
2. Run:

   ```bash
   python scripts/export_factory_db.py data/private/ResidentialModular_Factory_Database_<date>.xlsx
   python scripts/export_survey_frame.py      # optional: survey mailing list -> output/ (git-ignored)
   ```

3. Review `git diff --stat`, then commit the CSVs with a message describing what changed (for example "Factory DB 11/09: 9 replies, VBC Tracy plant added").
