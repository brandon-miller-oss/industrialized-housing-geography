"""Build the public, read-only factory database web page (for GitHub Pages).

    python scripts/build_site.py            # -> output/site/index.html

Reads the committed, contact-free CSVs in data/processed/factory_db/ and writes ONE
self-contained HTML file with the data embedded. Nothing personal goes in: no emails,
phone numbers, contact names, verification notes or outreach status.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUTPUT, PROCESSED  # noqa: E402

DB = PROCESSED / "factory_db"
TEMPLATE = Path(__file__).resolve().parent / "site_template.html"

BUILD = {"Volumetric": "Volumetric", "Volumetric + Panelized": "Volumetric + panels",
         "Panelized-Only": "Panelized only", "Likely Panelized - verify": "Likely panelized",
         "Unknown": "Unknown"}
SEG = {"SF-Only": "Single-family", "MF-Only": "Multifamily", "SF-and-MF": "SF + MF",
       "Mixed-Modular-and-MH": "SF (modular + HUD)", "MH-Only": "HUD only",
       "Commercial-Only": "Commercial only", "Unknown": "Unknown"}
CODE = {"IRC-Modular": "State code (IRC)", "HUD-Code": "HUD code",
        "IRC-Modular; HUD-Code": "IRC + HUD", "Unknown": "Unknown"}


def rows(fname, kind):
    df = pd.read_csv(DB / fname, dtype=str).fillna("")
    out = []
    for _, r in df.iterrows():
        name = r.get("Company Name", "")
        if not name or "(DUPLICATE" in name.upper():
            continue
        if r.get("US_Based", "") == "NO":
            continue
        closed = "(CLOSED)" in name.upper() or r.get("Active", "") == "NO"
        out.append({
            "id": r["row_id"], "kind": kind,
            "name": name.replace(" (CLOSED)", ""),
            "aka": r.get("Factory Name / Formerly Known As", ""),
            "street": r.get("Street Address", ""), "city": r.get("City", ""),
            "state": r.get("State", ""), "zip": r.get("Zip", ""),
            "web": r.get("Website", ""),
            "build": BUILD.get(r.get("Build_Method", ""), r.get("Build_Method", "")),
            "seg": SEG.get(r.get("Residential_Type", ""), r.get("Residential_Type", "")),
            "code": CODE.get(r.get("Regulatory_Basis", ""), r.get("Regulatory_Basis", "")),
            "active": "Closed" if closed else {"YES": "Active", "UNKNOWN": "Unknown"}.get(r.get("Active", ""), "Unknown"),
            "review": r.get("Row_Status", ""),
            "eligible": r.get("Survey_Eligible", ""),
            "source": r.get("Source", ""),
        })
    return out


def main():
    data = rows("manufacturers.csv", "Factory") + rows("candidates_to_verify.csv", "Candidate") \
        + rows("builders_deployers.csv", "Builder")
    log = pd.read_csv(DB / "change_log.csv", dtype=str)
    meta = {"updated": pd.read_csv(PROCESSED / "plants_modular.csv", dtype=str)["export_date"].max(),
            "edits": int(len(log))}
    html = TEMPLATE.read_text()
    payload = json.dumps({"rows": data, "meta": meta}, separators=(",", ":")).replace("</", "<\\/")
    html = html.replace("__DATA__", payload)
    dest = OUTPUT / "site"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(html)
    print(f"{len(data)} rows -> {dest / 'index.html'}")


if __name__ == "__main__":
    main()
