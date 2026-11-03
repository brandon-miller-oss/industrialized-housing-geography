"""Pull ACS 5-year housing and income indicators from the Census API.

Usage:
    python scripts/fetch_acs.py --year 2023 --level state
    python scripts/fetch_acs.py --year 2023 --level county
    python scripts/fetch_acs.py --year 2023 --level tract --state 08     # Colorado tracts

A free API key (https://api.census.gov/data/key_signup.html) is optional but
recommended; set it as the CENSUS_API_KEY environment variable.
"""
import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROCESSED  # noqa: E402

VARS = {
    "B01003_001E": "total_population",
    "B25001_001E": "total_housing_units",
    "B25024_001E": "units_in_structure_total",
    "B25024_010E": "mobile_homes",
    "B19013_001E": "median_hh_income",
    "B25077_001E": "median_home_value",
    "B25070_001E": "renter_households",
    "B25070_007E": "rb_30_35",
    "B25070_008E": "rb_35_40",
    "B25070_009E": "rb_40_50",
    "B25070_010E": "rb_50_plus",
    "B25070_011E": "rb_not_computed",
}


def build_url(year, level, state=None):
    base = f"https://api.census.gov/data/{year}/acs/acs5"
    params = {"get": "NAME," + ",".join(VARS)}
    if level == "state":
        params["for"] = "state:*"
    elif level == "county":
        params["for"] = "county:*"
        params["in"] = f"state:{state}" if state else "state:*"
    elif level == "tract":
        if not state:
            raise SystemExit("--state is required for tracts")
        params["for"] = "tract:*"
        params["in"] = f"state:{state} county:*"
    key = os.environ.get("CENSUS_API_KEY")
    if key:
        params["key"] = key
    return base, params


def transform(payload, level, year):
    """Census API JSON (list of lists) -> demographics table rows."""
    header, *rows = payload
    df = pd.DataFrame(rows, columns=header)
    for v in VARS:
        df[v] = pd.to_numeric(df[v], errors="coerce")
        df.loc[df[v] < 0, v] = pd.NA  # Census sentinels like -666666666
    df = df.rename(columns=VARS)
    geo_cols = {"state": ["state"], "county": ["state", "county"], "tract": ["state", "county", "tract"]}[level]
    df["geoid"] = df[geo_cols].astype(str).agg("".join, axis=1)
    burden = df[["rb_30_35", "rb_35_40", "rb_40_50", "rb_50_plus"]].sum(axis=1, min_count=1)
    computed = df["renter_households"] - df["rb_not_computed"]
    out = pd.DataFrame({
        "geoid": df["geoid"],
        "geo_level": level,
        "name": df["NAME"],
        "acs_vintage": year,
        "total_population": df["total_population"],
        "total_housing_units": df["total_housing_units"],
        "mobile_homes": df["mobile_homes"],
        "mobile_home_share": (df["mobile_homes"] / df["units_in_structure_total"]).round(4),
        "median_hh_income": df["median_hh_income"],
        "median_home_value": df["median_home_value"],
        "renter_households": df["renter_households"],
        "renter_burden_30plus": burden,
        "renter_burden_share": (burden / computed).round(4),  # share of renters with computed burden
        "source_id": "SRC14",
    })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int, default=2023)
    ap.add_argument("--level", choices=["state", "county", "tract"], default="state")
    ap.add_argument("--state", help="2-digit state FIPS (e.g. 08 for Colorado)")
    a = ap.parse_args()
    import requests
    base, params = build_url(a.year, a.level, a.state)
    r = requests.get(base, params=params, timeout=120)
    r.raise_for_status()
    out = transform(r.json(), a.level, a.year)
    suffix = f"_{a.state}" if a.state else ""
    path = PROCESSED / f"acs_{a.level}{suffix}_{a.year}.csv"
    out.to_csv(path, index=False)
    print(f"Wrote {len(out)} rows -> {path}")


if __name__ == "__main__":
    main()
