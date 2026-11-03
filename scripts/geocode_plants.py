"""Geocode plants to place centroids using the Census Gazetteer places file.

City-level points are accurate enough for state/regional maps and distance
analysis. Replace with address geocodes for site-level work.

Usage:
    # download once (or let the script do it):
    #   https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_place_national.zip
    python scripts/geocode_plants.py data/processed/plants_mhi.csv --gazetteer data/raw/2024_Gaz_place_national.zip
"""
import argparse
import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RAW  # noqa: E402

GAZ_URL = ("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
           "2024_Gazetteer/2024_Gaz_place_national.zip")
LSAD = re.compile(r"\s+(city and borough|consolidated government.*|metropolitan government.*|"
                  r"unified government.*|urban county|city|town|village|borough|CDP|municipality|township)$",
                  re.IGNORECASE)


def norm_city(s):
    s = str(s).upper().strip()
    s = re.sub(r"\bST\.?\s", "SAINT ", s)
    s = re.sub(r"\bFT\.?\s", "FORT ", s)
    s = re.sub(r"\bMT\.?\s", "MOUNT ", s)
    return re.sub(r"[^A-Z ]", "", s).strip()


def read_gazetteer(path):
    path = Path(path)
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            name = [n for n in z.namelist() if n.endswith(".txt")][0]
            data = z.read(name).decode("latin-1")
        df = pd.read_csv(io.StringIO(data), sep="\t", dtype=str)
    else:
        df = pd.read_csv(path, sep="\t", dtype=str, encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    df["city_key"] = df["NAME"].str.replace(LSAD, "", regex=True).map(norm_city)
    df["lat"] = df["INTPTLAT"].astype(float)
    df["lon"] = df["INTPTLONG"].astype(float)
    # Prefer incorporated places over CDPs when names collide
    df["is_cdp"] = df["NAME"].str.endswith("CDP")
    df = df.sort_values("is_cdp").drop_duplicates(["USPS", "city_key"])
    return df[["USPS", "city_key", "GEOID", "lat", "lon"]]


def geocode(plants, gaz):
    p = plants.copy()
    p["city_key"] = p["city"].map(norm_city)
    out = p.merge(gaz, how="left", left_on=["state_abbr", "city_key"], right_on=["USPS", "city_key"])
    out["geocode_method"] = out["lat"].notna().map({True: "gazetteer_place", False: ""})
    out = out.rename(columns={"GEOID": "place_geoid"}).drop(columns=["USPS", "city_key"])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plants_csv")
    ap.add_argument("--gazetteer", default=str(RAW / "2024_Gaz_place_national.zip"))
    a = ap.parse_args()
    gpath = Path(a.gazetteer)
    if not gpath.exists():
        import requests
        print(f"Downloading {GAZ_URL}")
        r = requests.get(GAZ_URL, timeout=120)
        r.raise_for_status()
        gpath.write_bytes(r.content)
    plants = pd.read_csv(a.plants_csv, dtype=str)
    out = geocode(plants, read_gazetteer(gpath))
    out.to_csv(a.plants_csv, index=False)
    miss = out[out["lat"].isna()]
    print(f"Geocoded {len(out) - len(miss)}/{len(out)} plants -> {a.plants_csv}")
    if len(miss):
        print("Unmatched (add lat/lon by hand, geocode_method=manual):")
        for _, r in miss.iterrows():
            print(f"   {r['plant_id']}: {r['city']}, {r['state_abbr']}")


if __name__ == "__main__":
    main()
