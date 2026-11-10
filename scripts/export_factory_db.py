"""Export the factory database workbook to version-controlled CSVs.

    python scripts/export_factory_db.py data/private/ResidentialModular_Factory_Database_<date>.xlsx

The Excel workbook stays the working copy (it has formulas, notes and contacts).
This script splits it into:

  data/processed/factory_db/<tab>.csv   one CSV per tab, contact fields removed (committed)
  data/processed/plants_modular.csv     master plant table used by the other scripts (committed)
  data/private/contacts.csv             emails, named contacts, survey contacts (git-ignored)
  data/private/outreach_log.csv         outreach status and notes per row (git-ignored)

Run it after every workbook update, then commit the CSVs. The workbook must have been
recalculated (opened and saved in Excel, or run through LibreOffice) so formula
columns such as Row_Status and Survey_Eligible have values.
"""
import datetime as dt
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROCESSED, ROOT, load_states  # noqa: E402

PRIVATE = ROOT / "data" / "private"
OUT = PROCESSED / "factory_db"

# tab name -> (header row number in Excel, row-id prefix, output file)
TABS = {
    "Manufacturers": (4, "M", "manufacturers.csv"),
    "Candidates_to_Verify": (1, "C", "candidates_to_verify.csv"),
    "Builders_Deployers": (4, "B", "builders_deployers.csv"),
    "Excluded": (1, "X", "excluded.csv"),
    "StateRegistry_CO": (1, "R", "state_registry_co.csv"),
    "Change_Log": (None, "L", "change_log.csv"),
}
# Columns that hold personal contact details; they go to data/private only.
PRIVATE_COLS = ["Email", "Email notes", "Survey_Contact / Contact", "Outreach_Notes (latest)"]
OUTREACH_COLS = ["Outreach_Status", "Outreach_Date", "Survey_Contact / Contact", "Outreach_Notes (latest)"]

PRODUCT = {"Volumetric": "modular_volumetric", "Panelized-Only": "panelized",
           "Volumetric + Panelized": "mixed", "Likely Panelized - verify": "panelized"}
CODE = {"IRC-Modular": "STATE_MODULAR", "HUD-Code": "HUD_CODE",
        "IRC-Modular; HUD-Code": "BOTH", "Unknown": "UNKNOWN"}
# market_segment codes follow the CHECK constraint in schema/schema.sql
SEGMENT = {"SF-Only": "SF", "MF-Only": "MF", "SF-and-MF": "SF_MF", "Mixed-Modular-and-MH": "SF",
           "Commercial-Only": "COMMERCIAL", "Unknown": "UNKNOWN"}
STATUS = {"YES": "active", "NO": "closed"}


EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9.-]+\.[A-Za-z]{2,})?")


def find_header(path, name):
    """Header row = first row whose column A is a known header label (Change_Log has notes above)."""
    raw = pd.read_excel(path, sheet_name=name, header=None, dtype=str, nrows=40)
    for i, v in enumerate(raw.iloc[:, 0].fillna("")):
        if v.strip() in ("Company Name", "Registry list", "Tab"):
            return i + 1
    raise ValueError(f"No header row found on {name}")


def read_tab(path, name, header_row, prefix):
    header_row = header_row or find_header(path, name)
    df = pd.read_excel(path, sheet_name=name, header=header_row - 1, dtype=str)
    df = df.dropna(how="all")
    first = df.columns[0]
    df = df[df[first].notna()].copy()
    # row id = tab prefix + Excel row number, matching the outreach tracker (e.g. M162, C96)
    df.insert(0, "row_id", [f"{prefix}{i + header_row + 1}" for i in df.index])
    df = df[[c for c in df.columns if not str(c).startswith("Unnamed")]]
    return df.fillna("")


def main(path):
    path = Path(path)
    OUT.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    frames = {}
    for name, (hdr, prefix, fname) in TABS.items():
        df = read_tab(path, name, hdr, prefix)
        frames[name] = df
        public = df.drop(columns=[c for c in PRIVATE_COLS if c in df.columns])
        # notes can quote email addresses; keep those out of the committed CSVs
        public = public.apply(lambda col: col.str.replace(EMAIL, "[email]", regex=True))
        public.to_csv(OUT / fname, index=False)
        print(f"{name}: {len(df)} rows -> {OUT / fname}")

    # Private contacts (one row per plant row that has an email or named contact).
    # Builders are not plants, so their contacts stay in outreach_log.csv only.
    rows = []
    for name in ("Manufacturers", "Candidates_to_Verify"):
        for _, r in frames[name].iterrows():
            email = (r.get("Email") or "").strip()
            survey = (r.get("Survey_Contact / Contact") or "").strip()
            if not (email or survey):
                continue
            rows.append({
                "contact_id": len(rows) + 1, "plant_id": r.row_id, "producer_id": "",
                "contact_name": survey, "title": "", "email": email.replace("\n", "; "),
                "phone": r.get("Phone") or "",
                "is_primary": "1" if survey.upper().startswith("SURVEY CONTACT") else "0",
                "contact_source": (r.get("Email notes") or "").replace("\n", " "),
                "verified_date": r.get("Outreach_Date") or "",
            })
    pd.DataFrame(rows).to_csv(PRIVATE / "contacts.csv", index=False)

    log = []
    for name in ("Manufacturers", "Candidates_to_Verify", "Builders_Deployers"):
        df = frames[name]
        keep = ["row_id", df.columns[1]] + [c for c in OUTREACH_COLS if c in df.columns]
        log.append(df[keep].rename(columns={df.columns[1]: "company"}))
    pd.concat(log).to_csv(PRIVATE / "outreach_log.csv", index=False)

    # Master plant table for the rest of the pipeline (Manufacturers + Candidates).
    # state_abbr must be a U.S. state in data/reference/states.csv (foreign key); others go in state_raw.
    us = {s["state_abbr"] for s in load_states()}
    plants = []
    for name in ("Manufacturers", "Candidates_to_Verify"):
        for _, r in frames[name].iterrows():
            plants.append({
                "plant_id": r.row_id,
                "plant_name": r.get("Company Name") or "",
                "aka": r.get("Factory Name / Formerly Known As") or "",
                "street": r.get("Street Address") or "",
                "city": r.get("City") or "",
                "state_abbr": (r.get("State") or "") if (r.get("State") or "") in us else "",
                "state_raw": r.get("State") or "",
                "zip": r.get("Zip") or "",
                "website": r.get("Website") or "",
                "us_based": r.get("US_Based") or "",
                "code_basis": CODE.get(r.get("Regulatory_Basis") or "", ""),
                "market_segment": SEGMENT.get(r.get("Residential_Type") or "", ""),
                "product_type": PRODUCT.get(r.get("Build_Method") or "", ""),
                "status": STATUS.get(r.get("Active") or "", "unknown"),
                "residential": "0" if (r.get("Residential_Type") or "") == "Commercial-Only" else "1",
                "row_status": r.get("Row_Status") or "",
                "survey_eligible": r.get("Survey_Eligible") or "",
                "in_survey_frame": "1" if (r.get("Survey_Eligible") or "") == "Eligible" else "0",
                "outreach_status": r.get("Outreach_Status") or "",
                "found_via": r.get("Source") or "",
                "notes": EMAIL.sub("[email]", r.get("Verification_Notes") or ""),
                "source_tab": name,
                "export_date": f"{dt.date.today():%Y-%m-%d}",
            })
    pd.DataFrame(plants).to_csv(PROCESSED / "plants_modular.csv", index=False)
    print(f"plants_modular.csv: {len(plants)} rows; contacts.csv: {len(rows)} rows (private)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
