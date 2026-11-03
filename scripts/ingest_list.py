"""Merge an outside factory list into the master modular factory table.

Works for any list with at least a company name and a state:
  - the Housing Innovation Alliance (HIA) database export     --kind hia
  - a state approved-manufacturer list (e.g., New York)        --kind state_list
  - an industry member directory (MBI, etc.)                   --kind directory
  - the team's existing factory spreadsheet (first import)     --kind directory

Each row is matched to data/processed/plants_modular.csv on normalized name +
plant state (+ city as a tiebreaker):
  score >= 0.92 and same state          -> matched (fills hia_id / approvals)
  0.75 <= score < 0.92 and same state   -> review  (added, flagged with the candidate)
  otherwise                             -> new     (added as a new plant)

Nothing is deleted. Review rows are written to output/review_<kind>_<date>.csv
so a person can confirm or merge them.

Examples:
  python scripts/ingest_list.py data/raw/hia_export.csv --kind hia \
      --name-col "Company" --state-col "State" --city-col "City" --id-col "HIA ID"
  python scripts/ingest_list.py data/raw/ny_certified_entities.csv --kind state_list \
      --approving-state NY --program "NY Manufactured Housing Program" \
      --name-col "Business Name" --state-col "State" --city-col "City" --list-date 2026-11-02
"""
import argparse
import datetime as dt
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUTPUT, PROCESSED, state_lookup  # noqa: E402

MASTER = PROCESSED / "plants_modular.csv"
APPROVALS = PROCESSED / "state_approvals.csv"
MASTER_COLS = ["plant_id", "producer_id", "plant_name", "city", "state_abbr", "code_basis",
               "product_type", "market_segment", "residential", "naics_code", "website", "hia_id",
               "match_status", "in_survey_frame", "found_via", "status", "source_id",
               "verified_date", "notes"]
APPROVAL_COLS = ["plant_id", "approving_state", "program", "listed_name", "listed_city",
                 "listed_state", "approval_status", "list_date", "source_id"]
SUFFIXES = r"\b(inc|incorporated|llc|l\.l\.c|ltd|co|corp|corporation|company|lp|llp|pllc|the)\b"
GENERIC = r"\b(homes?|modular|housing|buildings?|building systems|systems|manufacturing|mfg|industries|structures|builders?|of|plant)\b"
MATCH, REVIEW = 0.92, 0.75


def norm_name(s):
    s = str(s).lower().replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(SUFFIXES, " ", s)
    return re.sub(r"\s+", " ", s).strip()


def core_name(s):
    """Name with generic industry words removed, for comparison ('Ritz-Craft Homes' -> 'ritz craft')."""
    n = norm_name(s)
    c = re.sub(r"\s+", " ", re.sub(GENERIC, " ", n)).strip()
    return c or n


def norm_state(s, lookup):
    st = lookup.get(str(s).strip().upper())
    return st["state_abbr"] if st else str(s).strip().upper()[:2]


def slug(name, state, taken):
    base = re.sub(r"[^a-z0-9]+", "-", norm_name(name)).strip("-")[:40] + f"-{state.lower()}"
    pid, i = base, 2
    while pid in taken:
        pid, i = f"{base}-{i}", i + 1
    taken.add(pid)
    return pid


def best_match(name, state, city, master):
    """Return (plant_id, score) of the best same-state candidate, or (None, 0)."""
    cands = master[master.state_abbr == state]
    if cands.empty:
        return None, 0.0
    n = core_name(name)
    best, score = None, 0.0
    for _, r in cands.iterrows():
        other = core_name(r.plant_name)
        s = SequenceMatcher(None, n, other).ratio()
        # Containment ("champion" vs "champion york") - strong but not automatic
        if n and other and (n in other or other in n):
            s = max(s, 0.9)
        if city and str(r.city).strip().lower() == str(city).strip().lower():
            s = min(1.0, s + 0.05)
        if s > score:
            best, score = r.plant_id, s
    return best, score


def load_master():
    if MASTER.exists():
        m = pd.read_csv(MASTER, dtype=str, keep_default_na=False)
        for c in MASTER_COLS:
            if c not in m.columns:
                m[c] = ""
        return m[MASTER_COLS]
    return pd.DataFrame(columns=MASTER_COLS, dtype=str)


def ingest(df, kind, name_col, state_col, city_col=None, id_col=None, approving_state=None,
           program=None, list_date="", source_id="", master=None):
    lookup = state_lookup()
    master = load_master() if master is None else master.copy()
    taken = set(master.plant_id)
    approvals, review, added = [], [], []
    stats = {"matched": 0, "review": 0, "new": 0}
    for _, row in df.iterrows():
        name = str(row[name_col]).strip()
        if not name or name.lower() == "nan":
            continue
        state = norm_state(row[state_col], lookup)
        city = str(row[city_col]).strip().title() if city_col else ""
        pid, score = best_match(name, state, city, master)
        if pid and score >= MATCH:
            status = "matched"
        else:
            status = "review" if pid and score >= REVIEW else "new"
            new_id = slug(name, state, taken)
            note = f"possible duplicate of {pid} (score {score:.2f})" if status == "review" else ""
            rec = {c: "" for c in MASTER_COLS}
            rec.update(plant_id=new_id, plant_name=name, city=city, state_abbr=state,
                       code_basis="STATE_MODULAR", match_status=status, found_via=kind,
                       status="active", source_id=source_id, notes=note, residential="1",
                       market_segment="UNKNOWN", in_survey_frame="0")
            master = pd.concat([master, pd.DataFrame([rec])], ignore_index=True)
            added.append(rec)
            if status == "review":
                review.append({"new_plant_id": new_id, "listed_name": name, "state": state, "city": city,
                               "candidate_plant_id": pid, "score": round(score, 3)})
            pid = new_id
        stats[status] += 1
        if kind == "hia" and id_col:
            master.loc[master.plant_id == pid, "hia_id"] = str(row[id_col])
        if kind == "state_list":
            approvals.append({"plant_id": pid, "approving_state": approving_state, "program": program,
                              "listed_name": name, "listed_city": city, "listed_state": state,
                              "approval_status": "active", "list_date": list_date,
                              "source_id": source_id})
    return master, pd.DataFrame(approvals, columns=APPROVAL_COLS), pd.DataFrame(review), stats


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="CSV or Excel file")
    ap.add_argument("--kind", choices=["hia", "state_list", "directory"], required=True)
    ap.add_argument("--name-col", required=True)
    ap.add_argument("--state-col", required=True)
    ap.add_argument("--city-col")
    ap.add_argument("--id-col", help="HIA record ID column (kind=hia)")
    ap.add_argument("--approving-state", help="2-letter state that published the list (kind=state_list)")
    ap.add_argument("--program", default="")
    ap.add_argument("--list-date", default=dt.date.today().isoformat())
    ap.add_argument("--source-id", default="")
    a = ap.parse_args()
    if a.kind == "state_list" and not a.approving_state:
        sys.exit("--approving-state is required for state lists")
    p = Path(a.path)
    df = pd.read_excel(p, dtype=str) if p.suffix in (".xlsx", ".xls") else pd.read_csv(p, dtype=str)
    master, approvals, review, stats = ingest(df, a.kind, a.name_col, a.state_col, a.city_col, a.id_col,
                                              a.approving_state, a.program, a.list_date, a.source_id)
    master.to_csv(MASTER, index=False)
    if not approvals.empty:
        old = pd.read_csv(APPROVALS, dtype=str) if APPROVALS.exists() else pd.DataFrame(columns=APPROVAL_COLS)
        pd.concat([old, approvals]).drop_duplicates(["plant_id", "approving_state", "program"], keep="last") \
            .to_csv(APPROVALS, index=False)
    print(f"{p.name}: {stats}  -> master now {len(master)} plants")
    if not review.empty:
        OUTPUT.mkdir(exist_ok=True)
        rp = OUTPUT / f"review_{a.kind}_{dt.date.today():%Y%m%d}.csv"
        review.to_csv(rp, index=False)
        print(f"{len(review)} possible duplicates to check -> {rp}")


if __name__ == "__main__":
    main()
