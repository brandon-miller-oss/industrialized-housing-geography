"""Build the project database from reference, seed and processed CSVs.

Outputs:
    output/ihg.sqlite  - relational database (schema/schema.sql)
    output/ihg.gpkg    - GeoPackage for ArcGIS Pro / QGIS:
                         plants (points), projects (points), state_summary (table,
                         or polygons if --states-shp is given)

Usage:
    python scripts/build_db.py
    python scripts/build_db.py --states-shp data/raw/cb_2023_us_state_20m.zip
"""
import argparse
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUTPUT, PROCESSED, REFERENCE, ROOT, SEED  # noqa: E402

# table -> CSV files that feed it (globs, in load order)
FEEDS = {
    "sources": [REFERENCE / "source_inventory.csv"],
    "states": [REFERENCE / "states.csv"],
    "producers": [SEED / "producers.csv", PROCESSED / "producers*.csv"],
    "plants": [SEED / "plants.csv", PROCESSED / "plants*.csv"],
    "shipments_state_year": [PROCESSED / "shipments_state_year*.csv"],
    "producer_distribution": [SEED / "producer_distribution.csv", PROCESSED / "producer_distribution*.csv"],
    "projects": [SEED / "projects.csv", PROCESSED / "projects*.csv"],
    "policies": [SEED / "policies.csv", PROCESSED / "policies*.csv"],
    "demographics": [PROCESSED / "acs_*.csv"],
    "cost_schedule": [SEED / "cost_schedule.csv", PROCESSED / "cost_schedule*.csv"],
    "hazards": [PROCESSED / "hazards_*.csv"],
}


def _files(patterns):
    seen = []
    for p in patterns:
        for f in sorted(p.parent.glob(p.name)):
            if f not in seen:
                seen.append(f)
    return seen


def load_table(con, table, files):
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
    n = 0
    for f in files:
        df = pd.read_csv(f, dtype=str, keep_default_na=False).replace({"": None})
        keep = [c for c in df.columns if c in cols]
        if not keep:
            continue
        df = df[keep]
        ph = ",".join("?" * len(keep))
        con.executemany(f"INSERT OR REPLACE INTO {table} ({','.join(keep)}) VALUES ({ph})",
                        df.itertuples(index=False, name=None))
        n += len(df)
    return n


def state_summary(con):
    q = """
    SELECT s.state_fips, s.state_abbr, s.state_name, s.region, s.division, s.mountain_west,
      (SELECT COUNT(*) FROM plants p WHERE p.state_abbr = s.state_abbr AND p.status='active') AS plants_active,
      (SELECT COUNT(*) FROM plants p WHERE p.state_abbr = s.state_abbr AND p.code_basis='HUD_CODE'
              AND p.status='active') AS plants_hud_code,
      (SELECT MAX(year) FROM shipments_state_year x WHERE x.state_fips = s.state_fips) AS ship_latest_year,
      (SELECT units FROM shipments_state_year x WHERE x.state_fips = s.state_fips
              ORDER BY year DESC LIMIT 1) AS ship_latest_units,
      (SELECT COUNT(*) FROM policies y WHERE y.state_abbr = s.state_abbr) AS policies_tracked,
      d.mobile_homes, d.mobile_home_share, d.median_hh_income, d.median_home_value,
      d.renter_burden_share, d.acs_vintage
    FROM states s
    LEFT JOIN (SELECT * FROM demographics WHERE geo_level='state'
               AND acs_vintage = (SELECT MAX(acs_vintage) FROM demographics WHERE geo_level='state')) d
      ON d.geoid = s.state_fips
    ORDER BY s.state_fips
    """
    return pd.read_sql(q, con)


def write_gpkg(con, path, states_shp=None):
    import geopandas as gpd
    if path.exists():
        path.unlink()
    for table in ("plants", "projects"):
        df = pd.read_sql(f"SELECT * FROM {table} WHERE lat IS NOT NULL AND lon IS NOT NULL", con)
        if df.empty:
            print(f"  {table}: no geocoded rows yet - layer skipped")
            continue
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon.astype(float), df.lat.astype(float)),
                               crs="EPSG:4326")
        gdf.to_file(path, layer=table, driver="GPKG")
        print(f"  {table}: {len(gdf)} points")
    summ = state_summary(con)
    if states_shp:
        shp = gpd.read_file(states_shp)
        geo = shp[["STATEFP", "geometry"]].rename(columns={"STATEFP": "state_fips"})
        gdf = geo.merge(summ, on="state_fips", how="inner").to_crs("EPSG:4326")
        gdf.to_file(path, layer="state_summary", driver="GPKG")
        print(f"  state_summary: {len(gdf)} polygons")
    else:
        # Attribute-only layer; join to state boundaries in GIS on state_fips
        gpd.GeoDataFrame(summ, geometry=[None] * len(summ), crs="EPSG:4326").to_file(
            path, layer="state_summary", driver="GPKG")
        print(f"  state_summary: {len(summ)} rows (no geometry - join on state_fips)")
    return summ


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--states-shp", help="Census cartographic boundary states file (zip or shp)")
    ap.add_argument("--out-dir", default=str(OUTPUT))
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    db = out / "ihg.sqlite"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.executescript((ROOT / "schema" / "schema.sql").read_text())
    print(f"Building {db}")
    for table, pats in FEEDS.items():
        n = load_table(con, table, _files(pats))
        print(f"  {table}: {n} rows")
    con.commit()
    bad = con.execute("PRAGMA foreign_key_check").fetchall()
    if bad:
        print(f"WARNING: {len(bad)} foreign-key problems, e.g. {bad[:5]}")
    print(f"Building {out / 'ihg.gpkg'}")
    write_gpkg(con, out / "ihg.gpkg", a.states_shp)
    con.close()


if __name__ == "__main__":
    main()
