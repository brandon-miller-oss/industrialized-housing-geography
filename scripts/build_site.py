"""Build the public, read-only factory database web page (for GitHub Pages).

    python scripts/build_site.py            # -> output/site/index.html + map.html

Reads the committed, contact-free CSVs in data/processed/factory_db/ and writes ONE
self-contained HTML file with the data embedded. Nothing personal goes in: no emails,
phone numbers, contact names, verification notes or outreach status.
"""
import json
import sys
from pathlib import Path

import re
from collections import defaultdict

import pandas as pd
import zipcodes

sys.path.insert(0, str(Path(__file__).resolve().parent))
from albers import project  # noqa: E402
from common import OUTPUT, PROCESSED, ROOT  # noqa: E402

DB = PROCESSED / "factory_db"
TEMPLATE = Path(__file__).resolve().parent / "site_template.html"
MAP_TEMPLATE = Path(__file__).resolve().parent / "map_template.html"
MAP = ROOT / "data" / "reference" / "us_map_albers.json"

_CITY = None


def locate(zip_code, city, state):
    """Map position (x, y on the 975x610 Albers USA map) from the ZIP, else the city's ZIP centroid."""
    global _CITY
    z = re.sub(r"\D", "", str(zip_code))[:5]
    ll = None
    if len(z) >= 4:
        m = zipcodes.matching(z.zfill(5))
        if m:
            ll = (float(m[0]["lat"]), float(m[0]["long"]))
    if ll is None and city and state:
        if _CITY is None:
            _CITY = defaultdict(list)
            for row in zipcodes.list_all():
                _CITY[(row["city"].upper(), row["state"])].append((float(row["lat"]), float(row["long"])))
        pts = _CITY.get((city.strip().upper(), state.strip()))
        if pts:
            ll = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    xy = project(*ll) if ll else None
    return [round(xy[0], 1), round(xy[1], 1)] if xy else None

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
            "xy": locate(r.get("Zip", ""), r.get("City", ""), r.get("State", "")),
        })
    return out


def main():
    data = rows("manufacturers.csv", "Factory") + rows("candidates_to_verify.csv", "Candidate") \
        + rows("builders_deployers.csv", "Builder")
    log = pd.read_csv(DB / "change_log.csv", dtype=str)
    meta = {"updated": pd.read_csv(PROCESSED / "plants_modular.csv", dtype=str)["export_date"].max(),
            "edits": int(len(log))}
    dest = OUTPUT / "site"
    dest.mkdir(parents=True, exist_ok=True)

    def embed(template, obj):
        payload = json.dumps(obj, separators=(",", ":")).replace("</", "<\\/")
        return template.read_text().replace("__DATA__", payload)

    # index.html: the searchable database (no map)
    table = [{k: v for k, v in d.items() if k != "xy"} for d in data]
    (dest / "index.html").write_text(embed(TEMPLATE, {"rows": table, "meta": meta}))

    # map.html: survey-eligible, active factories only, with SF / MF layers
    usmap = json.loads(MAP.read_text())
    eligible = [d for d in data if d["kind"] == "Factory" and d["eligible"] == "Eligible" and d["active"] != "Closed"]
    (dest / "map.html").write_text(embed(MAP_TEMPLATE, {"rows": eligible, "meta": meta,
                                                        "map": {"land": usmap["land"], "borders": usmap["borders"]}}))
    print(f"map.html: {len(eligible)} eligible factories ({sum(1 for d in eligible if d['xy'])} placed)")
    print(f"index.html: {len(data)} rows -> {dest}")


if __name__ == "__main__":
    main()
