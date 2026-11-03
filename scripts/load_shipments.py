"""Load Census/IBTS 'shipments of new manufactured homes by state' Excel into tidy CSV.

Download the annual-by-state file from
https://www.census.gov/data/tables/time-series/econ/mhs/shipments.html
into data/raw/, then run:

    python scripts/load_shipments.py data/raw/<file>.xlsx

The parser looks for a header row of years and rows labelled with state names,
so it tolerates title rows, notes and footers. Check the printed summary
against the source table.
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROCESSED, state_lookup  # noqa: E402

YEAR = re.compile(r"^(19[5-9]\d|20[0-4]\d)(\.0)?$")


def _clean_label(v):
    s = re.sub(r"[\d\\/*]+$", "", str(v)).strip()  # strip footnote markers like 'Texas 1/'
    return re.sub(r"\s+", " ", s).upper()


def parse_sheet(df, states):
    """Return tidy rows (state_fips, year, units) from one raw sheet (header=None)."""
    year_row, year_cols = None, {}
    for i in range(min(len(df), 40)):
        cols = {j: int(float(v)) for j, v in df.iloc[i].items() if YEAR.match(str(v).strip())}
        if len(cols) >= 2:
            year_row, year_cols = i, cols
            break
    if year_row is None:
        return []
    out = []
    for i in range(year_row + 1, len(df)):
        row = df.iloc[i]
        label = next((v for v in row.tolist() if isinstance(v, str) and v.strip()), None)
        if label is None:
            continue
        st = states.get(_clean_label(label))
        if st is None:
            continue
        for j, yr in year_cols.items():
            v = row.iloc[j] if j < len(row) else None
            try:
                units = int(round(float(str(v).replace(",", ""))))
            except (TypeError, ValueError):
                continue  # '(S)', 'NA', blanks
            out.append({"state_fips": st["state_fips"], "year": yr, "units": units})
    return out


def load(path):
    states = state_lookup()
    xl = pd.read_excel(path, sheet_name=None, header=None)
    rows = []
    for name, df in xl.items():
        got = parse_sheet(df, states)
        if got:
            print(f"  sheet '{name}': {len(got)} state-year values")
        rows += got
    tidy = pd.DataFrame(rows).drop_duplicates(["state_fips", "year"])
    tidy["code_basis"] = "HUD_CODE"
    tidy["floors"] = pd.NA
    tidy["source_id"] = "SRC01"
    return tidy


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xlsx")
    ap.add_argument("--out", default=str(PROCESSED / "shipments_state_year.csv"))
    a = ap.parse_args()
    tidy = load(a.xlsx)
    if tidy.empty:
        sys.exit("No state rows found - open the file and check its layout.")
    tidy.to_csv(a.out, index=False)
    yrs = sorted(tidy["year"].unique())
    print(f"Wrote {len(tidy)} rows, {tidy['state_fips'].nunique()} states, {yrs[0]}-{yrs[-1]} -> {a.out}")
    co = tidy[tidy.state_fips == "08"].sort_values("year").tail(5)
    print("Colorado, last 5 years:\n", co[["year", "units"]].to_string(index=False))


if __name__ == "__main__":
    main()
