"""Export the survey mailing list (sampling frame) for the survey consultant.

    python scripts/export_survey_frame.py

Joins plants flagged in_survey_frame=1 with contacts in data/private/contacts.csv.
Output goes to output/survey_frame_<date>.csv (git-ignored; contains PII).
Plants in the frame with no email are listed so contacts can be found.
"""
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUTPUT, PROCESSED, ROOT  # noqa: E402

PRIVATE = ROOT / "data" / "private"
FIELDS = ["plant_id", "plant_name", "city", "state_abbr", "market_segment", "product_type",
          "website", "contact_name", "title", "email", "phone"]


def build_frame(master, contacts):
    frame = master[master.in_survey_frame.fillna("0").astype(str) == "1"]
    if contacts is not None and not contacts.empty:
        prim = contacts.sort_values("is_primary", ascending=False).drop_duplicates("plant_id")
        frame = frame.merge(prim, on="plant_id", how="left")
    for c in FIELDS:
        if c not in frame.columns:
            frame[c] = ""
    frame = frame[FIELDS].fillna("")
    missing = frame[frame.email.str.strip() == ""]
    return frame, missing


def main():
    master = pd.read_csv(PROCESSED / "plants_modular.csv", dtype=str)
    cpath = PRIVATE / "contacts.csv"
    contacts = pd.read_csv(cpath, dtype=str) if cpath.exists() else None
    frame, missing = build_frame(master, contacts)
    OUTPUT.mkdir(exist_ok=True)
    path = OUTPUT / f"survey_frame_{dt.date.today():%Y%m%d}.csv"
    frame.to_csv(path, index=False)
    print(f"{len(frame)} plants in frame, {len(frame) - len(missing)} with email -> {path}")
    if len(missing):
        print(f"{len(missing)} need a contact:")
        for _, r in missing.head(25).iterrows():
            print(f"   {r.plant_id}: {r.plant_name} ({r.city}, {r.state_abbr})")


if __name__ == "__main__":
    main()
