"""Pull County Business Patterns establishment counts for factory-built NAICS codes.

    python scripts/fetch_cbp.py --year 2023

Codes: 321992 Prefabricated wood building manufacturing (modular/panelized),
       321991 Manufactured home (mobile home) manufacturing,
       332311 Prefabricated metal building manufacturing (optional, via --naics).
State-level counts are a completeness benchmark for the factory database
(see scripts/completeness_check.py). CBP counts establishments, not product
lines, and includes non-residential producers, so treat gaps as leads, not errors.
"""
import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROCESSED  # noqa: E402

DEFAULT_NAICS = ["321992", "321991"]


def transform(payload, naics_var, year):
    header, *rows = payload
    df = pd.DataFrame(rows, columns=header)
    return pd.DataFrame({
        "state_fips": df["state"].str.zfill(2),
        "naics_code": df[naics_var],
        "year": year,
        "establishments": pd.to_numeric(df["ESTAB"], errors="coerce"),
        "employees": pd.to_numeric(df["EMP"], errors="coerce"),  # 0 can mean suppressed - see EMP_N flag
        "source_id": "SRC25",
    })


def fetch(year, naics):
    import requests
    key = os.environ.get("CENSUS_API_KEY")
    # CBP has used NAICS2017 and NAICS2022 variable names in different vintages; try both.
    for var in ("NAICS2022", "NAICS2017"):
        frames = []
        for code in naics:
            params = {"get": f"ESTAB,EMP,{var}", "for": "state:*", var: code}
            if key:
                params["key"] = key
            r = requests.get(f"https://api.census.gov/data/{year}/cbp", params=params, timeout=60)
            if r.status_code != 200:
                break
            frames.append(transform(r.json(), var, year))
        else:
            return pd.concat(frames, ignore_index=True)
    raise SystemExit(f"CBP {year} request failed for NAICS2022 and NAICS2017: {r.status_code} {r.text[:200]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, default=2023)
    ap.add_argument("--naics", nargs="+", default=DEFAULT_NAICS)
    a = ap.parse_args()
    out = fetch(a.year, a.naics)
    path = PROCESSED / f"cbp_establishments_{a.year}.csv"
    out.to_csv(path, index=False)
    print(f"Wrote {len(out)} rows -> {path}")
    print(out.groupby("naics_code")["establishments"].sum().to_string())


if __name__ == "__main__":
    main()
