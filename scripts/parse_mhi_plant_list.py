"""Parse the MHI HUD-Code Plant List PDF into data/processed/plants_mhi.csv.

The PDF has columns: MFG # | Plant Code | Manufacturer | CITY | STATE, plus a
"State / Number of Plants" summary table printed to the right of the first rows.
Columns are found from the x-position of the header words, so the side table is
ignored automatically.

Usage:
    python scripts/parse_mhi_plant_list.py data/raw/Plant-List-01_31_26-1.pdf --snapshot 2026-01-31
"""
import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROCESSED  # noqa: E402

PLANT_CODE = re.compile(r"^[A-Z]{3,5}\d{2}$")
OUT_FIELDS = ["plant_id", "mfg_number", "plant_name", "producer_guess", "city",
              "state_abbr", "code_basis", "product_type", "certifications",
              "status", "source_id", "snapshot_date"]


def _lines(words, tol=3):
    """Group pdfplumber words into lines by vertical position."""
    rows = defaultdict(list)
    for w in words:
        key = round(w["top"] / tol)
        rows[key].append(w)
    return [sorted(v, key=lambda w: w["x0"]) for _, v in sorted(rows.items())]


def find_columns(words):
    """Return x boundaries {code, mfr, city, state, side} from the header row."""
    cols = {}
    for line in _lines(words):
        texts = [w["text"] for w in line]
        upper = [t.upper() for t in texts]
        if "MANUFACTURER" in upper and "CITY" in upper:
            for w in line:
                t = w["text"].upper()
                if t == "PLANT" and "code" not in cols:
                    cols["code"] = w["x0"]
                elif t == "MANUFACTURER":
                    cols["mfr"] = w["x0"]
                elif t == "CITY":
                    cols["city"] = w["x0"]
                elif t == "STATE" and "state" not in cols:
                    cols["state"] = w["x0"]
                elif t == "STATE" and "state" in cols:
                    cols["side"] = w["x0"]  # summary table header
            break
    if not {"code", "mfr", "city", "state"} <= cols.keys():
        return None
    cols.setdefault("side", float("inf"))
    return cols


def producer_guess(name):
    """'CAVCO-GOODYEAR' -> 'CAVCO'; 'CHAMPION #157' -> 'CHAMPION'. Needs manual review."""
    return re.split(r"\s*[-#(]\s*", name, maxsplit=1)[0].strip().title()


def parse(pdf_path, snapshot=""):
    rows, cols = [], None
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
            cols = find_columns(words) or cols  # header may only be on page 1
            if cols is None:
                continue
            slack = 2  # points of tolerance left of each header
            for line in _lines(words):
                line = [w for w in line if w["x0"] < cols["side"] - slack]
                if len(line) < 4 or not line[0]["text"].isdigit():
                    continue
                if not PLANT_CODE.match(line[1]["text"]):
                    continue
                parts = defaultdict(list)
                for w in line[2:]:
                    x = w["x0"]
                    if x >= cols["state"] - slack:
                        parts["state"].append(w["text"])
                    elif x >= cols["city"] - slack:
                        parts["city"].append(w["text"])
                    else:
                        parts["mfr"].append(w["text"])
                name = " ".join(parts["mfr"])
                rows.append({
                    "plant_id": line[1]["text"],
                    "mfg_number": int(line[0]["text"]),
                    "plant_name": name,
                    "producer_guess": producer_guess(name),
                    "city": " ".join(parts["city"]).title(),
                    "state_abbr": " ".join(parts["state"]).upper(),
                    "code_basis": "HUD_CODE",
                    "product_type": "manufactured",
                    "certifications": "HUD",
                    "status": "active",
                    "source_id": "SRC05",
                    "snapshot_date": snapshot,
                })
    if cols is None:
        raise ValueError("Could not find the header row (Manufacturer / CITY / STATE).")
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--snapshot", default="", help="Date of the plant list, e.g. 2026-01-31")
    ap.add_argument("--out", default=str(PROCESSED / "plants_mhi.csv"))
    a = ap.parse_args()
    rows = parse(a.pdf, a.snapshot)
    bad = [r for r in rows if len(r["state_abbr"]) != 2 or not r["city"]]
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} plants to {a.out}")
    if bad:
        print(f"WARNING: {len(bad)} rows need review (missing city or bad state):")
        for r in bad[:20]:
            print("  ", r["plant_id"], r["plant_name"], "|", r["city"], "|", r["state_abbr"])
    print("Cross-check the total against the PDF's 'Total' line (147 in the 1/31/2026 list).")


if __name__ == "__main__":
    main()
